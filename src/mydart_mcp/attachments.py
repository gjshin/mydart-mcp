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


def _get(url: str, binary: bool = False) -> httpx.Response:
    response = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=60.0,
        follow_redirects=True,
    )
    if response.status_code != 200:
        raise AttachmentError(f"DART 요청 실패: {url} → HTTP {response.status_code}")
    if binary and len(response.content) > MAX_ATTACHMENT_BYTES:
        raise AttachmentError(
            f"첨부파일이 너무 큽니다 ({len(response.content) // 1024 // 1024}MB). "
            f"브라우저에서 직접 받으세요: {url}"
        )
    return response


def list_attachments(rcept_no: str) -> dict:
    """공시 하나의 첨부파일 목록."""
    viewer_url = f"{DART_ORIGIN}/dsaf001/main.do?rcpNo={rcept_no}"
    dcm_no = extract_dcm_no(_get(viewer_url).text, rcept_no)
    if not dcm_no:
        # 거래소공시 등 일부는 뷰어에 dcm_no가 없어 첨부 경로 자체가 존재하지 않는다.
        return {
            "rcept_no": rcept_no,
            "viewer_url": viewer_url,
            "attachments": [],
            "note": (
                "이 공시에는 접근 가능한 첨부파일이 없습니다(거래소공시 등). "
                "본문은 get_disclosure_document로 조회하세요."
            ),
        }

    download_page = f"{DART_ORIGIN}/pdf/download/main.do?rcp_no={rcept_no}&dcm_no={dcm_no}"
    rows = parse_attachment_table(_get(download_page).text)
    return {
        "rcept_no": rcept_no,
        "viewer_url": viewer_url,
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


def download(url: str) -> bytes:
    return _get(url, binary=True).content
