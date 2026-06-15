"""
classify.py — 정규화 DataFrame에 GICS 섹터 + 버킷(tech/other/cash) 태깅
"""

import pathlib
import pandas as pd


def run(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    df: normalize.run() 반환값
    반환: gics_sector, tech_economic, bucket 컬럼 추가된 DataFrame
    """
    map_path = pathlib.Path(cfg["paths"]["sector_map"])
    tech_group = set(cfg.get("tech_group", ["Information Technology"]))

    # sector_map 로드
    smap = pd.read_csv(map_path, dtype=str).fillna("")
    smap["ticker"] = smap["ticker"].str.strip().str.upper()
    smap_dict = smap.set_index("ticker").to_dict("index")

    results = []
    unmapped = []

    for _, row in df.iterrows():
        ticker = str(row["ticker"]).upper()
        atype  = row.get("asset_type", "stock")

        info = smap_dict.get(ticker, {})
        gics   = info.get("gics_sector", "")
        tech_e = info.get("tech_economic", "")

        if not info and ticker not in ("CASH",):
            unmapped.append(ticker)
            gics = "미분류"

        # 버킷 결정
        if atype in ("cash",) or ticker == "CASH":
            bucket = "cash"
        elif atype in ("futures", "etf"):
            bucket = "cash"          # 파생·ETF는 현금 버킷으로 취급
        elif gics in tech_group:
            bucket = "tech"
        elif gics == "미분류":
            bucket = "unclassified"
        else:
            bucket = "other"

        results.append({**row.to_dict(),
                        "gics_sector":    gics or "미분류",
                        "tech_economic":  tech_e,
                        "bucket":         bucket})

    out = pd.DataFrame(results)

    # 미분류 경고
    unique_unmapped = sorted(set(unmapped))
    if unique_unmapped:
        print(f"\n  [classify] ⚠ 미분류 신규종목 ({len(unique_unmapped)}개):")
        for t in unique_unmapped:
            print(f"    {t}")
        print("  → sector_map.csv에 추가 후 재실행 권장\n")

    return out
