# lifeinfo-console — 클라우드 세션 규칙

## 기준: 콘솔 PC가 메인
- 정본은 **콘솔 PC** (`C:\lifeinfo`, 배포는 `C:\lifeinfo-deploy` + `deploy.bat`).
- 클라우드 세션은 **작업 브랜치에만** push 한다. 병합은 **PC에서 사용자가** 한다.

## 금지
- `main` 에 직접 push / 직접 병합 / PR 자동 병합 금지.
- `--force`, `--force-with-lease`, 브랜치 삭제 금지 (사용자가 명시한 경우만).
- 사용자가 요청하지 않은 PR 생성 금지.
- `lifeinfo-console` 의 `main` 은 `deploy.bat` 이 단독 관리한다 (CLOUD_SETUP.md 참고).
  클라우드가 `main` 을 건드리면 PC 클론 이력이 갈라져 배포가 거부된다.

## 절차
1. 세션 지정 브랜치(`ccr-…`)에서만 작업한다. 없으면 `origin/main` 에서 만든다.
2. 커밋 후 `git push -u origin <작업브랜치>` 까지만 한다.
3. **병합은 항상 이부장 세션에 보고하고 지시를 받은 뒤에만 한다.**
   push 직후 이부장 세션(`session_01ViMehLaJfRpksUjtMgQLy7`, 이름 "이부장 인계 및 시작")에
   `send_message` 로 보고한다: 브랜치명 · 커밋 수 · 변경 요지 · `MERGE_NEEDED.md` 갱신 여부.
   이부장의 병합 지시가 오기 전에는 병합·`병합_실행.bat` 안내를 "실행하라"고 하지 않는다.
   (이부장 세션이 바뀌면 `session_names.json` 의 role 이부장 중 `superseded` 없는 항목을 확인한다.)
4. 끝나면 사용자에게 알린다: "PC에서 `git fetch && git merge origin/<브랜치>` 하세요."
5. 자격증명(`token*.json`, `client_secret*.json`, `.env` 등)은 절대 커밋하지 않는다 (PUBLIC 저장소).

## 강제 장치
`.claude/guard_push.sh` (PreToolUse 훅)이 `main`/`master` 대상 push, force push,
`HEAD:main` 형태 push 를 차단한다.
