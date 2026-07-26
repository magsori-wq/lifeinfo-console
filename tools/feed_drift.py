#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라이브 피드 ↔ DB 드리프트 검사 (읽기 전용).

Blogger 에 실제로 발행된 글과 lifeinfo_db.txt 를 대조해 어긋난 것을 찾는다.
어떤 파일도 수정하지 않는다 — 보고만 한다.

찾아내는 것:
  1. 발행됐는데 DB 에 없는 글   → register_post 누락 (콘솔·색인에서 빠진 상태)
  2. DB 에는 있는데 라이브에 없는 글 → 삭제됐거나 임시보관으로 내려간 상태
  3. 제목이 서로 다른 글          → 발행 후 제목만 수정하고 DB 반영 안 함

⚠️ 이 스크립트는 Claude Code 웹 컨테이너에서는 동작하지 않는다.
   그 환경의 프록시가 blogspot.com 을 차단한다(실측: CONNECT 403).
   GitHub Actions 러너에는 그 제약이 없으므로 거기서 실행한다.

실행:
    python tools/feed_drift.py
    python tools/feed_drift.py --json

종료 코드: 0 = 드리프트 없음, 1 = 드리프트 발견, 2 = 피드 접근 실패
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = "https://lifeinfo8975.blogspot.com/feeds/posts/default"
PAGE = 150


def fetch_all():
    entries, start, total = [], 1, None
    while True:
        qs = urllib.parse.urlencode({"alt": "json", "max-results": PAGE, "start-index": start})
        req = urllib.request.Request("%s?%s" % (FEED, qs),
                                     headers={"User-Agent": "lifeinfo-feed-drift/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            feed = json.loads(r.read().decode("utf-8"))["feed"]
        if total is None:
            total = int(feed.get("openSearch$totalResults", {}).get("$t", 0))
        batch = feed.get("entry", []) or []
        if not batch:
            break
        entries.extend(batch)
        if len(entries) >= total:
            break
        start += len(batch)
    return entries, total


def alt_link(e):
    for ln in e.get("link", []):
        if ln.get("rel") == "alternate" and ln.get("type") == "text/html":
            return ln.get("href", "")
    return ""


def norm(u):
    if not u:
        return ""
    try:
        return urllib.parse.urlparse(u).path.rstrip("/").lower()
    except ValueError:
        return u.strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="사람용 출력 대신 JSON 을 stdout 에")
    ap.add_argument("--json-out", metavar="PATH",
                    help="사람용 출력은 그대로 두고 JSON 을 파일로도 쓴다 "
                         "(한 번 실행으로 둘 다 얻기 위한 옵션 — 피드를 두 번 긁지 않는다)")
    args = ap.parse_args()

    with open(os.path.join(ROOT, "lifeinfo_db.txt"), encoding="utf-8") as f:
        posts = json.load(f)["posts"]
    by_url = {norm(p.get("url")): p for p in posts if p.get("url")}

    try:
        entries, total = fetch_all()
    except Exception as e:
        msg = "피드 접근 실패: %s" % e
        payload = {"error": msg}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print("⛔ " + msg)
            print("   Claude Code 웹 컨테이너에서는 정상적으로 막힌다 — Actions 에서 실행하라.")
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
        return 2

    # 키는 비교용 정규화 경로, 값은 원본 URL 과 제목 (보고에는 전체 URL 을 써야
    # 클릭해서 바로 확인할 수 있다)
    live = {}
    for e in entries:
        full = alt_link(e)
        u = norm(full)
        if u:
            live[u] = {"url": full, "title": e.get("title", {}).get("$t", "")}

    unregistered = [{"url": v["url"], "title": v["title"]}
                    for u, v in live.items() if u not in by_url]
    vanished = [{"code": p["code"], "title": p["title"], "url": p["url"]}
                for u, p in by_url.items() if u not in live]
    retitled = []
    for u, p in by_url.items():
        v = live.get(u)
        if v is not None and v["title"].strip() != (p.get("title") or "").strip():
            retitled.append({"code": p["code"], "db": p.get("title"), "live": v["title"]})

    drift = len(unregistered) + len(vanished) + len(retitled)

    payload = {
        "live_total": total, "db_total": len(posts), "drift": drift,
        "unregistered": unregistered, "vanished": vanished, "retitled": retitled,
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        print("=" * 64)
        print(" 라이브 피드 ↔ DB 드리프트 검사")
        print("=" * 64)
        print("라이브 발행 %d편 · DB %d편" % (total, len(posts)))
        print()
        if unregistered:
            print("⛔ 발행됐는데 DB 에 없음 (%d건) — register_post 누락:" % len(unregistered))
            for x in unregistered:
                print("   - %s" % x["title"])
                print("     %s" % x["url"])
        if vanished:
            print("⚠️  DB 에는 있는데 라이브에 없음 (%d건) — 삭제 또는 임시보관:" % len(vanished))
            for x in vanished:
                print("   - %s %s" % (x["code"], x["title"]))
        if retitled:
            print("⚠️  제목 불일치 (%d건):" % len(retitled))
            for x in retitled:
                print("   - %s" % x["code"])
                print("     DB   : %s" % x["db"])
                print("     LIVE : %s" % x["live"])
        if not drift:
            print("✅ 드리프트 없음 — 라이브와 DB 가 완전히 일치한다.")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## %s 피드 드리프트 검사\n\n" % ("🔴" if drift else "🟢"))
            f.write("라이브 **%d**편 · DB **%d**편 · 드리프트 **%d**건\n\n" % (total, len(posts), drift))
            if unregistered:
                f.write("### ⛔ 발행됐는데 DB 에 없음\n")
                for x in unregistered:
                    f.write("- [%s](%s)\n" % (x["title"], x["url"]))
            if vanished:
                f.write("### ⚠️ DB 에는 있는데 라이브에 없음\n")
                for x in vanished:
                    f.write("- `%s` %s\n" % (x["code"], x["title"]))
            if retitled:
                f.write("### ⚠️ 제목 불일치\n")
                for x in retitled:
                    f.write("- `%s`\n  - DB: %s\n  - LIVE: %s\n" % (x["code"], x["db"], x["live"]))
            if not drift:
                f.write("드리프트 없음.\n")

    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
