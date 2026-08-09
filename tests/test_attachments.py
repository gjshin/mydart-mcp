import io
import zipfile

import pytest

from mydart_mcp import attachments, extract, server


# --- 픽스처 -------------------------------------------------------------------


def hwp_record(tag_id: int, payload: bytes) -> bytes:
    header = tag_id | (0 << 10) | (len(payload) << 20)
    return header.to_bytes(4, "little") + payload


def para(text: str) -> bytes:
    return hwp_record(extract.HWPTAG_PARA_TEXT, text.encode("utf-16-le"))


def hwpx_bytes(*paragraphs: str) -> bytes:
    body = "".join(f"<hp:p><hp:t>{p}</hp:t></hp:p>" for p in paragraphs)
    xml = f'<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">{body}</hp:sec>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Contents/section0.xml", xml)
    return buffer.getvalue()


def minimal_pdf(text: str) -> bytes:
    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    bodies = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length %d>>stream\n" % len(stream) + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(bodies, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj" % i + body + b"endobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(bodies) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(bodies) + 1, xref)
    return bytes(out)


# --- HWP 5.0 레코드 파서 -------------------------------------------------------


def test_hwp5_reads_paragraph_text():
    section = para("매출액") + para("1,234")
    assert extract.hwp5_section_text(section).split() == ["매출액", "1,234"]


def test_hwp5_skips_inline_and_extended_controls():
    # 확장 제어문자(코드 2)는 자신을 포함해 8글자(16바이트)를 차지한다.
    payload = "가".encode("utf-16-le") + b"\x02\x00" + b"\x00" * 14 + "나".encode("utf-16-le")
    assert extract.hwp5_section_text(hwp_record(extract.HWPTAG_PARA_TEXT, payload)).strip() == "가나"


def test_hwp5_turns_paragraph_break_into_newline():
    payload = ("가" + chr(13) + "나").encode("utf-16-le")
    text = extract.hwp5_section_text(hwp_record(extract.HWPTAG_PARA_TEXT, payload))
    assert text.splitlines()[:2] == ["가", "나"]


def test_hwp5_ignores_non_text_records():
    section = hwp_record(16, b"\x00" * 8) + para("본문")
    assert extract.hwp5_section_text(section).strip() == "본문"


def test_hwp5_handles_extended_record_size():
    text = "가" * 5000  # size가 0xFFF를 넘어 4바이트 확장 길이로 기록된다
    payload = text.encode("utf-16-le")
    header = extract.HWPTAG_PARA_TEXT | (0xFFF << 20)
    record = header.to_bytes(4, "little") + len(payload).to_bytes(4, "little") + payload
    assert extract.hwp5_section_text(record).strip() == text


def test_hwp5_stops_cleanly_on_truncated_stream():
    full = para("가")  # 헤더 4바이트 + 본문 2바이트
    assert extract.hwp5_section_text(full[:3]) == ""  # 헤더가 잘린 경우
    assert extract.hwp5_section_text(full[:5]).strip() == ""  # 본문이 잘린 경우
    # 길이가 실제 남은 바이트보다 크다고 선언된 경우에도 멈춰야 한다
    assert extract.hwp5_section_text(para("가" * 10)[:10]).strip() == "가가가"


def test_extract_hwp_rejects_non_ole():
    with pytest.raises(extract.ExtractError, match="HWP 5.0 파일이 아닙니다"):
        extract.extract_hwp(b"not an ole file")


# --- HWPX / PDF / 텍스트 -------------------------------------------------------


def test_extract_hwpx():
    assert extract.extract(hwpx_bytes("매출액", "1,234"), "hwpx") == "매출액\n1,234"


def test_extract_hwpx_without_section_fails():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip")
    with pytest.raises(extract.ExtractError, match="본문"):
        extract.extract_hwpx(buffer.getvalue())


def test_extract_pdf():
    assert extract.extract(minimal_pdf("Hello DART"), "pdf") == "Hello DART"


def test_extract_text_strips_markup_and_handles_cp949():
    assert extract.extract("<p>주식회사</p>".encode("cp949"), "text") == "주식회사"


def test_extract_rejects_unsupported_format():
    with pytest.raises(extract.ExtractError, match="지원하지 않습니다"):
        extract.extract(b"...", "xlsx")


def test_detect_format():
    assert attachments.detect_format("감사보고서.HWP") == "hwp"
    assert attachments.detect_format("평가의견서.hwpx") == "hwpx"
    assert attachments.detect_format("사업보고서.pdf") == "pdf"
    assert attachments.detect_format("첨부.xlsx") == "unsupported"


# --- DART 뷰어 파싱 ------------------------------------------------------------

VIEWER_HTML = """
<script>
node1['rcpNo'] = "20240315000123"; node1['dcmNo'] = "9876543";
</script>
"""

DOWNLOAD_HTML = """
<!-- <td class="tL">주석에걸린파일.hwp</td><td><a class="btnFile" href="/nope"> -->
<table>
<tr><td class="tL"> 감사보고서.hwp </td><td><a class="btnFile" href="/pdf/download/pdf.do?a=1">받기</a></td></tr>
<tr><td class="tL">외부평가의견서.pdf</td><td><a class="btnFile" href="https://dart.fss.or.kr/x.pdf">받기</a></td></tr>
</table>
"""


def test_extract_dcm_no_from_viewer():
    assert attachments.extract_dcm_no(VIEWER_HTML, "20240315000123") == "9876543"


def test_extract_dcm_no_falls_back_to_view_doc():
    html = "onclick=\"viewDoc('20240315000123', '5551234', null)\""
    assert attachments.extract_dcm_no(html, "20240315000123") == "5551234"


def test_extract_dcm_no_returns_none_when_absent():
    assert attachments.extract_dcm_no("<html>no script</html>", "20240315000123") is None


def test_parse_attachment_table_skips_comments():
    rows = attachments.parse_attachment_table(DOWNLOAD_HTML)
    assert [name for name, _ in rows] == ["감사보고서.hwp", "외부평가의견서.pdf"]


# --- 도구 동작 ----------------------------------------------------------------

LISTED = {
    "rcept_no": "20240315000123",
    "viewer_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240315000123",
    "attachments": [
        {
            "index": 0,
            "filename": "감사보고서.hwpx",
            "format": "hwpx",
            "download_url": "https://dart.fss.or.kr/a",
        },
        {
            "index": 1,
            "filename": "외부평가의견서.pdf",
            "format": "pdf",
            "download_url": "https://dart.fss.or.kr/b",
        },
    ],
}


@pytest.fixture
def stub_dart(monkeypatch):
    monkeypatch.setattr(attachments, "list_attachments", lambda rcept_no: LISTED)
    monkeypatch.setattr(
        attachments,
        "download",
        lambda url: hwpx_bytes("감사의견", "적정") if url.endswith("a") else minimal_pdf("Fair"),
    )


def test_read_attachment_by_index(stub_dart):
    result = server.read_attachment("20240315000123", index=0)
    assert result["filename"] == "감사보고서.hwpx"
    assert result["text"] == "감사의견\n적정"
    assert result["truncated"] is False


def test_read_attachment_by_partial_filename(stub_dart):
    assert server.read_attachment("20240315000123", filename="평가의견")["text"] == "Fair"


def test_read_attachment_chunks_long_text(stub_dart):
    first = server.read_attachment("20240315000123", index=0, max_chars=3)
    assert first["text"] == "감사의"
    assert first["truncated"] is True
    rest = server.read_attachment("20240315000123", index=0, offset=first["next_offset"])
    assert rest["text"] == "견\n적정"
    assert rest["truncated"] is False


def test_read_attachment_rejects_bad_targets(stub_dart):
    with pytest.raises(attachments.AttachmentError, match="맞는 첨부가 없습니다"):
        server.read_attachment("20240315000123", filename="없는파일.hwp")
    with pytest.raises(attachments.AttachmentError, match="index는"):
        server.read_attachment("20240315000123", index=9)
    with pytest.raises(attachments.AttachmentError, match="filename 또는 index"):
        server.read_attachment("20240315000123")


def test_read_attachment_reports_when_no_attachments(monkeypatch):
    monkeypatch.setattr(
        attachments,
        "list_attachments",
        lambda rcept_no: {"rcept_no": rcept_no, "attachments": [], "note": "거래소공시라 첨부 없음"},
    )
    with pytest.raises(attachments.AttachmentError, match="거래소공시"):
        server.read_attachment("20240315000123")


def test_user_agent_identifies_the_tool_and_does_not_spoof_a_browser():
    assert attachments.USER_AGENT.startswith("mydart-mcp/")
    assert "Mozilla" not in attachments.USER_AGENT
