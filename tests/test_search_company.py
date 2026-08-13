"""회사를 목록으로 한 번에 찾는 동작을 고정한다.

다른 도구는 전부 corp_code(8자리)를 요구하는데, 밖에서 받는 것은 종목코드(6자리)다.
한 건씩만 찾을 수 있으면 회사 스무 곳을 넘길 때 스무 번을 불러야 하고, 그쯤 되면
중간에 몇 곳이 빠진 채로 결론이 난다. 빠진 것이 not_found 로 드러나는지도 함께 본다.
"""

from __future__ import annotations

import pytest

from mydart_mcp import dart, server

CORPS = [
    {"corp_code": "00126380", "corp_name": "삼성전자", "stock_code": "005930"},
    {"corp_code": "00164779", "corp_name": "SK하이닉스", "stock_code": "000660"},
    {"corp_code": "00230814", "corp_name": "한미반도체", "stock_code": "042700"},
    {"corp_code": "00999999", "corp_name": "비상장부품", "stock_code": ""},
]


@pytest.fixture(autouse=True)
def corps(monkeypatch):
    monkeypatch.setattr(dart, "load_corp_codes", lambda: CORPS)


def test_one_company_still_answers_the_old_way():
    """문자열 하나로 부르던 방식이 그대로 동작해야 한다."""
    result = server.search_company("005930")
    assert result["query"] == "005930"
    assert result["count"] == 1
    assert result["companies"][0]["corp_code"] == "00126380"
    assert "queries" not in result


def test_a_list_is_resolved_in_one_call():
    result = server.search_company(["005930", "000660", "042700"])
    assert result["queries"] == 3
    assert [c["corp_code"] for c in result["companies"]] == ["00126380", "00164779", "00230814"]
    assert "not_found" not in result


def test_each_row_says_which_query_it_came_from():
    """회사명으로 찾으면 여러 건이 걸린다. 어느 검색어의 결과인지 알 수 있어야 한다."""
    result = server.search_company(["005930", "SK하이닉스"])
    assert {c["query"] for c in result["companies"]} == {"005930", "SK하이닉스"}


def test_missing_companies_are_named_not_dropped():
    """조용히 빠지면 스무 곳을 넘겼는데 열여덟 곳으로 답이 나온 것을 알 수 없다."""
    result = server.search_company(["005930", "999999", "000660"])
    assert result["not_found"] == ["999999"]
    assert result["count"] == 2


def test_the_same_company_twice_is_returned_once():
    result = server.search_company(["005930", "005930", "삼성전자"])
    assert result["count"] == 1


def test_unlisted_is_reached_only_after_listed_finds_nothing():
    result = server.search_company(["비상장부품"])
    assert result["count"] == 1
    assert "비상장부품" in result["note"]


def test_an_empty_list_is_refused():
    with pytest.raises(dart.DartError):
        server.search_company([])


def test_too_many_at_once_is_refused_with_the_count():
    with pytest.raises(dart.DartError) as exc:
        server.search_company(["005930"] * (server.MAX_QUERIES + 1))
    assert str(server.MAX_QUERIES) in str(exc.value)
