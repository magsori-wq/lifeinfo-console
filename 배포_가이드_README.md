# 생활정보 모음 · 통합 운영 콘솔 — 실행 & 배포 가이드

이 `webapp` 폴더 = 통합 웹앱입니다. 5개 파일로 구성됩니다.

- `index.html` — 허브(탭 메뉴 + Claude 디스패치) ← **이게 메인**
- `dashboard.html` — 운영 대시보드(체크리스트)
- `generator.html` — 글 HTML 생성기
- `osmu.html` — OSMU 변환기
- `jisikin.html` — 지식인 답변 헬퍼
- `thumbs/` — 블로그 글 썸네일 15장 (배포 후 'URL 사용'으로 글에 삽입)

> ⚠️ GitHub에 올릴 때 **`thumbs` 폴더까지 함께** 올리세요. (GitHub 웹 업로드 화면에 webapp 폴더 안의 파일들을 드래그하면 thumbs 폴더도 같이 올라갑니다.)
> 배포되면 각 썸네일 주소는 다음과 같습니다:
> `https://<내깃허브아이디>.github.io/<저장소명>/thumbs/01_youtube.png`

### 글 ↔ 썸네일 매칭 (배포 후 'URL 사용'으로 삽입)
| 글 | 썸네일 파일 |
|---|---|
| 유튜브 프리미엄 해지 | thumbs/01_youtube.png |
| 카카오톡 차단 확인 | thumbs/02_kakao.png |
| 정부24 주민등록등본 | thumbs/03_gov24.png |
| 실업급여 | thumbs/04_unemploy.png |
| 알뜰폰 | thumbs/05_mvno.png |
| 전입신고 | thumbs/06_movein.png |
| 건강보험 환급금 | thumbs/07_insurance.png |
| 자동차 과태료·범칙금 | thumbs/08_fine.png |
| 휴면예금 | thumbs/09_dormant.png |
| 인스타 삭제 | thumbs/10_insta.png |
| 토익 성적표 | thumbs/11_toeic.png |
| 카뱅 모임통장 | thumbs/12_bank.png |
| 근로장려금 | thumbs/13_eitc.png |
| 기초연금 | thumbs/14_basicpension.png |
| 재산세 | thumbs/15_property.png |

---

## A. 로컬에서 바로 쓰기 (가장 간단)

**방법 1 — 더블클릭**
`index.html`을 더블클릭하면 브라우저에서 열립니다. (탭 메뉴로 모든 도구 이용)

**방법 2 — 로컬호스트 서버 (권장: 일부 브라우저의 iframe 제한 회피)**
1. 윈도우 검색 → '명령 프롬프트' 실행
2. 아래 입력(폴더 경로로 이동):
   ```
   cd "C:\Users\...\leesg_개인\webapp"
   python -m http.server 8000
   ```
3. 브라우저 주소창에 **http://localhost:8000** 입력
   (파이썬이 없으면 https://www.python.org 에서 설치 후 진행)

---

## B. 웹 배포 — GitHub Pages (외부에서 접속, 무료 영구)

> 계정·로그인이 필요해 마지막 단계는 직접 하셔야 합니다. (제가 대신 로그인/계정생성 불가)
> 이 웹앱은 로그인·개인데이터가 없는 '도구 모음'이라 공개되어도 안전합니다.

**브라우저만으로 (Git 몰라도 됨)**

1. **github.com** 접속 → 로그인(계정 없으면 'Sign up'으로 가입)
2. 우측 상단 **+** → **New repository**
   - Repository name: 예) `lifeinfo-console`
   - **Public** 선택 → **Create repository**
3. 새 저장소 화면에서 **"uploading an existing file"** 클릭
4. `webapp` 폴더 안의 **5개 파일을 모두 드래그**해서 올림 → 아래 **Commit changes**
   (⚠️ 폴더째 말고 '파일 5개'를 올려서 index.html이 최상위에 오게)
5. 상단 **Settings → 좌측 Pages**
   - Source: **Deploy from a branch**
   - Branch: **main** / 폴더 **/(root)** → **Save**
6. 1~2분 뒤 페이지 새로고침하면 주소가 뜹니다:
   **https://<내깃허브아이디>.github.io/lifeinfo-console/**
   이 주소를 어디서나(폰·외부 PC) 열면 됩니다.

**업데이트 방법**: 도구를 수정하면, 같은 저장소에서 'Add file → Upload files'로 해당 파일만 다시 올리면 자동 반영됩니다.

---

## C. Claude 디스패치 사용법

허브 상단의 **⚡ Claude 디스패치** 탭에서:
1. 주제/키워드 입력 (예: 근로장려금)
2. 버튼 클릭 → **프롬프트가 자동 복사 + claude.ai 새 탭 열림**
3. Claude 입력창에 **붙여넣기(Ctrl+V)** → 실행

※ 공개 사이트라 API 키를 넣을 수 없어(보안), '프롬프트 복사 + Claude 열기' 방식입니다.
   완전 자동 실행은 이미 설정된 '매일 아침 글감 추천' 예약작업이 담당합니다.
