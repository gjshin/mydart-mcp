"""연도를 받는 도구에 연도 규칙이 실려 나가는지 확인한다.

모델은 연도를 안 적어주면 "재무제표는 보통 작년 걸 본다"는 관행대로 한 해를 빼고
부르는 일이 있다. 조회는 성공하고 숫자도 그럴듯해서 틀린 해를 봤다는 걸 알기 어렵다.
설명에만 있는 규칙이라 코드로는 안 지켜지고, 도구를 늘리다 빠뜨리기도 쉬워 여기서 고정한다.
"""

from __future__ import annotations

import pytest

from mydart_mcp.server import mcp

pytestmark = pytest.mark.anyio

# bsns_year / bsns_years 를 받는 도구는 전부 여기 있어야 한다
YEAR_TOOLS = {
    "get_financial_statements",
    "compare_financials",
    "get_financial_indicators",
    "get_periodic_report_item",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def tools():
    return {tool.name: tool for tool in await mcp.list_tools()}


async def test_year_tools_carry_the_year_rule(tools):
    for name in YEAR_TOOLS:
        description = tools[name].description or ""
        assert "[연도 규칙]" in description, f"{name}에 연도 규칙이 빠졌다"
        assert "작년으로 바꾸지 않는다" in description, name


async def test_year_rule_did_not_eat_the_original_description(tools):
    """규칙을 붙이다 원래 설명을 덮어쓰면 도구가 무엇인지 알 수 없게 된다."""
    assert "전체 재무제표" in (tools["get_financial_statements"].description or "")
    assert "나란히 비교" in (tools["compare_financials"].description or "")
    assert "재무지표" in (tools["get_financial_indicators"].description or "")
    # 항목명 목록은 카탈로그에서 붙는다 — 규칙을 붙여도 남아 있어야 한다
    assert "사용 가능한 item" in (tools["get_periodic_report_item"].description or "")


async def test_every_tool_taking_a_year_is_listed(tools):
    """도구를 새로 만들며 연도 규칙을 빠뜨리는 것을 막는다."""
    takes_year = {
        name
        for name, tool in tools.items()
        if any(key.startswith("bsns_year") for key in tool.input_schema.get("properties", {}))
    }
    assert takes_year == YEAR_TOOLS, f"연도를 받는데 규칙이 없는 도구: {takes_year - YEAR_TOOLS}"
