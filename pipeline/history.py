"""
history.py — 일별 diff 결과를 누적 parquet 로그로 저장·조회
"""

import pathlib
import pandas as pd


def _history_path(cfg: dict) -> pathlib.Path:
    return pathlib.Path(cfg["paths"].get("diff_history", "data/diff_history.parquet"))


def _load(path: pathlib.Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame(columns=[
        "date", "added", "removed", "major_changes", "turnover_pct"
    ])


def _fmt_changes(changes: list) -> str:
    if not changes:
        return ""
    parts = []
    for c in changes[:4]:  # 최대 4개 표시
        sign = "+" if c["delta_pct"] > 0 else ""
        parts.append(f"{c['ticker']} {sign}{c['delta_pct']:.1f}%p")
    return ", ".join(parts)


def run(diff_result: dict, cfg: dict, date_str: str) -> pd.DataFrame:
    """
    diff_result를 한 행으로 변환해 누적 parquet에 저장.
    반환: 전체 이력 DataFrame (최신일 우선)
    """
    if diff_result.get("is_first_run"):
        row = {
            "date":          date_str,
            "added":         "기준일(최초)",
            "removed":       "",
            "major_changes": "",
            "turnover_pct":  0.0,
        }
    else:
        added_str   = ", ".join(t["ticker"] for t in diff_result.get("added",   [])) or "없음"
        removed_str = ", ".join(t["ticker"] for t in diff_result.get("removed", [])) or "없음"
        row = {
            "date":          date_str,
            "added":         added_str,
            "removed":       removed_str,
            "major_changes": _fmt_changes(diff_result.get("changes", [])),
            "turnover_pct":  float(diff_result.get("turnover", 0.0)),
        }

    path = _history_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)

    hist = _load(path)
    hist = hist[hist["date"] != date_str]  # 당일 덮어쓰기
    hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    hist = hist.sort_values("date", ascending=False).reset_index(drop=True)
    hist.to_parquet(path, index=False)

    print(f"  [history] 변동 이력 저장 → {path} ({len(hist)}일 누적)")
    return hist
