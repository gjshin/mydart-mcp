"""OpenDART(전자공시) MCP 서버."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from . import dart

mcp = MCPServer("mydart")


def _num(value: str | None) -> int | None:
    if not value or value.strip() in ("-", ""):
        return None
    try:
        return int(value.replace(",", "").replace(" ", ""))
    except ValueError:
        return None


@mcp.tool()
def search_company(query: str, listed_only: bool = True, limit: int = 10) -> dict[str, Any]:
    """회사명이나 6자리 종목코드로 DART 고유번호(corp_code)를 찾는다.

    다른 모든 도구는 corp_code를 요구하므로 보통 여기서 시작한다.

    Args:
        query: 회사명 일부 또는 6자리 종목코드 (예: "삼성전자", "005930")
        listed_only: True면 상장사만 검색한다.
        limit: 최대 결과 수.
    """
    corps = dart.load_corp_codes()
    matches = dart.search_corp_codes(corps, query, listed_only=listed_only, limit=limit)
    return {"query": query, "count": len(matches), "companies": matches}


@mcp.tool()
def get_company_profile(corp_code: str) -> dict[str, Any]:
    """기업개황을 조회한다 (대표자, 법인구분, 설립일, 결산월, 주소, 홈페이지 등).

    Args:
        corp_code: DART 고유번호 8자리. search_company로 먼저 찾는다.
    """
    data = dart.get_json("company.json", corp_code=corp_code)
    data.pop("status", None)
    data.pop("message", None)
    return data


@mcp.tool()
def search_disclosures(
    corp_code: str | None = None,
    bgn_de: str | None = None,
    end_de: str | None = None,
    pblntf_ty: str | None = None,
    last_reprt_only: bool = True,
    page_no: int = 1,
    page_count: int = 20,
) -> dict[str, Any]:
    """공시를 검색한다. 특정 회사의 공시 목록이나 기간별 전체 공시를 볼 때 쓴다.

    Args:
        corp_code: DART 고유번호 8자리. 생략하면 전체 회사가 대상이다.
        bgn_de: 검색 시작일 YYYYMMDD. 생략하면 종료일 기준 최근 공시.
        end_de: 검색 종료일 YYYYMMDD.
        pblntf_ty: 공시유형 (A=정기공시, B=주요사항보고, C=발행공시, D=지분공시,
            E=기타공시, F=외부감사관련, G=펀드공시, H=자산유동화, I=거래소공시, J=공정위공시)
        last_reprt_only: True면 정정된 공시는 최종 보고서만 보여준다.
        page_no: 페이지 번호.
        page_count: 페이지당 건수 (최대 100).
    """
    data = dart.get_json(
        "list.json",
        corp_code=corp_code,
        bgn_de=bgn_de,
        end_de=end_de,
        pblntf_ty=pblntf_ty,
        last_reprt_at="Y" if last_reprt_only else "N",
        page_no=page_no,
        page_count=min(page_count, 100),
    )
    return {
        "total_count": data.get("total_count", 0),
        "page_no": data.get("page_no", page_no),
        "total_page": data.get("total_page", 0),
        "disclosures": [
            {
                "rcept_no": item.get("rcept_no"),
                "corp_name": item.get("corp_name"),
                "corp_code": item.get("corp_code"),
                "stock_code": item.get("stock_code"),
                "report_nm": item.get("report_nm"),
                "rcept_dt": item.get("rcept_dt"),
                "flr_nm": item.get("flr_nm"),
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no')}",
            }
            for item in data.get("list", [])
        ],
    }


@mcp.tool()
def get_disclosure_document(rcept_no: str, max_chars: int = 20000, offset: int = 0) -> dict[str, Any]:
    """공시 원문을 텍스트로 가져온다.

    원문은 수십만 자에 달할 수 있어 잘라서 반환한다. truncated가 True면
    next_offset을 넣어 다시 호출해 이어서 읽는다.

    Args:
        rcept_no: 접수번호 14자리. search_disclosures 결과의 rcept_no.
        max_chars: 이번 호출에서 반환할 최대 글자 수.
        offset: 읽기 시작할 위치.
    """
    files = dart.get_zip("document.xml", rcept_no=rcept_no)
    text = "\n\n".join(dart.document_to_text(content) for content in files.values())
    chunk = text[offset : offset + max_chars]
    end = offset + len(chunk)
    return {
        "rcept_no": rcept_no,
        "total_chars": len(text),
        "offset": offset,
        "truncated": end < len(text),
        "next_offset": end if end < len(text) else None,
        "text": chunk,
    }


@mcp.tool()
def get_financial_statements(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
    sj_div: str | None = None,
) -> dict[str, Any]:
    """단일 회사의 전체 재무제표를 계정과목 단위로 조회한다 (당기/전기/전전기 3개년).

    Args:
        corp_code: DART 고유번호 8자리.
        bsns_year: 사업연도 4자리 (2015년 이후만 제공).
        reprt_code: 11011=사업보고서, 11012=반기, 11013=1분기, 11014=3분기.
        fs_div: CFS=연결재무제표, OFS=별도재무제표.
        sj_div: 특정 재무제표만 볼 때 지정 (BS=재무상태표, IS=손익계산서,
            CIS=포괄손익계산서, CF=현금흐름표, SCE=자본변동표).
    """
    data = dart.get_json(
        "fnlttSinglAcntAll.json",
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=dart.normalize_reprt_code(reprt_code),
        fs_div=fs_div.upper(),
    )
    rows = data.get("list", [])
    if sj_div:
        rows = [row for row in rows if row.get("sj_div") == sj_div.upper()]
    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div.upper(),
        "currency": rows[0].get("currency") if rows else None,
        "accounts": [
            {
                "sj": row.get("sj_nm"),
                "account": row.get("account_nm"),
                "detail": row.get("account_detail") if row.get("account_detail") != "-" else None,
                "current": _num(row.get("thstrm_amount")),
                "prior": _num(row.get("frmtrm_amount")),
                "prior2": _num(row.get("bfefrmtrm_amount")),
            }
            for row in rows
        ],
    }


@mcp.tool()
def compare_financials(
    corp_codes: list[str],
    bsns_year: str,
    reprt_code: str = "11011",
) -> dict[str, Any]:
    """여러 회사의 주요계정(매출액, 영업이익, 당기순이익, 자산, 부채, 자본)을 나란히 비교한다.

    Args:
        corp_codes: DART 고유번호 목록 (최대 10개).
        bsns_year: 사업연도 4자리.
        reprt_code: 11011=사업보고서, 11012=반기, 11013=1분기, 11014=3분기.
    """
    if not corp_codes:
        raise dart.DartError("corp_codes가 비어 있습니다.")
    if len(corp_codes) > 10:
        raise dart.DartError("한 번에 최대 10개 회사까지 비교할 수 있습니다.")

    data = dart.get_json(
        "fnlttMultiAcnt.json",
        corp_code=",".join(corp_codes),
        bsns_year=bsns_year,
        reprt_code=dart.normalize_reprt_code(reprt_code),
    )
    names = {corp["corp_code"]: corp["corp_name"] for corp in dart.load_corp_codes()}

    companies: dict[str, dict[str, Any]] = {}
    for row in data.get("list", []):
        code = row.get("corp_code")
        company = companies.setdefault(
            code,
            {"corp_code": code, "corp_name": names.get(code), "fs_div": row.get("fs_nm"), "accounts": {}},
        )
        company["accounts"][row.get("account_nm")] = {
            "current": _num(row.get("thstrm_amount")),
            "prior": _num(row.get("frmtrm_amount")),
            "prior2": _num(row.get("bfefrmtrm_amount")),
        }

    return {
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "companies": list(companies.values()),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
