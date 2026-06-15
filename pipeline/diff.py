"""
diff.py — 전일 대비 포트폴리오 변동 분석
  - 포트폴리오를 data/portfolios/{date}.parquet에 저장
  - 직전 날짜 스냅샷과 비교해 IN/OUT/CHANGE 분류
  - 첫 실행(이전 스냅샷 없음)이면 is_first_run=True 반환
"""

import pathlib
import pandas as pd


def _find_prev(port_dir: pathlib.Path, today: str):
    """today 이전 날짜의 가장 최근 parquet 반환 (없으면 None, None)."""
    files = sorted(port_dir.glob("*.parquet"))
    prev_files = [f for f in files if f.stem < today]
    if not prev_files:
        return None, None
    pf = prev_files[-1]
    return pf.stem, pd.read_parquet(pf)


def run(port: pd.DataFrame, cfg: dict, date_str: str) -> dict:
    """
    port     : construct.run() 반환 DataFrame
    반환 dict:
      is_first_run=True  → {'is_first_run': True, 'date': ...}
      is_first_run=False → {is_first_run, prev_date, date,
                            added, removed, changes, held,
                            turnover, trade_list}
    """
    port_dir = pathlib.Path(cfg["paths"].get("portfolio_dir", "data/portfolios"))
    port_dir.mkdir(parents=True, exist_ok=True)

    # 오늘 포트폴리오를 먼저 저장 (다음 실행에서 prev가 됨)
    today_path = port_dir / f"{date_str}.parquet"
    port.to_parquet(today_path, index=False)
    print(f"  [diff] 포트폴리오 스냅샷 저장 → {today_path}")

    threshold = float(cfg.get("rebalance_threshold", 0.005))

    prev_date, prev_port = _find_prev(port_dir, date_str)

    if prev_port is None:
        print("  [diff] 이전 스냅샷 없음 → 기준일(최초) 처리")
        return {"is_first_run": True, "date": date_str}

    print(f"  [diff] 비교 기준일: {prev_date}")

    name_map      = dict(zip(port["ticker"],      port["name"]))
    prev_name_map = dict(zip(prev_port["ticker"], prev_port["name"]))

    today_w = dict(zip(port["ticker"],      port["target_weight"]))
    prev_w  = dict(zip(prev_port["ticker"], prev_port["target_weight"]))

    all_tickers = set(today_w) | set(prev_w)

    added      = []
    removed    = []
    changes    = []
    held       = []
    trade_list = []

    for t in sorted(all_tickers):
        curr  = today_w.get(t, 0.0)
        prev  = prev_w.get(t, 0.0)
        delta = curr - prev
        nm    = name_map.get(t) or prev_name_map.get(t, t)

        if prev == 0.0 and curr > 0.0:
            added.append({"ticker": t, "name": nm,
                          "target_weight": curr, "target_pct": round(curr * 100, 2)})
            trade_list.append({"ticker": t, "name": nm,
                               "direction": "BUY", "delta_pct": round(curr * 100, 2)})

        elif curr == 0.0 and prev > 0.0:
            removed.append({"ticker": t, "name": nm,
                            "prev_weight": prev, "prev_pct": round(prev * 100, 2)})
            trade_list.append({"ticker": t, "name": nm,
                               "direction": "SELL", "delta_pct": round(-prev * 100, 2)})

        elif abs(delta) >= threshold:
            direction = "BUY" if delta > 0 else "SELL"
            changes.append({"ticker": t, "name": nm,
                            "prev_pct": round(prev * 100, 2),
                            "curr_pct": round(curr * 100, 2),
                            "delta_pct": round(delta * 100, 2)})
            trade_list.append({"ticker": t, "name": nm,
                               "direction": direction, "delta_pct": round(delta * 100, 2)})
        else:
            held.append(t)

    # 턴오버 = 전체 비중변화 합계 / 2 (편도 기준)
    turnover = sum(abs(today_w.get(t, 0.0) - prev_w.get(t, 0.0)) for t in all_tickers) / 2.0

    result = {
        "is_first_run": False,
        "prev_date":    prev_date,
        "date":         date_str,
        "added":        added,
        "removed":      removed,
        "changes":      sorted(changes, key=lambda x: abs(x["delta_pct"]), reverse=True),
        "held":         held,
        "turnover":     round(turnover * 100, 2),
        "trade_list":   sorted(trade_list, key=lambda x: abs(x["delta_pct"]), reverse=True),
    }

    print(f"  [diff] IN={len(added)}, OUT={len(removed)}, "
          f"변화={len(changes)}, 유지={len(held)}, 턴오버={result['turnover']:.2f}%")

    return result
