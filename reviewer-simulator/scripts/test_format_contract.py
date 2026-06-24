#!/usr/bin/env python3
"""test_format_contract.py — reviewer-simulator 引用反查审稿检查的回归测试。

固化 citation_guard.py 的 --gates（J4 著录完整 / J5 自引 / J7 时效 / A4 双向）
作为**审稿端报告级**检查的契约，防止退化：

  审稿端硬约束（与 general-sci-writing 写作门禁的关键区别）：
    --gates 永远 exit 0（report-only），无论检出多少问题；不 fail-closed。
    每个检查的 strength 都是 "report"。

  J4  缺字段（缺 title / 无 identifier 且无 raw 回退）→ 列入 incomplete；
       raw_only 条目（仅 raw_vancouver + identifier）不误判 incomplete。
  J5  manuscript_authors 高自引 → warn；无 authors → skipped（不报错、不阻断）。
  J7  时效低 → warn；健康 → ok；无年份 → skipped。
  A4  双向：reference_index 的 cited_by/orphan_type 反查信号优先；
       僵尸引用（列而未引）/ 孤儿引用（引而无条目）被检出；干净不误报。

纯 assert、无 pytest、自包含合成输入（tempfile）。
验证用 subprocess.run(...).returncode。
运行：python3 test_format_contract.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
GUARD_SCRIPT = SCRIPTS_DIR / "citation_guard.py"
CORE_PATH = SCRIPTS_DIR / "citation_guard_core.py"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True, text=True,
    )


def _load_core():
    spec = importlib.util.spec_from_file_location("citation_guard_core", str(CORE_PATH))
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core


def _run_gates(index_path: Path, report_path: Path, *extra: str) -> tuple[int, dict]:
    proc = _run([
        str(GUARD_SCRIPT), "--index", str(index_path),
        "--gates", "--gates-report", str(report_path), *extra,
    ])
    assert proc.returncode == 0, (
        "review-side --gates must ALWAYS exit 0 (report-only), got rc="
        f"{proc.returncode}\n--- output ---\n{proc.stdout}{proc.stderr}"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "review_report", "gates must run in review_report mode"
    assert report["exit_code"] == 0, "review-side exit_code pinned to 0"
    for sect in ("j4_completeness", "j5_self_citation", "j7_recency", "a4_bidirectional"):
        assert report[sect]["strength"] == "report", \
            f"{sect} strength must be 'report' on the review side, got {report[sect]['strength']}"
    return proc.returncode, report


# ---------------------------------------------------------------------------
# 端到端：--gates 在脏稿件上仍 exit 0，且检出 J4/A4 问题（report-only）
# ---------------------------------------------------------------------------
def test_gates_report_only_detects_problems_but_never_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        idx = root / "reference_index.json"
        rpt = root / "report.json"
        # reference_index 风格：ref 3 列而未引（zombie），ref 99 引而无条目（orphan）；
        # ref 5 缺 title（J4 incomplete）。
        idx.write_text(json.dumps({
            "entries": [
                {"ref_number": 1, "raw_entry": "Smith J. Title A. Nat. 2024.",
                 "doi": "10.1/a", "cited_by": ["intro"], "orphan_type": None},
                {"ref_number": 2, "raw_entry": "Doe A. Title B. Cell. 2023.",
                 "doi": "10.1/b", "cited_by": ["methods"], "orphan_type": None},
                {"ref_number": 3, "raw_entry": "Lee K. Title C. Sci. 2022.",
                 "doi": "10.1/c", "cited_by": [], "orphan_type": "entry_not_cited"},
                {"ref_number": 5, "raw_entry": "", "doi": None, "pmid": None,
                 "cited_by": ["results"], "orphan_type": None},
                {"ref_number": 99, "raw_entry": "", "doi": None, "pmid": None,
                 "cited_by": [], "orphan_type": "cited_no_entry"},
            ],
        }, ensure_ascii=False), encoding="utf-8")

        rc, report = _run_gates(idx, rpt)
        assert rc == 0

        # A4：用了 reference_index 反查信号；zombie=3（列而未引），orphan=99（引而无条目）。
        a4 = report["a4_bidirectional"]
        assert a4["source"] == "reference_index", \
            f"A4 must prefer reference_index reverse-lookup, got {a4.get('source')}"
        assert a4["status"] == "fail", "A4 must flag broken pairing"
        assert 3 in a4["zombies"], f"A4 zombie 3 must be caught, got {a4['zombies']}"
        assert 99 in a4["orphans"], f"A4 orphan 99 must be caught, got {a4['orphans']}"

        # J4：ref 5（空 raw、无 identifier、缺 title）→ incomplete。
        j4_refs = {x["ref"] for x in report["j4_completeness"]["incomplete"]}
        assert 5 in j4_refs or 99 in j4_refs, \
            f"J4 must flag the title/identifier-less entries, got {j4_refs}"


# ---------------------------------------------------------------------------
# 干净的 PPE 风格结构化 index：不误杀（A4 ok 或 skip、J4 不报 incomplete）
# ---------------------------------------------------------------------------
def test_gates_clean_structured_index_no_false_positive() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        idx = root / "literature_index.json"
        rpt = root / "report.json"
        # PPE 风格：list，字段 index/title/authors/journal/year（无 cited_by 信号）。
        idx.write_text(json.dumps([
            {"index": 1, "title": "Global cancer statistics 2022",
             "authors": "BRAY F, et al.", "journal": "CA", "year": 2024,
             "volume": "74(3)", "pages": "229-263", "doi": "10.3322/caac.21834"},
            {"index": 2, "title": "Hallmarks of cancer",
             "authors": "Hanahan D", "journal": "Cell", "year": 2023,
             "volume": "12", "pages": "1-30", "doi": "10.1016/x"},
        ], ensure_ascii=False), encoding="utf-8")

        # 无 drafts、无 cited_by → A4 应 skip（不误判 fail）。
        rc, report = _run_gates(idx, rpt)
        assert rc == 0
        assert not report["j4_completeness"]["incomplete"], \
            f"clean structured entries must NOT be J4-incomplete: {report['j4_completeness']['incomplete']}"
        a4 = report["a4_bidirectional"]
        assert a4["status"] == "skipped", \
            f"no reverse-lookup signal and no drafts -> A4 skipped, got {a4['status']}"
        # 无 manuscript authors → J5 skipped（不报错）。
        assert report["j5_self_citation"]["status"] == "skipped", \
            "no authors -> J5 must skip, never error"


# ---------------------------------------------------------------------------
# raw_only 条目（仅 raw_vancouver + identifier，无结构化字段）不被误杀为 incomplete
# ---------------------------------------------------------------------------
def test_gates_raw_only_not_killed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        idx = root / "ref.json"
        rpt = root / "report.json"
        idx.write_text(json.dumps({"entries": [
            {"ref_number": 1, "title": "X", "raw_vancouver": "BRAY F. ...",
             "doi": "10.1/x", "cited_by": ["intro"]},
        ]}, ensure_ascii=False), encoding="utf-8")
        rc, report = _run_gates(idx, rpt)
        assert rc == 0
        assert not report["j4_completeness"]["incomplete"], \
            "raw_only entry (raw_vancouver + identifier) must NOT be J4-incomplete"
        assert report["j4_completeness"]["raw_only_count"] >= 1, \
            "raw_only entry must be counted under raw_only, not silently dropped"


# ---------------------------------------------------------------------------
# A4 drafts-scan 回退：index 无 cited_by 信号时，扫 drafts_dir 的 [n]
# ---------------------------------------------------------------------------
def test_gates_a4_drafts_scan_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        idx = root / "lit.json"
        rpt = root / "report.json"
        drafts = root / "manuscripts"
        drafts.mkdir()
        # 列出 ref 1,2,3（无 cited_by 字段 → 无反查信号）。
        idx.write_text(json.dumps([
            {"index": 1, "title": "A", "doi": "10.1/a", "year": 2024},
            {"index": 2, "title": "B", "doi": "10.1/b", "year": 2023},
            {"index": 3, "title": "C", "doi": "10.1/c", "year": 2022},
        ], ensure_ascii=False), encoding="utf-8")
        # 正文引用 [1],[2] 和 [7]（7 是 orphan：引而无条目；3 是 zombie：列而未引）。
        (drafts / "body.md").write_text(
            "As shown [1] and confirmed [2,7], the effect holds.\n", encoding="utf-8")
        rc, report = _run_gates(idx, rpt, "--drafts-dir", str(drafts))
        assert rc == 0
        a4 = report["a4_bidirectional"]
        assert a4["source"] == "drafts_scan", \
            f"no index signal -> A4 must scan drafts, got {a4.get('source')}"
        assert a4["status"] == "fail"
        assert 7 in a4["orphans"], f"A4 orphan 7 must be caught, got {a4['orphans']}"
        assert 3 in a4["zombies"], f"A4 zombie 3 must be caught, got {a4['zombies']}"


# ---------------------------------------------------------------------------
# J5 自引：传入 manuscript_authors 后高自引 → warn（report-only）
# ---------------------------------------------------------------------------
def test_gates_j5_self_citation_warn() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        idx = root / "lit.json"
        rpt = root / "report.json"
        cfg = root / "config.json"
        idx.write_text(json.dumps([
            {"index": 1, "title": "A", "doi": "10.1/a", "authors": ["Smith J", "Lee K"]},
            {"index": 2, "title": "B", "doi": "10.1/b", "authors": ["Doe A"]},
            {"index": 3, "title": "C", "doi": "10.1/c", "authors": ["Smith J", "Wu Q"]},
        ], ensure_ascii=False), encoding="utf-8")
        cfg.write_text(json.dumps({"authors": ["John Smith"]}), encoding="utf-8")
        rc, report = _run_gates(idx, rpt, "--project-config", str(cfg))
        assert rc == 0, "J5 warn must stay report-only (exit 0)"
        j5 = report["j5_self_citation"]
        assert j5["status"] == "warn" and j5["count"] == 2, \
            f"J5 high self-citation must warn, got {j5}"


# ---------------------------------------------------------------------------
# J7 时效：低时效 → warn（report-only，不阻断）
# ---------------------------------------------------------------------------
def test_gates_j7_recency_warn() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        idx = root / "lit.json"
        rpt = root / "report.json"
        idx.write_text(json.dumps([
            {"index": i, "title": f"T{i}", "doi": f"10.1/{i}", "year": y}
            for i, y in enumerate((2005, 2006, 2007, 2008, 2025), 1)
        ], ensure_ascii=False), encoding="utf-8")
        rc, report = _run_gates(idx, rpt, "--current-year", "2026")
        assert rc == 0, "J7 warn must stay report-only (exit 0)"
        assert report["j7_recency"]["status"] == "warn", \
            f"J7 low recency must warn, got {report['j7_recency']}"


# ---------------------------------------------------------------------------
# 纯函数层断言（core 三新函数 + check_bidirectional），与 general 范本对齐
# ---------------------------------------------------------------------------
def test_core_functions_present_and_correct() -> None:
    core = _load_core()
    # J4
    assert core.check_completeness({"doi": "10.1/x"})["status"] == "incomplete"
    raw_entry = {"title": "X", "raw_vancouver": "BRAY F. ...", "doi": "10.1/x"}
    assert core.check_completeness(raw_entry)["status"] == "raw_only"
    # J5
    assert core.check_self_citation([{"authors": ["A"]}], [])["status"] == "skipped"
    high = [{"authors": ["Smith J"]}, {"authors": ["Doe A"]}, {"authors": ["Smith J"]}]
    assert core.check_self_citation(high, ["John Smith"])["status"] == "warn"
    # J7
    old = [{"year": y} for y in (2005, 2006, 2007, 2008, 2025)]
    assert core.check_recency(old, 2026)["status"] == "warn"
    assert core.check_recency([{"title": "x"}], 2026)["status"] == "skipped"
    # A4
    res = core.check_bidirectional({1, 2, 99}, {1, 2, 3})
    assert res["status"] == "fail" and res["orphans"] == [99] and res["zombies"] == [3]
    clean = core.check_bidirectional({1, 2, 3}, {1, 2, 3})
    assert clean["status"] == "ok"


if __name__ == "__main__":
    test_gates_report_only_detects_problems_but_never_blocks()
    test_gates_clean_structured_index_no_false_positive()
    test_gates_raw_only_not_killed()
    test_gates_a4_drafts_scan_fallback()
    test_gates_j5_self_citation_warn()
    test_gates_j7_recency_warn()
    test_core_functions_present_and_correct()
    print("OK: reviewer-simulator citation reverse-lookup checks (J4/J5/J7/A4, report-only) locked")
