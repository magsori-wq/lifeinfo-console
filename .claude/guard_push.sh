#!/usr/bin/env bash
# PreToolUse(Bash) 훅: main/master 로 가는 push 와 force push 를 차단한다.
# 정본은 콘솔 PC. 클라우드는 작업 브랜치에만 push 하고 병합은 PC에서 한다.
cmd=$(python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)
# 커밋 메시지 등 다른 구간의 단어에 오탐하지 않도록 "git push" 구간(; & | 전까지)만 검사한다.
seg=$(printf '%s\n' "$cmd" | grep -Eo 'git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+push[^;&|]*' | tr '\n' ' ')
[ -z "$seg" ] && exit 0
cmd="$seg"

block() { echo "차단: $1 — 콘솔 PC가 메인입니다. 작업 브랜치에만 push 하고 PC에서 병합하세요." >&2; exit 2; }

echo "$cmd" | grep -Eq -- '(--force|--force-with-lease|(^|[[:space:]])-f([[:space:]]|$)|--delete|[[:space:]]:[A-Za-z])' && block "force/삭제 push"
echo "$cmd" | grep -Eq -- '(^|[[:space:]:/])(main|master)([[:space:]]|$)' && block "main/master 대상 push"
cur=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$cur" = "main" ] || [ "$cur" = "master" ]; then
  echo "$cmd" | grep -Eq 'git push[[:space:]]*($|origin[[:space:]]*$)' && block "현재 브랜치가 $cur"
fi
exit 0
