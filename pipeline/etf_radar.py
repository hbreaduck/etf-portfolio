"""
etf_radar.py — 소스 ETF 3종 구성종목 전일/전주 대비 변동 분석
"""

import pathlib
import pandas as pd

ETF_SHORT = {
    "456600":  "AI인공지능",
    "426030":  "나스닥100",
    "00015B0": "나스닥성장",
}
ETF_CODES = list(ETF_SHORT.keys())


def run(cfg: dict, portfolio: pd.DataFrame, date_str: str) -> dict:
    """
    holdings.parquet에서 오늘/이전 기간 구성종목을 비교해 레이더 결과 반환.

    반환 dict:
      available    : bool
      prev_date    : str
      period       : 'daily' | 'weekly'
      new_entries  : [{ticker, name, etfs, in_portfolio, star}]
      exits        : [{ticker, name, etfs, in_portfolio}]
      movers       : [{ticker, name, total_delta, delta_by_etf, in_portfolio, star}]
    """
    snap_path = pathlib.Path(cfg["paths"]["snapshot"])
    if not snap_path.exists():
        return {"available": False, "reason": "스냅샷 없음"}

    snap = pd.read_parquet(snap_path)
    snap = snap[snap["asset_type"] == "stock"].copy()

    radar_cfg   = cfg.get("etf_radar", {})
    period      = radar_cfg.get("compare_period", "daily")
    min_chg     = float(radar_cfg.get("min_change_pct", 0.5))

    dates = sorted(snap["date"].unique())
    if date_str not in dates or len(dates) < 2:
        return {"available": False, "reason": "비교할 이전 스냅샷 없음"}

    today_idx = dates.index(date_str)
    prev_idx  = max(0, today_idx - (5 if period == "weekly" else 1))
    if prev_idx == today_idx:
        return {"available": False, "reason": "비교할 이전 스냅샷 없음"}

    prev_date  = dates[prev_idx]
    today_snap = snap[snap["date"] == date_str]
    prev_snap  = snap[snap["date"] == prev_date]

    # 현재 포트폴리오 티커 집합 (현금 제외)
    port_tickers = set(portfolio[portfolio["bucket"] != "cash"]["ticker"])

    # (ETF코드, ticker) → weight_pct
    def to_wdict(df):
        return {(r["ETF코드"], r["ticker"]): r["weight_pct"]
                for _, r in df.iterrows()}

    today_w = to_wdict(today_snap)
    prev_w  = to_wdict(prev_snap)

    # 이름 맵
    name_map = {}
    for _, r in pd.concat([today_snap, prev_snap]).iterrows():
        if r["ticker"] not in name_map and r["name"]:
            name_map[r["ticker"]] = r["name"]

    # 티커별 집계
    all_keys = set(today_w) | set(prev_w)
    info: dict[str, dict] = {}

    for (etf, ticker) in all_keys:
        curr  = today_w.get((etf, ticker), 0.0)
        prev  = prev_w.get((etf, ticker), 0.0)
        delta = curr - prev

        if ticker not in info:
            info[ticker] = {
                "name":         name_map.get(ticker, ticker),
                "etfs_today":   [],
                "etfs_new":     [],
                "etfs_out":     [],
                "delta_by_etf": {},
                "in_portfolio": ticker in port_tickers,
            }

        if curr > 0:
            info[ticker]["etfs_today"].append(etf)
        if prev == 0.0 and curr > 0.0:
            info[ticker]["etfs_new"].append(etf)
        if curr == 0.0 and prev > 0.0:
            info[ticker]["etfs_out"].append(etf)
        if abs(delta) > 1e-6:
            info[ticker]["delta_by_etf"][etf] = round(delta, 4)

    # ── 신규 편입 ──────────────────────────────────────────────────────────
    new_entries = []
    for t, d in info.items():
        if not d["etfs_new"]:
            continue
        etfs_up = [e for e, v in d["delta_by_etf"].items() if v > 0]
        new_entries.append({
            "ticker":       t,
            "name":         d["name"],
            "etfs":         d["etfs_new"],
            "in_portfolio": d["in_portfolio"],
            "star":         len(etfs_up) >= 2,
        })
    new_entries.sort(key=lambda x: x["ticker"])

    # ── 완전 편출 ──────────────────────────────────────────────────────────
    exits = []
    for t, d in info.items():
        if d["etfs_out"] and not d["etfs_today"]:
            exits.append({
                "ticker":       t,
                "name":         d["name"],
                "etfs":         d["etfs_out"],
                "in_portfolio": d["in_portfolio"],
            })
    exits.sort(key=lambda x: x["ticker"])

    # ── 비중 급변 종목 ─────────────────────────────────────────────────────
    movers = []
    for t, d in info.items():
        if not d["delta_by_etf"]:
            continue
        total = round(sum(d["delta_by_etf"].values()), 4)
        if abs(total) < min_chg:
            continue
        etfs_up = [e for e, v in d["delta_by_etf"].items() if v > 0]
        movers.append({
            "ticker":       t,
            "name":         d["name"],
            "total_delta":  total,
            "delta_by_etf": d["delta_by_etf"],
            "in_portfolio": d["in_portfolio"],
            "star":         len(etfs_up) >= 2,
        })
    movers.sort(key=lambda x: abs(x["total_delta"]), reverse=True)

    return {
        "available":      True,
        "prev_date":      prev_date,
        "date":           date_str,
        "period":         period,
        "min_change_pct": min_chg,
        "new_entries":    new_entries,
        "exits":          exits,
        "movers":         movers[:25],
    }
