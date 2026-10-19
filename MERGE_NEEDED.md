# 🔔 병합 필요 안내 (콘솔 PC에서 실행)

> 클라우드 세션은 `main` 에 직접 올리지 않는다. 아래 브랜치가 **PC 병합 대기** 중이다.

| 브랜치 | 대기 커밋 | 내용 |
|---|---|---|
| `ccr-478bb848-5x7ulr` | 5개 | 세션 규칙(CLAUDE.md)·push 차단 훅, 한글 폰트 부트스트랩 수정, credit.json 2026-10-19 기록 |

> ⚠️ **병합은 항상 이부장 세션에 보고하고 지시를 받은 뒤에 한다.**
> 버튼도 "이부장 지시를 받았나요?" 를 먼저 묻는다.

## 실행 (버튼)
`병합_실행.bat` 을 **더블클릭**한다 (저장소 클론 폴더 안에서).
→ 대기 커밋 목록 확인 → `y` → `main` 에 병합. **push 는 하지 않는다.**
다른 브랜치면: `병합_실행.bat 브랜치이름`

## 수동 (같은 동작)
```
git fetch origin
git checkout main
git pull --ff-only origin main
git merge --no-ff origin/ccr-478bb848-5x7ulr
```

## 병합 후
`deploy.bat` 으로 평소처럼 배포한다. 충돌이 나면 `git merge --abort` 후 Claude 에게 알린다.
병합이 끝나면 이 파일의 해당 행을 지운다.
