#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
posts/*.lsg 복구 스크립트 — Blogger 라이브 피드에서 발행 본문을 회수한다.

C:\\lifeinfo\\posts 가 사라졌을 때 사용한다. 발행된 글의 본문 HTML은 Blogger
서버에 그대로 살아 있으므로, 피드에서 content를 받아 .lsg 파일로 되살릴 수 있다.
lifeinfo_db.txt(코드↔URL 매핑)와 대조해 파일명을 코드 기준으로 정한다.

사용법 (C:\\lifeinfo 에서):
    python restore\\recover_posts_from_blogger.py --db lifeinfo_db.txt --out posts
    python restore\\recover_posts_from_blogger.py --dry-run          # 받아만 보고 안 씀
    python restore\\recover_posts_from_blogger.py --out posts_recovered --force

기본은 안전 모드다. 이미 있는 파일은 건너뛴다(--force 로 덮어쓰기).
자격증명이 필요 없다 — 공개 피드만 읽는다.
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BLOG = "https://lifeinfo8975.blogspot.com"
FEED = BLOG + "/feeds/posts/default"
PAGE = 150  # 피드 1회 최대치. Blogger 상한은 500이지만 150이 안정적이다.


def fetch_feed_page(start_index):
    """피드 한 페이지를 dict 로 반환."""
    qs = urllib.parse.urlencode({
        "alt": "json",
        "max-results": PAGE,
        "start-index": start_index,
    })
    url = "%s?%s" % (FEED, qs)
    req = urllib.request.Request(url, headers={"User-Agent": "lifeinfo-restore/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_all_entries():
    """발행 글 전체를 리스트로 회수."""
    entries = []
    start = 1
    total = None
    while True:
        feed = fetch_feed_page(start)["feed"]
        if total is None:
            total = int(feed.get("openSearch$totalResults", {}).get("$t", 0))
            print("[feed] 발행 글 총 %d편" % total)
        batch = feed.get("entry", []) or []
        if not batch:
            break
        entries.extend(batch)
        print("[feed] %d/%d 수신" % (len(entries), total))
        if len(entries) >= total:
            break
        start += len(batch)
    return entries, total


def alt_link(entry):
    """엔트리의 공개 URL."""
    for ln in entry.get("link", []):
        if ln.get("rel") == "alternate" and ln.get("type") == "text/html":
            return ln.get("href", "")
    return ""


def norm(url):
    """DB URL 과 피드 URL 을 비교하기 위한 정규화 — 경로만 소문자로."""
    if not url:
        return ""
    try:
        p = urllib.parse.urlparse(url)
    except ValueError:
        return url.strip().lower()
    return p.path.rstrip("/").lower()


def safe_name(code, title):
    """파일명. 원래 규칙을 모르면 코드만 쓰는 게 가장 충돌이 없다."""
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", title or "").strip("_")[:40]
    return "%s_%s.lsg" % (code, slug) if slug else "%s.lsg" % code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="lifeinfo_db.txt", help="lifeinfo_db.txt 경로")
    ap.add_argument("--out", default="posts", help="복구 대상 폴더")
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 보고")
    ap.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    ap.add_argument("--code-only", action="store_true",
                    help="파일명을 <코드>.lsg 로만 (제목 슬러그 제외)")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit("[중단] DB 를 찾을 수 없다: %s\n  → GitHub 저장소에서 lifeinfo_db.txt 를 먼저 확보하라." % args.db)

    with open(args.db, encoding="utf-8") as f:
        db = json.load(f)
    posts = db.get("posts", [])
    by_url = {}
    for p in posts:
        key = norm(p.get("url"))
        if key:
            by_url[key] = p
    print("[db] %d편 (URL 매핑 %d건)" % (len(posts), len(by_url)))

    try:
        entries, total = fetch_all_entries()
    except Exception as e:
        sys.exit("[중단] 피드 수신 실패: %s\n  → 인터넷 연결 및 블로그 공개 상태를 확인하라." % e)

    if not args.dry_run:
        os.makedirs(args.out, exist_ok=True)

    wrote = skipped = unmatched = empty = 0
    unmatched_rows = []

    for e in entries:
        title = e.get("title", {}).get("$t", "")
        body = e.get("content", {}).get("$t", "")
        url = alt_link(e)
        rec = by_url.get(norm(url))

        if not body:
            empty += 1
            print("  [빈본문] %s" % (title or url))
            continue

        if rec is None:
            unmatched += 1
            unmatched_rows.append({"title": title, "url": url})
            print("  [DB없음] %s" % (title or url))
            continue

        code = rec.get("code", "UNKNOWN")
        name = "%s.lsg" % code if args.code_only else safe_name(code, rec.get("title") or title)
        path = os.path.join(args.out, name)

        if os.path.exists(path) and not args.force:
            skipped += 1
            continue

        if args.dry_run:
            wrote += 1
            print("  [예정] %s  (%d bytes)" % (name, len(body)))
            continue

        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        wrote += 1
        print("  [복구] %s  (%d bytes)" % (name, len(body)))

    # DB 에는 있는데 라이브에 없는 글 = 삭제됐거나 임시보관 상태
    live = {norm(alt_link(e)) for e in entries}
    ghosts = [p for p in posts if norm(p.get("url")) not in live]

    print("\n===== 복구 요약 =====")
    print("피드 수신     : %d편" % len(entries))
    print("복구/예정     : %d개" % wrote)
    print("이미 있어 건너뜀: %d개  (덮어쓰려면 --force)" % skipped)
    print("DB 매칭 실패  : %d개" % unmatched)
    print("본문 빈 글    : %d개" % empty)
    print("DB엔 있고 라이브엔 없음: %d개" % len(ghosts))
    for g in ghosts[:20]:
        print("   - %s %s" % (g.get("code"), g.get("title")))
    if len(ghosts) > 20:
        print("   ... 외 %d건" % (len(ghosts) - 20))

    if unmatched_rows and not args.dry_run:
        rp = os.path.join(args.out, "_unmatched.json")
        with open(rp, "w", encoding="utf-8") as f:
            json.dump(unmatched_rows, f, ensure_ascii=False, indent=1)
        print("\nDB 매칭 실패 목록 → %s" % rp)

    print("\n주의: 복구된 .lsg 는 '발행된 결과물'이다. 원래 로컬 파일에 있던")
    print("      주석·작업메모는 남아 있지 않고, 발행 후 Blogger 에디터가")
    print("      정규화한 마크업일 수 있다. 본문 내용 자체는 동일하다.")


if __name__ == "__main__":
    main()
