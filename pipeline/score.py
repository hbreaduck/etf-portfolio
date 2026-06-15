"""
score.py — 종목 스코어 산출
  equal: 3개 ETF에서의 비중(%) 단순 합산
  aum_weighted: (미구현 — 추후 ETF AUM 파라미터 추가)
"""

import pandas as pd


def run(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    df: classify.run() 반환값
    반환: ticker별 최고득점 집계 DataFrame
      컬럼: ticker, name, gics_sector, tech_economic, bucket, score, etf_weights{}
    """
    method = cfg.get("scoring", "equal")

    # stock 자산만 스코어링 (cash/futures/etf 제외)
    stocks = df[df["asset_type"] == "stock"].copy()

    if method == "equal":
        # ETF별 비중 합산
        agg = (stocks.groupby(["ticker", "bucket", "gics_sector", "tech_economic"])
               .agg(score=("weight_pct", "sum"),
                    name=("name", "first"))
               .reset_index())
    else:
        raise NotImplementedError(f"scoring={method} 미구현")

    # ETF별 개별 비중 (디버그·참고용)
    pivot = (stocks.pivot_table(index="ticker", columns="ETF코드",
                                values="weight_pct", aggfunc="sum")
             .reset_index()
             .rename_axis(None, axis=1))

    agg = agg.merge(pivot, on="ticker", how="left")
    agg = agg.sort_values("score", ascending=False).reset_index(drop=True)

    return agg
