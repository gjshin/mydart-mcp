"""첨부파일에서 본문 텍스트를 뽑는다 (HWP / HWPX / PDF / 텍스트).

DART 첨부는 사실상 HWP·HWPX·PDF가 전부라 그 셋만 다룬다. 파이썬 쪽에 쓸 만한
경량 HWP 라이브러리가 없어(pyhwp는 AGPL) HWP 5.0 레코드 파서를 직접 넣었다.
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
import zlib

MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024


class ExtractError(RuntimeError):
    """지원하지 않는 형식이거나 파싱에 실패한 경우."""


# --- HWP 5.0 -----------------------------------------------------------------

HWPTAG_PARA_TEXT = 67  # HWPTAG_BEGIN(0x10) + 51

# 문단 텍스트 안의 제어문자 분류. char는 1글자, inline/extended는 8글자를 차지한다.
_CONTROL_KIND = {code: "extended" for code in (1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23)}
_CONTROL_KIND.update({code: "inline" for code in (4, 5, 6, 7, 8, 9, 19, 20)})
_CONTROL_KIND.update({code: "char" for code in (0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31)})


def _iter_records(stream: bytes):
    """HWP 레코드 스트림을 (tag_id, payload)로 훑는다."""
    offset = 0
    while offset + 4 <= len(stream):
        header = int.from_bytes(stream[offset : offset + 4], "little")
        offset += 4
        tag_id = header & 0x3FF
        size = (header >> 20) & 0xFFF
        if size == 0xFFF:
            if offset + 4 > len(stream):
                return
            size = int.from_bytes(stream[offset : offset + 4], "little")
            offset += 4
        yield tag_id, stream[offset : offset + size]
        offset += size


def hwp5_section_text(section: bytes) -> str:
    """압축이 풀린 BodyText 섹션 하나에서 문단 텍스트를 뽑는다."""
    out: list[str] = []
    for tag_id, payload in _iter_records(section):
        if tag_id != HWPTAG_PARA_TEXT:
            continue
        i = 0
        while i + 2 <= len(payload):
            code = int.from_bytes(payload[i : i + 2], "little")
            if code >= 32:
                out.append(chr(code))
                i += 2
                continue
            kind = _CONTROL_KIND.get(code, "char")
            if kind == "char":
                if code in (10, 13):
                    out.append("\n")
                i += 2
            else:
                i += 16
        out.append("\n")
    return "".join(out)


def extract_hwp(data: bytes) -> str:
    try:
        import olefile
    except ImportError as exc:  # pragma: no cover - 의존성 누락은 설치 문제다
        raise ExtractError("HWP를 읽으려면 olefile이 필요합니다.") from exc

    if not olefile.isOleFile(io.BytesIO(data)):
        raise ExtractError("HWP 5.0 파일이 아닙니다 (구버전 HWP 3.0은 지원하지 않습니다).")

    ole = olefile.OleFileIO(io.BytesIO(data))
    try:
        header = ole.openstream("FileHeader").read()
        if len(header) < 40:
            raise ExtractError("HWP 헤더가 손상되었습니다.")
        flags = int.from_bytes(header[36:40], "little")
        if flags & 0x02:
            raise ExtractError("암호가 걸린 HWP 파일이라 읽을 수 없습니다.")
        compressed = bool(flags & 0x01)

        sections = sorted(
            ("/".join(entry) for entry in ole.listdir() if entry[0] == "BodyText"),
            key=lambda name: int(re.sub(r"\D", "", name) or 0),
        )
        if not sections:
            raise ExtractError("HWP 본문(BodyText)이 없습니다.")

        texts = []
        for name in sections:
            raw = ole.openstream(name).read()
            if compressed:
                raw = zlib.decompress(raw, -15)
            texts.append(hwp5_section_text(raw))
        return "\n".join(texts)
    finally:
        ole.close()


# --- HWPX --------------------------------------------------------------------


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def extract_hwpx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        _guard_zip_size(archive)
        sections = sorted(
            name
            for name in archive.namelist()
            if re.fullmatch(r"Contents/section\d+\.xml", name, re.IGNORECASE)
        )
        if not sections:
            raise ExtractError("HWPX 본문(Contents/sectionN.xml)이 없습니다.")
        texts = []
        for name in sections:
            root = ET.fromstring(archive.read(name))
            out: list[str] = []
            for element in root.iter():
                local = _localname(element.tag)
                if local == "t" and element.text:
                    out.append(element.text)
                elif local == "p":
                    out.append("\n")
            texts.append("".join(out))
    return "\n".join(texts)


def _guard_zip_size(archive: zipfile.ZipFile) -> None:
    total = sum(info.file_size for info in archive.infolist())
    if total > MAX_UNCOMPRESSED_BYTES:
        raise ExtractError(f"압축을 풀면 {total // 1024 // 1024}MB라 처리하지 않습니다.")


# --- PDF / 텍스트 -------------------------------------------------------------


def extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - 의존성 누락은 설치 문제다
        raise ExtractError("PDF를 읽으려면 pypdf가 필요합니다.") from exc

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ExtractError("암호가 걸린 PDF라 읽을 수 없습니다.")
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


_TAG_RE = re.compile(r"<[^>]+>")


def extract_text(data: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", "replace")
    return _TAG_RE.sub("", text)


EXTRACTORS = {
    "hwp": extract_hwp,
    "hwpx": extract_hwpx,
    "pdf": extract_pdf,
    "text": extract_text,
}


def extract(data: bytes, fmt: str) -> str:
    if not data:
        raise ExtractError("내려받은 파일이 비어 있습니다.")
    extractor = EXTRACTORS.get(fmt)
    if extractor is None:
        raise ExtractError(
            f"'{fmt}' 형식은 지원하지 않습니다. 지원 형식: {', '.join(EXTRACTORS)}. "
            "download_url로 직접 받아서 여시면 됩니다."
        )
    text = extractor(data)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.rstrip() for line in text.splitlines())).strip()
