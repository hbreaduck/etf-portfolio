"""
perf.py — 포트폴리오 일간 수익률 계산 + 누적 이력 저장

지표 정의:
  port_usd_pct  : Σ(종목 등락률 × 타깃 비중)  — USD 기준
  port_krw_pct  : (1+port_usd) × (1+USDKRW 등락률) − 1
  fx_pct        : USDKRW 일간 등락률 (원화 강세 시 음수)
  bm_usd_pct    : 벤치마크(기본 QQQ) 일간 등락률
  excess_usd_pct: port_usd − bm_usd
"""

import pathlib
import pandas as pd

# 파이프라인 티커 → yfinance 티커 매핑 (None 이면 수익률 수집 제외)
# 여기 없는 6자리 숫자 티커는 run()에서 KRX(.KS)로 자동 처리된다.
_TICKER_MAP: dict[str, str | None] = {
    # 홍콩
    "9988":   "9988.HK",
    "700":    "0700.HK",
    "1347":   "1347.HK",
    "2513":   None,
    # 일본
    "285A":   "285A.T",
    "6981":   "6981.T",
    # 한국 (KRX)
    "000660": "000660.KS",   # SK하이닉스
    "005930": "005930.KS",   # 삼성전자
    "009150": "009150.KS",   # 삼성전기
    # SK하이닉스 소스 축약 티커 변형 (수집 소스가 종목명을 잘라 보냄)
    "SKHY":   "000660.KS",
    "SKHYV":  "000660.KS",
    # 중국 심천
    "002371": "002371.SZ",   # NAURA
    # 파생·지수 ETF (수집 제외)
    "0043Y0": None,
}

_FX_TICKER = "USDKRW=X"


def _fetch_closes(yf_tickers: list[str]) -> pd.DataFrame:
    """yfinance로 5영업일 일봉을 가져와 종가 DataFrame 반환."""
    import yfinance as yf

    if not yf_tickers:
        return pd.DataFrame()

    raw = yf.download(
        yf_tickers,
        period="5d",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    # yfinance 버전에 따라 MultiIndex / 단일 레벨 처리
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]].rename(columns={"Close": yf_tickers[0]})

    # 단일 티커가 Series로 반환된 경우
    if isinstance(closes, pd.Series):
        closes = closes.to_frame(name=yf_tickers[0])

    return closes


def _calc_returns(closes: pd.DataFrame) -> dict[str, tuple[float, object]]:
    """각 티커의 최근 2거래일 종가로 (등락률, 사용한 최신 종가일)을 반환 (캘린더 독립)."""
    result = {}
    for ticker in closes.columns:
        series = closes[ticker].dropna()
        if len(series) >= 2:
            result[ticker] = (float(series.iloc[-1] / series.iloc[-2] - 1),
                              series.index[-1])
        else:
            result[ticker] = (float("nan"), None)
    return result


def run(portfolio: pd.DataFrame, cfg: dict, date_str: str) -> dict:
    """
    portfolio : construct.run() 반환 DataFrame
    반환      : perf dict (report.py에서 소비)
    """
    perf_cfg  = cfg.get("performance", {})
    bm_ticker = perf_cfg.get("benchmark", "QQQ")
    hist_path = pathlib.Path(cfg["paths"].get("perf_history", "data/perf_history.parquet"))

    # 주식 티커만 추출 (cash 제외)
    stocks = portfolio[portfolio["bucket"] != "cash"].copy()
    tickers = stocks["ticker"].tolist()

    # yfinance 티커 매핑
    #  - 명시 매핑 우선 (None 이면 제외)
    #  - 매핑에 없는 6자리 숫자 티커는 KRX(.KS)로 자동 처리
    fetch_map: dict[str, str] = {}   # original → yf ticker
    for t in tickers:
        if t in _TICKER_MAP:
            mapped = _TICKER_MAP[t]
        elif t.isdigit() and len(t) == 6:
            mapped = f"{t}.KS"
        else:
            mapped = t
        if mapped:
            fetch_map[t] = mapped

    all_yf = sorted(set(fetch_map.values())) + [bm_ticker, _FX_TICKER]
    print(f"  [perf] 수익률 조회: 종목 {len(fetch_map)}개 + BM({bm_ticker}) + USDKRW")

    try:
        closes = _fetch_closes(all_yf)
    except Exception as e:
        print(f"  [perf] yfinance 오류: {e}")
        return {"available": False, "reason": str(e)}

    if closes.empty:
        return {"available": False, "reason": "데이터 없음"}

    all_returns = _calc_returns(closes)

    # ── 포트폴리오 USD 수익률 ──────────────────────────────────────────────────
    port_usd_sum  = 0.0
    weight_used   = 0.0
    missing       = []
    contrib_rows  = []
    stock_dates   = []   # 실제 등락률 계산에 사용한 종목 종가일

    for _, row in stocks.iterrows():
        t = row["ticker"]
        w = float(row["target_weight"])
        yft = fetch_map.get(t)
        r, rd = all_returns.get(yft, (float("nan"), None)) if yft else (float("nan"), None)

        if pd.notna(r):
            stock_dates.append((rd, w))
            contrib = r * w
            port_usd_sum += contrib
            weight_used  += w
            contrib_rows.append({
                "ticker": t,
                "name":   row.get("name", ""),
                "ret_pct":    round(r * 100, 3),
                "weight_pct": round(w * 100, 2),
                "contrib_pct": round(contrib * 100, 3),
            })
        else:
            missing.append(t)

    # 미수집 종목 비중을 보유 종목으로 재안분
    total_stock_w = float(stocks["target_weight"].sum())
    if 0 < weight_used < total_stock_w:
        port_usd_sum = port_usd_sum * (total_stock_w / weight_used)

    # ── BM / FX ───────────────────────────────────────────────────────────────
    bm_ret = all_returns.get(bm_ticker, (float("nan"), None))[0]
    fx_ret = all_returns.get(_FX_TICKER, (float("nan"), None))[0]

    port_krw    = (1 + port_usd_sum) * (1 + fx_ret) - 1 if pd.notna(fx_ret) else float("nan")
    excess_usd  = port_usd_sum - bm_ret               if pd.notna(bm_ret)  else float("nan")

    # ── 기준 날짜 파악 ─────────────────────────────────────────────────────────
    # 시장별 데이터 지연으로 종목마다 최신 종가일이 다를 수 있어,
    # "가장 많은 비중이 반영된 종가일"을 대표 기준일로 잡는다 (동률이면 최신).
    as_of_date = ""
    from collections import defaultdict
    weight_by_date: dict = defaultdict(float)
    for d, w in stock_dates:
        if d is not None:
            weight_by_date[d] += w
    if weight_by_date:
        as_of_ts = max(weight_by_date, key=lambda k: (weight_by_date[k], k))
        as_of_date = as_of_ts.strftime("%Y-%m-%d")

    # 신선도 점검: 리포트 기준일 대비 종가 지연 일수
    stale_days = None
    try:
        from datetime import datetime as _dt
        if as_of_date:
            stale_days = (_dt.strptime(date_str, "%Y%m%d").date()
                          - _dt.strptime(as_of_date, "%Y-%m-%d").date()).days
    except Exception:
        stale_days = None

    if missing:
        print(f"  [perf] 수익률 미수집: {missing}")
    if stale_days is not None and stale_days >= 2:
        print(f"  [perf] [!] 종가 지연: 기준일 {date_str} 대비 최신 종가 {as_of_date} ({stale_days}일 전) "
              f"- 데이터 소스(yfinance) 반영 지연")

    print(f"  [perf] 기준 종가: {as_of_date or '?'}  "
          f"포트USD: {port_usd_sum*100:+.2f}%  "
          f"BM({bm_ticker}): {bm_ret*100:+.2f}%  "
          f"초과: {excess_usd*100:+.2f}%  "
          f"USDKRW: {fx_ret*100:+.2f}%  "
          f"포트KRW: {port_krw*100:+.2f}%")

    def _pct(v):
        return round(float(v) * 100, 3) if pd.notna(v) else None

    result = {
        "available":       True,
        "date":            date_str,
        "as_of_date":      as_of_date,
        "stale_days":      stale_days,
        "port_usd_pct":    _pct(port_usd_sum),
        "bm_usd_pct":      _pct(bm_ret),
        "fx_pct":          _pct(fx_ret),
        "port_krw_pct":    _pct(port_krw),
        "excess_usd_pct":  _pct(excess_usd),
        "bm_ticker":       bm_ticker,
        "missing":         missing,
        "contrib":         sorted(contrib_rows, key=lambda x: -abs(x["contrib_pct"])),
    }

    _save_history(result, hist_path)
    return result


def _save_history(result: dict, path: pathlib.Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    new_row = pd.DataFrame([{
        "date":            result["date"],
        "port_usd_pct":    result.get("port_usd_pct"),
        "port_krw_pct":    result.get("port_krw_pct"),
        "fx_pct":          result.get("fx_pct"),
        "bm_usd_pct":      result.get("bm_usd_pct"),
        "excess_usd_pct":  result.get("excess_usd_pct"),
    }])

    if path.exists():
        hist = pd.read_parquet(path)
        hist = hist[hist["date"] != result["date"]]
        hist = pd.concat([hist, new_row], ignore_index=True)
    else:
        hist = new_row

    hist = hist.sort_values("date").reset_index(drop=True)
    hist.to_parquet(path, index=False)
    print(f"  [perf] 이력 저장 → {path} ({len(hist)}일 누적)")
