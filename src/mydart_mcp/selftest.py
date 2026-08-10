"""설치가 제대로 됐는지 한 번에 확인한다.

    uv run mydart-mcp-selftest

MCP 서버는 stdout이 JSON-RPC 채널이라 아무것도 찍으면 안 되지만, 이 진입점은
서버가 아니므로 사람이 읽을 출력을 stdout에 낸다. 두 경로를 섞지 않는다.

단계가 실패해도 멈추지 않고 끝까지 간다. 어디까지 되고 어디서 깨지는지 한눈에
보여야 하기 때문이다.
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from typing import Any, Callable

from . import attachments, dart, server


class Failure(Exception):
    """점검 실패. fatal이면 이후 단계는 건너뛴다."""

    def __init__(self, message: str, fatal: bool = False) -> None:
        super().__init__(message)
        self.fatal = fatal


class Skip(Exception):
    """확인할 수 없었지만 실패는 아닌 경우."""


State = dict[str, Any]


def check_api_key(state: State) -> str:
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        raise Failure(
            "DART_API_KEY가 비어 있습니다. https://opendart.fss.or.kr 에서 인증키를 발급받아 "
            "환경변수로 설정하세요.",
            fatal=True,
        )
    return f"{len(key)}자 설정됨"


def check_opendart(state: State) -> str:
    today = date.today()
    data = dart.get_json(
        "list.json",
        bgn_de=(today - timedelta(days=7)).strftime("%Y%m%d"),
        end_de=today.strftime("%Y%m%d"),
        page_count=1,
    )
    return f"최근 7일 공시 {data.get('total_count', 0)}건 조회됨"


def check_corp_codes(state: State) -> str:
    result = server.search_company("삼성전자")
    if not result["companies"]:
        raise Failure("고유번호 목록에서 삼성전자를 찾지 못했습니다.")
    company = result["companies"][0]
    state["corp_code"] = company["corp_code"]
    return f"{company['corp_name']} → {company['corp_code']} (캐시: {dart.cache_dir()})"


def check_financials(state: State) -> str:
    corp_code = state.get("corp_code")
    if not corp_code:
        raise Skip("고유번호를 못 구해서 건너뜁니다.")

    last_error: Exception | None = None
    for year in (date.today().year - 1, date.today().year - 2):
        try:
            statements = server.get_financial_statements(corp_code, str(year), sj_div="IS")
        except Exception as exc:  # 해당 연도 미공시 등
            last_error = exc
            continue
        accounts = [a for a in statements["accounts"] if a["current"] is not None]
        if accounts:
            return f"{year}년 손익계산서 계정 {len(accounts)}개 (통화 {statements['currency']})"
    raise Failure(f"재무제표를 가져오지 못했습니다: {last_error}")


def check_attachment_list(state: State) -> str:
    rcept_no = state.get("rcept_no")
    if not rcept_no:
        today = date.today()
        found = server.search_disclosures(
            bgn_de=(today - timedelta(days=30)).strftime("%Y%m%d"),
            end_de=today.strftime("%Y%m%d"),
            pblntf_ty="B",  # 주요사항보고서. 첨부가 붙어 있을 가능성이 높다.
            page_count=1,
        )
        if not found["disclosures"]:
            raise Skip("최근 30일 주요사항보고서가 없어 확인할 공시를 못 골랐습니다.")
        rcept_no = found["disclosures"][0]["rcept_no"]
        state["rcept_no"] = rcept_no

    listed = attachments.list_attachments(rcept_no)
    files = listed["attachments"]
    if not files:
        raise Skip(
            f"공시 {rcept_no}에 첨부가 없습니다. "
            "--rcept-no 로 첨부가 있는 공시를 지정하면 다시 확인합니다."
        )
    state["attachment_count"] = len(files)
    names = ", ".join(f["filename"] for f in files[:3])
    return f"공시 {rcept_no} 첨부 {len(files)}개 — {names}"


def check_read_attachment(state: State) -> str:
    if not state.get("attachment_count"):
        raise Skip("읽을 첨부가 없어 건너뜁니다.")
    result = server.read_attachment(state["rcept_no"], index=0, max_chars=200)
    if not result["text"].strip():
        raise Failure(
            f"{result['filename']}({result['format']})에서 텍스트를 한 글자도 뽑지 못했습니다."
        )
    preview = result["text"].strip().splitlines()[0][:40]
    return f"{result['filename']} → {result['total_chars']:,}자 추출 (첫 줄: {preview})"


STEPS: list[tuple[str, Callable[[State], str]]] = [
    ("API 키 설정", check_api_key),
    ("OpenDART 연결", check_opendart),
    ("기업 고유번호 조회", check_corp_codes),
    ("재무제표 조회", check_financials),
    ("공시 첨부 목록", check_attachment_list),
    ("첨부파일 읽기", check_read_attachment),
]

HINTS = (
    "OpenDART 오류 [020]  → 일일 호출 한도(20,000건)를 넘겼습니다.\n"
    "OpenDART 오류 [010]  → 인증키가 등록되지 않았습니다. 키를 다시 확인하세요.\n"
    "ConnectError/ProxyError/Timeout → 방화벽이나 프록시가 opendart.fss.or.kr 또는 "
    "dart.fss.or.kr을 막고 있습니다.\n"
    "HTTP 403/404 (첨부)  → DART 뷰어 HTML 구조가 바뀌었을 수 있습니다. "
    "이 출력을 그대로 붙여넣어 주세요."
)


def run(rcept_no: str | None = None) -> int:
    state: State = {}
    if rcept_no:
        state["rcept_no"] = rcept_no

    print("mydart-mcp 자체점검\n")
    passed = skipped = failed = 0
    aborted = False

    for name, check in STEPS:
        if aborted:
            print(f"  –  {name}: 앞 단계 실패로 건너뜀")
            skipped += 1
            continue
        try:
            print(f"  ✓  {name}: {check(state)}")
            passed += 1
        except Skip as exc:
            print(f"  –  {name}: {exc}")
            skipped += 1
        except Exception as exc:
            print(f"  ✗  {name}: {type(exc).__name__}: {exc}")
            failed += 1
            if isinstance(exc, Failure) and exc.fatal:
                aborted = True

    print(f"\n통과 {passed} · 건너뜀 {skipped} · 실패 {failed}")
    if failed:
        print(f"\n자주 보는 원인\n{HINTS}")
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mydart-mcp-selftest",
        description="mydart-mcp가 실제 DART에 붙는지 단계별로 확인한다.",
    )
    parser.add_argument(
        "--rcept-no",
        help="첨부 점검에 쓸 공시 접수번호 14자리. 생략하면 최근 주요사항보고서에서 하나 고른다.",
    )
    raise SystemExit(run(parser.parse_args().rcept_no))


if __name__ == "__main__":
    main()
