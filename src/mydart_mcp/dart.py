"""OpenDART(전자공시) OpenAPI 클라이언트."""

from __future__ import annotations

import io
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://opendart.fss.or.kr/api"
CORP_CODE_TTL_SEC = 60 * 60 * 24 * 7  # 고유번호 파일은 주 1회만 새로 받는다

# 보고서 코드. 사람이 쓰는 표현도 받아준다.
REPRT_CODES = {
    "11013": "1분기보고서",
    "11012": "반기보고서",
    "11014": "3분기보고서",
    "11011": "사업보고서",
}
REPRT_ALIASES = {
    "1분기": "11013",
    "q1": "11013",
    "반기": "11012",
    "2분기": "11012",
    "q2": "11012",
    "3분기": "11014",
    "q3": "11014",
    "사업보고서": "11011",
    "연간": "11011",
    "annual": "11011",
}

# 재무제표구분 코드
SJ_DIV = {
    "BS": "재무상태표",
    "IS": "손익계산서",
    "CIS": "포괄손익계산서",
    "CF": "현금흐름표",
    "SCE": "자본변동표",
}


class DartError(RuntimeError):
    """OpenDART가 오류 상태를 반환했거나 설정이 잘못된 경우."""


_KEY_RE = re.compile(r"(crtfc_key=)[^&\s\"']+")


def _redact(value: Any) -> Any:
    """crtfc_key 값을 가린다. httpx가 str이 아닌 URL 객체를 넘기기도 한다."""
    if isinstance(value, str):
        return _KEY_RE.sub(r"\1***", value)
    rendered = str(value)
    return _KEY_RE.sub(r"\1***", rendered) if "crtfc_key=" in rendered else value


class _RedactApiKey(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(_redact(arg) for arg in record.args)
        return True


def hide_api_key_in_logs() -> None:
    """OpenDART는 인증키를 URL 쿼리로 받고 httpx는 요청 URL을 통째로 로그에 남긴다.
    그대로 두면 터미널과 클라이언트 로그 파일에 인증키가 평문으로 찍힌다.

    수준을 올려 애초에 안 찍히게 하고, 누가 다시 INFO로 낮춰도 새지 않도록 필터를
    함께 건다. 진입점(server.main, selftest.main)에서 호출한다.
    """
    for name in ("httpx", "httpcore"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        if not any(isinstance(existing, _RedactApiKey) for existing in logger.filters):
            logger.addFilter(_RedactApiKey())


def cache_dir() -> Path:
    path = Path(os.environ.get("MYDART_CACHE_DIR") or (Path.home() / ".cache" / "mydart-mcp"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _api_key() -> str:
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        raise DartError(
            "DART_API_KEY 환경변수가 없습니다. "
            "https://opendart.fss.or.kr 에서 인증키를 발급받아 설정하세요."
        )
    return key


def _check_status(status: str | None, message: str | None) -> None:
    if status in (None, "000"):
        return
    raise DartError(f"OpenDART 오류 [{status}] {message or ''}".strip())


def get_json(path: str, **params: Any) -> dict[str, Any]:
    """OpenDART JSON 엔드포인트 호출. 데이터 없음(013)은 빈 결과로 돌려준다."""
    query = {k: v for k, v in params.items() if v is not None}
    query["crtfc_key"] = _api_key()
    response = httpx.get(f"{BASE_URL}/{path}", params=query, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    if data.get("status") == "013":
        return {"status": "013", "message": "조회된 데이터가 없습니다.", "list": []}
    _check_status(data.get("status"), data.get("message"))
    return data


def get_zip(path: str, **params: Any) -> dict[str, bytes]:
    """ZIP으로 응답하는 엔드포인트(corpCode.xml, document.xml) 호출."""
    query = {k: v for k, v in params.items() if v is not None}
    query["crtfc_key"] = _api_key()
    response = httpx.get(f"{BASE_URL}/{path}", params=query, timeout=60.0)
    response.raise_for_status()
    content = response.content
    if not content.startswith(b"PK"):
        # 오류일 때는 ZIP 대신 XML 상태 응답이 온다.
        status = re.search(rb"<status>(.*?)</status>", content)
        message = re.search(rb"<message>(.*?)</message>", content)
        _check_status(
            status.group(1).decode("utf-8", "replace") if status else "unknown",
            message.group(1).decode("utf-8", "replace") if message else content[:200].decode("utf-8", "replace"),
        )
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def normalize_reprt_code(value: str) -> str:
    code = value.strip()
    if code in REPRT_CODES:
        return code
    alias = REPRT_ALIASES.get(code.lower())
    if alias:
        return alias
    raise DartError(f"알 수 없는 보고서 코드입니다: {value} (사용 가능: {', '.join(REPRT_CODES)})")


# --- 고유번호(corp_code) 조회 -------------------------------------------------


def parse_corp_codes(xml_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    corps = []
    for item in root.iter("list"):
        corps.append(
            {
                "corp_code": (item.findtext("corp_code") or "").strip(),
                "corp_name": (item.findtext("corp_name") or "").strip(),
                "stock_code": (item.findtext("stock_code") or "").strip(),
                "modify_date": (item.findtext("modify_date") or "").strip(),
            }
        )
    return corps


_corp_cache: list[dict[str, str]] | None = None


def load_corp_codes(refresh: bool = False) -> list[dict[str, str]]:
    """전체 기업 고유번호 목록. 디스크에 캐시하고 메모리에도 올려둔다."""
    global _corp_cache
    path = cache_dir() / "CORPCODE.xml"
    stale = not path.exists() or (time.time() - path.stat().st_mtime) > CORP_CODE_TTL_SEC
    if refresh or stale:
        files = get_zip("corpCode.xml")
        xml_bytes = next(iter(files.values()))
        path.write_bytes(xml_bytes)
        _corp_cache = parse_corp_codes(xml_bytes)
    elif _corp_cache is None:
        _corp_cache = parse_corp_codes(path.read_bytes())
    return _corp_cache


def search_corp_codes(
    corps: list[dict[str, str]],
    query: str,
    listed_only: bool = True,
    limit: int = 10,
) -> list[dict[str, str]]:
    """회사명 또는 6자리 종목코드로 검색. 완전일치 → 시작일치 → 부분일치 순."""
    keyword = query.strip()
    if listed_only:
        corps = [c for c in corps if c["stock_code"]]

    if keyword.isdigit() and len(keyword) == 6:
        return [c for c in corps if c["stock_code"] == keyword][:limit]

    lowered = keyword.lower()
    exact, prefix, partial = [], [], []
    for corp in corps:
        name = corp["corp_name"].lower()
        if name == lowered:
            exact.append(corp)
        elif name.startswith(lowered):
            prefix.append(corp)
        elif lowered in name:
            partial.append(corp)
    return (exact + prefix + partial)[:limit]


# --- 공시 원문 --------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n{3,}")


def document_to_text(xml_bytes: bytes) -> str:
    """공시 원문 XML에서 태그를 걷어내고 본문 텍스트만 남긴다."""
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            text = xml_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = xml_bytes.decode("utf-8", "replace")

    text = re.sub(r"<(SPAN|TD|BR|P)[^>]*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"</(TR|P|TITLE|SECTION-\d)>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    lines = [line.strip() for line in text.splitlines()]
    return _WS_RE.sub("\n\n", "\n".join(line for line in lines if line))
