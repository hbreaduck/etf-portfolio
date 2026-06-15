"""
run_pipeline.py — ETF 포트폴리오 수집·산출 파이프라인 진입점

  python run_pipeline.py           # 오늘 날짜로 전체 실행
  python run_pipeline.py 20260612  # 특정 날짜 지정 (수집은 항상 실시간)
"""

import sys
import datetime
import pathlib
import yaml

import pipeline.collect   as collect
import pipeline.normalize as normalize
import pipeline.classify  as classify
import pipeline.score     as score
import pipeline.construct as construct

# ── UTF-8 출력 (Windows) ──────────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_cfg(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime("%Y%m%d")
    cfg = load_cfg()

    print("=" * 60)
    print(f"ETF 포트폴리오 파이프라인  [{date_str}]")
    print("=" * 60)

    # ── Step 0: 수집 ────────────────────────────────────────────────────────
    print("\n[STEP 0] 구성종목 수집")
    raw = collect.fetch_all()
    for code, df in raw.items():
        print(f"  {code}: {len(df)}종목")

    # ── Step 1: 정규화 + parquet 저장 ───────────────────────────────────────
    print("\n[STEP 1] 정규화 + 저장")
    df_norm = normalize.run(raw, date_str, cfg)

    # ── Step 2: 섹터 분류 ───────────────────────────────────────────────────
    print("\n[STEP 2] 섹터 분류 (GICS)")
    df_cls = classify.run(df_norm, cfg)
    bkt_cnt = df_cls.groupby("bucket")["ticker"].nunique()
    for bkt, n in bkt_cnt.items():
        print(f"  {bkt}: {n}개 티커")

    # ── Step 3: 스코어 ─────────────────────────────────────────────────────
    print("\n[STEP 3] 스코어 산출")
    df_scored = score.run(df_cls, cfg)
    print(f"  stock universe: {len(df_scored)}종목")
    print(df_scored[["ticker", "bucket", "score"]].head(15).to_string(index=False))

    # ── Step 4: 포트폴리오 구성 ─────────────────────────────────────────────
    print("\n[STEP 4] 타깃 포트폴리오 구성")
    portfolio = construct.run(df_scored, cfg, date_str)

    print("\n" + "=" * 60)
    print("타깃 포트폴리오")
    print("=" * 60)
    print(portfolio[["bucket", "ticker", "name", "target_pct"]].to_string(index=False))
    print(f"\n합계: {portfolio['target_pct'].sum():.2f}%")

    # Excel 열기
    out_path = pathlib.Path(cfg["paths"].get("output_dir", "output")) / f"portfolio_{date_str}.xlsx"
    if out_path.exists() and sys.platform == "win32":
        import subprocess
        subprocess.Popen(["start", "", str(out_path)], shell=True)


if __name__ == "__main__":
    main()
