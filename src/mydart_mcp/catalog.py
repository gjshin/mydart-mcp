"""OpenDART 83개 오픈API 카탈로그.

dart-fss(josw123/dart-fss)의 API 모듈에서 엔드포인트명·한글명·파라미터를 추출하고,
거기 없던 6개(list, company, document, corpCode, fnlttXbrl, fnlttSinglIndx,
fnlttCmpnyIndx)를 OpenDART 개발가이드 기준으로 채워 넣은 것이다.
"""

from __future__ import annotations

from typing import NamedTuple


class Endpoint(NamedTuple):
    id: str
    ext: str  # json | xml(zip)
    category: str
    name: str  # 한글 항목명
    params: tuple[str, ...]


CATEGORY_NAMES = {
    "disclosure": "공시정보 (DS001)",
    "periodic_report": "사업보고서 주요정보 (DS002)",
    "finance": "상장기업 재무정보 (DS003)",
    "shareholding": "지분공시 종합정보 (DS004)",
    "major_event": "주요사항보고서 주요정보 (DS005)",
    "securities_registration": "증권신고서 주요정보 (DS006)",
}

ENDPOINTS: dict[str, Endpoint] = {
    "corpCode": Endpoint("corpCode", "xml", "disclosure", "고유번호", ()),
    "list": Endpoint("list", "json", "disclosure", "공시검색", ('corp_code', 'bgn_de', 'end_de', 'last_reprt_at', 'pblntf_ty', 'pblntf_detail_ty', 'corp_cls', 'sort', 'sort_mth', 'page_no', 'page_count')),
    "document": Endpoint("document", "xml", "disclosure", "공시서류원본파일", ('rcept_no',)),
    "company": Endpoint("company", "json", "disclosure", "기업개황", ('corp_code',)),
    "xbrlTaxonomy": Endpoint("xbrlTaxonomy", "json", "finance", "XBRL택사노미재무제표양식", ('sj_div',)),
    "fnlttCmpnyIndx": Endpoint("fnlttCmpnyIndx", "json", "finance", "다중회사 주요 재무지표", ('corp_code', 'bsns_year', 'reprt_code', 'idx_cl_code')),
    "fnlttMultiAcnt": Endpoint("fnlttMultiAcnt", "json", "finance", "다중회사 주요계정", ('corp_code', 'bsns_year', 'reprt_code')),
    "fnlttSinglAcntAll": Endpoint("fnlttSinglAcntAll", "json", "finance", "단일회사 전체 재무제표", ('corp_code', 'bsns_year', 'reprt_code', 'fs_div')),
    "fnlttSinglIndx": Endpoint("fnlttSinglIndx", "json", "finance", "단일회사 주요 재무지표", ('corp_code', 'bsns_year', 'reprt_code', 'idx_cl_code')),
    "fnlttSinglAcnt": Endpoint("fnlttSinglAcnt", "json", "finance", "단일회사 주요계정", ('corp_code', 'bsns_year', 'reprt_code')),
    "fnlttXbrl": Endpoint("fnlttXbrl", "xml", "finance", "재무제표 원본파일(XBRL)", ('rcept_no', 'reprt_code')),
    "crDecsn": Endpoint("crDecsn", "json", "major_event", "감자 결정", ('corp_code', 'bgn_de', 'end_de')),
    "exbdIsDecsn": Endpoint("exbdIsDecsn", "json", "major_event", "교환사채권 발행결정", ('corp_code', 'bgn_de', 'end_de')),
    "fricDecsn": Endpoint("fricDecsn", "json", "major_event", "무상증자 결정", ('corp_code', 'bgn_de', 'end_de')),
    "dfOcr": Endpoint("dfOcr", "json", "major_event", "부도발생", ('corp_code', 'bgn_de', 'end_de')),
    "wdCocobdIsDecsn": Endpoint("wdCocobdIsDecsn", "json", "major_event", "상각형 조건부자본증권 발행결정", ('corp_code', 'bgn_de', 'end_de')),
    "lwstLg": Endpoint("lwstLg", "json", "major_event", "소송 등의 제기", ('corp_code', 'bgn_de', 'end_de')),
    "bdwtIsDecsn": Endpoint("bdwtIsDecsn", "json", "major_event", "신주인수권부사채권 발행결정", ('corp_code', 'bgn_de', 'end_de')),
    "bsnTrfDecsn": Endpoint("bsnTrfDecsn", "json", "major_event", "영업양도 결정", ('corp_code', 'bgn_de', 'end_de')),
    "bsnInhDecsn": Endpoint("bsnInhDecsn", "json", "major_event", "영업양수 결정", ('corp_code', 'bgn_de', 'end_de')),
    "bsnSp": Endpoint("bsnSp", "json", "major_event", "영업정지", ('corp_code', 'bgn_de', 'end_de')),
    "pifricDecsn": Endpoint("pifricDecsn", "json", "major_event", "유무상증자 결정", ('corp_code', 'bgn_de', 'end_de')),
    "piicDecsn": Endpoint("piicDecsn", "json", "major_event", "유상증자 결정", ('corp_code', 'bgn_de', 'end_de')),
    "tgastTrfDecsn": Endpoint("tgastTrfDecsn", "json", "major_event", "유형자산 양도 결정", ('corp_code', 'bgn_de', 'end_de')),
    "tgastInhDecsn": Endpoint("tgastInhDecsn", "json", "major_event", "유형자산 양수 결정", ('corp_code', 'bgn_de', 'end_de')),
    "tsstkDpDecsn": Endpoint("tsstkDpDecsn", "json", "major_event", "자기주식 처분 결정", ('corp_code', 'bgn_de', 'end_de')),
    "tsstkAqDecsn": Endpoint("tsstkAqDecsn", "json", "major_event", "자기주식 취득 결정", ('corp_code', 'bgn_de', 'end_de')),
    "tsstkAqTrctrCnsDecsn": Endpoint("tsstkAqTrctrCnsDecsn", "json", "major_event", "자기주식취득 신탁계약 체결 결정", ('corp_code', 'bgn_de', 'end_de')),
    "tsstkAqTrctrCcDecsn": Endpoint("tsstkAqTrctrCcDecsn", "json", "major_event", "자기주식취득 신탁계약 해지 결정", ('corp_code', 'bgn_de', 'end_de')),
    "astInhtrfEtcPtbkOpt": Endpoint("astInhtrfEtcPtbkOpt", "json", "major_event", "자산양수도(기타), 풋백옵션", ('corp_code', 'bgn_de', 'end_de')),
    "cvbdIsDecsn": Endpoint("cvbdIsDecsn", "json", "major_event", "전환사채권 발행결정", ('corp_code', 'bgn_de', 'end_de')),
    "stkrtbdTrfDecsn": Endpoint("stkrtbdTrfDecsn", "json", "major_event", "주권 관련 사채권 양도 결정", ('corp_code', 'bgn_de', 'end_de')),
    "stkrtbdInhDecsn": Endpoint("stkrtbdInhDecsn", "json", "major_event", "주권 관련 사채권 양수 결정", ('corp_code', 'bgn_de', 'end_de')),
    "stkExtrDecsn": Endpoint("stkExtrDecsn", "json", "major_event", "주식교환·이전 결정", ('corp_code', 'bgn_de', 'end_de')),
    "bnkMngtPcbg": Endpoint("bnkMngtPcbg", "json", "major_event", "채권은행 등의 관리절차 개시", ('corp_code', 'bgn_de', 'end_de')),
    "bnkMngtPcsp": Endpoint("bnkMngtPcsp", "json", "major_event", "채권은행 등의 관리절차 중단", ('corp_code', 'bgn_de', 'end_de')),
    "otcprStkInvscrTrfDecsn": Endpoint("otcprStkInvscrTrfDecsn", "json", "major_event", "타법인 주식 및 출자증권 양도결정", ('corp_code', 'bgn_de', 'end_de')),
    "otcprStkInvscrInhDecsn": Endpoint("otcprStkInvscrInhDecsn", "json", "major_event", "타법인 주식 및 출자증권 양수결정", ('corp_code', 'bgn_de', 'end_de')),
    "dsRsOcr": Endpoint("dsRsOcr", "json", "major_event", "해산사유 발생", ('corp_code', 'bgn_de', 'end_de')),
    "ovLst": Endpoint("ovLst", "json", "major_event", "해외 증권시장 주권등 상장", ('corp_code', 'bgn_de', 'end_de')),
    "ovLstDecsn": Endpoint("ovLstDecsn", "json", "major_event", "해외 증권시장 주권등 상장 결정", ('corp_code', 'bgn_de', 'end_de')),
    "ovDlst": Endpoint("ovDlst", "json", "major_event", "해외 증권시장 주권등 상장폐지", ('corp_code', 'bgn_de', 'end_de')),
    "ovDlstDecsn": Endpoint("ovDlstDecsn", "json", "major_event", "해외 증권시장 주권등 상장폐지 결정", ('corp_code', 'bgn_de', 'end_de')),
    "cmpDvDecsn": Endpoint("cmpDvDecsn", "json", "major_event", "회사분할 결정", ('corp_code', 'bgn_de', 'end_de')),
    "cmpDvmgDecsn": Endpoint("cmpDvmgDecsn", "json", "major_event", "회사분할합병 결정", ('corp_code', 'bgn_de', 'end_de')),
    "cmpMgDecsn": Endpoint("cmpMgDecsn", "json", "major_event", "회사합병 결정", ('corp_code', 'bgn_de', 'end_de')),
    "ctrcvsBgrq": Endpoint("ctrcvsBgrq", "json", "major_event", "회생절차 개시신청", ('corp_code', 'bgn_de', 'end_de')),
    "adtServcCnclsSttus": Endpoint("adtServcCnclsSttus", "json", "periodic_report", "감사용역체결현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "indvdlByPay": Endpoint("indvdlByPay", "json", "periodic_report", "개인별 보수지급 금액(5억이상 상위5인)", ('corp_code', 'bsns_year', 'reprt_code')),
    "pssrpCptalUseDtls": Endpoint("pssrpCptalUseDtls", "json", "periodic_report", "공모자금의 사용내역", ('corp_code', 'bsns_year', 'reprt_code')),
    "entrprsBilScritsNrdmpBlce": Endpoint("entrprsBilScritsNrdmpBlce", "json", "periodic_report", "기업어음증권 미상환 잔액", ('corp_code', 'bsns_year', 'reprt_code')),
    "srtpdPsndbtNrdmpBlce": Endpoint("srtpdPsndbtNrdmpBlce", "json", "periodic_report", "단기사채 미상환 잔액", ('corp_code', 'bsns_year', 'reprt_code')),
    "unrstExctvMendngSttus": Endpoint("unrstExctvMendngSttus", "json", "periodic_report", "미등기임원 보수현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "alotMatter": Endpoint("alotMatter", "json", "periodic_report", "배당에 관한 사항", ('corp_code', 'bsns_year', 'reprt_code')),
    "prvsrpCptalUseDtls": Endpoint("prvsrpCptalUseDtls", "json", "periodic_report", "사모자금의 사용내역", ('corp_code', 'bsns_year', 'reprt_code')),
    "outcmpnyDrctrNdChangeSttus": Endpoint("outcmpnyDrctrNdChangeSttus", "json", "periodic_report", "사외이사 및 그 변동현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "mrhlSttus": Endpoint("mrhlSttus", "json", "periodic_report", "소액주주 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "newCaplScritsNrdmpBlce": Endpoint("newCaplScritsNrdmpBlce", "json", "periodic_report", "신종자본증권 미상환 잔액", ('corp_code', 'bsns_year', 'reprt_code')),
    "hmvAuditAllSttus": Endpoint("hmvAuditAllSttus", "json", "periodic_report", "이사·감사 전체의 보수현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "drctrAdtAllMendngSttusMendngPymntamtTyCl": Endpoint("drctrAdtAllMendngSttusMendngPymntamtTyCl", "json", "periodic_report", "이사·감사 전체의 보수현황(보수지급금액 - 유형별)", ('corp_code', 'bsns_year', 'reprt_code')),
    "drctrAdtAllMendngSttusGmtsckConfmAmount": Endpoint("drctrAdtAllMendngSttusGmtsckConfmAmount", "json", "periodic_report", "이사·감사 전체의 보수현황(주주총회 승인금액)", ('corp_code', 'bsns_year', 'reprt_code')),
    "hmvAuditIndvdlBySttus": Endpoint("hmvAuditIndvdlBySttus", "json", "periodic_report", "이사·감사의 개인별 보수 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "exctvSttus": Endpoint("exctvSttus", "json", "periodic_report", "임원 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "tesstkAcqsDspsSttus": Endpoint("tesstkAcqsDspsSttus", "json", "periodic_report", "자기주식 취득 및 처분 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "cndlCaplScritsNrdmpBlce": Endpoint("cndlCaplScritsNrdmpBlce", "json", "periodic_report", "조건부 자본증권 미상환 잔액", ('corp_code', 'bsns_year', 'reprt_code')),
    "stockTotqySttus": Endpoint("stockTotqySttus", "json", "periodic_report", "주식의 총수 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "irdsSttus": Endpoint("irdsSttus", "json", "periodic_report", "증자(감자) 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "empSttus": Endpoint("empSttus", "json", "periodic_report", "직원 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "detScritsIsuAcmslt": Endpoint("detScritsIsuAcmslt", "json", "periodic_report", "채무증권 발행실적", ('corp_code', 'bsns_year', 'reprt_code')),
    "hyslrChgSttus": Endpoint("hyslrChgSttus", "json", "periodic_report", "최대주주 변동현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "hyslrSttus": Endpoint("hyslrSttus", "json", "periodic_report", "최대주주 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "otrCprInvstmntSttus": Endpoint("otrCprInvstmntSttus", "json", "periodic_report", "타법인 출자현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "accnutAdtorNonAdtServcCnclsSttus": Endpoint("accnutAdtorNonAdtServcCnclsSttus", "json", "periodic_report", "회계감사인과의 비감사용역 계약체결 현황", ('corp_code', 'bsns_year', 'reprt_code')),
    "accnutAdtorNmNdAdtOpinion": Endpoint("accnutAdtorNmNdAdtOpinion", "json", "periodic_report", "회계감사인의 명칭 및 감사의견", ('corp_code', 'bsns_year', 'reprt_code')),
    "cprndNrdmpBlce": Endpoint("cprndNrdmpBlce", "json", "periodic_report", "회사채 미상환 잔액", ('corp_code', 'bsns_year', 'reprt_code')),
    "dvRs": Endpoint("dvRs", "json", "securities_registration", "분할", ('corp_code', 'bgn_de', 'end_de')),
    "extrRs": Endpoint("extrRs", "json", "securities_registration", "주식의포괄적교환·이전", ('corp_code', 'bgn_de', 'end_de')),
    "stkdpRs": Endpoint("stkdpRs", "json", "securities_registration", "증권예탁증권", ('corp_code', 'bgn_de', 'end_de')),
    "estkRs": Endpoint("estkRs", "json", "securities_registration", "지분증권", ('corp_code', 'bgn_de', 'end_de')),
    "bdRs": Endpoint("bdRs", "json", "securities_registration", "채무증권", ('corp_code', 'bgn_de', 'end_de')),
    "mgRs": Endpoint("mgRs", "json", "securities_registration", "합병", ('corp_code', 'bgn_de', 'end_de')),
    "majorstock": Endpoint("majorstock", "json", "shareholding", "대량보유 상황보고", ('corp_code',)),
    "elestock": Endpoint("elestock", "json", "shareholding", "임원·주요주주 소유보고", ('corp_code',)),
}


def by_category(category: str) -> list[Endpoint]:
    return [e for e in ENDPOINTS.values() if e.category == category]


def item_names(category: str) -> str:
    """도구 docstring에 넣을 한글 항목명 나열."""
    return ", ".join(e.name for e in by_category(category))


def resolve(category: str, item: str) -> Endpoint:
    """한글 항목명 또는 엔드포인트 id로 엔드포인트를 찾는다."""
    candidates = by_category(category)
    keyword = item.strip()
    for endpoint in candidates:
        if keyword in (endpoint.id, endpoint.name):
            return endpoint
    normalized = keyword.replace(" ", "").replace("·", "").lower()
    partial = [
        e
        for e in candidates
        if normalized in e.name.replace(" ", "").replace("·", "").lower()
        or normalized in e.id.lower()
    ]
    if len(partial) == 1:
        return partial[0]
    if partial:
        raise ValueError(
            f"'{item}'에 해당하는 항목이 여러 개입니다: {', '.join(e.name for e in partial)}"
        )
    raise ValueError(
        f"'{item}'은(는) {CATEGORY_NAMES[category]}에 없는 항목입니다. "
        f"사용 가능: {item_names(category)}"
    )
