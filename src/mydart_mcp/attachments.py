"""DART 공시 첨부파일 목록 조회·다운로드.

OpenDART 오픈API에는 첨부파일 엔드포인트가 없다. 첨부는 DART 뷰어를 거쳐야만
닿을 수 있어서 뷰어 HTML을 읽는다. 경로는 두 단계다.

    1. 뷰어      /dsaf001/main.do?rcpNo=...            → JS 변수에서 dcm_no 추출
    2. 다운로드   /pdf/download/main.do?rcp_no=&dcm_no= → 첨부 테이블 파싱

주의: 위 두 경로는 dart.fss.or.kr/robots.txt가 크롤러에 Disallow로 지정한 곳이다.
그래서 이 모듈은 사용자가 접수번호를 지정한 단일 공시에만 접근하고, 브라우저를
사칭하지 않고 도구 이름을 User-Agent에 그대로 노출한다. 공시 목록을 훑으며
첨부를 긁어모으는 용도로 쓰면 안 된다.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager

import httpx

DART_ORIGIN = "https://dart.fss.or.kr"
USER_AGENT = "mydart-mcp/0.1.0 (MCP server; single-disclosure fetch)"

MAX_ATTACHMENT_BYTES = 30 * 1024 * 1024

EXT_FORMATS = {
    ".hwpx": "hwpx",
    ".hwp": "hwp",
    ".pdf": "pdf",
    ".zip": "zip",
    ".xml": "text",
    ".txt": "text",
    ".html": "text",
    ".htm": "text",
}


class AttachmentError(RuntimeError):
    """첨부 조회·다운로드가 불가능한 경우."""


def detect_format(filename: str) -> str:
    lowered = filename.lower()
    for ext, fmt in EXT_FORMATS.items():
        if lowered.endswith(ext):
            return fmt
    return "unsupported"


def extract_dcm_no(html: str, rcept_no: str) -> str | None:
    """뷰어 HTML의 JS 변수에서 문서번호(dcm_no)를 뽑는다."""
    paired = re.search(
        rf"node[12]\['rcpNo'\]\s*=\s*\"{rcept_no}\";\s*node[12]\['dcmNo'\]\s*=\s*\"(\d+)\"",
        html,
    )
    if paired:
        return paired.group(1)
    single = re.search(r"viewDoc\('(\d+)',\s*'(\d+)'", html)
    return single.group(2) if single else None


_ROW_RE = re.compile(
    r'<td class="tL">\s*([^<]+?)\s*</td>\s*<td>\s*<a class="btnFile"\s+href="([^"]+)"'
)


def parse_attachment_table(html: str) -> list[tuple[str, str]]:
    """다운로드 페이지에서 (파일명, 링크) 목록을 뽑는다. 주석 블록은 먼저 걷어낸다."""
    cleaned = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    return [(name.strip(), href) for name, href in _ROW_RE.findall(cleaned)]


@contextmanager
def session() -> Iterator[httpx.Client]:
    """뷰어 → 다운로드 페이지 → 파일을 한 연결로 잇는다.

    DART는 뷰어에서 발급한 세션 쿠키를 들고 와야 파일을 내준다. 요청마다 새로
    접속하면 200을 주면서 본문은 비워 보낸다. 브라우저가 하는 대로 쿠키를 물고
    Referer를 붙여야 한다.
    """
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=60.0,
        follow_redirects=True,
    ) as client:
        yield client


def _get(client: httpx.Client, url: str, referer: str | None = None) -> httpx.Response:
    response = client.get(url, headers={"Referer": referer} if referer else {})
    if response.status_code != 200:
        raise AttachmentError(f"DART 요청 실패: {url} → HTTP {response.status_code}")
    return response


def list_attachments(rcept_no: str, client: httpx.Client | None = None) -> dict:
    """공시 하나의 첨부파일 목록."""
    if client is None:
        with session() as own:
            return list_attachments(rcept_no, client=own)

    viewer_url = f"{DART_ORIGIN}/dsaf001/main.do?rcpNo={rcept_no}"
    dcm_no = extract_dcm_no(_get(client, viewer_url).text, rcept_no)
    if not dcm_no:
        # 거래소공시 등 일부는 뷰어에 dcm_no가 없어 첨부 경로 자체가 존재하지 않는다.
        return {
            "rcept_no": rcept_no,
            "viewer_url": viewer_url,
            "download_page_url": None,
            "attachments": [],
            "note": (
                "이 공시에는 접근 가능한 첨부파일이 없습니다(거래소공시 등). "
                "본문은 get_disclosure_document로 조회하세요."
            ),
        }

    download_page = f"{DART_ORIGIN}/pdf/download/main.do?rcp_no={rcept_no}&dcm_no={dcm_no}"
    rows = parse_attachment_table(_get(client, download_page, referer=viewer_url).text)
    return {
        "rcept_no": rcept_no,
        "viewer_url": viewer_url,
        "download_page_url": download_page,
        "attachments": [
            {
                "index": i,
                "filename": name,
                "format": detect_format(name),
                "download_url": href if href.startswith("http") else f"{DART_ORIGIN}{href}",
            }
            for i, (name, href) in enumerate(rows)
        ],
    }


def download(url: str, referer: str | None = None, client: httpx.Client | None = None) -> bytes:
    """첨부파일 하나를 내려받는다. referer에는 그 파일이 걸려 있던 다운로드 페이지를 넘긴다."""
    if client is None:
        with session() as own:
            return download(url, referer=referer, client=own)

    response = _get(client, url, referer=referer)
    content = response.content
    if not content:
        # DART가 세션·Referer를 못 받아들이면 200을 주면서 본문을 비워 보낸다.
        raise AttachmentError(
            f"DART가 빈 응답을 돌려줬습니다 "
            f"(content-type={response.headers.get('content-type', '알 수 없음')}). "
            f"브라우저에서 직접 받으세요: {url}"
        )
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise AttachmentError(
            f"첨부파일이 너무 큽니다 ({len(content) // 1024 // 1024}MB). "
            f"브라우저에서 직접 받으세요: {url}"
        )
    return content
