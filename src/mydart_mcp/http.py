"""원격(HTTP)으로 띄울 때 쓰는 진입점.

Claude Desktop에 설치해 쓰는 경우에는 필요 없다. claude.ai 채팅이나 폰에서 쓰려면
서버가 인터넷 어딘가에 떠 있어야 하고, 그때 이 파일이 쓰인다.

인증키는 서버에 저장하지 않는다. 커넥터 주소 뒤에 붙여 보낸 것을 그 요청 동안만
쓴다 — 여러 사람이 같은 주소를 써도 서로의 키가 섞이지 않는다.

    https://<주소>/mcp?key=발급받은_인증키
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.types import Receive, Scope, Send

from . import dart
from .server import mcp

# 서버리스(Vercel 등)에서는 홈 디렉터리에 쓸 수 없다. 쓸 수 있는 곳은 /tmp뿐이고,
# 인스턴스가 살아 있는 동안 유지되므로 캐시 자리로는 충분하다.
os.environ.setdefault("MYDART_CACHE_DIR", "/tmp/mydart-mcp")

_KEY_PARAMS = ("key", "opendart_key", "crtfc_key", "dart_api_key")


def _build_mcp_app():
    """요청 하나를 처리할 MCP 앱을 새로 만든다.

    SDK의 세션 관리자는 인스턴스당 한 번만 시작할 수 있고, 시작은 Starlette의
    lifespan에서 일어난다. 서버리스 플랫폼은 lifespan을 돌려준다는 보장이 없어,
    하나를 오래 들고 있으면 'Task group is not initialized'로 죽는다.

    세션을 쓰지 않는 모드라 요청 사이에 이어갈 상태가 없으므로, 매 요청마다 만들고
    끝나면 버린다. 도구 정의는 모듈 수준 `mcp`에 그대로 있어 다시 만들지 않는다.
    """
    return mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        # SDK 기본값은 로컬 주소만 허용한다. 이건 브라우저가 내 PC의 로컬 서버를 치는
        # DNS 리바인딩을 막기 위한 것이라, 공개 주소로 배포하면 배포 도메인을 미리 알 수
        # 없어 전부 거부된다. 여기서는 인증키가 없으면 위에서 이미 막히므로 끈다.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


def _key_from(scope: Scope) -> str:
    """주소의 쿼리나 Authorization 헤더에서 인증키를 꺼낸다."""
    from urllib.parse import parse_qs

    query = parse_qs(scope.get("query_string", b"").decode("utf-8", "replace"))
    for name in _KEY_PARAMS:
        values = query.get(name)
        if values and values[0].strip():
            return values[0].strip()

    for raw_name, raw_value in scope.get("headers", []):
        if raw_name == b"authorization":
            value = raw_value.decode("utf-8", "replace")
            if value.lower().startswith("bearer "):
                return value[7:].strip()
    return ""


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        # 우리는 요청마다 MCP 앱을 새로 세우므로 여기서 할 일이 없다.
        # 그래도 플랫폼이 보내면 받아 줘야 시작 단계에서 멈추지 않는다.
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    if scope["type"] != "http":
        return

    path = scope.get("path", "")

    # 배포가 살아 있는지 브라우저로 확인하는 용도. 인증키는 필요 없고 받지도 않는다.
    if path in ("/", "/health"):
        await PlainTextResponse(
            "mydart-mcp is running.\n"
            "커넥터 주소: <이 주소>/mcp?key=발급받은_인증키\n",
        )(scope, receive, send)
        return

    key = _key_from(scope)
    if not key:
        await JSONResponse(
            {
                "error": "missing_api_key",
                "message": "주소 뒤에 ?key=발급받은_인증키 를 붙이세요. "
                "https://opendart.fss.or.kr 에서 무료로 발급받습니다.",
            },
            status_code=401,
        )(scope, receive, send)
        return

    dart.use_api_key(key)
    mcp_app = _build_mcp_app()
    async with mcp_app.router.lifespan_context(mcp_app):
        await mcp_app(scope, receive, send)


def main() -> Any:
    """로컬에서 원격 방식으로 띄워 볼 때 쓴다: `mydart-mcp-http`."""
    import uvicorn

    dart.hide_api_key_in_logs()
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        access_log=False,  # 주소에 인증키가 들어 있어 접근 로그를 남기지 않는다
    )
