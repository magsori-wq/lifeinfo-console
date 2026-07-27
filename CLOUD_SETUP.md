# 클라우드 작업 환경 구축 계획

**목적**: PC 한 대가 고장나도 블로그 운영이 멈추지 않게 한다.
2026-07-26 사고(내장 패널 고장 + 안전모드 잠금)로 며칠간 작업이 전면 중단됐다.
원인은 하드웨어가 아니라 **작업 환경 전체가 `C:\lifeinfo` 한 곳에만 존재했다는 구조**다.

---

## 1. 무엇이 문제였나

> ### ⚠️ 2026-07-27 정정
>
> 이 문서는 처음에 **"`studio/` 는 어떤 저장소에도 없다"** 는 전제로 쓰였다. **틀렸다.**
> private 저장소 **`magsori-wq/lifeinfo-source`** 가 이미 존재하고, `studio/`(131개) ·
> `posts/`(108개) · `thumbs_naver/` · `webapp/` · `CLAUDE.md` 전체를 담고 있다.
> 자격증명 위생도 이미 갖춰져 있었다 — `.gitignore` 에 `studio/.secrets/`,
> `*_token.json`, `*_client.json` 이 진작 들어 있고 커밋된 비밀은 없다.
>
> 오판의 원인: `lifeinfo-console` 의 git 이력만 확인하고 "추적된 적 없음" 을
> **"백업이 없음"** 으로 넘겨짚었다. 실제 구조는 2단이다 —
> `lifeinfo-source`(private, 전체) → `deploy.bat` → `lifeinfo-console`(public, 배포 subset).

| 항목 | 사고 당시 상태 |
|---|---|
| 콘솔·DB·썸네일 | ✅ 공개 저장소에 백업 (07-26 06:00까지 무손실) |
| `studio/` · `posts/` · `CLAUDE.md` | ✅ **`lifeinfo-source`(private)에 백업됨** |
| 단, 그 백업의 최신 커밋 | ⚠️ **2026-07-23 17:51 — 4일치 누락** |
| Blogger API 자격증명 | ❌ PC에만 존재 (의도된 설계 — 재발급으로 복구) |
| **작업 가능한 장소** | ❌ **그 PC 앞뿐** |

**진짜 위험은 "백업이 없다" 가 아니라 "백업이 뒤처진다" 였다.** 사고 시점에
`collab.json` 은 `uncommitted: 77` 이었고, 실제로 `lifeinfo-source` 에는 최근 발행
3편의 원고, 대기 글 원고, 썸네일 126~131 이 빠져 있었다.

그리고 마지막 항목은 그대로 유효하다 — 데이터가 살아 있어도 **작업할 곳이 없으면
운영은 멈춘다.** 이것이 클라우드 환경을 만드는 이유다.

---

## 2. 목표 구조

```
┌─────────────────────────────────────────────┐
│  lifeinfo-source        (기존, PRIVATE)      │  ← 전체 원본 = C:\lifeinfo
│    studio/       발행 파이프라인 (파이썬)      │
│    posts/        .lsg 본문 원본               │
│    webapp/       콘솔 소스 (배포 전 원본)      │
│    thumbs/ thumbs_naver/  CLAUDE.md          │
│    ⚠ 자격증명은 .gitignore 로 제외됨          │
└─────────────────────────────────────────────┘
                     │ 발행·배포
                     ▼
┌─────────────────────────────────────────────┐
│  lifeinfo-console      (기존, PUBLIC)        │  ← 배포 결과물
│    *.html  thumbs/  logo/                    │
│    lifeinfo_db.txt  *.json                   │
│    = GitHub Pages 호스팅                     │
└─────────────────────────────────────────────┘
```

**저장소를 둘로 나누는 이유**: `lifeinfo-console` 은 GitHub Pages 때문에 반드시 공개여야
한다. 여기에 `studio/` 를 넣으면 **자격증명이 섞여 들어갈 위험**이 생기고, 한 번 커밋되면
이력에 영구히 남는다. 도구는 private 쪽에 두는 것이 유일하게 안전한 배치다.
**이 구조는 이미 그렇게 되어 있었다** — 새로 만들 필요가 없었다.

### 작업 방식 — PC·클라우드 병행 규칙 (2026-07-27 실측 확립)

두 곳에서 같이 작업할 수 있다. 단 아래를 지켜야 한다.

> 🔴 **클라우드는 `lifeinfo-source` 에만 push 한다.**
> `lifeinfo-console` 은 `C:\lifeinfo-deploy` 클론에서 `deploy.bat` 이 단독 관리한다.
> 클라우드가 직접 push 하면 그 클론의 이력이 갈라져 배포가 거부된다.
> (실측: `! [rejected] main -> main (fetch first)` → `C:\lifeinfo-deploy` 에서
> `git reset --hard origin/main` 후 재배포로 해소. 이 폴더는 순수 파생물이라
> 병합 없이 리셋해도 잃는 것이 없다.)

**예외** — `deploy.bat` 의 robocopy 대상은 `webapp/*` · `thumbs/` · `logo` · `buttons` ·
`videos` 뿐이다(deploy.bat 확인). 따라서 `tools/` · `.github/workflows/` · `restore/` ·
`docs/` 는 console 에 직접 push 해도 충돌하지 않는다. 자동화 도구를 그렇게 넣었다.

| 작업 | 클라우드 | PC |
|---|---|---|
| 콘솔 HTML · 자동화 도구 · 문서 | ✅ | ✅ |
| 썸네일 생성 | ✅ (기존 디자인 97.3% 재현 검증) | ✅ |
| 중복 게이트 · 정합성 검사 | ✅ | ✅ |
| **팩트체크(`.go.kr`)** | ❌ 프록시 403 | ✅ |
| **Blogger 발행 · 피드 조회** | ❌ | ✅ |
| `deploy.bat` · `bake` | ❌ (CLAUDE.md: 사용자 실행) | ✅ |
| 네이버·쓰레드·인스타 게시 | ❌ | ✅ 수동 |

**순서**
- PC 시작 = `cd C:\lifeinfo && git pull origin main` · 종료 = `.\deploy.bat`
- 클라우드 종료 = `lifeinfo-source` push → 사용자가 PC 에서 pull
- **양쪽에서 동시에 `webapp/*` 를 만지지 않는다.** (실측: 같은 `queue.json` 을 양쪽에서
  고쳐 F1-08 주제가 되돌아갈 뻔했다 — push 가 거부된 덕에 원격 위에 다시 쌓아 해소)

### 알려진 양성 경고

`128_visitjapanweb.png` 가 고아로 잡힌다. F1-08 이 주제를 **보조배터리 기내 반입**으로
바꿨기 때문이다. 비지트재팬웹 원고는 `lifeinfo-source` 에 남아 있어 나중에 발행할 수
있으므로 **파일은 지우지 않고 둔다** — 지우면 썸네일을 다시 만들어야 한다.
(대조: `59_car_bond.png` 은 source 에도 없고 어떤 원고도 참조하지 않아 삭제했다.)

### 참고


- **작업 장소**: [claude.ai/code](https://claude.ai/code) 에서 `lifeinfo-source` 세션을 연다.
  브라우저만 있으면 되므로 **휴대폰·아이패드·아무 PC 에서도** 작업 가능하다.
- **발행**: 아직 PC 전용이다(프록시가 Blogger 를 막는다). 클라우드에서 되게 하는 것이 Phase 2.
- **배포**: `deploy.bat` 은 **사용자가 PC 에서** 실행한다(CLAUDE.md 규칙 — Claude 임의 실행 금지,
  연속 push 가 Pages 배포한도를 넘긴다). 클라우드는 `lifeinfo-source` push 까지만.
- **예약작업**: 월 1일 팩트체크, 헬스체크 → GitHub Actions.

---

## 3. 클라우드에서 되는 것 / 안 되는 것

### ✅ 검증 완료 (2026-07-26, 이 컨테이너에서 실측)

| 항목 | 결과 |
|---|---|
| Python 3.11 | 사용 가능 |
| Pillow 설치 | `pip3 install Pillow` → 12.3.0 성공 |
| Noto Sans CJK 설치 | `apt-get install fonts-noto-cjk` 성공 |
| **한글 썸네일 생성** | **1200x630 실제 생성·한글 렌더링 확인** |
| git / GitHub 연동 | 사용 가능 |

썸네일 생성이 가장 걱정되던 관문이었는데(한글 폰트가 없으면 □□□ 로 나온다) 해결됐다.
`.claude/bootstrap.sh` 가 세션 시작 시 자동으로 이 환경을 갖춘다.

### ⚠️ 제약 — 프록시 정책

이 컨테이너의 외부 접속은 프록시를 거치며 **허용 목록 방식**이다. 실측 결과:

| 대상 | 결과 |
|---|---|
| `api.github.com` | ✅ 200 |
| `pypi.org` (pip) | ✅ 통과 |
| Ubuntu apt 저장소 | ✅ 통과 |
| `lifeinfo8975.blogspot.com` | ❌ 403 (CONNECT 거부) |
| `magsori-wq.github.io` | ❌ 403 |

즉 **블로그 피드·Pages 를 직접 읽는 작업은 이 환경에서 막힌다.**
Blogger API 발행도 같은 제약을 받을 가능성이 크다 → **Phase 2 에서 반드시 실측 확인이 필요하다.**
막힌다면 대안은 GitHub Actions 러너에서 실행하는 것이다(Actions 는 이 프록시 정책과 무관).

### ❌ 자동화 불가 (수동 유지)

- **네이버 블로그·쓰레드·인스타그램 게시** — 로그인·봇차단. OSMU 는 초안까지만 자동, 게시는 사람이.
- **GSC 색인요청** — Indexing API 는 채용공고·방송 일정용이라 일반 글에 쓸 수 없다. 브라우저 수동.

이 두 개는 원래도 수동이었으므로 손실이 없다.

---

## 4. 단계별 실행

### Phase 0 — 지금 완료 (PC 없이 가능했던 것)

- [x] `.gitignore` — 공개 저장소에 자격증명이 커밋되는 것을 차단
- [x] `.claude/bootstrap.sh` + `settings.json` — 세션 시작 시 Pillow·Noto CJK 자동 설치
- [x] 클라우드에서 한글 썸네일 생성 검증
- [x] 프록시 제약 실측 및 문서화
- [x] 이 계획 문서

### Phase 1 — 이미 되어 있었음 (정정)

- [x] private 저장소 — **`lifeinfo-source`** 가 이 세션 전부터 존재
- [x] `studio/`, `posts/`, `thumbs_naver/`, `CLAUDE.md` 이관 완료
- [x] 자격증명 차단 — `.gitignore` 에 이미 반영, 커밋된 비밀 없음(스캔 확인)
- [x] **`lifeinfo-source` 최신화** — 2026-07-27 사용자가 89파일 push (`2f061e1`)
- [x] `CLAUDE.md` 에 디스플레이 안전 규칙 + 클라우드 병행 규칙 추가 (`3a5f190`)

새 저장소를 만들 필요가 없었다. `restore/backup_studio.bat` 은 이 오판 위에서 만든
것이므로 **일상 운영에는 쓰지 않는다** — 필요한 것은 스크립트가 아니라
`cd C:\lifeinfo && git add -A && git commit && git push` 습관이다.

> 그 스크립트를 만드는 과정에서 자격증명 게이트의 실패 방식 두 가지를 실측으로
> 배웠고, 그건 남길 가치가 있다. `restore/scan_secrets.py` 는 어느 폴더에든 쓸 수
> 있으므로 커밋 전 점검용으로 계속 유효하다.
>
> **1차 실행에서 실제로 토큰이 스테이징됐다.** `studio/.secrets/` 의 OAuth 토큰
> 4개가 목록에 올랐고 사람이 읽고 중단시켰다. 원인은 ① 제외 패턴을
> `token*.json` 으로 앞을 고정해 `blogger_token.json` 을 놓친 것 ② 인라인
> PowerShell 스캔이 이스케이프 오류로 실행되지 않았는데 "clean" 을 출력한 것.
> **검사가 돌지 않고 통과를 보고하는 것이 가장 위험한 실패 방식이다.**
> 자동 게이트가 통과했다고 사람 검토를 생략하면 안 된다는 근거가 됐다.

### Phase 2 — 클라우드 발행 검증

- [ ] Blogger OAuth 자격증명 재발급 (Google Cloud Console)
- [ ] refresh token 을 GitHub Secrets 에 등록
- [ ] `studio/` 가 환경변수에서 자격증명을 읽도록 수정 (파일 경로 하드코딩 제거)
- [ ] **클라우드 세션에서 Blogger API 도달 가능한지 실측** ← 프록시 제약 확인
- [ ] 막히면 GitHub Actions 러너 경로로 전환
- [ ] 테스트 글 1편을 클라우드에서 발행 → 실패 시에도 안전하게 되돌릴 수 있는 임시보관 상태로

### Phase 3 — 자동화 파이프라인 (착수 완료)

`studio/` 없이도 만들 수 있는 검사 두 개를 Actions 로 올렸다.

| 워크플로 | 언제 | 무엇을 |
|---|---|---|
| `console-check.yml` | push · 매일 06:10 KST · 수동 | 저장소 정합성 13개 항목 |
| `feed-drift.yml` | 매일 07:00 KST · 수동 | 라이브 피드 ↔ DB 대조 (읽기 전용) |
| `link-rot.yml` | 매월 1일 · 수동 | 본문의 `.go.kr` 공식 링크 생존 확인 |

- [x] `tools/console_check.py` — 저장소 정합성 검사
- [x] `tools/feed_drift.py` — 라이브 피드 드리프트 검사
- [x] `tools/link_rot.py` — 공식 링크 부패 검사 (오탐 방지: 403 봇차단과 404 를 분리)
- [x] `tools/dupcheck.py` — 중복 게이트 (클라우드에서도 실행 가능)
- [x] `tools/make_thumb.py` — 썸네일 생성기 (기존 디자인 97.3% 재현 검증)
- [x] 세 워크플로 등록, 요약 패널·리포트 아티팩트 출력
- [ ] 월 1일 팩트체크 → Actions (`studio/` 이관 후)
- [ ] 썸네일 생성 → Actions 또는 세션 (`studio/` 이관 후)

#### 왜 저장소 쪽 검사가 따로 필요한가

`deploy.bat` 은 `git add` 로 추가·수정만 한다. **로컬에서 파일을 삭제해도 저장소에서는
지워지지 않는다.** 그래서 로컬 `selfcheck` 는 저장소의 실제 상태를 볼 수 없다.

실측 사례: 로컬 `health.json` 은 "고아 썸네일 없음" 인데, 저장소에는
`59_car_bond.png` 가 남아 있었다. `B2-03 자동차 채권 미환급금` 이 번호를 바꿔
`60_carbond_refund.png` 를 쓰게 되면서 버려진 파일이다.

> ✅ **2026-07-27 해소** — `lifeinfo-source` 를 확인해 근거를 확정하고 삭제했다:
> 그 파일은 source 에 **아예 없고**, `B2-03` 원고는 `thumbs/60_carbond_refund.png` 를
> 참조하며, **어떤 원고도 `59_car_bond` 를 참조하지 않는다.**
> (원고를 직접 확인할 수 있게 된 것이 판단 근거였다. 그 전에는 "본문이 참조할 수도
> 있으니 지우지 말 것" 이 맞는 판단이었다.)
> DB 의 `thumb` 필드와 본문의 실제 `<img src>` 는 다를 수 있다.
> 지우기 전에 해당 글 본문을 열어 확인해야 한다.

#### 왜 피드 검사는 Actions 에서만 되는가

Claude Code 웹 컨테이너의 프록시가 `blogspot.com` 을 차단한다(실측: CONNECT 403).
**Actions 러너에는 그 제약이 없다.** 그래서 라이브 데이터가 필요한 작업은 Actions 로
넘긴다 — Phase 2 의 Blogger API 발행도 여기서 막히면 같은 방법으로 우회한다.

---

## 5. CLAUDE.md 규칙 — ✅ 반영 완료 (2026-07-27, `lifeinfo-source` `3a5f190`)

`lifeinfo-source/CLAUDE.md` 에 넣었다. `studio/session_rules.py`(SessionStart 훅)가
세션 시작 시 주입하는 파일이라 **실제로 강제된다.**
- 디스플레이 안전 규칙 → `## 함정·규칙` 섹션 맨 앞(가장 파괴적이라 최상단)
- 클라우드 병행 규칙 → `## 핵심 구조` 의 저장소 항목 뒤

아래는 반영된 내용의 요지다.

```markdown
## 디스플레이 안전 규칙 (2026-07-26 사고 후 추가)

이 PC는 노트북 내장 패널이 고장나 **외부 모니터 1대만으로 동작**한다.
따라서 다음을 **제안하거나 실행하지 말 것**:

- 안전모드(safeboot) 부팅 — 안전모드는 다중 디스플레이 투사를 비활성화하므로
  외부 모니터가 꺼지고 **조작이 완전히 불가능해진다**
- `bcdedit` 부팅 설정 변경
- 디스플레이 드라이버 제거·롤백, 그래픽 어댑터 비활성화

부팅 설정 변경이 정말 필요하면, **먼저 화면 접근 수단(원격 데스크톱 등)이
확보되어 있는지 사용자에게 확인**한 뒤에만 진행한다.

## 백업 규칙

`studio/`, `posts/`, `references/` 는 커밋되지 않은 변경을 방치하지 않는다.
작업 종료 시 push 를 확인한다. 이 폴더들이 로컬에만 있는 상태는 사고 상태다.
```

---

## 6. 이 사고에서 얻은 교훈

1. **데이터 백업과 작업환경 백업은 다른 문제다.** DB 153편이 온전히 살아 있었지만
   작업할 곳이 없어 운영이 멈췄다.
2. **공개 저장소에 도구를 두면 안 된다.** 자격증명 유출 위험 때문에 `studio/` 를
   `lifeinfo-console` 에 넣을 수 없었고, 그래서 백업이 아예 없었다.
   private 저장소를 만드는 것이 정답이었다.
3. **화면 접근 수단을 잃는 조치는 되돌릴 수 없다.** 원격 데스크톱을 미리 켜두는 것만으로
   이번 사고는 30분 안에 끝났을 것이다.
