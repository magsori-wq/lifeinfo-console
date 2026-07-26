# 노트북 주모니터 고장 → 외부 모니터로 복구하기

**증상**: 노트북 내장 패널(주모니터) 고장 + 안전모드에서 보조(외부) 모니터 출력 안 됨.

**핵심 진단**: 안전모드가 원인이다. 안전모드는 「Microsoft 기본 디스플레이 어댑터」로
부팅하고, 이 상태에서 Windows는 **다중 디스플레이 투사 기능을 아예 끈다**.
안전모드에서 `Win + P` 를 누르면 "이 PC는 다른 화면에 표시할 수 없습니다"가 뜬다.
즉 안전모드 안에서는 외부 모니터를 살릴 방법이 없다. **안전모드를 벗어나는 것이 해법이다.**

---

## 0단계 — 먼저 확인 (30초)

외부 모니터에 **BIOS 로고나 부팅 화면이 잠깐이라도** 나오는가?

- **나온다** → 펌웨어가 외부 출력을 잡고 있다는 뜻. A경로로 거의 확실히 복구된다.
- **전혀 안 나온다 (계속 "신호 없음")** → C경로(하드웨어)로 간다. 케이블·포트를 먼저 바꿔볼 것:
  HDMI ↔ USB-C/DP 는 내부적으로 다른 경로를 타므로 한쪽만 죽어 있을 수 있다.

---

## A경로 — 안전모드 탈출 후 Win+P (권장, 가장 빠름)

내장 패널이 안 보이니 **전부 블라인드 타이핑**이다. 각 단계마다 넉넉히 기다려라.

### A-1. 안전모드 플래그 제거

안전모드가 반복된다면 `msconfig`의 안전부팅 옵션이 켜진 상태로 저장된 것이다.
이 플래그는 스스로 풀리지 않는다.

1. 부팅 완료까지 **2분** 기다린다 (로그인 화면 도달).
2. 비밀번호 입력 + `Enter` → 다시 **1분** 대기 (바탕화면 로딩).
3. `Win + R` → `cmd` 타이핑 → `Ctrl + Shift + Enter` (관리자 권한)
4. UAC 창이 뜬다 → `Alt + Y`
5. 아래를 타이핑하고 `Enter`:
   ```
   bcdedit /deletevalue {current} safeboot
   ```
6. 이어서 타이핑하고 `Enter`:
   ```
   shutdown /r /t 0
   ```

### A-2. 정상 부팅 후 출력 전환

정상 모드로 부팅되면 실제 GPU 드라이버가 올라오므로 외부 출력이 가능해진다.

1. 로그인 (비밀번호 + `Enter`) → **1분** 대기
2. `Win + P` → **1초 대기** → `↓` `↓` `↓` → `Enter`
   - 목록은 위에서부터 [PC 화면만 / 복제 / 확장 / **두 번째 화면만**] 순서다.
   - ↓ 3번 = "두 번째 화면만". 내장 패널이 죽었으니 이게 정답이다.
3. 안 되면 `Ctrl + Win + Shift + B` (그래픽 드라이버 리셋) 후 A-2를 다시.

> `Win + P` 는 로그인 **전**에는 잘 동작하지 않는다. 반드시 로그인 후에 하라.

### A-3. 복구되면 즉시 할 일

화면이 보이면 곧바로 고정해 둔다 — 재부팅 때마다 반복하지 않도록:

- 설정 → 시스템 → 디스플레이 → 외부 모니터 선택 → **"이 디스플레이를 주 디스플레이로 만들기"** 체크
- 설정 → 시스템 → 전원 → **덮개를 닫을 때: 아무 것도 하지 않음**
- 그리고 **원격 접속을 미리 켜 둔다** (다음에 같은 일이 생겼을 때 다른 PC에서 들어갈 수 있게):
  설정 → 시스템 → 원격 데스크톱 → 켜기. 또는 RustDesk / Chrome 원격 데스크톱 설치.

---

## B경로 — 블라인드로 원격접속 켜기 (A가 안 될 때)

화면 없이도 원격 데스크톱만 켜면 다른 PC에서 정상 화면으로 들어갈 수 있다.
A-1의 1~4단계로 **관리자 cmd**를 띄운 뒤:

```
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f
netsh advfirewall firewall set rule group="remote desktop" new enable=Yes
net start TermService
ipconfig
```

- Windows **Home 에디션은 RDP 호스트가 안 된다**. 이 경우 B경로는 실패한다 → C경로로.
- `ipconfig` 결과를 볼 수 없으니, 다른 PC에서 같은 공유기의 `192.168.x.x` 대역을 스캔하거나
  공유기 관리페이지에서 노트북 IP를 확인하라.
- 다른 PC에서: `mstsc` → 그 IP 입력 → 로그인.

> 안전모드에서는 RDP 서비스가 기본적으로 안 뜬다. 이 작업도 **정상 부팅 상태**에서 해야 한다.

---

## C경로 — 하드웨어 (A·B 모두 실패)

### C-1. 내장 패널 케이블 분리 (외부 모니터가 자동으로 주 디스플레이가 됨)
노트북을 열어 메인보드의 내장 패널 eDP/LVDS 커넥터를 분리한다. 내장 패널이 아예
없는 것으로 인식되어 외부 모니터가 유일한 출력이 된다. **가장 확실한 해법**이지만
분해가 필요하다. 자신 없으면 서비스센터에 "내장 패널 케이블 분리만" 요청하면 된다.

### C-2. SSD를 빼서 다른 PC에 연결 (데이터 우선 확보)
작업 재개가 급하다면 이게 최단 경로다. 화면 문제를 완전히 우회한다.

1. 노트북 SSD(NVMe/SATA) 분리 → USB 외장 케이스에 장착
2. 다른 PC에 연결 → **`C:\lifeinfo` 폴더 전체를 통째로 복사**
3. 특히 다음은 GitHub에 백업이 없으므로 반드시 챙긴다:
   - `studio\` (파이썬 패키지 전체)
   - `posts\` (.lsg 원본)
   - `deploy.bat`, `CLAUDE.md`
   - `thumbs_naver\`
   - Blogger API 자격증명 파일 (client_secret*.json, token*.json 등)
4. BitLocker가 걸려 있으면 복구 키가 필요하다 →
   https://account.microsoft.com/devices/recoverykey (Microsoft 계정으로 로그인)

---

## 참고: 지금 GitHub에 안전하게 있는 것 / 없는 것

`magsori-wq/lifeinfo-console` 최신 커밋 = **2026-07-26 06:00** (검증 완료, 자체 정합성 OK)

**있음 (100% 복구 가능)**
- 콘솔 HTML 전체 (index, dashboard, progress, search, categories, adsense, gsc, generator, jisikin, osmu)
- `thumbs/` 161개 · `logo/`
- `lifeinfo_db.txt` — 153편 전량, URL·썸네일·OSMU 링크까지 완비
- 상태 JSON 전체 (queue, pending, progress, health, index_status, gsc_requested, posts_index, covered_topics, adsense_plan, collab, draft_hygiene)
- `trends.txt`

**없음 (git 이력 전체를 확인했다 — 한 번도 추적된 적 없음)**
- `studio\` ← **가장 큰 손실 위험**. 발행 파이프라인 전체
- `posts\` (.lsg 108개) ← `restore/recover_posts_from_blogger.py` 로 Blogger 피드에서 회수 가능
- `deploy.bat`, `CLAUDE.md`, `thumbs_naver\`
- Blogger API 자격증명 ← 복구 불가, Google Cloud Console에서 재발급

즉 **콘솔·DB·썸네일은 잃지 않았다.** 위험한 건 `studio\`와 자격증명이고,
`posts\`는 발행본에서 되살릴 수 있다.

---

## 새 PC / 복구된 PC에서 재구축

```
restore\restore_console.bat                     GitHub 사본을 C:\lifeinfo_restore 로 클론
python restore\recover_posts_from_blogger.py --dry-run    posts 회수 예행연습
python restore\recover_posts_from_blogger.py             실제 복구
```

`restore_console.bat` 은 기존 `C:\lifeinfo` 를 **절대 덮어쓰지 않는다** — 별도 폴더에
클론만 한다. 부분적으로 살아 있는 설치를 망치지 않기 위한 설계다.

---

## 재발 방지 (복구 후 반드시)

1. `studio\` 를 **별도 private 저장소**에 백업.
   현재 `lifeinfo-console` 은 GitHub Pages 공개 저장소이므로 자격증명이 섞여 들어가면
   유출된다. `studio\` 는 반드시 private 쪽으로.
2. 자격증명은 어떤 저장소에도 커밋하지 않는다 (`.gitignore`: `client_secret*.json`,
   `token*.json`, `*.pem`, `credentials*`).
3. 원격 데스크톱을 미리 켜 둔다 — 화면이 죽어도 다른 PC에서 들어갈 수 있다.
4. 외부 모니터를 주 디스플레이로 고정해 두면, 내장 패널이 죽어도 부팅 직후부터 보인다.
