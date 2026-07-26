#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
썸네일 생성기 — 1200x630 다크네이비 카드.

지금까지 썸네일은 PC 의 PIL 환경에서만 만들 수 있었다. 이 스크립트는 클라우드
세션에서도 돌아가므로(.claude/bootstrap.sh 가 Pillow + Noto Sans CJK 를 깔아준다)
어느 기기에서든 썸네일을 만들 수 있다.

디자인은 기존 썸네일(124_cancerscreen.png · 131_inheritance_waiver.png)을 픽셀 단위로
측정해 맞췄다. 임의로 정한 값이 아니다:
  · 배경 #1B283D, 카테고리색 원 2개(배경에 17% 알파로 섞인 색)
  · 좌상단 알약형 카테고리 배지, 큰 제목, 카테고리색 부제, 짧은 밑줄 바, 푸터
  · 폰트 크기는 기존 썸네일의 글자 폭을 역산해 구했다 (제목 64~67 / 배지 27 /
    부제 32 / 푸터 30)

사용:
  python tools/make_thumb.py --cat E --code E1-02 \
      --title "어르신 휴대폰 요금감면" \
      --sub "기초연금·장애인·국가유공자 대상" \
      --out thumbs/132_telecom_discount.png

  --light 를 주면 네이버용 밝은 변형을 만든다.
"""

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

W, H = 1200, 630
BG = (27, 40, 61)            # #1B283D
BG_LIGHT = (247, 249, 252)
FOOT = (138, 151, 173)       # #8A97AD
FOOT_LIGHT = (120, 132, 150)
BRAND = "생활정보 모음"

# 측정으로 얻은 좌표
PAD_X = 82
PILL_Y0, PILL_H, PILL_PAD = 88, 59, 24
TITLE_TOP_1, TITLE_TOP_2 = 246, 253   # 1줄일 때 / 2줄일 때 첫 줄 잉크 상단
LINE_GAP = 78
SUB_TOP = 455
BAR_X, BAR_Y, BAR_W, BAR_H = 80, 510, 160, 12
TRACK_SUB, TRACK_FOOT = 2.1, 2.7      # 실측 자간(px) — 제목·배지는 0
FOOT_TOP = 566
CIRCLES = [((1095, 68), 122), ((1150, 559), 154)]
CIRCLE_ALPHA = 0.17

FONT_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
KR = 1                        # .ttc 안의 한국어 페이스 인덱스

TITLE_MAX_W = 840
TITLE_SIZE_MAX, TITLE_SIZE_MIN = 68, 46


def load_taxonomy():
    """대분류 코드 -> (이름, 색). DB 를 정답으로 삼아 색을 하드코딩하지 않는다."""
    with open(os.path.join(ROOT, "lifeinfo_db.txt"), encoding="utf-8") as f:
        tax = json.load(f)["taxonomy"]
    return {t["code"]: (t["name"], t["color"]) for t in tax}


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def font(path, size):
    return ImageFont.truetype(path, size, index=KR)


def ink_size(draw, text, f):
    bb = draw.textbbox((0, 0), text, font=f)
    return bb[2] - bb[0], bb[3] - bb[1], bb[0], bb[1]


def wrap(draw, text, f, maxw):
    """공백 기준 그리디 줄바꿈."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if ink_size(draw, trial, f)[0] <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_title(draw, text, maxw, max_lines=2):
    """2줄 안에 들어가는 가장 큰 크기를 고른다 — 기존 썸네일의 동작과 같다."""
    for size in range(TITLE_SIZE_MAX, TITLE_SIZE_MIN - 1, -1):
        f = font(FONT_B, size)
        lines = wrap(draw, text, f, maxw)
        if len(lines) <= max_lines:
            return f, lines, size
    f = font(FONT_B, TITLE_SIZE_MIN)
    return f, wrap(draw, text, f, maxw)[:max_lines], TITLE_SIZE_MIN


def draw_text_at_ink_top(draw, xy, text, f, fill, track=0.0):
    """잉크 상단을 기준으로 그린다(측정값이 잉크 기준이므로).

    track 은 자간(px). 기존 썸네일 실측 결과 부제와 푸터에는 자간이 들어가 있고
    제목·배지에는 없다. 푸터 폭은 121개 중 76개가 186px(자간 있음)이라 이쪽이 표준이다.
    """
    x, y = xy
    if not track:
        bb = draw.textbbox((0, 0), text, font=f)
        draw.text((x - bb[0], y - bb[1]), text, font=f, fill=fill)
        return
    # 자간을 넣으면 textbbox 를 쓸 수 없으므로 첫 글자 기준으로 정렬을 맞춘다
    bb0 = draw.textbbox((0, 0), text[0], font=f)
    cx = x - bb0[0]
    top = y - draw.textbbox((0, 0), text, font=f)[1]
    for ch in text:
        draw.text((cx, top), ch, font=f, fill=fill)
        cx += draw.textlength(ch, font=f) + track


def build(cat, title, sub, light=False):
    tax = load_taxonomy()
    if cat not in tax:
        sys.exit("알 수 없는 대분류: %s (가능: %s)" % (cat, ", ".join(sorted(tax))))
    cat_name, cat_hex = tax[cat]
    cc = hex2rgb(cat_hex)

    bg = BG_LIGHT if light else BG
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)

    # 배경 원 — 배경에 카테고리색을 옅게 섞은 색
    circ = blend(bg, cc, 0.10 if light else CIRCLE_ALPHA)
    for (cx, cy), r in CIRCLES:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=circ)

    # 카테고리 배지
    fp = font(FONT_B, 27)
    tw = ink_size(d, cat_name, fp)[0]
    pill_w = tw + PILL_PAD * 2
    d.rounded_rectangle([80, PILL_Y0, 80 + pill_w, PILL_Y0 + PILL_H],
                        radius=PILL_H // 2, fill=cc)
    bb = d.textbbox((0, 0), cat_name, font=fp)
    d.text((80 + PILL_PAD - bb[0],
            PILL_Y0 + (PILL_H - (bb[3] - bb[1])) // 2 - bb[1]),
           cat_name, font=fp, fill=(255, 255, 255))

    # 제목
    ft, lines, _ = fit_title(d, title, TITLE_MAX_W)
    top = TITLE_TOP_1 if len(lines) == 1 else TITLE_TOP_2
    tcol = (18, 26, 40) if light else (255, 255, 255)
    for i, ln in enumerate(lines):
        draw_text_at_ink_top(d, (PAD_X, top + i * LINE_GAP), ln, ft, tcol)

    # 부제
    if sub:
        fs = font(FONT_B, 32)
        draw_text_at_ink_top(d, (PAD_X, SUB_TOP), sub, fs, cc, TRACK_SUB)

    # 밑줄 바
    d.rounded_rectangle([BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + BAR_H],
                        radius=BAR_H // 2, fill=cc)

    # 푸터
    ff = font(FONT_R, 30)
    draw_text_at_ink_top(d, (PAD_X - 1, FOOT_TOP), BRAND, ff,
                         FOOT_LIGHT if light else FOOT, TRACK_FOOT)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", required=True, help="대분류 코드 A~H")
    ap.add_argument("--title", required=True, help="썸네일용 짧은 제목(긴 DB 제목 말고)")
    ap.add_argument("--sub", default="", help="부제 한 줄")
    ap.add_argument("--out", required=True)
    ap.add_argument("--code", default="", help="글 코드(로그용)")
    ap.add_argument("--light", action="store_true", help="네이버용 밝은 변형")
    args = ap.parse_args()

    im = build(args.cat, args.title, args.sub, args.light)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    im.save(args.out)
    print("생성: %s  (%dx%d)%s" % (args.out, im.size[0], im.size[1],
                                 "  [%s]" % args.code if args.code else ""))


if __name__ == "__main__":
    main()
