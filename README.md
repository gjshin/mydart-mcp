# mydart-mcp

한국 금융감독원 전자공시시스템(DART)의 [OpenDART API](https://opendart.fss.or.kr)를 MCP 도구로 감싼 서버.
Claude가 상장사 공시와 재무제표를 직접 조회해서 분석할 수 있게 한다.

**OpenDART가 공개한 83개 오픈API를 전부 커버한다.** 다만 도구를 83개 등록하면 도구 목록만으로
컨텍스트를 크게 잡아먹고 모델의 도구 선택 정확도가 떨어지므로, 자주 쓰는 것은 전용 도구로 두고
나머지는 카테고리별 묶음 도구가 `item` 파라미터로 받는 구조로 정리했다.

## 도구 15개

### 자주 쓰는 것 — 전용 도구

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

### 나머지 — 카테고리 묶음 도구

각 도구의 설명에 선택 가능한 `item` 이름이 전부 들어 있어, 모델이 별도 조회 없이 바로 고를 수 있다.

| 도구 | 커버 범위 | API 수 |
|---|---|---|
| `get_periodic_report_item` | 사업보고서 주요정보 — 증자·배당·자기주식·최대주주·임원·직원·보수·감사인·미상환잔액·자금사용내역 등 | 28 |
| `get_major_event` | 주요사항보고서 — 합병·분할·감자·사채발행·자기주식결정·영업양수도·소송·부도·회생 등 | 36 |
| `get_securities_registration` | 증권신고서 — 지분증권·채무증권·증권예탁증권·합병·분할·주식교환 | 6 |
| `get_shareholding` | 지분공시 — 대량보유 상황보고(5%룰), 임원·주요주주 소유보고 | 2 |

### 탐색·직접 호출

| 도구 | 하는 일 |
|---|---|
| `list_dart_apis` | 83개 API 전체 목록을 카테고리·검색어로 훑는다 |
| `call_dart_api` | 엔드포인트 이름으로 JSON API를 직접 호출 (전용 도구가 없는 API용 창구) |

### API 커버리지

| 카테고리 | API 수 | 담당 도구 |
|---|---|---|
| 공시정보 (DS001) | 4 | `search_company`, `get_company_profile`, `search_disclosures`, `get_disclosure_document` |
| 사업보고서 주요정보 (DS002) | 28 | `get_periodic_report_item` |
| 상장기업 재무정보 (DS003) | 7 | `get_financial_statements`, `compare_financials`, `get_financial_indicators`, `call_dart_api` |
| 지분공시 종합정보 (DS004) | 2 | `get_shareholding` |
| 주요사항보고서 주요정보 (DS005) | 36 | `get_major_event` |
| 증권신고서 주요정보 (DS006) | 6 | `get_securities_registration` |
| **합계** | **83** | |

첨부파일(`list_attachments`, `read_attachment`)은 오픈API 83개에 속하지 않는다 — 아래 참고.

## 첨부파일 읽기

DART 공시는 "본문 + 첨부" 구조이고, 감사보고서·외부평가의견서·계약서처럼 정작 중요한 내용은
첨부에 있는 경우가 많다. 그런데 **OpenDART 오픈API에는 첨부 엔드포인트가 없다.** 그래서 이
두 도구만 API가 아니라 DART 뷰어 페이지를 거친다.

```
list_attachments(rcept_no="20240315000123")
  → {"attachments": [{"index": 0, "filename": "감사보고서.hwp", "format": "hwp", ...}]}

read_attachment(rcept_no="20240315000123", filename="감사보고서")
  → {"format": "hwp", "total_chars": 51200, "truncated": true,
     "next_offset": 20000, "text": "..."}
```

지원 형식은 **HWP(5.0), HWPX, PDF, 텍스트/HTML/XML**이다. DART 첨부는 사실상 이 셋이 전부다.
그 밖의 형식(XLSX 등)은 목록에 `unsupported`로 표시되고 `download_url`을 주니 직접 받으면 된다.
HWP는 파이썬에 쓸 만한 경량 라이브러리가 없어(`pyhwp`는 AGPL) HWP 5.0 레코드 파서를 직접 넣었다.

### 지켜야 할 선

`dart.fss.or.kr/robots.txt`는 뷰어(`/dsaf001/main.do`)와 다운로드(`/pdf/download/`) 경로를
크롤러에 대해 Disallow로 지정하고 있다. 이 두 도구는 그래서 아래를 지킨다.

- **사용자가 접수번호로 지목한 단일 공시**에만 호출한다. 공시 목록을 훑으며 첨부를 긁어모으는
  용도로 쓰지 않는다.
- User-Agent에 `mydart-mcp/<버전>`을 그대로 노출한다. 브라우저를 사칭하지 않는다 — DART 운영자가
  로그에서 트래픽 주체를 식별하고 필요하면 차단할 수 있어야 한다.
- 첨부 30MB, 압축 해제 200MB를 넘으면 받지 않고 링크만 돌려준다.

공시 본문과 재무 데이터는 언제나 공식 오픈API를 쓴다. 스크래핑은 첨부에만 쓴다.

## 설치

1. [OpenDART](https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do)에서 인증키를 발급받는다 (무료, 일 20,000건).
2. Claude Desktop 설정 파일에 아래를 추가한다.
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mydart": {
      "command": "uvx",
      "args": ["--from", "/절대경로/mydart-mcp", "mydart-mcp"],
      "env": {
        "DART_API_KEY": "발급받은_인증키"
      }
    }
  }
}
```

3. Claude Desktop을 완전히 종료했다가 다시 켠다.

Claude Code에서는 아래 한 줄로 등록한다.

```bash
claude mcp add mydart --env DART_API_KEY=발급받은_인증키 -- uvx --from /절대경로/mydart-mcp mydart-mcp
```

## 사용 예

- "삼성전자 2024년 연결재무제표 보여줘"
- "카카오 최근 한 달 정기공시 찾아줘"
- "네이버랑 카카오 2024년 매출·영업이익 비교해줘"
- "현대차 2024년 최대주주 현황이랑 임원 보수 알려줘" (사업보고서 주요정보)
- "셀트리온 작년 자기주식 취득 결정 공시 다 찾아줘" (주요사항보고서)
- "에코프로 5% 이상 대량보유 변동 내역" (지분공시)
- "포스코홀딩스 2024년 안정성지표 뽑아줘" (재무지표)
- "이 합병 공시 첨부된 외부평가의견서 읽고 합병비율 근거 정리해줘" (첨부파일)

## 환경변수

| 변수 | 설명 |
|---|---|
| `DART_API_KEY` | OpenDART 인증키 (필수) |
| `MYDART_CACHE_DIR` | 고유번호 파일 캐시 경로 (기본 `~/.cache/mydart-mcp`) |

전체 기업 고유번호 목록(약 10만 건)은 처음 한 번 내려받아 캐시하고 7일마다 갱신한다.

## 개발

```bash
uv sync --group dev
uv run pytest
```

## 알아둘 점

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
