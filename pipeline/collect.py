"""
collect.py — 3종 ETF 구성종목 수집
  456600 TIMEFOLIO 글로벌AI인공지능액티브  (timeetf.co.kr  Excel)
  426030 TIMEFOLIO 미국나스닥100액티브     (timeetf.co.kr  Excel)
  00015B0 KoAct 미국나스닥성장기업액티브   (samsungactive   JSON API)
"""

import io
import requests
import pandas as pd

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

TIMEFOLIO_ETFS = {
    "456600": {"name": "TIMEFOLIO 글로벌AI인공지능액티브", "idx": 6, "cate": "001"},
    "426030": {"name": "TIMEFOLIO 미국나스닥100액티브",    "idx": 2, "cate": "001"},
}

KOACT = {"code": "00015B0", "name": "KoAct 미국나스닥성장기업액티브", "fId": "2ETFQ1"}
SAMSUNG_BASE = "https://www.samsungactive.co.kr"

RAW_COLS = ["ETF코드", "티커_원본", "종목명", "수량", "평가금액(원)", "비중(%)"]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _to_num(val) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, AttributeError):
        return float("nan")


# ── TIMEFOLIO ──────────────────────────────────────────────────────────────────

def fetch_timefolio(etf_code: str, sess: requests.Session) -> pd.DataFrame:
    info = TIMEFOLIO_ETFS[etf_code]
    url = f"https://www.timeetf.co.kr/pdf_excel.php?idx={info['idx']}&cate={info['cate']}"
    resp = sess.get(url, timeout=20)
    resp.raise_for_status()

    df_raw = pd.read_excel(io.BytesIO(resp.content), header=None)

    # 헤더 행 탐지
    header_row = None
    for i, row in df_raw.iterrows():
        joined = " ".join(row.astype(str).str.lower())
        if any(k in joined for k in ["종목명", "비중", "수량"]):
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"[{etf_code}] 헤더 행 탐지 실패")

    df = df_raw.iloc[header_row:].copy()
    df.columns = [str(c).strip() for c in df.iloc[0]]
    df = df.iloc[1:].reset_index(drop=True).dropna(how="all")

    col_map = {}
    for c in df.columns:
        lc = str(c).lower()
        if "티커" in lc or "종목코드" in lc:
            col_map[c] = "티커_원본"
        elif "종목명" in lc:
            col_map[c] = "종목명"
        elif "수량" in lc:
            col_map[c] = "수량"
        elif "평가금액" in lc:
            col_map[c] = "평가금액(원)"
        elif "비중" in lc:
            col_map[c] = "비중(%)"

    df = df.rename(columns=col_map)
    result = pd.DataFrame()
    result["티커_원본"]  = df.get("티커_원본", "").astype(str).str.strip()
    result["종목명"]     = df.get("종목명", "").astype(str).str.strip()
    result["수량"]       = df.get("수량",       pd.Series(dtype=object)).apply(_to_num)
    result["평가금액(원)"] = df.get("평가금액(원)", pd.Series(dtype=object)).apply(_to_num)
    result["비중(%)"]    = df.get("비중(%)",     pd.Series(dtype=object)).apply(_to_num)
    result["ETF코드"]    = etf_code  # 빈 DF에 먼저 할당하면 확장 시 NaN이 되므로 마지막에 대입

    result = result[result["종목명"].str.strip().ne("") & result["종목명"].notna()]
    return result[RAW_COLS]


# ── KoAct ──────────────────────────────────────────────────────────────────────

def fetch_koact(sess: requests.Session) -> pd.DataFrame:
    fId  = KOACT["fId"]
    code = KOACT["code"]
    hdrs = {**HEADERS,
            "Referer": f"{SAMSUNG_BASE}/etf/view.do?id={fId}",
            "Accept": "application/json, */*; q=0.01"}

    info = sess.get(f"{SAMSUNG_BASE}/api/v1/product/etf/{fId}.do",
                    headers=hdrs, timeout=15).json()
    gijun = (info.get("pdf", {}).get("gijunYMD", "")
             or info["suik"]["standardList"][0]["EVAL_D"])

    pdf = sess.get(f"{SAMSUNG_BASE}/api/v1/product/etf-pdf/{fId}.do",
                   params={"gijunYMD": gijun}, headers=hdrs, timeout=15).json()
    holdings = pdf["pdf"]["list"]

    rows = [{"ETF코드":      code,
             "티커_원본":    str(h.get("itmNo", "")).strip(),
             "종목명":       str(h.get("secNm", "")).strip(),
             "수량":         _to_num(h.get("applyQ", "")),
             "평가금액(원)": _to_num(h.get("evalA", "")),
             "비중(%)":      _to_num(h.get("ratio", ""))}
            for h in holdings]

    df = pd.DataFrame(rows, columns=RAW_COLS)
    return df[df["종목명"].str.strip().ne("")]


# ── 공개 인터페이스 ────────────────────────────────────────────────────────────

def fetch_all() -> dict[str, pd.DataFrame]:
    """3종 ETF 구성종목 수집. 반환값: {etf_code: DataFrame(RAW_COLS)}"""
    sess = _session()
    results: dict[str, pd.DataFrame] = {}
    errors:  dict[str, str] = {}

    for code in TIMEFOLIO_ETFS:
        try:
            results[code] = fetch_timefolio(code, sess)
        except Exception as e:
            errors[code] = str(e)

    try:
        results[KOACT["code"]] = fetch_koact(sess)
    except Exception as e:
        errors[KOACT["code"]] = str(e)

    if errors:
        for code, msg in errors.items():
            print(f"  [WARN] {code} 수집 실패: {msg}")

    return results
