import io
import zipfile

import pytest

from mydart_mcp import dart
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


class _FakeResponse:
    def __init__(self, json_body=None, content=b""):
        self._json = json_body
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._json
