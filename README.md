# mydart-mcp

한국 금융감독원 전자공시시스템(DART)의 [OpenDART API](https://opendart.fss.or.kr)를 MCP 도구로 감싼 서버.
Claude가 상장사 공시·재무제표·첨부파일을 직접 조회해서 분석할 수 있게 한다.

- **공시 첨부파일 읽기** — 감사보고서·외부평가의견서 같은 HWP/PDF를 텍스트로. **공개된 DART MCP 중 이걸 하는 건 여기뿐이다**
- **OpenDART 83개 오픈API 전부** 커버 (재무제표, 지분공시, 주요사항보고서, 증권신고서 …)
- **내 PC에서도, 폰·웹에서도** — 확장 파일로 설치하거나 Vercel에 올려 커넥터로 붙인다
- **도구는 15개뿐** — 83개를 항목 선택형으로 묶어 대화 여유를 남긴다

```
"삼성전자 2025년 연결 손익계산서 정리해줘"
"네이버랑 카카오 실적 비교해줘"
"이 합병 공시 첨부된 외부평가의견서 읽고 합병비율 근거 정리해줘"
```

## 설치 방법 세 가지

| | 어디서 쓰나 | 시간 |
|---|---|---|
| [**확장 파일**](#확장-파일로-설치-가장-쉬움--1분) | 이 PC의 Claude Desktop | 1분 |
| [**스크립트**](#스크립트로-설치-확장-파일이-안-될-때--5분) | 이 PC (확장 파일이 안 될 때) | 5분 |
| [**Vercel 배포**](#원격으로-쓰기--폰웹-채팅-선택) | 폰·웹 채팅 어디서나 | 10분 |

---

# 다른 DART MCP와 무엇이 다른가

공개된 것이 여럿 있다. 실제로 코드를 열어 확인한 내용이다.

| | 방식 | 도구 수 | 첨부파일 | 특징 |
|---|---|---|---|---|
| **mydart** (이것) | 로컬 + 원격 | 15 | **읽음** | 항목 선택형, 기업목록 주 1회 자동 갱신 |
| [procpalee](https://github.com/procpalee/OpenDART-MCP-Server) | 원격 (Vercel) | 82 | 없음 | 마크다운 표 출력, 완성도 높음 |
| [snaiws](https://github.com/snaiws/DART-mcp-server) | 로컬 (Docker) | 89 | 없음 | XML 표 → CSV 변환 |
| [2geonhyup](https://github.com/2geonhyup/dart-mcp) | 로컬 (uv) | — | 없음 | XBRL 지원 |
| [open-proxy](https://github.com/MarcoYou/open-proxy-mcp) | 원격 (fly.io) | 25 | 없음 | 거버넌스·주주총회 분석 특화 |
| [seapy/dartcli](https://github.com/seapy/dartcli) | — | — | — | MCP가 아니라 Go CLI |

## 이 서버가 나은 점

**① 첨부파일을 읽는다 — 이게 제일 큰 차이다**

DART 공시는 "본문 + 첨부" 구조이고, **감사보고서·외부평가의견서·계약서처럼 정작 중요한 내용은 첨부에 있다.**
그런데 OpenDART 오픈API에는 첨부 엔드포인트가 없다. 그래서 API만 감싼 서버들은 이걸 못 한다.

합병비율 산정 근거, 감사인의 강조사항, 계속기업 불확실성 문단 — 전부 첨부 안에 있다.
숫자만 보는 것과 근거 문서를 읽는 것의 차이다.

**② 로컬과 원격을 모두 지원한다**

다른 것들은 둘 중 하나다. 여기는 같은 코드로 둘 다 된다 — 노트북에서는 확장 파일로,
밖에서는 Vercel에 올린 주소로. 첨부파일 읽기는 원격에서도 그대로 된다.

**③ 도구가 15개다**

83개 API를 도구 하나씩 만들면 그만큼 대화 컨텍스트를 먹는다. 여기서는 카테고리별로 묶고
선택 가능한 항목 이름을 도구 설명에 담았다. 모델이 별도 조회 없이 바로 고른다.

**④ 기업 목록이 최신이다**

10만 건을 DART에서 받아 **7일마다 새로 갱신**한다. 파일로 박아 두는 방식은 그 시점 이후
신규 상장사를 이름으로 못 찾는다 — procpalee가 그렇다(2026년 3월 기준으로 고정).

**⑤ 원격으로 써도 인증키가 섞이지 않는다**

키를 서버에 저장하지 않고 주소로 받아 **그 요청 동안만** 쓴다. 전역 변수에 담으면 한 사람의
키가 다음 사람 요청에 딸려 나갈 수 있어, 요청 단위로 갈리는 `ContextVar`에 담고
동시 요청 두 개를 경쟁시키는 테스트로 고정해 두었다.

**⑥ 설치가 끝났는지 한 번에 확인된다**

`mydart-mcp-selftest`가 공시검색·고유번호·재무제표·첨부목록·첨부추출까지 6가지를 훑고
어디서 깨졌는지 알려준다. 사내 방화벽 차단도 여기서 드러난다.

## 저쪽이 나은 점

공정하게 적는다.

- **출력 형태** — procpalee는 마크다운 표로 내보내 채팅에서 바로 읽힌다. 여기는 JSON을 돌려주고
  표로 만드는 건 모델에 맡긴다
- **도구 이름이 API와 1:1** — 정확히 뭘 부를지 모델이 헷갈릴 여지가 적다. 대신 컨텍스트를 먹는다
- **XBRL** — 2geonhyup은 지원한다. 여기는 아직 안 한다
- **표 → CSV 변환** — snaiws는 공시 본문의 표를 CSV로 정리해 준다
- **검증 범위** — 개인이 만든 것이고, 실물 DART로 확인된 건 selftest가 훑는 경로다.
  나머지 API는 아직 실제 응답으로 확인되지 않았다

---

# 설치 (Windows + Claude Desktop)

## 준비물

| | |
|---|---|
| OpenDART 인증키 | [여기서 무료 발급](https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do) (일 20,000건) |
| Claude Desktop | [claude.ai/download](https://claude.ai/download)의 **정식 설치 파일**. Microsoft Store 버전은 안 된다 (아래 참고) |
| GitHub 로그인 | 이 저장소가 비공개면 로그인해야 코드를 받을 수 있다 |
| 관리자 권한 | **필요 없다.** 모두 사용자 폴더에 설치된다 (회사 노트북에서도 가능) |

## 확장 파일로 설치 (가장 쉬움 · 1분)

1. 이 저장소에서 **`mydart-mcp.mcpb`** 를 클릭 → 오른쪽 **Download** 버튼으로 받는다
2. 받은 파일을 **더블클릭**한다
3. Claude Desktop이 열리며 설치 여부를 묻는다 → **Install**
4. **OpenDART 인증키**를 넣는 칸이 나온다 → 붙여넣고 저장

끝입니다. 파이썬도 uv도 따로 깔 필요가 없습니다 — Claude Desktop이 알아서 준비합니다.
첫 실행에만 몇 초 더 걸리고 그다음부터는 바로 뜹니다.

> **안 될 수도 있습니다.** 이 방식(uv 런타임)은 아직 실험 단계라, Claude Desktop 버전에 따라
> 설치가 안 되거나 서버가 안 뜰 수 있습니다. 그때는 아래 스크립트 방식으로 하면 됩니다.
> 자체점검(`mydart-mcp-selftest`)도 스크립트 방식에만 딸려 옵니다.

## 스크립트로 설치 (확장 파일이 안 될 때 · 5분)

1. 이 저장소 → 초록색 **Code** → **Download ZIP** → 압축 해제
2. **`pyproject.toml`이 바로 보이는 폴더**를 연다 (압축을 풀면 같은 이름 폴더가 한 겹 더 있는 경우가 많다)
3. 폴더 창의 **주소창을 클릭** → `powershell` 입력 → 엔터
4. 아래 한 줄을 붙여넣고 엔터:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

인증키를 물어보면 붙여넣는다 (화면에 표시되지 않는다). 미리 주려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -ApiKey "발급받은키"
```

스크립트가 하는 일: Store 버전 Claude 확인 → uv 설치 → 실행 중인 서버 종료 → 프로그램 설치 →
Claude 설정에 `mydart` 추가(기존 서버는 보존, `.bak` 백업) → **자체점검 실행**.

마지막에 자체점검이 아래처럼 나오면 DART 쪽은 정상이다.

```
mydart-mcp 자체점검

  ✓  API 키 설정: 40자 설정됨
  ✓  OpenDART 연결: 최근 7일 공시 3,806건 조회됨
  ✓  기업 고유번호 조회: 삼성전자 → 00126380
  ✓  재무제표 조회: 2025년 손익계산서 계정 17개 (통화 KRW)
  ✓  공시 첨부 목록: 공시 20260807000794 첨부 1개 — ...
  ✓  첨부파일 읽기: ... → 51,203자 추출

통과 6 · 건너뜀 0 · 실패 0
```

**6개 다 ✓여야 다음으로 간다.** 실패해도 멈추지 않고 끝까지 돌기 때문에 어디서 깨졌는지 한눈에 보인다.

그다음 Claude Desktop을 실행하고 **설정 → 개발자(Developer)** 에 `mydart`가 보이는지 확인한다.
채팅창에 `삼성전자 찾아줘`를 넣어 `00126380`이 나오면 끝이다.

> 슬래시(`/`) 메뉴에는 안 나타난다. 그건 프롬프트용이고, MCP **도구**는 Claude가 필요할 때
> 알아서 호출한다. 설정 → 개발자에 떠 있으면 정상이다.

## 새 PC로 옮길 때

챙길 것은 **인증키 하나뿐이다.** 파일은 저장소에서 다시 받으면 된다.
새 PC에 Claude Desktop을 설치·로그인해 둔 뒤 위 순서를 그대로 반복한다.

---

# 손으로 설치하려면

스크립트가 막히거나, 각 단계에서 무슨 일이 일어나는지 보고 싶을 때. 30분쯤 걸린다.
**순서대로 하고, 각 단계의 확인을 건너뛰지 않는 게 결국 빠르다.**

## 0단계 · Microsoft Store 버전 Claude 제거 ⚠️

**이걸 먼저 하지 않으면 나머지가 전부 헛수고가 된다.**

Store 버전 Claude는 설정 파일을 격리된 폴더에서 읽는다. 표준 위치에 설정을 넣어도 앱이 못 본다.

PowerShell을 열고 (시작 버튼 → `powershell` 입력 → 엔터):

```powershell
Get-AppxPackage *Claude*
```

무언가 나오면 Store 버전이 깔려 있는 것이다. 제거한다:

```powershell
Get-AppxPackage *Claude* | Remove-AppxPackage
```

그다음 [claude.ai/download](https://claude.ai/download)에서 **정식 설치 파일**을 받아 설치한다.

확인 — Claude를 실행한 상태에서:

```powershell
Get-Process Claude | Select-Object -ExpandProperty Path -Unique
```

`...\AppData\Local\AnthropicClaude\...` 가 나와야 한다.
`...\WindowsApps\Claude_...` 가 나오면 아직 Store 버전이다.

## 1단계 · uv 설치

`uv`는 파이썬 프로그램을 자동으로 준비·실행해 준다. 파이썬을 따로 깔 필요 없다.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**설치 후 PowerShell 창을 닫고 새로 연다** (경로 인식에 필요). 확인:

```powershell
uv --version
```

## 2단계 · 코드 받기

1. 브라우저에서 이 저장소 접속 → 초록색 **Code** → **Download ZIP**
2. 압축을 푼다
3. **`pyproject.toml`이 바로 보이는 폴더**를 찾는다 — 압축을 풀면 같은 이름 폴더가 한 겹 더 있는 경우가 많다

## 3단계 · 그 폴더에서 PowerShell 열기

파일 탐색기에서 그 폴더를 열고 → **주소창을 클릭** → `powershell` 입력 → 엔터.
그 위치에서 PowerShell이 열린다. 경로를 타이핑할 필요가 없다.

확인:

```powershell
dir pyproject.toml
```

**파일 정보가 안 나오면 폴더가 틀린 것이다. 여기서 멈추고 폴더부터 바로잡는다.**

## 4단계 · 설치 + 설정 (명령 2개)

먼저 인증키를 변수에 담는다. 키 부분만 바꿔서:

```powershell
$key = "여기에_발급받은_인증키"
```

이어서 아래 전체를 복사해 붙여넣고 엔터. 1~2분 걸린다.

```powershell
Get-Process Claude,mydart-mcp -ErrorAction SilentlyContinue | Stop-Process -Force
& "$env:USERPROFILE\.local\bin\uv.exe" tool install --force .
$exe = "$env:USERPROFILE\.local\bin\mydart-mcp.exe"
$path = "$env:APPDATA\Claude\claude_desktop_config.json"
if (Test-Path $path) { Copy-Item $path "$path.bak" -Force; $cfg = Get-Content $path -Raw | ConvertFrom-Json } else { New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null; $cfg = [pscustomobject]@{} }
if (-not $cfg.mcpServers) { $cfg | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{}) -Force }
$cfg.mcpServers | Add-Member -NotePropertyName mydart -NotePropertyValue ([ordered]@{ command = $exe; env = [ordered]@{ DART_API_KEY = $key } }) -Force
[System.IO.File]::WriteAllText($path, ($cfg | ConvertTo-Json -Depth 30))
(Get-Content $path -Raw) -replace '"DART_API_KEY":\s*"[^"]*"','"DART_API_KEY": "***"'
```

이 명령이 하는 일:

- 실행 중인 서버를 **먼저 끈다.** 돌고 있으면 실행 파일이 잠겨
  `failed to remove directory ... 액세스가 거부되었습니다 (os error 5)`가 난다
- 프로그램을 `mydart-mcp.exe`로 **미리 설치**한다
- Claude 설정 파일에 `mydart` 항목을 **추가**한다. 이미 `myacc` 같은 다른 서버가
  등록돼 있으면 **그대로 두고 `mydart`만 얹는다** (`.bak` 백업 생성)
- 마지막에 결과를 화면에 보여준다 (키는 `***`로 가려짐)

> 마지막 줄에서 키를 가리는 이유: 설정 파일을 그대로 출력하면 인증키가 터미널과
> 스크롤 기록에 평문으로 남는다.

> **왜 `uvx`가 아니라 `uv tool install`인가**
> 설정에 `"command": "uvx", "args": ["--from", "폴더", "mydart-mcp"]`를 쓰면, Claude가 켜질 때마다
> uvx가 패키지를 새로 빌드한다. 1~2분이 걸려서 Claude가 기다리다 포기하고
> **"Could not attach to MCP server mydart"**를 띄운다. 미리 exe로 설치해두면 즉시 뜬다.

## 5단계 · DART 연결 확인 (Claude에 붙이기 전에)

```powershell
mydart-mcp-selftest
```

인증키는 4단계에서 Claude 설정에 넣었으므로 거기서 읽어온다. 다른 키로 확인하려면
`$env:DART_API_KEY="키"`를 먼저 실행하면 그쪽이 우선한다.
출력은 위 "스크립트로"에 실린 것과 같고, **6개 다 ✓여야 다음으로 간다.**

사내망에서 `opendart.fss.or.kr` 또는 `dart.fss.or.kr`이 막혀 있으면 여기서 드러난다
(`ConnectError` / `ProxyError`). 그 경우 방화벽 예외를 요청해야 한다.

## 6단계 · Claude Desktop 재시작

X로 닫는 것만으로는 백그라운드에 남아 설정을 다시 읽지 않는다:

```powershell
Get-Process Claude -ErrorAction SilentlyContinue | Stop-Process -Force
```

시작 메뉴에서 Claude를 다시 실행한다.

## 7단계 · 확인

**설정 → 개발자(Developer)** 에 `mydart`가 보이면 성공. 채팅창에:

```
삼성전자 찾아줘
```

`00126380`이 나오면 끝이다. 처음엔 도구 사용 승인을 물어볼 수 있다 — 허용하면 된다.

---

# 문제 해결

실제로 겪은 것들이다. 증상별로 찾아보면 된다.

### "Could not attach to MCP server mydart"

Claude가 서버를 띄웠지만 응답을 못 받은 것이다. 로그부터 본다:

```powershell
Get-Content "$env:APPDATA\Claude\logs\mcp-server-mydart.log" -Tail 30
```

| 로그에 보이는 것 | 원인과 해결 |
|---|---|
| `initialize` 후 60초 뒤 `notifications/cancelled` | 응답이 파이프 버퍼에 갇힌 것. 최신 버전은 코드에서 해결됐다. 구버전이면 아래 "버퍼링" 참고 |
| 프로그램 실행 자체가 안 됨 | `command` 경로 확인 → `dir "$env:USERPROFILE\.local\bin\mydart-mcp.exe"` |
| 아무 로그도 없음 | 앱이 설정을 못 읽는 중. Store 버전 여부부터 확인 (0단계) |

**버퍼링 임시 조치** — 설정의 `env`에 아래를 추가하면 우회된다:

```powershell
$path = "$env:APPDATA\Claude\claude_desktop_config.json"
$cfg = Get-Content $path -Raw | ConvertFrom-Json
$cfg.mcpServers.mydart.env | Add-Member -NotePropertyName PYTHONUNBUFFERED -NotePropertyValue "1" -Force
$cfg.mcpServers.mydart.env | Add-Member -NotePropertyName PYTHONUTF8 -NotePropertyValue "1" -Force
[System.IO.File]::WriteAllText($path, ($cfg | ConvertTo-Json -Depth 30))
Get-Process Claude -ErrorAction SilentlyContinue | Stop-Process -Force
```

서버가 정상인지 직접 확인하려면:

```powershell
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' | & "$env:USERPROFILE\.local\bin\mydart-mcp.exe"
```

`{"jsonrpc":"2.0","id":1,"result":{...}}` 가 나오면 서버는 정상이다.

### 설정 → 개발자에 `mydart`가 아예 없다

앱이 설정 파일을 못 읽고 있다. **거의 항상 Store 버전 문제다** (0단계).

앱이 실제로 읽는 파일은 **설정 → 개발자 → 구성 편집**을 누르면 열린다. 그 경로가
`%APPDATA%\Claude\claude_desktop_config.json`이 아니면, 앱이 다른 폴더를 보고 있는 것이다.

폴더가 맞는지 보는 요령 — 앱이 쓰는 폴더라면 `logs` 같은 것들이 같이 있다:

```powershell
dir "$env:APPDATA\Claude"
```

우리가 만든 `claude_desktop_config.json` 하나만 덩그러니 있으면 그 폴더가 아니다.

### `notepad "경로"` 가 "지정된 경로를 찾을 수 없습니다"

경로에 공백이 있으면 따옴표 없이는 실패한다. 항상 큰따옴표로 감싼다. 폴더 자체가 없으면:

```powershell
New-Item -ItemType Directory -Force -Path "$env:APPDATA\Claude"
```

### selftest에서 `ConnectError` / `ProxyError`

방화벽·프록시가 `opendart.fss.or.kr` 또는 `dart.fss.or.kr`을 막고 있다. 사내망에서 흔하다.

### selftest에서 `OpenDART 오류 [020]` / `[010]`

`020`은 일일 20,000건 한도 초과, `010`은 등록되지 않은 인증키다.

### 첨부파일 읽기만 실패한다

DART 뷰어 HTML 구조가 바뀌었을 수 있다. 오류 메시지에 `content-type`이 함께 나오니 그대로 보고하면 된다.

### 응답이 너무 느리다

- **첫 질문**은 기업 목록 10만 건을 받느라 느리다. 이후 7일간 캐시된다
- **주가·시세를 물으면** DART에 없는 정보라 Claude가 웹을 뒤지느라 오래 걸린다
- 그 밖에는 대부분 OpenDART 서버 응답 시간이다

정기보고서 항목의 다년도 조회(`"최근 5년 타법인 출자현황"`)는 한 번의 도구 호출로 처리한다.
연도별로 따로 부르면 그때마다 모델이 판단하느라 훨씬 느려진다.

---

# 사용법

자연어로 물어보면 된다. Claude가 알아서 고유번호를 찾고 필요한 도구를 호출한다.

```
에코프로비엠 개황이랑 최근 공시 정리해줘
삼성전자 2025년 연결 손익계산서 표로 만들어줘
네이버 카카오 크래프톤 2025년 실적 비교해줘
셀트리온 최대주주 현황이랑 변동 이력 정리해줘
에코프로 5% 이상 대량보유 변동 내역 보여줘
셀트리온 작년에 전환사채나 유상증자 한 적 있어?
이 합병 공시 첨부된 외부평가의견서 읽고 합병비율 근거 정리해줘
```

## 잘 나오게 하는 요령

| | |
|---|---|
| **회사를 특정한다** | `컴투스` → 컴투스/컴투스홀딩스 혼동. `컴투스(078340)`처럼 종목코드를 주면 확실하다 |
| **연도를 말한다** | "2025년 사업보고서 기준", "최근 3년" |
| **목적을 붙인다** | "재무제표 보여줘"보다 "재무건전성 위험한지 판단해줘"가 훨씬 낫다 |
| **여러 단계를 한 번에** | "5년치 뽑아서 연도별 표 만들고 추세 정리해줘" — 알아서 반복 조회한다 |

## 한계

| | |
|---|---|
| 기간 | 재무제표·주요사항보고서는 2015년 이후, 재무지표는 2023년 이후 |
| 기본 단위 | 연간(사업보고서). 분기는 "3분기 기준으로"라고 명시 |
| 주가 | 없음. DART는 공시 시스템이라 시세·시가총액을 제공하지 않는다 |
| 연결 없는 회사 | "별도재무제표로 보여줘" |
| 비상장사 | 사업보고서 제출대상법인이면 상장사와 똑같이 조회된다. 감사보고서만 내는 회사라면 그 첨부를 읽어야 한다 |
| 첨부 형식 | HWP·HWPX·PDF·텍스트만. XLSX 등은 다운로드 링크만 준다 |

---

# 원격으로 쓰기 — 폰·웹 채팅 (선택)

Claude Desktop에 설치하면 그 PC에서만 쓸 수 있다. claude.ai 채팅이나 폰에서도 쓰려면
서버가 인터넷에 떠 있어야 한다. **Vercel 무료 등급으로 된다.**

## 배포

1. 이 저장소를 본인 GitHub 계정으로 **Fork**
2. [vercel.com](https://vercel.com) → GitHub로 로그인 → **Add New… → Project**
3. Fork한 저장소를 **Import** → 환경변수는 비워 두고 **Deploy**
4. 3분쯤 뒤 나오는 주소 뒤에 `/mcp?key=발급받은_인증키` 를 붙인다
5. claude.ai → **설정 → 커넥터 → 사용자 지정 커넥터 추가** → 그 주소 붙여넣기

배포가 살아 있는지는 브라우저로 주소만 열어 보면 된다 (인증키 없이 응답한다).

## 인증키는 서버에 저장되지 않는다

주소에 붙여 보낸 키를 **그 요청 동안만** 쓰고 버린다. 환경변수에 넣어 두지 않으므로
여러 사람이 같은 주소를 써도 각자 자기 키로 조회되고, 하루 20,000건 한도도 각자 것이다.

전역 변수 대신 요청 단위로 갈리는 `ContextVar`에 담는다. 동시에 들어온 두 요청이
서로의 키를 쓰지 않는지는 테스트로 고정해 두었다(`tests/test_http.py`).

> **그래도 주소를 공유하지 않는 게 좋다.** 키가 주소에 들어 있어 브라우저 기록이나
> 중간 장비 로그에 남을 수 있다. 새면 OpenDART에서 재발급하면 된다.

## 로컬에서 원격 방식으로 띄워 보기

```bash
uv run mydart-mcp-http           # http://127.0.0.1:8000/mcp?key=인증키
```

## 알아둘 점

- 서버리스는 요청 사이에 상태를 들고 있지 못해 **세션 없는(stateless) 모드**로 돈다.
  MCP 세션 관리자는 인스턴스당 한 번만 시작할 수 있고 그 시작이 lifespan에서 일어나는데,
  서버리스 플랫폼은 lifespan을 돌려준다는 보장이 없다. 그래서 요청마다 새로 세우고 버린다.
- **첫 호출은 느리다.** 기업 고유번호 10만 건을 새로 받는다. 서버가 잠들었다 깨면 다시 겪는다.
  `/tmp`에 캐시하므로 깨어 있는 동안은 빠르다.
- 첨부파일 읽기도 원격에서 그대로 된다. 다만 함수 실행시간 60초 안에 끝나야 하므로
  아주 큰 PDF는 실패할 수 있다.
- Vercel 무료 등급은 **개인 용도 조건**이 붙어 있다. 업무로 쓸 거면 약관을 확인한다.

---

# macOS

같은 흐름이고 명령만 다르다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # 1. uv 설치
git clone <이 저장소> && cd mydart-mcp                    # 2. 코드 받기
uv tool install --force .                                # 3. 프로그램 설치
DART_API_KEY=인증키 uv run mydart-mcp-selftest            # 4. 연결 확인
```

설정 파일은 `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mydart": {
      "command": "/Users/사용자명/.local/bin/mydart-mcp",
      "env": { "DART_API_KEY": "발급받은_인증키" }
    }
  }
}
```

Claude Code에서는 한 줄로 끝난다:

```bash
claude mcp add mydart --env DART_API_KEY=인증키 -- ~/.local/bin/mydart-mcp
```

---

# 업데이트

**확장 파일로 설치했다면** 새 `.mcpb`를 받아 다시 더블클릭하면 덮어쓴다. 인증키는 유지된다.

**스크립트로 설치했다면** ZIP을 새로 받아 압축을 풀고, **`pyproject.toml`이 보이는 폴더**에서
설치 때와 같은 한 줄:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

**인증키는 다시 묻지 않는다.** 기존 Claude 설정에서 읽어 그대로 쓴다.

손으로 하려면:

```powershell
Get-Process Claude,mydart-mcp -ErrorAction SilentlyContinue | Stop-Process -Force
& "$env:USERPROFILE\.local\bin\uv.exe" tool install --force .
```

**끄는 게 먼저다.** 서버가 돌고 있으면 실행 파일이 잠겨 있어
`failed to remove directory ... 액세스가 거부되었습니다 (os error 5)`가 난다.

새 코드가 맞는지 미리 확인하려면 (옛 폴더에서 실행하는 실수를 막는다):

```powershell
Select-String -Path "src\mydart_mcp\server.py" -Pattern "bsns_years" -Quiet   # True여야 한다
```

설정 파일은 손댈 필요 없다 — `mydart-mcp.exe` 자리는 그대로다.
설치가 끝나면 옛 폴더는 지워도 된다. `uv tool install`이 코드를 자기 저장소로 복사해 가므로
실행에 원본 폴더가 필요하지 않다 (`uvx --from 폴더` 방식과 다른 점이다).

---

# 엑셀 산출물 스킬 (선택)

`skills/dart-excel-report/`에 스킬 하나가 함께 들어 있다. DART 데이터를 **감사 추적이
가능한 엑셀**로 옮기는 코드를 작성하게 한다.

```
삼성전자 3개년 재무제표 뽑아서 엑셀로 만들어줘
네이버·카카오·크래프톤 피어 비교표 만들어줘
```

핵심 규약은 세 가지다.

- **글자색이 곧 출처다** — 검정=수식, 빨강=하드코딩 원본, 노랑=가정, 초록=타시트 참조.
  DART에서 받은 숫자는 전부 빨강이고, 거기서 계산한 값은 검정이다. 리뷰어가 색만 보고
  어디를 대사해야 하는지 판단한다.
- **Summary는 Detail을 `SUMIFS`로 참조한다** — 값을 붙여넣지 않는다. 모든 나눗셈은
  `IFERROR`로 감싼다.
- **계정과목을 표준 순서로 강제 정렬한다** — DART는 회사마다 계정 순서가 다르다.

도구 응답을 그대로 담은 `Raw` 시트를 함께 만들어, 숫자가 의심스러울 때 원본과 대사할
수 있게 한다.

## 설치

스킬은 MCP 서버와 별개다. `uv tool install`로는 깔리지 않고 따로 넣어야 한다.

### Claude Desktop / claude.ai — 계정에 등록 (권장)

Desktop은 **계정에 등록한 스킬을 내려받아 쓰는 구조**라, claude.ai에서 올리는 쪽이 확실하다.
한 번 올리면 회원님의 모든 기기에 따라온다 — 이직해서 PC를 바꿔도 그대로다.

1. ZIP을 푼 폴더에서 `skills\dart-excel-report` 폴더만 따로 **압축**한다
   (폴더에 우클릭 → 압축 → `dart-excel-report.zip`)
2. [claude.ai](https://claude.ai) → **설정 → Capabilities/Skills** → 스킬 추가 → 그 ZIP 업로드
3. Claude Desktop을 껐다 켠다

### Claude Code — 폴더에 복사

```powershell
$src = "skills\dart-excel-report"
$dst = "$env:USERPROFILE\.claude\skills\dart-excel-report"
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
Copy-Item $src $dst -Recurse -Force
dir $dst
```

`SKILL.md`가 보이면 된 것이다. 특정 프로젝트에서만 쓰려면 `$env:USERPROFILE\.claude` 대신
그 프로젝트의 `.claude` 폴더에 넣는다.

### 확인

```
지금 쓸 수 있는 스킬 목록 보여줘
```

`dart-excel-report`가 보이면 설치된 것이다. 그다음:

```
삼성전자 3개년 재무제표 뽑아서 엑셀로 만들어줘
```

스킬은 조건이 맞으면 Claude가 알아서 쓴다. 확실히 하려면 **"엑셀로"**를 넣어 말하면 된다.

폰트와 테마 컬러는 중립값이다. 소속 조직의 하우스 스타일이 있으면 `FONT_NAME`과
`COLORS`만 바꾸면 된다. **글자색 규약은 조직과 무관한 공통 관행이므로 그대로 둔다.**

---

# 도구 15개

## 자주 쓰는 것 — 전용 도구

| 도구 | 하는 일 |
|---|---|
| `search_company` | 회사명·종목코드 → DART 고유번호(`corp_code`). 다른 도구의 출발점 |
| `get_company_profile` | 기업개황 (대표자, 법인구분, 설립일, 결산월, 주소 등) |
| `search_disclosures` | 공시 검색 (회사별·기간별·공시유형별) |
| `get_disclosure_document` | 공시 원문을 텍스트로 조회 (긴 문서는 `offset`으로 이어 읽기) |
| `list_attachments` | 공시에 딸린 첨부파일 목록 |
| `read_attachment` | 첨부파일(HWP·HWPX·PDF)을 내려받아 텍스트로 읽기 |
| `get_financial_statements` | 단일 회사 전체 재무제표를 계정과목 단위로 (당기/전기/전전기) |
| `compare_financials` | 여러 회사(최대 10곳)의 주요계정 비교 |
| `get_financial_indicators` | 주요 재무지표 — 수익성·안정성·성장성·활동성 (단일/다중회사 자동 선택) |

## 나머지 — 카테고리 묶음 도구

각 도구의 설명에 선택 가능한 `item` 이름이 전부 들어 있어, 모델이 별도 조회 없이 바로 고른다.
`item`은 한글명(`"최대주주 현황"`), 엔드포인트 id(`"hyslrSttus"`), 부분일치(`"소액주주"`) 모두 받는다.

| 도구 | 커버 범위 | API 수 |
|---|---|---|
| `get_periodic_report_item` | 사업보고서 주요정보 — 증자·배당·자기주식·최대주주·임원·직원·보수·감사인·미상환잔액·자금사용내역 등. **여러 연도를 한 번에** 받는다 | 28 |
| `get_major_event` | 주요사항보고서 — 합병·분할·감자·사채발행·자기주식결정·영업양수도·소송·부도·회생 등 | 36 |
| `get_securities_registration` | 증권신고서 — 지분증권·채무증권·증권예탁증권·합병·분할·주식교환 | 6 |
| `get_shareholding` | 지분공시 — 대량보유 상황보고(5%룰), 임원·주요주주 소유보고 | 2 |

## 탐색·직접 호출

| 도구 | 하는 일 |
|---|---|
| `list_dart_apis` | 83개 API 전체 목록을 카테고리·검색어로 훑는다 |
| `call_dart_api` | 엔드포인트 이름으로 JSON API를 직접 호출 (전용 도구가 없는 API용 창구) |

## API 커버리지

| 카테고리 | API 수 | 담당 도구 |
|---|---|---|
| 공시정보 (DS001) | 4 | `search_company`, `get_company_profile`, `search_disclosures`, `get_disclosure_document` |
| 사업보고서 주요정보 (DS002) | 28 | `get_periodic_report_item` |
| 상장기업 재무정보 (DS003) | 7 | `get_financial_statements`, `compare_financials`, `get_financial_indicators`, `call_dart_api` |
| 지분공시 종합정보 (DS004) | 2 | `get_shareholding` |
| 주요사항보고서 주요정보 (DS005) | 36 | `get_major_event` |
| 증권신고서 주요정보 (DS006) | 6 | `get_securities_registration` |
| **합계** | **83** | |

83개 중 `fnlttXbrl`(재무제표 원본파일)만 ZIP 응답이라 지원하지 않는다. 나머지 82개는 모두 호출 가능하다.
첨부파일 도구 2개는 오픈API에 속하지 않는다 — 아래 참고.

---

# 첨부파일 읽기

DART 공시는 "본문 + 첨부" 구조이고, 감사보고서·외부평가의견서·계약서처럼 정작 중요한 내용은
첨부에 있는 경우가 많다. 그런데 **OpenDART 오픈API에는 첨부 엔드포인트가 없다.** 그래서 이
두 도구만 API가 아니라 DART 뷰어 페이지를 거친다.

```
list_attachments(rcept_no="20240315000123")
  → {"documents": ["본문", "외부평가기관의 평가의견서", "감사보고서"],
     "attachments": [{"index": 0, "filename": "평가의견서.pdf",
                      "document": "외부평가기관의 평가의견서", "format": "pdf", ...}]}

read_attachment(rcept_no="20240315000123", filename="감사보고서")
  → {"format": "hwp", "total_chars": 51200, "truncated": true,
     "next_offset": 20000, "text": "..."}
```

DART 뷰어는 본문 문서 하나만 보여주는 게 아니다. 외부평가기관의 평가의견서·감사보고서·이사회의사록
같은 것들이 **'첨부문서' 드롭다운에 각자 다른 문서번호로** 걸린다. 본문 문서번호만 보면 그것들은
존재조차 보이지 않으므로, 딸린 문서를 모두 열거한 뒤 각각의 다운로드 페이지를 확인한다.
각 파일의 `document` 필드가 어느 문서에서 나왔는지 알려준다.

지원 형식은 **HWP(5.0), HWPX, PDF, 텍스트/HTML/XML**이다. DART 첨부는 사실상 이 셋이 전부다.
그 밖의 형식(XLSX 등)은 목록에 `unsupported`로 표시되고 `download_url`을 주니 직접 받으면 된다.
HWP는 파이썬에 쓸 만한 경량 라이브러리가 없어(`pyhwp`는 AGPL) HWP 5.0 레코드 파서를 직접 넣었다.

## 지켜야 할 선

`dart.fss.or.kr/robots.txt`는 뷰어(`/dsaf001/main.do`)와 다운로드(`/pdf/download/`) 경로를
크롤러에 대해 Disallow로 지정하고 있다. 이 두 도구는 그래서 아래를 지킨다.

- **사용자가 접수번호로 지목한 단일 공시**에만 호출한다. 공시 목록을 훑으며 첨부를 긁어모으는
  용도로 쓰지 않는다. 그 공시에 딸린 문서는 전부 훑되 20개로 끊는다.
- User-Agent에 `mydart-mcp/<버전>`을 그대로 노출한다. 브라우저를 사칭하지 않는다 — DART 운영자가
  로그에서 트래픽 주체를 식별하고 필요하면 차단할 수 있어야 한다.
- 첨부 30MB, 압축 해제 200MB를 넘으면 받지 않고 링크만 돌려준다.
- 뷰어 → 다운로드 페이지 → 파일을 **한 연결로** 잇는다. DART가 발급한 세션 쿠키와 Referer를
  들고 가야 파일을 내준다. 요청마다 새로 접속하면 200을 주면서 본문을 비워 보낸다.

공시 본문과 재무 데이터는 언제나 공식 오픈API를 쓴다. 스크래핑은 첨부에만 쓴다.

---

# 환경변수

| 변수 | 설명 |
|---|---|
| `DART_API_KEY` | OpenDART 인증키 (필수) |
| `MYDART_CACHE_DIR` | 고유번호 파일 캐시 경로 (기본 `~/.cache/mydart-mcp`) |

전체 기업 고유번호 목록(약 10만 건)은 처음 한 번 내려받아 캐시하고 7일마다 갱신한다.
DART 원본은 15MB XML이라 파싱에 1.5초쯤 걸리므로, 파싱 결과를 `corpcode.json`으로 저장해 두고
그쪽을 읽는다 (0.13초). 서버가 새로 뜰 때마다 치르던 값이라 체감 차이가 있다.

**인증키는 Claude 설정 파일에 평문으로 저장된다.** 그 파일을 공유하지 않는다.
서버는 로그에 키가 찍히지 않도록 `crtfc_key` 값을 가린다 — OpenDART가 인증키를 URL 쿼리로 받고
httpx가 요청 URL을 통째로 로그에 남기기 때문에 필요한 조치다.

---

# 개발

```bash
uv sync --group dev
uv run pytest
npx @anthropic-ai/mcpb pack . mydart-mcp.mcpb   # 확장 파일 다시 빌드
```

---

# 알아둘 점

- 재무제표 API는 2015년 이후 사업연도만 제공한다. 재무지표(`get_financial_indicators`)는 2023년 이후다.
- `get_financial_statements`의 `fs_div`는 `CFS`(연결) / `OFS`(별도)다. 연결재무제표가 없는 회사는 `OFS`로 조회해야 한다.
- 공시 원문(`document.xml`)은 회사가 제출한 XML을 텍스트로 변환한 것이라, 표는 줄 단위로 펼쳐져 나온다.
- 재무제표 원본파일(`fnlttXbrl.xml`)과 고유번호(`corpCode.xml`)는 ZIP 응답이라 `call_dart_api`로는 못 부른다.
  고유번호는 `search_company`가, 원문은 `get_disclosure_document`가 대신한다. XBRL 파싱은 아직 지원하지 않는다.
- API 카탈로그(`src/mydart_mcp/catalog.py`)는 [dart-fss](https://github.com/josw123/dart-fss)의 API 모듈에서
  엔드포인트명·한글명·파라미터를 추출하고, 거기 없던 7개를 OpenDART 개발가이드 기준으로 채워 만든 것이다.
- 첨부 접근 경로(뷰어 → dcm_no → 다운로드 페이지)는 [korean-dart-mcp](https://github.com/chrisryugj/korean-dart-mcp)와
  OpenDartReader가 쓰는 것과 같다. DART 뷰어 HTML이 바뀌면 깨질 수 있는 부분이다.
- 거래소공시 등 일부 공시는 뷰어에 문서번호가 없어 첨부 경로 자체가 존재하지 않는다.
  `list_attachments`가 빈 목록과 함께 그 사유를 알려준다.
- 원격 배포는 Vercel 무료 등급에서 실제로 돌려 확인했다 — 커넥터 등록, 도구 목록, 회사 조회까지.
- 실제 DART에 대해 검증된 범위는 selftest가 훑는 경로(공시검색·고유번호·재무제표·첨부 목록·PDF 추출)다.
  HWP 파서는 같은 코드를 쓰는 [myacc-mcp](https://github.com/gjshin/myacc-mcp)에서 실물 한글 파일로 확인했다.
  나머지 API는 아직 실물 응답으로 확인되지 않았다. 오류를 만나면 메시지를 그대로 보고하면 된다.
