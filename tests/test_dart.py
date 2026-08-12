import io
import logging
import zipfile

import httpx
import pytest

from mydart_mcp import catalog, dart, server
from mydart_mcp.server import _num

CORP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list><corp_code>00126380</corp_code><corp_name>삼성전자</corp_name><stock_code>005930</stock_code><modify_date>20240401</modify_date></list>
  <list><corp_code>00164779</corp_code><corp_name>삼성전자서비스</corp_name><stock_code></stock_code><modify_date>20240401</modify_date></list>
  <list><corp_code>00126186</corp_code><corp_name>삼성물산</corp_name><stock_code>028260</stock_code><modify_date>20240401</modify_date></list>
  <list><corp_code>00164742</corp_code><corp_name>대한전자</corp_name><stock_code>000660</stock_code><modify_date>20240401</modify_date></list>
</result>
""".encode("utf-8")


@pytest.fixture
def corps():
    return dart.parse_corp_codes(CORP_XML)


def test_parse_corp_codes(corps):
    assert len(corps) == 4
    assert corps[0] == {
        "corp_code": "00126380",
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "modify_date": "20240401",
    }


def test_search_by_stock_code(corps):
    assert [c["corp_name"] for c in dart.search_corp_codes(corps, "005930")] == ["삼성전자"]


def test_search_ranks_exact_then_prefix_then_partial(corps):
    names = [c["corp_name"] for c in dart.search_corp_codes(corps, "전자", listed_only=False)]
    assert names == ["삼성전자", "삼성전자서비스", "대한전자"]  # prefix 없음 → 부분일치 순서 유지
    names = [c["corp_name"] for c in dart.search_corp_codes(corps, "삼성전자", listed_only=False)]
    assert names == ["삼성전자", "삼성전자서비스"]


def test_search_listed_only_filters_unlisted(corps):
    names = [c["corp_name"] for c in dart.search_corp_codes(corps, "삼성")]
    assert "삼성전자서비스" not in names


def test_normalize_reprt_code():
    assert dart.normalize_reprt_code("11011") == "11011"
    assert dart.normalize_reprt_code("반기") == "11012"
    with pytest.raises(dart.DartError):
        dart.normalize_reprt_code("작년치")


def test_document_to_text_strips_markup():
    xml = "<DOCUMENT><TITLE>사업보고서</TITLE><P>매출액은&nbsp;100원</P></DOCUMENT>".encode("utf-8")
    assert dart.document_to_text(xml) == "사업보고서\n매출액은 100원"


def test_document_to_text_handles_cp949():
    xml = "<P>주식회사</P>".encode("cp949")
    assert "주식회사" in dart.document_to_text(xml)


def test_num_parses_amounts():
    assert _num("1,234,567") == 1234567
    assert _num("-1,000") == -1000
    assert _num("-") is None
    assert _num("") is None
    assert _num(None) is None


def test_get_json_treats_013_as_empty(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "test-key")
    monkeypatch.setattr(dart.httpx, "get", lambda *a, **k: _FakeResponse(json_body={"status": "013", "message": "조회된 데이타가 없습니다."}))
    assert dart.get_json("list.json")["list"] == []


def test_get_json_raises_on_error_status(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "test-key")
    monkeypatch.setattr(dart.httpx, "get", lambda *a, **k: _FakeResponse(json_body={"status": "020", "message": "요청 제한을 초과하였습니다."}))
    with pytest.raises(dart.DartError, match="020"):
        dart.get_json("list.json")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    with pytest.raises(dart.DartError, match="DART_API_KEY"):
        dart.get_json("list.json")


def test_get_zip_raises_on_xml_error_response(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "test-key")
    body = "<result><status>012</status><message>접근할 수 없는 IP입니다.</message></result>".encode("utf-8")
    monkeypatch.setattr(dart.httpx, "get", lambda *a, **k: _FakeResponse(content=body))
    with pytest.raises(dart.DartError, match="012"):
        dart.get_zip("document.xml", rcept_no="20240101000001")


def test_get_zip_returns_members(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "test-key")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CORPCODE.xml", CORP_XML)
    monkeypatch.setattr(dart.httpx, "get", lambda *a, **k: _FakeResponse(content=buffer.getvalue()))
    assert dart.get_zip("corpCode.xml")["CORPCODE.xml"] == CORP_XML


def test_api_key_never_reaches_the_logs(caplog):
    """OpenDART는 인증키를 URL에 싣고 httpx는 URL을 통째로 로그에 남긴다.
    이 조합 때문에 실제로 사용자 터미널에 키가 평문으로 찍힌 적이 있다."""
    dart.hide_api_key_in_logs()
    logger = logging.getLogger("httpx")
    url = httpx.URL(
        "https://opendart.fss.or.kr/api/list.json?bgn_de=20260101&crtfc_key=SUPERSECRETKEY"
    )

    # 누군가 로그 수준을 다시 낮춰도 새면 안 된다
    with caplog.at_level(logging.INFO, logger="httpx"):
        logger.info('HTTP Request: GET %s "HTTP/1.1 200 OK"', url)

    assert "SUPERSECRETKEY" not in caplog.text
    assert "crtfc_key=***" in caplog.text
    assert "bgn_de=20260101" in caplog.text  # 나머지는 남아야 진단이 된다


def test_log_redaction_is_installed_once():
    dart.hide_api_key_in_logs()
    dart.hide_api_key_in_logs()
    installed = logging.getLogger("httpx").filters
    assert sum(isinstance(f, dart._RedactApiKey) for f in installed) == 1


def test_catalog_covers_all_83_open_apis():
    assert len(catalog.ENDPOINTS) == 83
    counts = {name: len(catalog.by_category(name)) for name in catalog.CATEGORY_NAMES}
    assert counts == {
        "disclosure": 4,
        "periodic_report": 28,
        "finance": 7,
        "shareholding": 2,
        "major_event": 36,
        "securities_registration": 6,
    }


def test_catalog_ids_match_dict_keys():
    for key, endpoint in catalog.ENDPOINTS.items():
        assert key == endpoint.id


def test_resolve_by_exact_name_and_id():
    assert catalog.resolve("periodic_report", "배당에 관한 사항").id == "alotMatter"
    assert catalog.resolve("major_event", "tsstkAqDecsn").name == "자기주식 취득 결정"


def test_resolve_by_partial_name():
    assert catalog.resolve("periodic_report", "소액주주").id == "mrhlSttus"


def test_resolve_rejects_ambiguous_and_unknown():
    with pytest.raises(ValueError, match="여러 개"):
        catalog.resolve("major_event", "발행결정")
    with pytest.raises(ValueError, match="없는 항목"):
        catalog.resolve("periodic_report", "임원 소유주식")  # 지분공시 소속이다


def test_resolve_is_scoped_to_category():
    with pytest.raises(ValueError):
        catalog.resolve("periodic_report", "tsstkAqDecsn")


def test_call_dart_api_rejects_unknown_and_non_json(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "test-key")
    with pytest.raises(dart.DartError, match="엔드포인트가 아닙니다"):
        server.call_dart_api("nopeApi", {})
    with pytest.raises(dart.DartError, match="ZIP/XML"):
        server.call_dart_api("document", {"rcept_no": "20240101000001"})


def test_financial_indicators_rejects_bad_index_code():
    with pytest.raises(dart.DartError, match="알 수 없는 지표"):
        server.get_financial_indicators(["00126380"], "2024", "M999999")
    with pytest.raises(dart.DartError, match="corp_codes"):
        server.get_financial_indicators([], "2024", "수익성지표")


def test_list_dart_apis_filters():
    assert server.list_dart_apis()["count"] == 83
    assert server.list_dart_apis(category="shareholding")["count"] == 2
    names = [api["name"] for api in server.list_dart_apis(query="자기주식")["apis"]]
    assert "자기주식 취득 및 처분 현황" in names
    with pytest.raises(dart.DartError, match="알 수 없는 카테고리"):
        server.list_dart_apis(category="nope")


def test_grouped_tool_descriptions_list_every_item():
    for category in ("periodic_report", "major_event", "securities_registration", "shareholding"):
        listed = catalog.item_names(category)
        for endpoint in catalog.by_category(category):
            assert endpoint.name in listed


class _FakeResponse:
    def __init__(self, json_body=None, content=b""):
        self._json = json_body
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


def test_stdio_is_line_buffered_and_utf8(monkeypatch):
    """Windows에서 stdout이 블록 버퍼링되면 initialize 응답이 버퍼에 갇혀
    클라이언트가 60초 뒤 연결을 포기한다. 실제로 겪은 증상이다."""
    calls = []

    class FakeStream:
        def reconfigure(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(server.sys, "stdin", FakeStream())
    monkeypatch.setattr(server.sys, "stdout", FakeStream())
    server._prepare_stdio()

    assert {"encoding": "utf-8"} in calls
    assert {"line_buffering": True} in calls


def test_prepare_stdio_survives_streams_without_reconfigure(monkeypatch):
    monkeypatch.setattr(server.sys, "stdin", object())
    monkeypatch.setattr(server.sys, "stdout", object())
    server._prepare_stdio()  # 예외 없이 지나가야 한다


def test_corp_codes_are_cached_as_json_not_reparsed(tmp_path, monkeypatch):
    """원본 XML 파싱은 10만 건에 1.5초쯤 걸린다. 서버가 뜰 때마다 그 값을 치르지
    않도록 파싱 결과를 JSON으로 저장하고 그쪽을 읽는다."""
    monkeypatch.setenv("MYDART_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("DART_API_KEY", "test-key")
    monkeypatch.setattr(dart, "_corp_cache", None)

    downloads = []

    def fake_zip(path, **params):
        downloads.append(path)
        return {"CORPCODE.xml": CORP_XML}

    monkeypatch.setattr(dart, "get_zip", fake_zip)

    first = dart.load_corp_codes()
    assert len(first) == 4
    assert (tmp_path / "corpcode.json").exists()

    # 메모리 캐시가 비어도 두 번째부터는 다시 내려받지 않고 JSON을 읽는다
    monkeypatch.setattr(dart, "_corp_cache", None)
    monkeypatch.setattr(dart, "parse_corp_codes", lambda _: pytest.fail("XML을 다시 파싱했다"))
    assert dart.load_corp_codes() == first
    assert downloads == ["corpCode.xml"]


def test_is_listed(monkeypatch, corps):
    monkeypatch.setattr(dart, "load_corp_codes", lambda: corps)
    assert dart.is_listed("00126380") is True  # 삼성전자, 종목코드 있음
    assert dart.is_listed("00164779") is False  # 삼성전자서비스, 비상장


def test_search_company_falls_back_to_unlisted(monkeypatch, corps):
    monkeypatch.setattr(dart, "load_corp_codes", lambda: corps)
    result = server.search_company("삼성전자서비스")
    assert [c["corp_name"] for c in result["companies"]] == ["삼성전자서비스"]
    assert "비상장" in result["note"]


def test_search_company_has_no_note_when_listed(monkeypatch, corps):
    monkeypatch.setattr(dart, "load_corp_codes", lambda: corps)
    assert "note" not in server.search_company("삼성전자")


CORPS = [
    {"corp_code": "00126380", "corp_name": "삼성전자", "stock_code": "005930"},
    {"corp_code": "00164779", "corp_name": "SK하이닉스", "stock_code": "000660"},
]


def _periodic_stub(monkeypatch, per_key):
    """per_key는 "회사코드 연도" 또는 "연도"를 키로 받는다."""

    def fake(path, **params):
        key = f"{params['corp_code']} {params['bsns_year']}"
        value = per_key.get(key, per_key.get(params["bsns_year"]))
        if isinstance(value, Exception):
            raise value
        return {"list": value}

    monkeypatch.setattr(dart, "get_json", fake)
    monkeypatch.setattr(dart, "is_listed", lambda corp_code: True)
    monkeypatch.setattr(dart, "load_corp_codes", lambda refresh=False: CORPS)


def test_periodic_report_fetches_every_year_in_one_call(monkeypatch):
    _periodic_stub(monkeypatch, {"2023": [{"a": 1}], "2024": [{"a": 2}, {"a": 3}], "2025": []})
    result = server.get_periodic_report_item(["00126380"], ["2023", "2024", "2025"], "타법인 출자현황")

    assert result["count"] == 3
    assert [row["bsns_year"] for row in result["rows"]] == ["2023", "2024", "2024"]
    assert result["empty"] == [
        {"corp_code": "00126380", "corp_name": "삼성전자", "bsns_year": "2025"}
    ]
    assert "failed" not in result


def test_periodic_report_screens_several_companies(monkeypatch):
    """후보군을 놓고 훑는 용도. 어느 회사 것인지 행마다 붙어 있어야 표가 된다."""
    _periodic_stub(
        monkeypatch,
        {
            "00126380 2025": [{"adt_opinion": "적정"}],
            "00164779 2025": [{"adt_opinion": "한정"}],
        },
    )
    result = server.get_periodic_report_item(
        ["00126380", "00164779"], ["2025"], "회계감사인의 명칭 및 감사의견"
    )

    assert result["companies"] == 2
    assert result["count"] == 2
    assert [(r["corp_name"], r["adt_opinion"]) for r in result["rows"]] == [
        ("삼성전자", "적정"),
        ("SK하이닉스", "한정"),
    ]


def test_periodic_report_keeps_going_when_one_company_fails(monkeypatch):
    _periodic_stub(
        monkeypatch,
        {
            "00126380 2025": dart.DartError("OpenDART 오류 [100]"),
            "00164779 2025": [{"a": 1}],
        },
    )
    result = server.get_periodic_report_item(["00126380", "00164779"], ["2025"], "타법인 출자현황")

    assert result["count"] == 1
    assert "100" in result["failed"]["삼성전자 2025"]


def test_periodic_report_refuses_too_many_lookups(monkeypatch):
    """원격에서는 함수 실행시간 제한이 있어, 끊기고 나서 알기보다 미리 막는다."""
    _periodic_stub(monkeypatch, {"2025": [{"a": 1}]})
    with pytest.raises(dart.DartError, match="나눠 부르세요"):
        server.get_periodic_report_item([f"{i:08d}" for i in range(31)], ["2024", "2025"], "타법인 출자현황")


def test_periodic_report_flags_unlisted_company_when_empty(monkeypatch):
    _periodic_stub(monkeypatch, {"2024": []})
    monkeypatch.setattr(dart, "is_listed", lambda corp_code: False)
    result = server.get_periodic_report_item(["00164779"], ["2024"], "타법인 출자현황")

    assert result["count"] == 0
    # 비상장사도 사업보고서 제출대상이면 데이터가 있다. 없다고 단정하면 안 된다.
    assert "비상장" in result["note"]
    assert "제출대상법인이면 조회" in result["note"]
    assert "search_disclosures" in result["note"]


def test_periodic_report_rejects_empty_lists():
    with pytest.raises(dart.DartError, match="bsns_years"):
        server.get_periodic_report_item(["00126380"], [], "타법인 출자현황")
    with pytest.raises(dart.DartError, match="corp_codes"):
        server.get_periodic_report_item([], ["2025"], "타법인 출자현황")
