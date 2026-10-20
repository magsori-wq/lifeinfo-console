# 택시비즈 (클라우드판)

택시 영업·지출·충전·통장 입금을 기록하고 월 손익을 보는 웹앱. 의존성 없는 Node 20+ 서버, 데이터는 `DATA_DIR/db.json`에 저장.

## 실행
    TAXIBIZ_PASSWORD=비밀번호 node server.js     # http://localhost:8080
    TAXIBIZ_PASSWORD=x node test.js              # 테스트

## 클라우드 배포 (Docker)
    docker build -t taxibiz .
    docker run -p 8080:8080 -e TAXIBIZ_PASSWORD=비밀번호 -v taxibiz-data:/data taxibiz
Fly.io, Render, Railway 등에서 `/data`에 영구 볼륨을 붙이고 `TAXIBIZ_PASSWORD`를 설정하세요. HTTPS는 호스팅 쪽 프록시가 처리합니다.

## 환경변수
- `TAXIBIZ_PASSWORD` (필수) 로그인 비밀번호. `TAXIBIZ_SECRET`로 세션 서명키를 따로 둘 수 있음
- `DATA_DIR` 데이터 폴더, `PORT` 기본 8080

## 계산 기준 (기존 월말 점검 규칙 반영)
- 총매출 = 현금 + 카드 + 기타
- 개인지출(담배 등)은 사업 지출에서 제외, 가용잔액에서만 차감
- 생활비·사납금·근무일·카드수수료율은 설정 탭 한 곳에서만 관리 (수식에 숫자 직접 입력 없음)
- 월말 전망 = 일평균 순이익 × 월 근무일 − 생활비
- 사납금 지출은 실제 송금액을 지출 탭에 `사납금` 분류로 입력
