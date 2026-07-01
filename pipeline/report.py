"""
report.py — 한국어 HTML 대시보드 생성
"""

import html as html_lib
import pathlib
import datetime
import pandas as pd


# ── 유틸 ───────────────────────────────────────────────────────────────────────

def _e(s) -> str:
    return html_lib.escape(str(s) if s is not None else "")


# ── HTML 블록 빌더 ─────────────────────────────────────────────────────────────

def _head(date_label: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ETF 포트폴리오 리포트 — {_e(date_label)}</title>
<style>
:root{{
  --blue:#1F3864;--tech:#2E75B6;--other:#2E8B57;--cash:#B8860B;
  --warn:#C00000;--bg:#F2F5F9;--card:#FFF;--border:#DEE2E6;
  --t-tech:#D6E4F7;--t-other:#E2EFDA;--t-cash:#FFF2CC;
  --green:#196F3D;--red:#C0392B;
}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:13px;
      background:var(--bg);color:#222;line-height:1.5;}}
.topbar{{background:var(--blue);color:#fff;padding:16px 32px;
         display:flex;justify-content:space-between;align-items:center;}}
.topbar h1{{font-size:19px;font-weight:700;letter-spacing:-0.5px;}}
.topbar .meta{{font-size:11px;opacity:.75;text-align:right;line-height:1.7;}}
.container{{max-width:1100px;margin:22px auto;padding:0 18px;}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:8px;
       padding:20px;margin-bottom:18px;}}
.card h2{{font-size:14px;font-weight:700;color:var(--blue);margin-bottom:14px;
          border-bottom:2px solid var(--blue);padding-bottom:6px;}}
.card h3{{font-size:13px;color:#444;margin:16px 0 8px;}}
/* ── bucket cards ── */
.bucket-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px;}}
.bcard{{background:var(--card);border:1px solid var(--border);border-radius:8px;
        padding:18px 16px;text-align:center;}}
.bcard.tech{{border-top:4px solid var(--tech);}}
.bcard.other{{border-top:4px solid var(--other);}}
.bcard.cash{{border-top:4px solid var(--cash);}}
.bcard .lbl{{font-size:12px;color:#666;margin-bottom:4px;}}
.bcard .big{{font-size:30px;font-weight:700;}}
.bcard.tech .big{{color:var(--tech);}}
.bcard.other .big{{color:var(--other);}}
.bcard.cash .big{{color:var(--cash);}}
.bcard .sub{{font-size:11px;color:#888;margin-top:4px;}}
.bcard .ddiff{{font-size:11px;margin-top:3px;}}
/* ── GICS vs econ ── */
.exp-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;}}
.ebox{{border-radius:6px;padding:16px;text-align:center;}}
.ebox .big{{font-size:26px;font-weight:700;}}
.ebox .lbl{{font-size:11px;color:#555;margin-top:6px;line-height:1.5;}}
/* ── table ── */
table{{width:100%;border-collapse:collapse;font-size:12px;}}
th{{background:var(--blue);color:#fff;padding:7px 10px;text-align:left;white-space:nowrap;}}
th.r,td.r{{text-align:right;}}
th.c,td.c{{text-align:center;}}
td{{padding:5px 10px;border-bottom:1px solid #EBEBEB;}}
tr:hover td{{filter:brightness(.97);}}
.tech-row td{{background:var(--t-tech);}}
.other-row td{{background:var(--t-other);}}
.cash-row td{{background:var(--t-cash);}}
/* ── warning ── */
.warn-box{{background:#FFF4F4;border:1px solid #F5C6C6;border-radius:6px;
           padding:13px 16px;margin-bottom:16px;}}
.warn-box .wt{{color:var(--warn);font-weight:700;font-size:13px;margin-bottom:5px;}}
.warn-box .wt2{{font-size:11px;color:#666;font-family:monospace;}}
/* ── diff ── */
.diff-first{{background:#EBF5EB;border:1px solid #A9DFBF;border-radius:6px;
             padding:14px 18px;color:var(--green);font-weight:600;font-size:13px;}}
.badge{{display:inline-block;padding:2px 9px;border-radius:10px;
        font-size:11px;font-weight:700;margin-right:4px;}}
.badge.in{{background:#D5F5E3;color:#1E8449;}}
.badge.out{{background:#FADBD8;color:#C0392B;}}
.badge.chg{{background:#D6EAF8;color:#1A5276;}}
.tover{{background:#F8F9FA;border:1px solid var(--border);border-radius:6px;
        padding:12px 20px;display:inline-block;margin:14px 0;}}
.tover .tl{{font-size:11px;color:#888;}}
.tover .tv{{font-size:26px;font-weight:700;color:var(--blue);}}
.held-row{{font-size:11px;color:#888;margin-top:12px;}}
.pos{{color:var(--green);font-weight:700;}} .neg{{color:var(--red);font-weight:700;}}
footer{{text-align:center;color:#bbb;font-size:11px;padding:22px;}}
/* ── history ── */
.hist-first{{color:var(--blue);font-style:italic;}}
/* ── radar ── */
.star{{display:inline-block;color:#E6AC00;font-size:14px;margin-left:3px;}}
.badge-port{{display:inline-block;padding:1px 6px;border-radius:8px;font-size:10px;
             font-weight:700;background:#D5F5E3;color:#1E8449;}}
.badge-noport{{display:inline-block;padding:1px 6px;border-radius:8px;font-size:10px;
               font-weight:700;background:#FDEBD0;color:#C0392B;}}
.noport-row td{{background:#FEF9F0 !important;}}
.etf-tag{{display:inline-block;padding:1px 5px;border-radius:4px;font-size:10px;
           font-weight:600;margin:1px;background:#EBF5FB;color:#1A5276;}}
.delta-up{{color:var(--green);font-weight:700;}}
.delta-dn{{color:var(--red);font-weight:700;}}
.radar-sub{{font-size:12px;color:#888;font-weight:400;margin-left:6px;}}
/* ── perf ── */
.perf-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px;}}
.pbox{{background:#FAFAFA;border:1px solid var(--border);border-radius:8px;padding:14px;text-align:center;}}
.pbox .lbl{{font-size:11px;color:#666;margin-bottom:4px;line-height:1.4;}}
.pbox .big{{font-size:26px;font-weight:700;}}
.pbox .sub{{font-size:10px;color:#999;margin-top:3px;}}
.pbox.highlight{{border:2px solid var(--blue);background:var(--card);}}
/* ── 반응형 (태블릿 ≤ 768px) ── */
@media(max-width:768px){{
  .topbar{{padding:12px 16px;flex-direction:column;align-items:flex-start;gap:4px;}}
  .topbar h1{{font-size:15px;letter-spacing:0;}}
  .topbar .meta{{font-size:10px;text-align:left;}}
  .container{{margin:10px auto;padding:0 12px;}}
  .card{{padding:16px 12px;margin-bottom:12px;}}
  .card h2{{font-size:13px;margin-bottom:10px;}}
  .card h3{{font-size:12px;margin:12px 0 6px;}}
  .bucket-grid{{grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px;}}
  .bcard{{padding:10px 6px;}}
  .bcard .big{{font-size:22px;}}
  .bcard .sub,.bcard .ddiff{{font-size:10px;}}
  .perf-grid{{grid-template-columns:repeat(2,1fr);gap:8px;}}
  .pbox{{padding:10px;}}
  .pbox .big{{font-size:20px;}}
  .pbox .lbl{{font-size:10px;}}
  .exp-grid{{grid-template-columns:1fr;gap:8px;}}
  .ebox{{padding:12px;}}
  .ebox .big{{font-size:22px;}}
  td{{white-space:nowrap;}}
  .tover{{display:block;margin:10px 0;padding:10px 16px;}}
  .tover .tv{{font-size:22px;}}
  .badge{{margin-bottom:4px;}}
  .held-row{{line-height:2;word-break:break-word;white-space:normal;}}
  .warn-box{{padding:10px 12px;}}
  footer{{padding:14px;}}
}}
/* ── 반응형 (모바일 ≤ 480px) ── */
@media(max-width:480px){{
  body{{font-size:12px;}}
  .topbar{{padding:10px 14px;}}
  .topbar h1{{font-size:13px;}}
  .container{{padding:0 8px;}}
  .card{{padding:12px 10px;border-radius:6px;}}
  .bucket-grid{{grid-template-columns:repeat(3,1fr);gap:6px;}}
  .bcard .big{{font-size:18px;}}
  .bcard .ddiff{{font-size:9px;white-space:normal;word-break:keep-all;line-height:1.3;}}
  .perf-grid{{grid-template-columns:repeat(2,1fr);gap:6px;}}
  .perf-grid>:last-child:nth-child(odd){{grid-column:1/-1;}}
  .pbox .big{{font-size:17px;}}
  .ebox .big{{font-size:20px;}}
  th,td{{padding:4px 6px;font-size:11px;}}
}}
</style>
</head>
<body>"""


def _header(date_label: str, gen_time: str) -> str:
    return f"""<div class="topbar">
  <h1>&#128202; ETF 타깃 포트폴리오 리포트</h1>
  <div class="meta">기준일: {_e(date_label)}<br>생성: {_e(gen_time)}</div>
</div>
<div class="container">"""


def _warning_box(tickers: list) -> str:
    items = " &nbsp;&#183;&nbsp; ".join(f"<b>{_e(t)}</b>" for t in tickers)
    return f"""<div class="warn-box">
  <div class="wt">&#9888;&#65039; 미분류 종목 {len(tickers)}개 — sector_map.csv에 GICS 섹터 추가 필요</div>
  <div class="wt2">{items}</div>
</div>"""


def _futures_exposure_bar(classified: "pd.DataFrame | None") -> str:
    """ETF 내 지수선물 비중을 ETF별로 한 줄로 표시."""
    if classified is None or "asset_type" not in classified.columns:
        return ""
    fut = classified[classified["asset_type"].isin(["futures", "index_future"])]
    if fut.empty:
        return ""

    etf_totals  = classified.groupby("ETF코드")["weight_pct"].sum()
    etf_fut_pct = fut.groupby("ETF코드")["weight_pct"].sum()

    parts = []
    for etf_code in etf_fut_pct.index:
        total = etf_totals.get(etf_code, 1) or 1
        pct   = etf_fut_pct[etf_code] / total * 100
        tkrs  = ", ".join(sorted(fut[fut["ETF코드"] == etf_code]["ticker"].unique()))
        parts.append(
            f'<span style="margin-right:18px;">'
            f'<b style="color:#7D5A1E;">{_e(etf_code)}</b>'
            f'&nbsp;<span style="font-family:monospace;font-size:11px;color:#555;">{_e(tkrs)}</span>'
            f'&nbsp;<b>{pct:.2f}%</b></span>'
        )

    body = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts)
    return (
        '<div style="background:#FDF6E3;border:1px solid #D4A843;border-radius:6px;'
        'padding:9px 16px;margin-top:-4px;margin-bottom:18px;font-size:12px;">'
        '<span style="font-weight:700;color:#7D5A1E;">&#128202; ETF 내 선물/현금성 비중</span>'
        '&ensp;<span style="color:#999;font-size:11px;">(지수선물 — 종목 유니버스 제외)</span>'
        f'&emsp;{body}'
        '</div>'
    )


def _bucket_cards(targets: dict, actual: dict) -> str:
    cards = ""
    for bkt, label in [("tech", "테크"), ("other", "기타"), ("cash", "현금")]:
        tgt = float(targets.get(bkt, 0))
        act = actual.get(bkt, 0.0)
        d   = (act - tgt) * 100
        if abs(d) < 0.01:
            d_cls, d_str = "diff-zero", "목표 일치"
        elif d > 0:
            d_cls, d_str = "pos", f"목표 대비 +{d:.2f}%p"
        else:
            d_cls, d_str = "neg", f"목표 대비 {d:.2f}%p"
        cards += f"""<div class="bcard {bkt}">
  <div class="lbl">{_e(label)}</div>
  <div class="big">{act*100:.2f}%</div>
  <div class="sub">목표 {tgt*100:.0f}%</div>
  <div class="ddiff {d_cls}">{_e(d_str)}</div>
</div>"""
    return f'<div class="bucket-grid">{cards}</div>'


def _gics_vs_econ(gics_w: float, econ_w: float, diff: float) -> str:
    sign = f"+{diff*100:.2f}" if diff >= 0 else f"{diff*100:.2f}"
    if diff > 0.001:
        diff_lbl = "실질 기술 익스포저가 GICS 대비 높음<br>(통신·소비재 내 기술기업 포함)"
        dcol = "var(--green)"
    elif diff < -0.001:
        diff_lbl = "GICS IT 비중이 실질보다 높음"
        dcol = "var(--red)"
    else:
        diff_lbl = "GICS와 실질 비중 동일"
        dcol = "#888"
    return f"""<div class="card">
  <h2>기술 익스포저 비교 — GICS 라벨 vs 실질(tech_economic=Y)</h2>
  <div class="exp-grid">
    <div class="ebox" style="background:var(--t-tech);">
      <div class="big" style="color:var(--tech);">{gics_w*100:.2f}%</div>
      <div class="lbl">GICS IT 기준<br>Information Technology 섹터만 집계</div>
    </div>
    <div class="ebox" style="background:#EBF5EB;">
      <div class="big" style="color:var(--other);">{econ_w*100:.2f}%</div>
      <div class="lbl">실질 기술 익스포저<br>tech_economic = Y 종목 합산</div>
    </div>
    <div class="ebox" style="background:#F8F9FA;border:1px solid var(--border);">
      <div class="big" style="color:{dcol};">{sign}%p</div>
      <div class="lbl">{diff_lbl}</div>
    </div>
  </div>
</div>"""


def _portfolio_table(port: pd.DataFrame) -> str:
    n_stock = len(port[port["bucket"] != "cash"])
    rows_html = ""
    for row in port.itertuples(index=False):
        bkt_label = {"tech": "테크", "other": "기타", "cash": "현금"}.get(row.bucket, row.bucket)
        row_cls   = f"{row.bucket}-row"
        gics      = _e(row.gics_sector) if row.gics_sector else "&#8212;"
        te        = _e(row.tech_economic) if row.tech_economic else "&#8212;"
        score_str = f"{row.score:.2f}" if row.score else "&#8212;"
        rows_html += f"""<tr class="{row_cls}">
  <td>{_e(bkt_label)}</td>
  <td><b>{_e(row.ticker)}</b></td>
  <td>{_e(row.name)}</td>
  <td>{gics}</td>
  <td class="c">{te}</td>
  <td class="r">{score_str}</td>
  <td class="r"><b>{row.target_pct:.2f}%</b></td>
</tr>"""
    return f"""<div class="card">
  <h2>타깃 포트폴리오 ({n_stock}종목 + 현금)</h2>
  <table>
    <thead><tr>
      <th>버킷</th><th>티커</th><th>종목명</th><th>GICS 섹터</th>
      <th class="c">실질기술</th><th class="r">스코어</th><th class="r">비중(%)</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""


def _diff_section(diff: dict) -> str:
    if diff.get("is_first_run"):
        return """<div class="card">
  <h2>전일 대비 변동</h2>
  <div class="diff-first">&#9989; 기준일(최초) &#8212; 오늘 포트폴리오를 기준 스냅샷으로 저장했습니다.<br>내일 실행부터 diff가 표시됩니다.</div>
</div>"""

    prev_date  = diff.get("prev_date", "")
    prev_label = (f"{prev_date[:4]}-{prev_date[4:6]}-{prev_date[6:]}"
                  if len(prev_date) == 8 else prev_date)
    turnover   = diff.get("turnover", 0.0)
    added      = diff.get("added", [])
    removed    = diff.get("removed", [])
    changes    = diff.get("changes", [])
    held       = diff.get("held", [])
    trade_list = diff.get("trade_list", [])

    # 요약 배지
    badges = ""
    if added:   badges += f'<span class="badge in">IN {len(added)}</span>'
    if removed: badges += f'<span class="badge out">OUT {len(removed)}</span>'
    if changes: badges += f'<span class="badge chg">변화 {len(changes)}</span>'

    # 턴오버
    to_html = f"""<div class="tover">
  <div class="tl">예상 턴오버 (편도 기준)</div>
  <div class="tv">{turnover:.2f}%</div>
</div>"""

    # 매매 리스트
    trade_html = ""
    if trade_list:
        trows = ""
        for t in trade_list:
            sign   = "+" if t["delta_pct"] > 0 else ""
            dcls   = "pos" if t["delta_pct"] > 0 else "neg"
            bdgcls = "in" if t["direction"] == "BUY" else "out"
            trows += f"""<tr>
  <td><span class="badge {bdgcls}">{_e(t['direction'])}</span></td>
  <td><b>{_e(t['ticker'])}</b></td><td>{_e(t['name'])}</td>
  <td class="r {dcls}">{sign}{t['delta_pct']:.2f}%p</td>
</tr>"""
        trade_html = f"""<h3>매매 리스트</h3>
<table><thead><tr><th>방향</th><th>티커</th><th>종목명</th><th class="r">증감(%p)</th></tr></thead>
<tbody>{trows}</tbody></table>"""

    # IN 상세
    in_html = ""
    if added:
        rows = "".join(f"""<tr class="other-row">
  <td><b>{_e(t['ticker'])}</b></td><td>{_e(t['name'])}</td>
  <td class="r pos">+{t['target_pct']:.2f}%</td>
</tr>""" for t in added)
        in_html = f"""<h3 style="color:var(--green);">&#9650; 신규 편입 (IN) {len(added)}종목</h3>
<table><thead><tr><th>티커</th><th>종목명</th><th class="r">비중(%)</th></tr></thead>
<tbody>{rows}</tbody></table>"""

    # OUT 상세
    out_html = ""
    if removed:
        rows = "".join(f"""<tr style="background:#FADBD8;">
  <td><b>{_e(t['ticker'])}</b></td><td>{_e(t['name'])}</td>
  <td class="r neg">&#8722;{t['prev_pct']:.2f}%</td>
</tr>""" for t in removed)
        out_html = f"""<h3 style="color:var(--red);">&#9660; 편출 (OUT) {len(removed)}종목</h3>
<table><thead><tr><th>티커</th><th>종목명</th><th class="r">이전 비중(%)</th></tr></thead>
<tbody>{rows}</tbody></table>"""

    # CHANGE 상세
    chg_html = ""
    if changes:
        rows = ""
        for c in changes:
            sign = "+" if c["delta_pct"] > 0 else ""
            dcls = "pos" if c["delta_pct"] > 0 else "neg"
            rows += f"""<tr>
  <td><b>{_e(c['ticker'])}</b></td><td>{_e(c['name'])}</td>
  <td class="r">{c['prev_pct']:.2f}%</td>
  <td class="r"><b>{c['curr_pct']:.2f}%</b></td>
  <td class="r {dcls}">{sign}{c['delta_pct']:.2f}%p</td>
</tr>"""
        chg_html = f"""<h3 style="color:var(--blue);">&#8597; 비중 변화 ({len(changes)}종목, &#8805;0.5%p)</h3>
<table><thead><tr>
  <th>티커</th><th>종목명</th>
  <th class="r">전일(%)</th><th class="r">오늘(%)</th><th class="r">변화(%p)</th>
</tr></thead><tbody>{rows}</tbody></table>"""

    held_html = ""
    if held:
        held_str = " &#183; ".join(_e(t) for t in sorted(held))
        held_html = f'<div class="held-row">유지 종목 ({len(held)}개, 변화 &lt;0.5%p): {held_str}</div>'

    return f"""<div class="card">
  <h2>전일 대비 변동 <span style="font-size:12px;font-weight:400;color:#888;">vs {_e(prev_label)}</span></h2>
  {badges}
  {to_html}
  {trade_html}
  {in_html}
  {out_html}
  {chg_html}
  {held_html}
</div>"""


def _history_section(hist: "pd.DataFrame | None") -> str:
    if hist is None or (hasattr(hist, "empty") and hist.empty):
        return ""

    rows_html = ""
    for row in hist.itertuples(index=False):
        d = str(row.date)
        date_label = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        to_val = float(row.turnover_pct) if row.turnover_pct else 0.0
        to_col = "var(--red)" if to_val > 10 else ("var(--blue)" if to_val > 3 else "#444")

        added_val   = _e(row.added)   if row.added   else "&#8212;"
        removed_val = _e(row.removed) if row.removed else "&#8212;"
        chg_val     = _e(row.major_changes) if row.major_changes else "&#8212;"

        is_base = row.added == "기준일(최초)"
        added_html   = f'<span class="hist-first">{added_val}</span>' if is_base else f'<span style="color:var(--green);">{added_val}</span>'
        removed_html = "" if is_base else f'<span style="color:var(--red);">{removed_val}</span>'
        to_html      = "" if is_base else f'<b style="color:{to_col};">{to_val:.2f}%</b>'

        rows_html += f"""<tr>
  <td style="white-space:nowrap;font-weight:600;">{date_label}</td>
  <td>{added_html}</td>
  <td>{removed_html}</td>
  <td>{chg_val}</td>
  <td class="r">{to_html}</td>
</tr>"""

    return f"""<div class="card">
  <h2>포트폴리오 변동 이력</h2>
  <table>
    <thead><tr>
      <th>일자</th><th>신규편입</th><th>편출</th><th>주요 비중변동</th><th class="r">턴오버(%)</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""


def _etf_radar_section(radar: dict) -> str:
    from pipeline.etf_radar import ETF_SHORT

    if not radar or not radar.get("available"):
        reason = radar.get("reason", "전일 스냅샷 없음") if radar else "데이터 없음"
        return f"""<div class="card">
  <h2>ETF 인사이트 레이더</h2>
  <div style="color:#888;font-size:12px;padding:8px 0;">데이터 부족 &#8212; {_e(reason)}</div>
</div>"""

    prev_d    = radar["prev_date"]
    prev_lbl  = f"{prev_d[:4]}-{prev_d[4:6]}-{prev_d[6:]}"
    period_lbl = "전주" if radar["period"] == "weekly" else "전일"
    min_chg   = radar.get("min_change_pct", 0.5)

    def etf_tags(etfs):
        return " ".join(f'<span class="etf-tag">{_e(ETF_SHORT.get(e, e))}</span>' for e in etfs)

    def port_badge(in_port: bool) -> str:
        if in_port:
            return '<span class="badge-port">포함</span>'
        return '<span class="badge-noport">미반영</span>'

    def star_mark(star: bool) -> str:
        return '<span class="star" title="2개 이상 ETF에서 동시 증가">&#9733;</span>' if star else ""

    def delta_fmt(v: float) -> str:
        sign = "+" if v > 0 else ""
        cls  = "delta-up" if v > 0 else "delta-dn"
        return f'<span class="{cls}">{sign}{v:.2f}%p</span>'

    # ── 신규 편입 ──────────────────────────────────────────────────────────
    new_html = ""
    entries = radar.get("new_entries", [])
    if entries:
        rows = ""
        for t in entries:
            rc = "noport-row" if not t["in_portfolio"] else ""
            rows += f"""<tr class="{rc}">
  <td><b>{_e(t['ticker'])}</b>{star_mark(t['star'])}</td>
  <td>{_e(t['name'])}</td>
  <td>{etf_tags(t['etfs'])}</td>
  <td class="c">{port_badge(t['in_portfolio'])}</td>
</tr>"""
        new_html = f"""<h3 style="color:var(--green);">&#9650; 신규 편입 {len(entries)}종목
  <span class="radar-sub">vs {prev_lbl}</span></h3>
<table><thead><tr><th>티커</th><th>종목명</th><th>ETF</th><th class="c">포트폴리오</th></tr></thead>
<tbody>{rows}</tbody></table>"""

    # ── 완전 편출 ──────────────────────────────────────────────────────────
    exit_html = ""
    exits = radar.get("exits", [])
    if exits:
        rows = ""
        for t in exits:
            rc = "noport-row" if not t["in_portfolio"] else ""
            rows += f"""<tr class="{rc}" style="background:#FAFAFA;">
  <td><b>{_e(t['ticker'])}</b></td>
  <td>{_e(t['name'])}</td>
  <td>{etf_tags(t['etfs'])}</td>
  <td class="c">{port_badge(t['in_portfolio'])}</td>
</tr>"""
        exit_html = f"""<h3 style="color:var(--red);margin-top:16px;">&#9660; 완전 편출 {len(exits)}종목
  <span class="radar-sub">vs {prev_lbl}</span></h3>
<table><thead><tr><th>티커</th><th>종목명</th><th>ETF</th><th class="c">포트폴리오</th></tr></thead>
<tbody>{rows}</tbody></table>"""

    # ── 비중 급변 ──────────────────────────────────────────────────────────
    mover_html = ""
    movers = radar.get("movers", [])
    if movers:
        rows = ""
        for t in movers:
            rc   = "noport-row" if not t["in_portfolio"] else ""
            d_by = t["delta_by_etf"]
            d456  = delta_fmt(d_by["456600"])  if "456600"  in d_by else "<span style='color:#ccc;'>&#8212;</span>"
            d426  = delta_fmt(d_by["426030"])  if "426030"  in d_by else "<span style='color:#ccc;'>&#8212;</span>"
            d001  = delta_fmt(d_by["00015B0"]) if "00015B0" in d_by else "<span style='color:#ccc;'>&#8212;</span>"
            rows += f"""<tr class="{rc}">
  <td><b>{_e(t['ticker'])}</b>{star_mark(t['star'])}</td>
  <td>{_e(t['name'])}</td>
  <td class="r">{d456}</td>
  <td class="r">{d426}</td>
  <td class="r">{d001}</td>
  <td class="r">{delta_fmt(t['total_delta'])}</td>
  <td class="c">{port_badge(t['in_portfolio'])}</td>
</tr>"""
        mover_html = f"""<h3 style="color:var(--blue);margin-top:16px;">&#8597; 비중 급변 상위
  <span class="radar-sub">&#916;&#8805;{min_chg}%p, {len(movers)}종목, vs {prev_lbl}</span></h3>
<table><thead><tr>
  <th>티커</th><th>종목명</th>
  <th class="r">AI인공지능&#916;</th><th class="r">나스닥100&#916;</th><th class="r">나스닥성장&#916;</th>
  <th class="r">합계&#916;</th><th class="c">포트폴리오</th>
</tr></thead><tbody>{rows}</tbody></table>
<div style="font-size:11px;color:#888;margin-top:8px;">
  &#9733; = 2개 이상 ETF에서 동시 증가 &nbsp;|&nbsp;
  <span class="badge-noport">미반영</span> = 현재 15종목 포트폴리오 미포함
</div>"""

    return f"""<div class="card">
  <h2>ETF 인사이트 레이더
    <span class="radar-sub">소스 ETF 3종 전체 구성종목 {period_lbl} 변동</span>
  </h2>
  {new_html}
  {exit_html}
  {mover_html}
</div>"""


def _perf_section(perf: dict) -> str:
    if not perf or not perf.get("available"):
        reason = perf.get("reason", "데이터 없음") if perf else "데이터 없음"
        return f"""<div class="card">
  <h2>당일 포트폴리오 성과</h2>
  <div style="color:#888;font-size:12px;padding:8px 0;">데이터 부족 &#8212; {_e(reason)}</div>
</div>"""

    as_of   = _e(perf.get("as_of_date", ""))
    bm_lbl  = _e(perf.get("bm_ticker", "QQQ"))

    def fmt(v, suffix="%"):
        if v is None:
            return "&#8212;"
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.2f}{suffix}"

    def cls(v):
        if v is None:
            return ""
        return "pos" if v > 0 else ("neg" if v < 0 else "")

    p_usd  = perf.get("port_usd_pct")
    p_krw  = perf.get("port_krw_pct")
    fx     = perf.get("fx_pct")
    bm     = perf.get("bm_usd_pct")
    excess = perf.get("excess_usd_pct")

    # FX 방향 설명
    if fx is not None:
        fx_desc = "원화 약세" if fx > 0.05 else ("원화 강세" if fx < -0.05 else "환율 보합")
    else:
        fx_desc = ""

    boxes = f"""<div class="perf-grid">
  <div class="pbox highlight">
    <div class="lbl">포트폴리오<br>(USD 기준)</div>
    <div class="big {cls(p_usd)}">{fmt(p_usd)}</div>
  </div>
  <div class="pbox highlight">
    <div class="lbl">포트폴리오<br>(KRW 기준)</div>
    <div class="big {cls(p_krw)}">{fmt(p_krw)}</div>
  </div>
  <div class="pbox">
    <div class="lbl">환율 영향<br>(USDKRW 등락)</div>
    <div class="big {cls(fx)}">{fmt(fx, "%p")}</div>
    <div class="sub">{_e(fx_desc)}</div>
  </div>
  <div class="pbox">
    <div class="lbl">벤치마크<br>({bm_lbl})</div>
    <div class="big {cls(bm)}">{fmt(bm)}</div>
  </div>
  <div class="pbox">
    <div class="lbl">BM 대비<br>초과수익</div>
    <div class="big {cls(excess)}">{fmt(excess, "%p")}</div>
  </div>
</div>"""

    # 기여도 상위 5 (절댓값 기준)
    contrib = perf.get("contrib", [])
    contrib_html = ""
    if contrib:
        top5 = contrib[:5]
        rows = ""
        for c in top5:
            r_cls = "pos" if c["ret_pct"] > 0 else "neg"
            co_cls = "pos" if c["contrib_pct"] > 0 else "neg"
            r_sign = "+" if c["ret_pct"] > 0 else ""
            co_sign = "+" if c["contrib_pct"] > 0 else ""
            rows += f"""<tr>
  <td><b>{_e(c['ticker'])}</b></td>
  <td>{_e(c['name'])}</td>
  <td class="r">{c['weight_pct']:.2f}%</td>
  <td class="r {r_cls}">{r_sign}{c['ret_pct']:.2f}%</td>
  <td class="r {co_cls}">{co_sign}{c['contrib_pct']:.3f}%p</td>
</tr>"""
        contrib_html = f"""<h3 style="margin-top:14px;">주요 기여 종목 (기여도 절댓값 상위)</h3>
<table>
  <thead><tr>
    <th>티커</th><th>종목명</th>
    <th class="r">비중</th><th class="r">등락률</th><th class="r">기여(%p)</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""

    missing = perf.get("missing", [])
    missing_html = ""
    if missing:
        missing_html = (f'<div style="font-size:11px;color:#999;margin-top:10px;">'
                        f'수익률 미수집: {", ".join(_e(t) for t in missing)}</div>')

    return f"""<div class="card">
  <h2>당일 포트폴리오 성과
    <span class="radar-sub">기준 종가: {as_of}</span>
  </h2>
  {boxes}
  {contrib_html}
  {missing_html}
</div>"""


def _footer() -> str:
    return """</div>
<footer>자동 생성 &#8212; ETF Portfolio Pipeline</footer>
<script>
(function(){
  /* 모든 카드 안의 table을 가로 스크롤 래퍼로 감싼다 (Safari 대응) */
  document.querySelectorAll('.card table').forEach(function(t){
    var w=document.createElement('div');
    w.style.cssText='overflow-x:auto;-webkit-overflow-scrolling:touch;';
    t.parentNode.insertBefore(w,t);
    w.appendChild(t);
    t.style.width='';          /* CSS width:100% 해제 → 내용 너비로 자연 확장 */
    t.style.minWidth='100%';   /* 넓은 화면에선 카드 너비 꽉 채움 */
  });
})();
</script>
</body></html>"""


# ── 메인 ───────────────────────────────────────────────────────────────────────

def run(port: pd.DataFrame, diff: dict, classified: pd.DataFrame,
        cfg: dict, date_str: str,
        history=None, radar=None, perf=None) -> str:
    """
    HTML 리포트를 생성하고 파일 경로를 반환.
    history : history.run() 반환 DataFrame (변동 이력)
    radar   : etf_radar.run() 반환 dict
    perf    : perf.run() 반환 dict
    """
    out_dir = pathlib.Path(cfg["paths"].get("output_dir", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"report_{date_str}.html"

    date_label = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    gen_time   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    targets      = cfg["sector_targets"]
    bucket_actual = {bkt: port[port["bucket"] == bkt]["target_weight"].sum()
                     for bkt in ["tech", "other", "cash"]}

    gics_tech_w = port[port["gics_sector"] == "Information Technology"]["target_weight"].sum()
    econ_tech_w = port[port["tech_economic"] == "Y"]["target_weight"].sum()
    econ_diff   = econ_tech_w - gics_tech_w

    # 미분류 티커 수집
    unclassified = []
    if classified is not None and "gics_sector" in classified.columns:
        mask = (classified["asset_type"].isin(["stock"])) & (
            classified["gics_sector"].isna() |
            (classified["gics_sector"] == "미분류") |
            (classified["bucket"] == "unclassified")
        )
        unclassified = sorted(classified[mask]["ticker"].unique().tolist())

    parts = [_head(date_label), _header(date_label, gen_time)]
    if unclassified:
        parts.append(_warning_box(unclassified))
    parts += [
        _perf_section(perf),
        _bucket_cards(targets, bucket_actual),
        _futures_exposure_bar(classified),
        _gics_vs_econ(gics_tech_w, econ_tech_w, econ_diff),
        _portfolio_table(port),
        _history_section(history),
        _diff_section(diff),
        _etf_radar_section(radar),
        _footer(),
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    print(f"  [report] HTML 저장 → {out_path}")
    return str(out_path)
