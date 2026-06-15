"""
normalize.py — raw DataFrame → 정규화된 단일 DataFrame + parquet 누적 저장
"""

import re
import json
import datetime
import pathlib
import pandas as pd

# 현금/파생/ETF 판별 정규식
_CASH_PAT    = re.compile(r"^(CASH|KRD|현금|설정현금액|원화현금)", re.I)
_FUTURES_PAT = re.compile(r"INDEX$|FUTURE|MINI|M\d$", re.I)   # NQM6 INDEX 등
_KR_ETF_PAT  = re.compile(r"^[0-9A-Z]{6,7}$")                 # 0043Y0 형태


def normalize_ticker(raw: str) -> str:
    """raw 티커 문자열 → 정규화된 base ticker"""
    t = str(raw).strip()
    if not t or t.lower() in ("nan", "none"):
        return "CASH"
    if _CASH_PAT.search(t):
        return "CASH"
    base = t.split()[0].upper()
    return base


def ticker_type(ticker: str, raw: str) -> str:
    """cash / futures / etf / stock 분류"""
    if ticker == "CASH":
        return "cash"
    raw_upper = str(raw).upper()
    if _FUTURES_PAT.search(raw_upper):
        return "futures"
    if _KR_ETF_PAT.match(ticker) and len(ticker) >= 6:
        return "etf"
    return "stock"


def run(raw: dict[str, pd.DataFrame], date_str: str, cfg: dict) -> pd.DataFrame:
    """
    raw: {etf_code: DataFrame} from collect.fetch_all()
    date_str: 'YYYYMMDD'
    반환: 정규화된 통합 DataFrame (하루치)
    """
    raw_dir      = pathlib.Path(cfg["paths"]["raw_dir"])
    snapshot_path = pathlib.Path(cfg["paths"]["snapshot"])

    # 날짜 폴더에 raw 보존
    date_dir = raw_dir / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for code, df in raw.items():
        # raw parquet 저장
        df.to_parquet(date_dir / f"{code}.parquet", index=False)

        norm = df.copy()
        norm["date"]       = date_str
        norm["ticker"]     = norm["티커_원본"].apply(normalize_ticker)
        norm["asset_type"] = [ticker_type(t, r)
                              for t, r in zip(norm["ticker"], norm["티커_원본"])]
        frames.append(norm)

    combined = pd.concat(frames, ignore_index=True)

    # 컬럼 정리
    combined = combined.rename(columns={"티커_원본": "ticker_raw",
                                        "종목명": "name",
                                        "수량": "quantity",
                                        "평가금액(원)": "market_value_krw",
                                        "비중(%)": "weight_pct"})

    cols_out = ["date", "ETF코드", "ticker", "ticker_raw", "name",
                "asset_type", "quantity", "market_value_krw", "weight_pct"]
    combined = combined[cols_out]

    # parquet 누적 저장 (같은 날 데이터는 교체)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    if snapshot_path.exists():
        prev = pd.read_parquet(snapshot_path)
        prev = prev[prev["date"] != date_str]
        updated = pd.concat([prev, combined], ignore_index=True)
    else:
        updated = combined

    updated.to_parquet(snapshot_path, index=False)
    print(f"  [normalize] {len(combined)}행 → {snapshot_path}")

    return combined
