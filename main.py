"""
main.py — ETF 포트폴리오 전체 파이프라인 진입점

  python main.py           # 오늘 날짜로 전체 실행
  python main.py 20260612  # 특정 날짜 지정 (수집은 항상 실시간)

파이프라인 순서:
  STEP 0  수집     (collect)
  STEP 1  정규화   (normalize)
  STEP 2  분류     (classify)
  STEP 3  스코어   (score)
  STEP 4  구성     (construct)
  STEP 5  비교     (diff)
  STEP 6  리포트   (report)
"""

import sys
import pathlib
import datetime
import traceback

# ── UTF-8 설정 (Tee 이전에 반드시 먼저) ─────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── 로그 Tee ─────────────────────────────────────────────────────────────────

class _Tee:
    """stdout/stderr를 콘솔 + 로그파일에 동시 출력."""
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            s.write(data)

    def flush(self):
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass

    def reconfigure(self, **kwargs):
        pass  # 이미 reconfigure 완료

    @property
    def encoding(self):
        return "utf-8"

    @property
    def errors(self):
        return "replace"


def _setup_log(date_str: str, log_dir: str = "logs"):
    logs_path = pathlib.Path(log_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    log_file = logs_path / f"{date_str}.log"
    lf = open(log_file, "a", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, lf)
    sys.stderr = _Tee(sys.__stderr__, lf)
    return lf, log_file


def _push_pages(report_path: str, date_str: str) -> str | None:
    """
    HTML 리포트를 docs/에 배포하고 GitHub Pages로 push.
    - docs/index.html      : 항상 최신 내용 (고정 URL)
    - docs/archive/YYYY-MM-DD.html : 날짜별 이력 보존
    git 또는 네트워크 오류 시 경고만 출력하고 계속 진행.
    반환: GitHub Pages URL (성공 시) 또는 None
    """
    import shutil
    import subprocess

    docs = pathlib.Path("docs")
    docs.mkdir(exist_ok=True)
    archive = docs / "archive"
    archive.mkdir(exist_ok=True)

    archive_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    archive_dest = archive / f"{archive_date}.html"

    shutil.copy2(report_path, docs / "index.html")
    shutil.copy2(report_path, archive_dest)

    try:
        def _git(*args):
            r = subprocess.run(["git"] + list(args), capture_output=True, text=True)
            if r.returncode != 0 and r.stderr:
                print(f"  [git] {r.stderr.strip()}")
            return r.returncode

        _git("add", str(docs / "index.html"), str(archive_dest))

        staged = subprocess.run(["git", "diff", "--cached", "--name-only"],
                                capture_output=True, text=True).stdout.strip()
        if not staged:
            print("  [pages] 변경 없음 — push 스킵")
        else:
            _git("commit", "-m", f"report: {date_str}")
            rc = _git("push")
            if rc == 0:
                print(f"  [pages] push 완료 → docs/index.html + archive/{archive_date}.html")
            else:
                print("  [pages] push 실패 — 로컬 파일은 정상 저장됨")

        remote = subprocess.run(["git", "remote", "get-url", "origin"],
                                capture_output=True, text=True).stdout.strip()
        if "github.com" in remote:
            repo_part = remote.replace("https://github.com/", "").replace(".git", "")
            user, repo = repo_part.split("/", 1)
            return f"https://{user}.github.io/{repo}/"
    except Exception as e:
        print(f"  [pages] 배포 건너뜀: {e}")

    return None


def _load_cfg(path: str = "config.yaml") -> dict:
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── 파이프라인 ────────────────────────────────────────────────────────────────

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime("%Y%m%d")

    cfg     = _load_cfg()
    log_dir = cfg.get("paths", {}).get("log_dir", "logs")
    log_fh, log_path = _setup_log(date_str, log_dir)

    # 모듈 임포트는 Tee 설정 이후 (print 출력이 로그에 잡히도록)
    import pipeline.collect   as collect
    import pipeline.normalize as normalize
    import pipeline.classify  as classify
    import pipeline.score     as score
    import pipeline.construct as construct
    import pipeline.diff      as diff
    import pipeline.history   as history
    import pipeline.etf_radar as etf_radar
    import pipeline.report    as report

    bar = "=" * 62
    try:
        print(f"\n{bar}")
        print(f"  ETF 포트폴리오 파이프라인  [{date_str}]")
        print(f"  시작: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  로그: {log_path}")
        print(bar)

        # ── STEP 0: 수집 ─────────────────────────────────────────────────────
        print("\n[STEP 0] 구성종목 수집")
        raw = collect.fetch_all()
        for code, df in raw.items():
            print(f"  {code}: {len(df)}종목")

        # ── STEP 1: 정규화 ───────────────────────────────────────────────────
        print("\n[STEP 1] 정규화 + parquet 저장")
        df_norm = normalize.run(raw, date_str, cfg)

        # ── STEP 2: 섹터 분류 ────────────────────────────────────────────────
        print("\n[STEP 2] 섹터 분류 (GICS)")
        df_cls = classify.run(df_norm, cfg)
        for bkt, n in df_cls.groupby("bucket")["ticker"].nunique().items():
            print(f"  {bkt}: {n}개 티커")

        # ── STEP 3: 스코어 산출 ──────────────────────────────────────────────
        print("\n[STEP 3] 스코어 산출")
        df_scored = score.run(df_cls, cfg)
        print(f"  유니버스: {len(df_scored)}종목")

        # ── STEP 4: 포트폴리오 구성 ──────────────────────────────────────────
        print("\n[STEP 4] 타깃 포트폴리오 구성")
        portfolio = construct.run(df_scored, cfg, date_str)

        # ── STEP 5: diff ─────────────────────────────────────────────────────
        print("\n[STEP 5] 전일 대비 diff")
        diff_result = diff.run(portfolio, cfg, date_str)

        # ── STEP 6: 변동 이력 누적 ──────────────────────────────────────────
        print("\n[STEP 6] 변동 이력 저장")
        hist_df = history.run(diff_result, cfg, date_str)

        # ── STEP 7: ETF 인사이트 레이더 ─────────────────────────────────────
        print("\n[STEP 7] ETF 인사이트 레이더")
        radar_result = etf_radar.run(cfg, portfolio, date_str)
        status = "가능" if radar_result.get("available") else radar_result.get("reason","불가")
        print(f"  [radar] 비교: {status}")

        # ── STEP 8: HTML 리포트 ──────────────────────────────────────────────
        print("\n[STEP 8] HTML 리포트 생성")
        report_path = report.run(portfolio, diff_result, df_cls, cfg, date_str,
                                 history=hist_df, radar=radar_result)

        # ── STEP 9: GitHub Pages 배포 ────────────────────────────────────────
        print("\n[STEP 9] GitHub Pages 배포")
        pages_url = _push_pages(report_path, date_str)

        # ── 완료 요약 ─────────────────────────────────────────────────────────
        cap_tag = f"cap{int(float(cfg['name_cap'])*100):02d}"
        print(f"\n{bar}")
        print("  완료")
        print(f"  포트폴리오: {len(portfolio[portfolio['bucket']!='cash'])}종목 + 현금")
        out_dir = cfg["paths"].get("output_dir", "output")
        print(f"  Excel  → {out_dir}/portfolio_{date_str}_{cap_tag}.xlsx")
        print(f"  리포트  → {report_path}")
        if pages_url:
            print(f"  Pages  → {pages_url}")
        print(f"  종료: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(bar)

        # 브라우저로 리포트 열기 (인터랙티브 실행 시에만)
        if sys.platform == "win32" and sys.stdin and sys.stdin.isatty():
            import subprocess
            url = pages_url or str(report_path)
            subprocess.Popen(["start", "", url], shell=True)

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        traceback.print_exc()
        sys.exit(1)

    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        log_fh.close()


if __name__ == "__main__":
    main()
