#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
콘솔 저장소 정합성 검사 — 저장소(GitHub) 쪽에서 실행한다.

왜 로컬 selfcheck 와 별도로 필요한가:
  deploy.bat 은 `git add` 로 파일을 추가·수정만 한다. 로컬에서 파일을 삭제해도
  저장소에서는 지워지지 않으므로, 저장소에는 로컬에 없는 잔여 파일이 쌓인다.
  로컬 selfcheck 는 그 잔여물을 볼 수 없다. 이 검사는 저장소의 실제 상태를 본다.

실행:
    python tools/console_check.py                 # 사람이 읽는 출력
    python tools/console_check.py --json          # 기계용
    python tools/console_check.py --strict        # WARN 도 실패로 취급

종료 코드: 0 = 통과(또는 WARN만), 1 = FAIL 있음
"""

import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

results = []  # (level, check, message)


def add(level, check, msg):
    results.append((level, check, msg))


def load_json(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- 1. HTML 참조
def check_html_refs():
    """콘솔 페이지가 참조하는 로컬 파일이 실제로 저장소에 있는지."""
    # 로컬 전용으로 의도된 참조 — 저장소에 없는 것이 정상이다.
    # dashboard.html 이 IS_LOCAL 게이트로 감싸고 github.io 에선 섹션을 숨긴다.
    LOCAL_ONLY = {"tasks.json"}

    broken = []
    for f in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        name = os.path.basename(f)
        text = open(f, encoding="utf-8", errors="replace").read()
        refs = set()
        refs |= set(re.findall(r"fetch\(\s*'([^']+)'", text))
        refs |= set(re.findall(r'fetch\(\s*"([^"]+)"', text))
        for m in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', text):
            if m.startswith(("http", "//", "#", "mailto:", "javascript:", "data:")):
                continue
            refs.add(m)
        for r in sorted(refs):
            p = r.split("?")[0].split("#")[0]
            if not p or p.startswith("/"):
                continue
            if p in LOCAL_ONLY:
                continue
            if not os.path.exists(os.path.join(ROOT, p)):
                broken.append("%s -> %s" % (name, p))

    if broken:
        add("FAIL", "HTML 참조", "깨진 로컬 참조 %d건: %s" % (len(broken), ", ".join(broken)))
    else:
        add("PASS", "HTML 참조", "모든 로컬 참조가 저장소에 존재 (로컬전용 %s 제외)"
            % ", ".join(sorted(LOCAL_ONLY)))


# ---------------------------------------------------------------- 2. DB 정합성
def check_db():
    db = load_json("lifeinfo_db.txt")
    posts = db.get("posts", [])
    n = len(posts)

    if db.get("count") == n:
        add("PASS", "DB count", "count 필드와 실제 글 수 일치: %d편" % n)
    else:
        add("FAIL", "DB count", "count=%r 인데 실제 %d편 — 손으로 수정하지 말고 파이프라인으로 재생성"
            % (db.get("count"), n))

    codes = [p.get("code") for p in posts]
    dups = sorted(c for c, k in collections.Counter(codes).items() if k > 1)
    if dups:
        add("FAIL", "코드 중복", "중복 코드: %s" % ", ".join(map(str, dups)))
    else:
        add("PASS", "코드 중복", "%d개 코드 모두 고유" % n)

    bad = [c for c in codes if not c or not re.match(r"^[A-H]\d-\d{2}$", str(c))]
    if bad:
        add("FAIL", "코드 형식", "형식 위반: %s" % ", ".join(map(str, bad[:10])))
    else:
        add("PASS", "코드 형식", "모든 코드가 [A-H]n-nn 형식")

    urls = [p.get("url") for p in posts]
    dupu = sorted(u for u, k in collections.Counter(urls).items() if k > 1)
    if dupu:
        add("FAIL", "URL 중복", "중복 URL %d건: %s" % (len(dupu), dupu[0]))
    else:
        add("PASS", "URL 중복", "%d개 URL 모두 고유" % n)

    nourl = [p["code"] for p in posts if not p.get("url")]
    if nourl:
        add("FAIL", "URL 누락", "URL 없는 글: %s" % ", ".join(nourl))
    else:
        add("PASS", "URL 누락", "모든 글에 URL 존재")

    return db, posts


# ---------------------------------------------------------------- 3. 썸네일
def check_thumbs(posts):
    used = {p["thumb"] for p in posts if p.get("thumb")}
    disk = set(os.listdir(os.path.join(ROOT, "thumbs")))

    missing = sorted(used - disk)
    if missing:
        add("FAIL", "썸네일 누락", "DB가 참조하는데 저장소에 없음: %s" % ", ".join(missing))
    else:
        add("PASS", "썸네일 정합", "DB 참조 썸네일 %d개 모두 존재" % len(used))

    nothumb = [p["code"] for p in posts if not p.get("thumb")]
    if nothumb:
        add("WARN", "썸네일 미지정", "thumb 비어 있는 글: %s" % ", ".join(nothumb))

    # 발행 대기 큐가 쓰는 썸네일은 고아가 아니다 (미리 만들어 둔 것)
    queued = set()
    try:
        for it in load_json("queue.json").get("items", []):
            if it.get("thumb"):
                queued.add(it["thumb"])
    except Exception:
        pass

    orphans = sorted(disk - used - queued)
    if orphans:
        add("WARN", "고아 썸네일",
            "DB·큐 어디서도 안 쓰는 파일 %d개: %s "
            "(deploy.bat 은 삭제를 반영하지 않으므로 저장소에만 남는다)"
            % (len(orphans), ", ".join(orphans)))
    else:
        add("PASS", "고아 썸네일", "미사용 썸네일 없음 (대기큐 %d개 반영)" % len(queued))


# ---------------------------------------------------------------- 4. 파생 파일 신선도
def check_derived(posts):
    n = len(posts)
    try:
        pi = load_json("posts_index.json")
        cnt = len(pi) if isinstance(pi, list) else len(pi.get("posts", pi.get("items", pi)))
        if cnt == n:
            add("PASS", "posts_index 신선도", "%d편 DB와 일치" % cnt)
        else:
            add("FAIL", "posts_index 신선도", "posts_index %d편 vs DB %d편 — 재생성 필요" % (cnt, n))
    except Exception as e:
        add("FAIL", "posts_index 신선도", "읽기 실패: %s" % e)

    try:
        ist = load_json("index_status.json")
        tot = ist.get("total")
        if tot in (None, n):
            add("PASS", "index_status", "total=%r (DB %d편과 정합)" % (tot, n))
        else:
            add("WARN", "index_status", "total=%r 인데 DB는 %d편 — 색인 점검 시점 차이일 수 있다" % (tot, n))
    except Exception as e:
        add("WARN", "index_status", "읽기 실패: %s" % e)


# ---------------------------------------------------------------- 5. OSMU 링크
def check_osmu(posts):
    seen = collections.Counter()
    bad = []
    total = 0
    for p in posts:
        for ch, u in (p.get("osmu") or {}).items():
            total += 1
            if not isinstance(u, str) or not u.startswith("http"):
                bad.append("%s/%s" % (p["code"], ch))
            else:
                seen[u] += 1
    dups = [u for u, k in seen.items() if k > 1]
    if bad:
        add("FAIL", "OSMU URL 형식", "잘못된 링크: %s" % ", ".join(bad[:8]))
    elif dups:
        add("FAIL", "OSMU URL 중복", "같은 링크가 여러 글에: %s" % dups[0])
    else:
        add("PASS", "OSMU 링크", "확산링크 %d개 형식·중복 통과" % total)


# ---------------------------------------------------------------- 6. 검사 신선도
def check_freshness():
    try:
        h = load_json("health.json")
        ts = str(h.get("checked_at", ""))[:19]
        when = dt.datetime.fromisoformat(ts)
        age_h = (dt.datetime.now() - when).total_seconds() / 3600.0
        msg = "health.json 점검 시각 %s (%.0f시간 전) · light=%s" % (ts, age_h, h.get("light"))
        if h.get("fail", 0) > 0:
            add("FAIL", "health 상태", msg + " — FAIL %d건" % h["fail"])
        elif age_h > 72:
            add("WARN", "health 신선도", msg + " — 3일 넘게 갱신 안 됨")
        else:
            add("PASS", "health 신선도", msg)
    except Exception as e:
        add("WARN", "health 신선도", "읽기 실패: %s" % e)


# ---------------------------------------------------------------- 7. 자격증명 유출
def check_secrets():
    """공개 저장소이므로 자격증명 형태의 파일·문자열이 없어야 한다."""
    patterns = [
        ("client_secret", re.compile(r"client_secret", re.I)),
        ("refresh_token", re.compile(r"refresh_token", re.I)),
        ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
        ("google oauth id", re.compile(r"\d{12}-[a-z0-9]{32}\.apps\.googleusercontent\.com")),
    ]
    hits = []
    for f in sorted(glob.glob(os.path.join(ROOT, "*.json")) +
                    glob.glob(os.path.join(ROOT, "*.txt")) +
                    glob.glob(os.path.join(ROOT, "*.html"))):
        text = open(f, encoding="utf-8", errors="replace").read()
        for name, rx in patterns:
            if rx.search(text):
                hits.append("%s: %s" % (os.path.basename(f), name))
    if hits:
        add("FAIL", "자격증명 노출", "공개 저장소에서 발견: %s" % ", ".join(hits))
    else:
        add("PASS", "자격증명 노출", "자격증명 패턴 없음 (공개 저장소 안전)")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="JSON 으로 출력")
    ap.add_argument("--json-out", metavar="PATH",
                    help="사람용 출력은 그대로 두고 JSON 을 파일로도 쓴다 "
                         "(한 번 실행으로 둘 다 얻어 요약 패널 중복을 막는다)")
    ap.add_argument("--strict", action="store_true", help="WARN 도 실패로 취급")
    args = ap.parse_args()

    check_html_refs()
    db, posts = check_db()
    check_thumbs(posts)
    check_derived(posts)
    check_osmu(posts)
    check_freshness()
    check_secrets()

    n_fail = sum(1 for lv, _, _ in results if lv == "FAIL")
    n_warn = sum(1 for lv, _, _ in results if lv == "WARN")
    n_pass = sum(1 for lv, _, _ in results if lv == "PASS")
    light = "red" if n_fail else ("yellow" if n_warn else "green")

    payload = {
        "light": light, "pass": n_pass, "warn": n_warn, "fail": n_fail,
        "checks": [{"level": lv, "check": c, "msg": m} for lv, c, m in results],
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "⛔"}
        print("=" * 64)
        print(" 콘솔 저장소 정합성 검사")
        print("=" * 64)
        for lv, c, m in results:
            print("%s [%s] %s" % (icon[lv], c, m))
        print("-" * 64)
        print("신호등: %s  (통과 %d · 경고 %d · 실패 %d)" % (light.upper(), n_pass, n_warn, n_fail))

    # GitHub Actions 요약 패널
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[light]
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## %s 콘솔 정합성 검사\n\n" % emoji)
            f.write("통과 **%d** · 경고 **%d** · 실패 **%d**\n\n" % (n_pass, n_warn, n_fail))
            f.write("| | 항목 | 내용 |\n|---|---|---|\n")
            for lv, c, m in results:
                f.write("| %s | %s | %s |\n" % ({"PASS": "✅", "WARN": "⚠️", "FAIL": "⛔"}[lv], c, m))

    if n_fail or (args.strict and n_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
