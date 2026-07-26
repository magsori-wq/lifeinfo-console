#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
중복 게이트 — 새 글감 제목이 기존 153편과 겹치는지 검사한다.

SKILL.md §0.5 의 중복 게이트를 클라우드에서 쓸 수 있게 만든 것이다.
`studio.dupcheck` 는 PC 에 있어 지금 실행할 수 없고, 이 검사는 DB 만 있으면
되므로 어디서든 돌아간다.

판정 기준(SKILL.md 와 동일):
    🔴 ≥ 0.60  기존 글과 사실상 같은 주제 — 발행 제외
    🟡 ≥ 0.45  겹칠 소지 있음 — 각도를 바꾸거나 기존 글 보강으로 전환 검토
    🟢 < 0.45  진행 가능

점수는 두 가지를 합쳐 쓴다:
  · 토큰 자카드 — 핵심 키워드가 얼마나 겹치는가
  · 문자열 유사도(difflib) — 제목 전체가 얼마나 닮았는가
어느 한쪽만 쓰면 "국민연금 임의계속가입"과 "국민연금 분할연금"처럼 앞부분만 같은
제목을 과다 검출하거나(문자열만), 어순이 다른 같은 주제를 놓친다(토큰만).

실행:
    python tools/dupcheck.py "국가암검진 대상 무료 검진 항목 총정리"
    python tools/dupcheck.py --queue          # 발행 대기 큐 전체를 한 번에
    python tools/dupcheck.py --queue --json-out dup.json

종료 코드: 0 = 🔴 없음, 1 = 🔴 있음
"""

import argparse
import difflib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RED, YELLOW = 0.60, 0.45

# 거의 모든 제목에 들어가 변별력이 없는 말 — 점수를 부풀리므로 뺀다
STOP = {
    "총정리", "방법", "신청", "조회", "발급", "계산", "비교", "정리", "안내",
    "얼마", "언제", "어디", "누가", "대상", "자격", "조건", "기준", "금액",
    "및", "과", "와", "의", "를", "을", "은", "는", "이", "가",
}
YEAR = re.compile(r"20\d{2}")


def tokens(title):
    """한글·영문·숫자 덩어리로 자르고 불용어와 연도를 제거."""
    t = YEAR.sub(" ", str(title))
    raw = re.findall(r"[가-힣]{2,}|[A-Za-z]{2,}|\d+", t)
    out = set()
    for w in raw:
        if w in STOP:
            continue
        # '신청방법' 처럼 붙어 있는 불용어 꼬리를 떼어 본다
        for s in STOP:
            if len(w) > len(s) + 1 and w.endswith(s):
                w = w[: -len(s)]
                break
        if len(w) >= 2 and w not in STOP:
            out.add(w)
    return out


def score(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        jac = 0.0
    else:
        jac = len(ta & tb) / len(ta | tb)
    seq = difflib.SequenceMatcher(None, str(a), str(b)).ratio()
    # 토큰 겹침에 무게를 더 둔다 — 주제 동일성을 더 잘 반영한다
    return round(jac * 0.65 + seq * 0.35, 3), round(jac, 3), round(seq, 3), sorted(ta & tb)


def level(s):
    return "RED" if s >= RED else ("YELLOW" if s >= YELLOW else "GREEN")


def check(title, posts, top=3):
    rows = []
    for p in posts:
        s, jac, seq, shared = score(title, p.get("title", ""))
        rows.append({"code": p.get("code"), "title": p.get("title"),
                     "score": s, "jaccard": jac, "seq": seq, "shared": shared})
    rows.sort(key=lambda r: -r["score"])
    best = rows[0]["score"] if rows else 0.0
    return {"title": title, "level": level(best), "best": best, "matches": rows[:top]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title", nargs="*", help="검사할 제목")
    ap.add_argument("--queue", action="store_true", help="queue.json 전체를 검사")
    ap.add_argument("--json-out", metavar="PATH")
    ap.add_argument("--top", type=int, default=3, help="제목당 표시할 유사 글 수")
    args = ap.parse_args()

    with open(os.path.join(ROOT, "lifeinfo_db.txt"), encoding="utf-8") as f:
        posts = json.load(f)["posts"]

    targets = []
    if args.queue:
        with open(os.path.join(ROOT, "queue.json"), encoding="utf-8") as f:
            for it in json.load(f).get("items", []):
                if it.get("title"):
                    targets.append((it.get("code"), it["title"]))
    if args.title:
        targets.append((None, " ".join(args.title)))
    if not targets:
        ap.error("제목을 주거나 --queue 를 쓰라")

    icon = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}
    results = []
    print("기존 글 %d편과 대조" % len(posts))
    print("=" * 68)
    for code, title in targets:
        r = check(title, posts, args.top)
        r["code"] = code
        results.append(r)
        print("%s %-7s %s" % (icon[r["level"]], code or "-", title[:52]))
        print("     최고 유사도 %.3f" % r["best"])
        for mm in r["matches"]:
            mark = "  <<<" if mm["score"] >= YELLOW else ""
            print("       %.3f  %-7s %s%s" % (mm["score"], mm["code"], mm["title"][:42], mark))
            if mm["score"] >= YELLOW and mm["shared"]:
                print("              공통 키워드: %s" % ", ".join(mm["shared"][:8]))
        print()

    n_red = sum(1 for r in results if r["level"] == "RED")
    n_yel = sum(1 for r in results if r["level"] == "YELLOW")
    print("-" * 68)
    print("🔴 %d · 🟡 %d · 🟢 %d  (기준 🔴≥%.2f · 🟡≥%.2f)"
          % (n_red, n_yel, len(results) - n_red - n_yel, RED, YELLOW))
    if n_red:
        print("🔴 는 기존 글과 사실상 같은 주제다 — 발행하지 말고 기존 글 보강을 검토하라.")
    if n_yel:
        print("🟡 는 각도를 확실히 달리하거나(계산예시·비교·탈락사유) 기존 글을 갱신하는 쪽이 낫다.")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"red": n_red, "yellow": n_yel, "results": results},
                      f, ensure_ascii=False, indent=1)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## %s 중복 게이트\n\n" % ("🔴" if n_red else ("🟡" if n_yel else "🟢")))
            f.write("| | 코드 | 제목 | 최고 유사도 | 가장 닮은 기존 글 |\n|---|---|---|---|---|\n")
            for r in results:
                m = r["matches"][0] if r["matches"] else {}
                f.write("| %s | %s | %s | %.3f | %s %s |\n" % (
                    icon[r["level"]], r.get("code") or "-", r["title"][:40],
                    r["best"], m.get("code", ""), (m.get("title") or "")[:34]))

    return 1 if n_red else 0


if __name__ == "__main__":
    sys.exit(main())
