# mydart-mcp

한국 금융감독원 전자공시시스템(DART)의 [OpenDART API](https://opendart.fss.or.kr)를 MCP 도구로 감싼 서버.
Claude가 상장사 공시와 재무제표를 직접 조회해서 분석할 수 있게 한다.

## 도구

| 도구 | 하는 일 |
|---|---|
| `search_company` | 회사명·종목코드 → DART 고유번호(`corp_code`). 다른 도구의 출발점 |
| `get_company_profile` | 기업개황 (대표자, 법인구분, 설립일, 결산월, 주소 등) |
| `search_disclosures` | 공시 검색 (회사별·기간별·공시유형별) |
| `get_disclosure_document` | 공시 원문을 텍스트로 조회 (긴 문서는 `offset`으로 이어 읽기) |
| `get_financial_statements` | 단일 회사 전체 재무제표를 계정과목 단위로 (당기/전기/전전기) |
| `compare_financials` | 여러 회사(최대 10곳)의 주요계정 비교 |

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
- "이 공시 원문 요약해줘" (접수번호로 원문 조회)

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

- 재무제표 API는 2015년 이후 사업연도만 제공한다.
- `get_financial_statements`의 `fs_div`는 `CFS`(연결) / `OFS`(별도)다. 연결재무제표가 없는 회사는 `OFS`로 조회해야 한다.
- 공시 원문(`document.xml`)은 회사가 제출한 XML을 텍스트로 변환한 것이라, 표는 줄 단위로 펼쳐져 나온다.
