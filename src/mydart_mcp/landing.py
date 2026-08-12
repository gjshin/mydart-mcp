"""배포 주소를 브라우저로 열었을 때 보여주는 안내 페이지.

저장소를 볼 수 없는 사람에게는 여기가 유일한 설명서다. GitHub 계정도, 내려받을
파일도 없이 **주소 하나와 자기 인증키만으로** 붙일 수 있어야 한다.
"""

from __future__ import annotations

from starlette.types import Scope

_STYLE = """
:root{--bg:#f4f6f8;--card:#fff;--ink:#16202b;--soft:#5b6b78;--line:#dde3e9;
--accent:#0e6a66;--code:#1b2530;--codeink:#dce5ed}
@media(prefers-color-scheme:dark){:root{--bg:#0e141a;--card:#171f27;--ink:#e4eaef;
--soft:#8b99a5;--line:#2a353f;--accent:#4fbab0;--code:#090d12;--codeink:#cfdae4}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.7;
font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Segoe UI",
"Malgun Gothic","Noto Sans KR",sans-serif}
.wrap{max-width:42rem;margin:0 auto;padding:2.5rem 1.15rem 4rem}
h1{font-size:1.5rem;margin:0 0 .35rem;letter-spacing:-.02em}
h2{font-size:1.05rem;margin:2rem 0 .75rem;letter-spacing:-.01em}
p{margin:0 0 .8rem}
.lede{color:var(--soft);margin-bottom:1.75rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;
padding:1.1rem 1.25rem;margin:0 0 1rem}
code,pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
pre{background:var(--code);color:var(--codeink);padding:.85rem 1rem;border-radius:5px;
overflow-x:auto;font-size:.82rem;margin:.5rem 0}
code{font-size:.88em}
ol{margin:0;padding-left:1.3rem}
li{margin-bottom:.6rem}
a{color:var(--accent)}
.k{color:var(--accent);font-weight:600}
.note{color:var(--soft);font-size:.9rem}
table{border-collapse:collapse;width:100%;font-size:.92rem}
td{border-top:1px solid var(--line);padding:.55rem .4rem;vertical-align:top}
tr:first-child td{border-top:0}
td:first-child{white-space:nowrap;color:var(--soft);padding-right:1rem}
"""


def _origin(scope: Scope) -> str:
    """이 배포의 주소를 요청 헤더에서 알아낸다. 도메인을 코드에 박지 않는다."""
    host, proto = "", ""
    for name, value in scope.get("headers", []):
        if name == b"host":
            host = value.decode("latin-1")
        elif name == b"x-forwarded-proto":
            proto = value.decode("latin-1").split(",")[0].strip()
    if not host:
        return "https://이-배포-주소"
    # 프록시 뒤에서는 scope의 scheme이 http로 보이므로 전달받은 헤더가 우선이다.
    proto = proto or scope.get("scheme") or "https"
    return f"{proto}://{host}"


def page(scope: Scope) -> str:
    origin = _origin(scope)
    connect = f"{origin}/mcp?key=발급받은_인증키"
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>mydart — DART 공시조회 커넥터</title>
<style>{_STYLE}</style></head><body><div class="wrap">

<h1>mydart</h1>
<p class="lede">전자공시시스템(DART)을 Claude에서 바로 조회합니다.
회사 공시·재무제표와 <strong>감사보고서·외부평가의견서 같은 첨부파일</strong>까지 읽습니다.</p>

<div class="card">
<p><strong>서버는 켜져 있습니다.</strong> 아래 순서대로 하면 연결됩니다.
설치할 것도, GitHub 계정도 필요 없습니다.</p>
</div>

<h2>연결하기</h2>
<ol>
<li><strong>인증키를 받습니다</strong> — <a href="https://opendart.fss.or.kr">opendart.fss.or.kr</a>에서
회원가입 후 발급. 무료이고 하루 20,000건입니다. <span class="note">각자 자기 키를 씁니다.</span></li>
<li><a href="https://claude.ai/settings/connectors">claude.ai</a> →
<strong>설정 → 커넥터 → 사용자 지정 커넥터 추가</strong></li>
<li>이름은 <code>mydart</code>, 주소는 아래에 <span class="k">본인 인증키</span>를 붙여서 넣습니다
<pre>{connect}</pre></li>
<li>채팅창에 <code>삼성전자 최근 공시 5개 보여줘</code> — 표가 나오면 끝입니다</li>
</ol>

<p class="note"><strong>폰에서는 앱이 아니라 브라우저로</strong> claude.ai에 접속해서 등록해야 합니다.
앱에는 커넥터를 추가하는 화면이 없습니다. 한 번 등록하면 앱에서도 그대로 쓸 수 있습니다.</p>

<h2>인증키는 어떻게 다뤄집니까</h2>
<div class="card">
<p><strong>서버에 저장하지 않습니다.</strong> 요청에 실려 온 키를 그 요청을 처리하는 동안만 쓰고 버립니다.
여러 사람이 같은 주소를 써도 각자 자기 키로 조회되고, 하루 20,000건 한도도 각자 것입니다.</p>
<p class="note">다만 키가 주소 안에 들어 있으니 <strong>이 주소를 남에게 그대로 주지 마세요.</strong>
커넥터 설정칸에만 넣고, 채팅창에는 붙여넣지 마세요. 샜다 싶으면 OpenDART에서 재발급하면 됩니다.</p>
</div>

<h2>무엇을 물어볼 수 있나</h2>
<pre>삼성전자 2025년 연결 손익계산서 표로 만들어줘
네이버 카카오 크래프톤 2025년 실적 비교해줘
셀트리온 최대주주 현황이랑 변동 이력 정리해줘
컴투스 지난 5년 타법인 출자내역 정리해줘
이 합병 공시 첨부된 외부평가의견서 읽고 합병비율 근거 정리해줘</pre>
<p class="note">회사를 특정할 때는 <code>컴투스(078340)</code>처럼 종목코드를 함께 주면 확실합니다.</p>

<h2>알아둘 점</h2>
<table>
<tr><td>다루는 범위</td><td>OpenDART 83개 API 전부와, 오픈API에 없는 공시 첨부파일(HWP·PDF) 읽기</td></tr>
<tr><td>기간</td><td>재무제표·주요사항보고서는 2015년 이후, 재무지표는 2023년 이후</td></tr>
<tr><td>주가</td><td>없습니다. DART는 공시 시스템이라 시세·시가총액을 제공하지 않습니다</td></tr>
<tr><td>첫 조회</td><td>기업 목록 10만 건을 받느라 10초쯤 걸립니다. 이후는 빠릅니다</td></tr>
<tr><td>큰 첨부</td><td>60초를 넘기면 실패합니다. 아주 큰 PDF는 안 될 수 있습니다</td></tr>
</table>

<h2>안 될 때</h2>
<table>
<tr><td>등록이 "로그인 서비스에<br>등록할 수 없습니다"로 실패</td>
<td>주소가 <code>/mcp?key=</code> 형태가 맞는지 확인하세요. 그래도 안 되면 커넥터를 지웠다 다시 추가합니다</td></tr>
<tr><td><code>오류 [010]</code></td><td>등록되지 않은 인증키입니다. 키를 다시 확인하세요</td></tr>
<tr><td><code>오류 [020]</code></td><td>하루 20,000건을 넘겼습니다. 자정에 초기화됩니다</td></tr>
<tr><td>회사를 못 찾음</td><td>종목코드로 물어보세요. 비상장사는 사업보고서 제출대상법인만 조회됩니다</td></tr>
</table>

</div></body></html>"""
