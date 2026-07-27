#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공식 링크 부패 검사 — 발행된 글 본문의 링크가 아직 살아 있는지 확인한다.

왜 필요한가:
  생활정보 글은 본문마다 🏛️ 공식 안내(.go.kr) 링크를 싣는다. 그런데 정부 사이트는
  개편이 잦아 링크가 조용히 죽는다. 독자가 클릭했다가 404를 만나면 신뢰도와
  체류시간에 직격이고, YMYL 주제라 애드센스 심사에도 불리하다.
  링크는 저장소가 아니라 Blogger 본문에 있으므로 피드에서 본문을 받아 검사한다.

⚠️ 실행 위치가 결과를 좌우한다 (2026-07-27 실측):
   · Claude Code 웹 컨테이너 → 프록시가 blogspot 을 차단해 아예 못 돈다.
   · GitHub Actions(미국 러너) → 외부·내부·이미지 링크는 잘 보지만,
     **공식(.go.kr) 링크가 139개나 타임아웃**했다. bokjiro·hometax·busanjin 처럼
     멀쩡히 살아 있는 사이트들이었다. 한국 정부 사이트가 해외 IP를 막거나 느린 탓이다.
   · 그래서 공식 링크는 **한국 IP(사용자 PC)** 에서 `--only official` 로 검사한다.
     Actions 는 `--only external --only internal --only asset` 로 돌린다.

오탐 방지가 이 스크립트의 핵심이다:
  정부·공공 사이트는 봇을 막으려 403/405 를 흔하게 돌려준다. 이것을 죽은 링크로
  세면 리포트가 노이즈가 되어 아무도 안 보게 된다. 그래서 상태를 나눠 분류하고,
  '확실히 죽은 것'만 실패로 취급한다.

실행:
    python tools/link_rot.py
    python tools/link_rot.py --json-out link_rot.json
    python tools/link_rot.py --limit 50        # 앞의 50편만 (빠른 확인)

종료 코드: 0 = 죽은 링크 없음, 1 = 죽은 링크 발견, 2 = 피드 접근 실패
"""

import argparse
import collections
import concurrent.futures as futures
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = "https://lifeinfo8975.blogspot.com/feeds/posts/default"
PAGE = 150
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 공식 기관으로 취급할 호스트 접미사
GOV_SUFFIX = (".go.kr", ".or.kr", ".re.kr", ".ac.kr", ".gov")
BLOG_HOST = "lifeinfo8975.blogspot.com"
ASSET_HOST = "magsori-wq.github.io"


# ------------------------------------------------------------------ 피드
def fetch_all():
    entries, start, total = [], 1, None
    while True:
        qs = urllib.parse.urlencode({"alt": "json", "max-results": PAGE, "start-index": start})
        req = urllib.request.Request("%s?%s" % (FEED, qs), headers={"User-Agent": UA})
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


# ------------------------------------------------------------------ 추출·분류
def extract_links(body):
    """본문 HTML 에서 href 와 img src 를 뽑는다."""
    out = []
    for m in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', body, re.I):
        out.append(("link", html.unescape(m.strip())))
    for m in re.findall(r'<img[^>]+src\s*=\s*["\']([^"\']+)["\']', body, re.I):
        out.append(("image", html.unescape(m.strip())))
    return out


def classify(url):
    if url.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
        return None
    if not url.startswith("http"):
        return None
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except ValueError:
        return None
    if not host:
        return None
    if host == BLOG_HOST:
        return "internal"
    if host == ASSET_HOST:
        return "asset"
    if host.endswith(GOV_SUFFIX):
        return "official"
    return "external"


# ------------------------------------------------------------------ 검사
def encode_url(u):
    """URL 의 비ASCII 문자를 퍼센트 인코딩한다.

    실측 버그(2026-07-27): 본문에 map.kakao.com/?q=삼계탕 처럼 한글이 그대로 든 링크가
    있어 urllib 이 UnicodeEncodeError 로 죽었고, '확인 실패' 로 집계됐다. 링크는 멀쩡했다.
    safe 에 '%' 를 포함시켜 이미 인코딩된 URL 을 두 번 인코딩하지 않는다.
    """
    try:
        p = urllib.parse.urlsplit(u)
    except ValueError:
        return u
    netloc = p.netloc
    if any(ord(c) > 127 for c in netloc):
        try:
            netloc = netloc.encode("idna").decode("ascii")
        except Exception:
            pass
    return urllib.parse.urlunsplit((
        p.scheme, netloc,
        urllib.parse.quote(p.path, safe="/%:@&=+$,;~!*'()"),
        urllib.parse.quote(p.query, safe="/%:@&=+$,;?~!*'()"),
        urllib.parse.quote(p.fragment, safe="/%:@&=+$,;?~!*'()"),
    ))


def probe(url, timeout=20):
    """(분류, 상태코드, 최종URL, 메모) 반환. HEAD 를 먼저 쓰고 막히면 GET 으로 재시도."""
    url = encode_url(url)

    def request(method):
        req = urllib.request.Request(url, method=method, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.geturl()

    try:
        code, final = request("HEAD")
    except urllib.error.HTTPError as e:
        # HEAD 를 거부하는 서버가 많다 — GET 으로 다시 본다
        if e.code in (403, 405, 400, 501, 500):
            try:
                code, final = request("GET")
            except urllib.error.HTTPError as e2:
                return verdict(e2.code), e2.code, url, ""
            except Exception as e2:
                return classify_error(e2), None, url, type(e2).__name__
        else:
            return verdict(e.code), e.code, url, ""
    except Exception as e:
        try:
            code, final = request("GET")
        except urllib.error.HTTPError as e2:
            return verdict(e2.code), e2.code, url, ""
        except Exception as e2:
            return classify_error(e2), None, url, "%s: %s" % (type(e2).__name__, e2)
    return verdict(code), code, final, ""


def classify_error(e):
    """예외를 판정으로. SSL 문제는 링크 부재가 아니므로 따로 본다."""
    s = "%s %s" % (type(e).__name__, e)
    if "SSL" in s or "CERTIFICATE" in s.upper() or "DH_KEY" in s:
        return "ssl"
    return "error"


def verdict(code):
    """상태코드를 판정으로. 죽은 것만 dead — 나머지는 사람이 볼 참고 정보."""
    if code is None:
        return "error"
    if code in (404, 410):
        return "dead"          # 확실히 사라진 페이지
    if code in (401, 403, 429):
        return "blocked"       # 봇 차단일 가능성이 높다 — 오탐 위험이라 실패로 안 침
    if 500 <= code < 600:
        return "server"        # 서버 일시 장애일 수 있다
    if 200 <= code < 400:
        return "ok"
    return "other"


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", metavar="PATH")
    ap.add_argument("--limit", type=int, default=0, help="검사할 글 수 제한(0=전체)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--only", action="append", metavar="CAT",
                    choices=["official", "external", "internal", "asset"],
                    help="검사 범위를 한정한다(반복 지정 가능). "
                         "해외 러너에서는 --only external --only internal --only asset 로 "
                         "공식(.go.kr)을 제외하라 — 아래 설명 참조")
    ap.add_argument("--skip-external", action="store_true",
                    help="(구) 외부 링크 제외. --only 로 대체 권장")
    args = ap.parse_args()

    try:
        with open(os.path.join(ROOT, "lifeinfo_db.txt"), encoding="utf-8") as f:
            posts = json.load(f)["posts"]
    except Exception:
        posts = []
    by_url = {}
    for p in posts:
        u = p.get("url")
        if u:
            by_url[urllib.parse.urlparse(u).path.rstrip("/").lower()] = p

    try:
        entries, total = fetch_all()
    except Exception as e:
        msg = "피드 접근 실패: %s" % e
        print("⛔ " + msg)
        print("   Claude Code 웹 컨테이너에서는 정상적으로 막힌다 — Actions 에서 실행하라.")
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump({"error": msg}, f, ensure_ascii=False, indent=1)
        return 2

    if args.limit:
        entries = entries[:args.limit]

    # URL 별로 어느 글에서 쓰였는지 모은다(같은 .go.kr 링크가 여러 글에 반복되므로 중복 제거가 핵심)
    refs = collections.defaultdict(list)   # url -> [(code, title, kind)]
    for e in entries:
        body = e.get("content", {}).get("$t", "") or ""
        purl = alt_link(e)
        rec = by_url.get(urllib.parse.urlparse(purl).path.rstrip("/").lower())
        code = rec["code"] if rec else "?"
        title = (rec["title"] if rec else e.get("title", {}).get("$t", "")) or ""
        for kind, u in extract_links(body):
            cat = classify(u)
            if cat is None:
                continue
            if args.only and cat not in args.only:
                continue
            if cat == "external" and args.skip_external:
                continue
            refs[u].append((code, title, cat))

    urls = sorted(refs)
    print("검사 대상: 글 %d편 · 고유 링크 %d개" % (len(entries), len(urls)))
    print("(같은 링크가 여러 글에 쓰이므로 중복을 제거했다)")
    print()

    results = {}
    with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {ex.submit(probe, u, args.timeout): u for u in urls}
        done = 0
        for f in futures.as_completed(fut):
            u = fut[f]
            try:
                results[u] = f.result()
            except Exception as e:
                results[u] = ("error", None, u, str(e))
            done += 1
            if done % 50 == 0:
                print("  ... %d/%d 확인" % (done, len(urls)))

    buckets = collections.defaultdict(list)
    for u, (v, code, final, note) in results.items():
        cats = {c for _, _, c in refs[u]}
        buckets[v].append({
            "url": u, "status": code, "final": final, "note": note,
            "cats": sorted(cats),
            "posts": sorted({(c, t) for c, t, _ in refs[u]}),
        })

    # 리다이렉트로 경로가 바뀐 것 = 링크 이전. 죽지는 않았지만 갱신 대상이다.
    moved = [x for x in buckets["ok"]
             if x["final"] and x["final"].rstrip("/") != x["url"].rstrip("/")]

    dead = buckets["dead"]
    blocked = buckets["blocked"]
    server = buckets["server"]
    ssl_bad = buckets["ssl"]
    errs = buckets["error"] + buckets["other"]

    def show(title, rows, limit=40):
        if not rows:
            return
        print(title % len(rows))
        for x in rows[:limit]:
            tag = "/".join(x["cats"])
            print("  [%s] %s%s" % (tag, x["url"], (" -> %s" % x["status"]) if x["status"] else ""))
            if x.get("note"):
                print("      %s" % x["note"])
            for c, t in x["posts"][:4]:
                print("      쓰인 글: %s %s" % (c, t[:38]))
            if len(x["posts"]) > 4:
                print("      ... 외 %d편" % (len(x["posts"]) - 4))
        if len(rows) > limit:
            print("  ... 외 %d건" % (len(rows) - limit))
        print()

    print("=" * 66)
    show("⛔ 죽은 링크 %d개 (404/410 — 즉시 수정 대상)", dead)
    show("🔀 이전된 링크 %d개 (리다이렉트 — 최종 주소로 갱신 권장)", moved)
    show("🚧 차단 응답 %d개 (401/403/429 — 봇 차단일 가능성이 높다, 직접 확인)", blocked)
    show("🛠️ 서버 오류 %d개 (5xx — 일시 장애일 수 있으니 다음 회차 확인)", server)
    show("🔐 SSL 협상 실패 %d개 (구형 암호화 설정 — 브라우저는 열리는 경우가 많다)", ssl_bad)
    show("❓ 확인 실패 %d개 (DNS·타임아웃 등)", errs)

    ok = len(buckets["ok"])
    print("-" * 66)
    print("정상 %d · 이전 %d · 죽음 %d · 차단 %d · 서버오류 %d · SSL실패 %d · 확인실패 %d"
          % (ok, len(moved), len(dead), len(blocked), len(server), len(ssl_bad), len(errs)))
    if not dead:
        print("✅ 확실히 죽은 링크는 없다.")

    # 관측 지점 경고 — 해외에서 돌리면 .go.kr 이 대량으로 타임아웃 난다
    gov_err = sum(1 for x in errs if "official" in x["cats"])
    if gov_err >= 10:
        print()
        print("⚠️  공식(.go.kr) 링크 %d개가 '확인 실패' 로 나왔다. 이 수치는" % gov_err)
        print("    링크 문제가 아니라 **검사한 위치**의 문제일 가능성이 크다.")
        print("    상당수 한국 정부 사이트가 해외 IP를 차단하거나 극도로 느리다.")
        print("    (실측 2026-07-27: GitHub Actions 미국 러너에서 139개 타임아웃,")
        print("     그중 bokjiro·hometax·busanjin 등은 실제로 살아 있는 사이트였다.)")
        print("    → 공식 링크는 **한국 IP(PC)에서** 검사하라:")
        print("       python tools/link_rot.py --only official")

    # 이미지 링크는 썸네일 정리 판단에 쓰인다.
    # ⚠️ 전수 검사일 때만 의미가 있다 — 일부 글만 봤다면 "참조되지 않는다"는 결론을
    #    낼 수 없고, 그 목록을 믿고 지우면 살아 있는 글의 이미지가 깨진다.
    used_assets = sorted({u for u in refs if classify(u) == "asset"})
    thumb_names = {os.path.basename(urllib.parse.urlparse(u).path) for u in used_assets}
    complete = (not args.limit) and len(entries) >= total
    never = []
    print()
    print("본문이 실제로 참조하는 썸네일 %d개" % len(thumb_names))
    if not complete:
        print("  ⚠️ 전수 검사가 아니므로(글 %d/%d편) 미참조 썸네일 판정은 생략한다." %
              (len(entries), total))
        print("     일부만 보고 '안 쓰인다'고 단정하면 살아 있는 이미지를 지우게 된다.")
    else:
        try:
            disk = set(os.listdir(os.path.join(ROOT, "thumbs")))
            # 발행 대기 큐의 썸네일은 아직 본문이 없어서 당연히 참조되지 않는다.
            # 이걸 '삭제해도 안전'으로 내보내면 곧 발행할 글의 이미지를 지우게 된다.
            queued = set()
            try:
                with open(os.path.join(ROOT, "queue.json"), encoding="utf-8") as qf:
                    for it in json.load(qf).get("items", []):
                        if it.get("thumb"):
                            queued.add(it["thumb"])
            except Exception:
                pass
            never = sorted(disk - thumb_names - queued)
            print("  발행 대기 큐가 예약한 썸네일 %d개는 제외했다" % len(queued & disk))
            print("  본문 어디에서도 참조되지 않는 저장소 썸네일: %d개" % len(never))
            for n in never[:15]:
                print("    - %s" % n)
            if len(never) > 15:
                print("    ... 외 %d개" % (len(never) - 15))
            print("  (전수 검사 기준 — 이 목록은 삭제해도 발행된 글의 이미지가 깨지지 않는다)")
        except Exception as e:
            print("  thumbs 폴더를 읽지 못했다: %s" % e)

    payload = {
        "checked_posts": len(entries), "unique_links": len(urls),
        "ok": ok, "dead": dead, "moved": moved, "blocked": blocked,
        "server": server, "ssl": ssl_bad, "errors": errs,
        "scope": args.only or ["official", "external", "internal", "asset"],
        "referenced_thumbs": sorted(thumb_names),
        "unreferenced_thumbs": never,
        "full_scan": complete,   # false 면 unreferenced_thumbs 를 신뢰하지 말 것
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## %s 공식 링크 부패 검사\n\n" % ("🔴" if dead else "🟢"))
            f.write("글 **%d**편 · 고유 링크 **%d**개\n\n" % (len(entries), len(urls)))
            f.write("| 상태 | 개수 |\n|---|---|\n")
            f.write("| ✅ 정상 | %d |\n| 🔀 이전됨 | %d |\n| ⛔ 죽음 | %d |\n"
                    "| 🚧 차단 | %d |\n| 🛠️ 서버오류 | %d |\n| 🔐 SSL실패 | %d |\n"
                    "| ❓ 확인실패 | %d |\n\n"
                    % (ok, len(moved), len(dead), len(blocked), len(server),
                       len(ssl_bad), len(errs)))
            if dead:
                f.write("### ⛔ 죽은 링크 — 즉시 수정\n\n")
                for x in dead:
                    f.write("- `%s` (%s)\n" % (x["url"], x["status"]))
                    for c, t in x["posts"][:5]:
                        f.write("  - %s %s\n" % (c, t))
            if moved:
                f.write("\n### 🔀 이전된 링크 — 최종 주소로 갱신 권장\n\n")
                for x in moved[:30]:
                    f.write("- `%s`\n  → `%s`\n" % (x["url"], x["final"]))
            if complete and never:
                f.write("\n### 🧹 본문에서 참조되지 않는 썸네일 (%d개)\n\n" % len(never))
                f.write("전수 검사 기준이므로 삭제해도 발행된 글의 이미지가 깨지지 않는다.\n\n")
                for n in never[:20]:
                    f.write("- `%s`\n" % n)
            elif not complete:
                f.write("\n_부분 검사였으므로 미참조 썸네일 판정은 생략했다._\n")

    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
