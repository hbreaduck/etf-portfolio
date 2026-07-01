"""
collect.py — 4종 ETF 구성종목 수집
  456600 TIMEFOLIO 글로벌AI인공지능액티브  (timeetf.co.kr  Excel)
  426030 TIMEFOLIO 미국나스닥100액티브     (timeetf.co.kr  Excel)
  00015B0 KoAct 미국나스닥성장기업액티브   (samsungactive   JSON API)
  466950 TIGER 글로벌AI액티브             (WiseReport CU_data + yfinance 비중 역산)
"""

import io
import re
import json
import warnings
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

TIGER_ETF_CODE = "466950"

# 종목명 → (파이프라인용 base 티커, 통화) 매핑 (WiseReport 영문명 기준)
# TIGER 사이트 PDF 엔드포인트가 접근 불가하여 WiseReport CU_data + yfinance 종가로 비중 역산
_TIGER_NAME_MAP: dict[str, tuple[str, str]] = {
    "MURATA MANUFACTURING CO LTD":    ("6981",   "JPY"),
    "HUA HONG GRACE SEMICONDUCTOR":   ("1347",   "HKD"),
    "INTEL CORP":                     ("INTC",   "USD"),
    "ADVANCED MICRO DEVICES":         ("AMD",    "USD"),
    "GLOBALFOUNDRIES INC":            ("GFS",    "USD"),
    "INFINEON TECHNOLOGIES AG":       ("IFNNY",  "USD"),
    "NAURA TECHNOLOGY GROUP CO-A":    ("002371", "CNY"),
    "삼성전자":                           ("005930", "KRW"),
    "ARM HOLDINGS PLC-ADR":           ("ARM",    "USD"),
    "ONTO INNOVATION INC":            ("ONTO",   "USD"),
    "MICRON TECHNOLOGY INC":          ("MU",     "USD"),
    "LAM RESEARCH CORP":              ("LRCX",   "USD"),
    "KLA CORP":                       ("KLAC",   "USD"),
    "MARVELL TECHNOLOGY INC":         ("MRVL",   "USD"),
    "KNOWLEDGE ATLAS TECHNOLOGY-H":   ("2513",   "HKD"),
    "KIOXIA HOLDINGS CORP":           ("285A",   "JPY"),
    "SANDISK CORP":                   ("SNDK",   "USD"),
    "APPLIED MATERIALS INC":          ("AMAT",   "USD"),
    "TERADYNE INC":                   ("TER",    "USD"),
    "SEAGATE TECHNOLOGY HOLDINGS":    ("STX",    "USD"),
    "BLOOM ENERGY CORP- A":           ("BE",     "USD"),
    "SPACE EXPLORATION TECHN-CL A":   ("SPCX",   "USD"),
    "ANALOG DEVICES INC":             ("ADI",    "USD"),
    "VERTIV HOLDINGS CO-A":           ("VRT",    "USD"),
    "WESTERN DIGITAL CORP":           ("WDC",    "USD"),
    "INTL BUSINESS MACHINES CORP":    ("IBM",    "USD"),
    "CORNING INC":                    ("GLW",    "USD"),
    "삼성전기":                           ("009150", "KRW"),
    "AMAZON.COM INC":                 ("AMZN",   "USD"),
    "TOWER SEMICONDUCTOR LTD":        ("TSEM",   "USD"),
    "SK하이닉스":                         ("000660", "KRW"),
    "ALPHABET INC-CL A":              ("GOOGL",  "USD"),
    "COHERENT CORP":                  ("COHR",   "USD"),
    "GE VERNOVA INC":                 ("GEV",    "USD"),
    "META PLATFORMS INC-CLASS A":     ("META",   "USD"),
    "LUMENTUM HOLDINGS INC":          ("LITE",   "USD"),
    "설정현금액":                          ("CASH",   "KRW"),
    "원화현금":                            ("CASH",   "KRW"),
}

# base 티커 → yfinance 티커 (거래소 suffix 필요한 경우만)
_TIGER_YF_TICKER: dict[str, str] = {
    "6981":   "6981.T",
    "1347":   "1347.HK",
    "002371": "002371.SZ",
    "005930": "005930.KS",
    "009150": "009150.KS",
    "000660": "000660.KS",
    "2513":   "2513.HK",
    "285A":   "285A.T",
}

_FX_FALLBACK = {"USD": 1380.0, "JPY": 9.2, "HKD": 177.0, "CNY": 190.0, "KRW": 1.0}

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


# ── TIGER ETF (466950) ─────────────────────────────────────────────────────────

def _tiger_fx() -> dict[str, float]:
    """USD/JPY/HKD/CNY → KRW 환율 (yfinance, 실패 시 fallback)"""
    import yfinance as yf
    fx = dict(_FX_FALLBACK)
    pairs = {"USD": "USDKRW=X", "JPY": "JPYKRW=X", "HKD": "HKDKRW=X", "CNY": "CNYKRW=X"}
    for ccy, sym in pairs.items():
        try:
            hist = yf.Ticker(sym).history(period="3d")
            if not hist.empty:
                fx[ccy] = float(hist["Close"].iloc[-1])
        except Exception:
            pass
    return fx


def _tiger_prices(base_tickers: list[str]) -> dict[str, float]:
    """yfinance 최근 종가 일괄 조회. 반환 키 = base 티커(파이프라인용)."""
    import yfinance as yf
    prices: dict[str, float] = {}
    for base_tk in base_tickers:
        yf_tk = _TIGER_YF_TICKER.get(base_tk, base_tk)
        try:
            hist = yf.Ticker(yf_tk).history(period="5d")
            if not hist.empty:
                prices[base_tk] = float(hist["Close"].iloc[-1])
        except Exception:
            pass
    return prices


def fetch_tigeretf(etf_code: str, sess: requests.Session) -> pd.DataFrame:
    """
    466950 TIGER 글로벌AI액티브 수집기
    - WiseReport(NaverComp 임베드)에서 CU_data(종목명+수량) 추출
    - yfinance 종가 × 환율로 평가금액(원) 계산, 합계 대비 비중(%) 역산
    - 티커 미확인 종목은 비중=NaN 처리
    """
    url = (f"https://navercomp.wisereport.co.kr/v2/ETF/index.aspx"
           f"?cmp_cd={etf_code}&cn=")
    resp = sess.get(url,
                    headers={"Referer": f"https://finance.naver.com/item/main.naver?code={etf_code}"},
                    timeout=20)
    resp.raise_for_status()
    html = resp.content.decode("utf-8", errors="replace")

    m = re.search(r'var\s+CU_data\s*=\s*(\{.*?\});\s*\n', html, re.DOTALL)
    if not m:
        raise ValueError(f"[{etf_code}] WiseReport CU_data 없음")
    cu_list = json.loads(m.group(1)).get("grid_data", [])
    if not cu_list:
        raise ValueError(f"[{etf_code}] WiseReport CU_data 빈 목록")

    # 환율 & 종가
    fx = _tiger_fx()
    tickers_needed = list({
        t for item in cu_list
        for t, _ in [_TIGER_NAME_MAP.get(item["STK_NM_KOR"], (None, None))]
        if t and t != "CASH"
    })
    prices = _tiger_prices(tickers_needed)

    rows = []
    for item in cu_list:
        nm  = item["STK_NM_KOR"]
        qty = _to_num(item["AGMT_STK_CNT"])
        ticker, currency = _TIGER_NAME_MAP.get(nm, (None, None))

        if ticker == "CASH" or nm in ("설정현금액", "원화현금"):
            # 원화현금: qty가 CU당 KRW금액, 설정현금액: qty=0
            eval_krw = qty
            t_raw = "CASH"
        elif ticker is None:
            # 티커 미확인: 비중 역산 불가 → NaN
            eval_krw = float("nan")
            t_raw = "".join(nm.split()[:2])[:8].upper()
        else:
            price = prices.get(ticker)
            eval_krw = price * fx.get(currency, 1.0) * qty if price else float("nan")
            t_raw = ticker

        rows.append({
            "ETF코드":       etf_code,
            "티커_원본":     t_raw,
            "종목명":        nm,
            "수량":          qty,
            "평가금액(원)":  eval_krw,
            "비중(%)":       float("nan"),   # 합산 후 재계산
        })

    df = pd.DataFrame(rows, columns=RAW_COLS)
    total = df["평가금액(원)"].sum(skipna=True)
    if total > 0:
        df["비중(%)"] = df["평가금액(원)"] / total * 100

    df = df[df["종목명"].str.strip().ne("") & df["종목명"].notna()]
    return df[RAW_COLS]


# ── 공개 인터페이스 ────────────────────────────────────────────────────────────

def fetch_all() -> dict[str, pd.DataFrame]:
    """4종 ETF 구성종목 수집. 반환값: {etf_code: DataFrame(RAW_COLS)}"""
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

    try:
        results[TIGER_ETF_CODE] = fetch_tigeretf(TIGER_ETF_CODE, sess)
    except Exception as e:
        errors[TIGER_ETF_CODE] = str(e)

    if errors:
        for code, msg in errors.items():
            print(f"  [WARN] {code} 수집 실패: {msg}")

    return results
