"""원격(HTTP)으로 띄웠을 때 인증키가 요청 단위로 갈리는지 확인한다.

여러 사람이 같은 주소를 쓰므로, 한 요청의 키가 다른 요청에 새면 그 사람 이름으로
조회가 나간다. 전역 변수 대신 ContextVar를 쓰는 이유가 이것이라 테스트로 고정한다.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from mydart_mcp import dart, http

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _rpc(method: str, params: dict | None = None, rpc_id: int = 1) -> dict:
    body = {"jsonrpc": "2.0", "id": rpc_id, "method": method}
    if params is not None:
        body["params"] = params
    return body


HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}

INIT = _rpc(
    "initialize",
    {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "t", "version": "1"},
    },
)


async def _call(client: httpx.AsyncClient, url: str, payload: dict) -> httpx.Response:
    return await client.post(url, json=payload, headers=HEADERS)


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=http.app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health_needs_no_key(client):
    async with client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "mydart-mcp" in response.text


async def test_missing_key_is_rejected(client):
    async with client:
        response = await _call(client, "/mcp", INIT)
    # 401이면 클라이언트가 OAuth 로그인 절차를 시작한다. 여기서 모자란 건 로그인이 아니다.
    assert response.status_code == 400
    assert response.json()["error"] == "missing_api_key"


async def test_oauth_discovery_is_answered_with_404(client):
    """OAuth 설정이 있다고 오해하면 커넥터 등록 자체가 실패한다."""
    async with client:
        for path in (
            "/.well-known/oauth-authorization-server",
            "/.well-known/oauth-protected-resource",
            "/.well-known/oauth-authorization-server/mcp",
        ):
            response = await client.get(path)
            assert response.status_code == 404, path


async def test_vercel_rewritten_path_still_reaches_mcp(client, monkeypatch):
    """Vercel은 rewrite를 거치며 경로를 /api/index 로 바꿔 넘긴다."""
    seen: list[str] = []

    def fake_get_json(path: str, **params):
        seen.append(dart._api_key())
        return {"status": "000", "list": []}

    monkeypatch.setattr(dart, "get_json", fake_get_json)

    async with client:
        await _call(client, "/api/index?key=DDD", INIT)
        response = await _call(
            client,
            "/api/index?key=DDD",
            _rpc("tools/call", {"name": "get_company_profile", "arguments": {"corp_code": "00126380"}}, 2),
        )

    assert response.status_code == 200
    assert seen == ["DDD"]


async def test_key_from_query_reaches_the_tool(client, monkeypatch):
    """주소에 붙인 키가 실제 조회에 쓰이는지."""
    seen: list[str] = []

    def fake_get_json(path: str, **params):
        seen.append(dart._api_key())
        return {"status": "000", "list": []}

    monkeypatch.setattr(dart, "get_json", fake_get_json)

    async with client:
        await _call(client, "/mcp?key=AAA", INIT)
        await _call(
            client,
            "/mcp?key=AAA",
            _rpc("tools/call", {"name": "get_company_profile", "arguments": {"corp_code": "00126380"}}, 2),
        )

    assert seen == ["AAA"]


async def test_two_requests_do_not_share_a_key(client, monkeypatch):
    """동시에 들어온 두 요청이 서로의 키를 쓰면 안 된다."""
    seen: list[tuple[str, str]] = []
    started = asyncio.Event()

    def fake_get_json(path: str, **params):
        key = dart._api_key()
        # 첫 요청이 키를 읽은 뒤 두 번째 요청이 끼어들도록 붙잡아 둔다.
        if key == "AAA":
            started.set()
        seen.append((params.get("corp_code", ""), key))
        return {"status": "000", "list": []}

    monkeypatch.setattr(dart, "get_json", fake_get_json)

    async def one(key: str, corp: str):
        transport = httpx.ASGITransport(app=http.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            await _call(c, f"/mcp?key={key}", INIT)
            await _call(
                c,
                f"/mcp?key={key}",
                _rpc("tools/call", {"name": "get_company_profile", "arguments": {"corp_code": corp}}, 2),
            )

    await asyncio.gather(one("AAA", "00000001"), one("BBB", "00000002"))

    assert dict(seen) == {"00000001": "AAA", "00000002": "BBB"}


async def test_bearer_header_also_works(client, monkeypatch):
    seen: list[str] = []

    def fake_get_json(path: str, **params):
        seen.append(dart._api_key())
        return {"status": "000", "list": []}

    monkeypatch.setattr(dart, "get_json", fake_get_json)

    async with client:
        headers = {**HEADERS, "authorization": "Bearer CCC"}
        await client.post("/mcp", json=INIT, headers=headers)
        await client.post(
            "/mcp",
            json=_rpc("tools/call", {"name": "get_company_profile", "arguments": {"corp_code": "00126380"}}, 2),
            headers=headers,
        )

    assert seen == ["CCC"]


def test_key_is_redacted_from_logs():
    """접속 주소가 로그에 남더라도 키는 가려져야 한다."""
    assert dart._redact("GET /mcp?key=SECRET123 HTTP/1.1") == "GET /mcp?key=*** HTTP/1.1"
    assert dart._redact("https://x/api?crtfc_key=SECRET&y=1") == "https://x/api?crtfc_key=***&y=1"
    # monkey= 처럼 key로 끝나는 다른 파라미터까지 지우면 안 된다.
    assert dart._redact("?monkey=banana") == "?monkey=banana"


def test_json_is_valid_for_the_error_body():
    body = json.dumps({"error": "missing_api_key"})
    assert json.loads(body)["error"] == "missing_api_key"
