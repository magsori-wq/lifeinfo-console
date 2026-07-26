#!/usr/bin/env bash
# ============================================================
#  lifeinfo 클라우드 세션 부트스트랩
#
#  Claude Code 웹 세션은 매번 새 컨테이너에서 시작하므로,
#  작업에 필요한 것들이 비어 있다. 이 스크립트가 채운다.
#
#  - Pillow          썸네일 생성 (1200x630)
#  - Noto Sans CJK   한글 렌더링 (없으면 글자가 □□□ 로 나온다)
#
#  멱등적이다. 이미 있으면 건너뛰므로 반복 실행해도 안전하다.
#  실패해도 세션을 막지 않는다 (exit 0) - 무엇이 빠졌는지만 알린다.
# ============================================================
set -uo pipefail

LOG="${TMPDIR:-/tmp}/lifeinfo_bootstrap.log"
: > "$LOG"

say() { printf '%s\n' "$*"; }
log() { printf '%s\n' "$*" >> "$LOG" 2>/dev/null || true; }

missing=()

# --- Pillow -------------------------------------------------
if python3 -c 'import PIL' 2>/dev/null; then
  log "Pillow: already present"
else
  log "Pillow: installing"
  if ! pip3 install --quiet Pillow >>"$LOG" 2>&1; then
    missing+=("Pillow (썸네일 생성 불가)")
  fi
fi

# --- 한글 폰트 ----------------------------------------------
# fc-list 가 없는 이미지도 있으므로 파일 존재로도 판정한다.
have_cjk=0
if command -v fc-list >/dev/null 2>&1; then
  fc-list 2>/dev/null | grep -qi 'CJK' && have_cjk=1
fi
if [ "$have_cjk" -eq 0 ] && ls /usr/share/fonts/opentype/noto/*CJK* >/dev/null 2>&1; then
  have_cjk=1
fi

if [ "$have_cjk" -eq 1 ]; then
  log "Noto CJK: already present"
else
  log "Noto CJK: installing"
  if ! { apt-get install -y -qq fonts-noto-cjk >>"$LOG" 2>&1; }; then
    missing+=("Noto Sans CJK (한글이 □□□ 로 렌더링됨)")
  fi
fi

# --- 검증: 실제로 한글이 그려지는지 --------------------------
verify=$(python3 - <<'PY' 2>/dev/null
import glob
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    print("NO_PIL"); raise SystemExit
c = sorted(glob.glob('/usr/share/fonts/**/*CJK*', recursive=True))
if not c:
    print("NO_FONT"); raise SystemExit
try:
    f = ImageFont.truetype(c[0], 48)
    im = Image.new('L', (400, 80), 0)
    ImageDraw.Draw(im).text((5, 5), "생활정보 모음 한글", font=f, fill=255)
    ink = sum(1 for v in im.get_flattened_data() if v > 100) if hasattr(im,'get_flattened_data') else sum(1 for v in list(im.getdata()) if v > 100)
    print("OK" if ink > 500 else "TOFU")
except Exception:
    print("ERR")
PY
)

case "${verify:-ERR}" in
  OK)      log "한글 렌더링 검증: OK" ;;
  NO_PIL)  missing+=("Pillow 임포트 실패") ;;
  NO_FONT) missing+=("CJK 폰트 파일 없음") ;;
  TOFU)    missing+=("한글이 빈 사각형으로 렌더링됨 - 폰트 확인 필요") ;;
  *)       missing+=("렌더링 검증 실패") ;;
esac

# --- 결과 보고 ----------------------------------------------
if [ ${#missing[@]} -eq 0 ]; then
  say "lifeinfo 환경 준비 완료 — Pillow + Noto CJK 확인, 한글 썸네일 생성 가능."
else
  say "lifeinfo 환경 일부 누락:"
  for m in "${missing[@]}"; do say "  - $m"; done
  say "  상세 로그: $LOG"
fi

exit 0
