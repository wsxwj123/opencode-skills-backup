#!/usr/bin/env python3
"""test_format_contract.py — 回归测试：固化引用诚信门禁，防止退化。

纯 assert、无 pytest、自包含合成输入（tempfile/字符串现造，不依赖外部真稿）。
运行：python3 test_format_contract.py
失败抛 AssertionError；全过打印 OK。

覆盖 4 个引用诚信门禁（review-writing 侧）：

  J4  check_completeness — 缺字段被抓（无 title / 无标识符 → incomplete）；
      完整条目不误报；raw_only 条目（只有 raw_entry/raw_vancouver）不被误判
      为 incomplete。fail-closed 强度通过 --fail-on-incomplete 端到端验证。

  J5  check_self_citation — 高自引（>阈值）→ warn；低自引 → ok（不误报）；
      manuscript_authors 空 → skipped（不破坏存量项目）。
      "Smith J" 必须匹配 "John Smith"（姓+首字母归一化）。

  J7  check_recency — 时效低 → warn；健康 → ok；无可用年份 → skipped。

  A4  validate_local（既有）— 僵尸（列而未引/unused）+ 孤儿（引而无条目/orphan）
      都被抓；干净配对不误报（端到端 subprocess，--fail-on-orphan）。
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_citations.py"
ABBR_SCRIPT = SCRIPTS_DIR / "abbreviation_consistency.py"


def _run_abbr(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ABBR_SCRIPT), *args],
        cwd=str(cwd), capture_output=True, text=True,
    )


def _load_validate_module():
    spec = importlib.util.spec_from_file_location(
        "validate_citations", str(VALIDATE_SCRIPT)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPTS_DIR))  # citation_utils import
    spec.loader.exec_module(mod)
    return mod


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), *args],
        cwd=str(cwd), capture_output=True, text=True,
    )


# ---------------------------------------------------------------------------
# J4 — completeness (pure function).
# ---------------------------------------------------------------------------
def test_j4_completeness() -> None:
    m = _load_validate_module()
    assert m.check_completeness({"doi": "10.1/x"})["status"] == "incomplete", \
        "J4: missing title must be incomplete"
    r = m.check_completeness({"title": "X", "authors": ["A B"]})
    assert r["status"] == "incomplete" and "identifier" in r["missing_fields"], \
        "J4: no DOI/PMID/raw must be incomplete"
    full = {"title": "X", "authors": ["Smith J"], "journal": "Nat",
            "year": 2020, "volume": "1", "pages": "1-9", "pmid": "999"}
    assert m.check_completeness(full)["status"] == "ok", \
        "J4: complete article must not be flagged"
    assert m.check_completeness(full)["missing_fields"] == [], \
        "J4: complete article must have no missing fields"
    raw_entry = {"title": "X", "raw_entry": "Smith J. ...", "pmid": "999"}
    assert m.check_completeness(raw_entry)["status"] == "raw_only", \
        "J4: raw_only entry must not be judged incomplete"


# ---------------------------------------------------------------------------
# J5 — self-citation (pure function).
# ---------------------------------------------------------------------------
def test_j5_self_citation() -> None:
    m = _load_validate_module()
    assert m.check_self_citation([{"authors": ["A"]}], [])["status"] == "skipped", \
        "J5: empty manuscript_authors must skip"
    high = [{"authors": ["Smith J", "Lee K"]}, {"authors": ["Doe A"]},
            {"authors": ["Smith J", "Wu Q"]}]
    res = m.check_self_citation(high, ["John Smith"])
    assert res["status"] == "warn" and res["count"] == 2, \
        f"J5: high self-citation must warn, got {res}"
    low = [{"authors": ["Smith J"]}] + [{"authors": [f"X{i} Y"]} for i in range(9)]
    assert m.check_self_citation(low, ["John Smith"])["status"] == "ok", \
        "J5: low self-citation must not warn"


# ---------------------------------------------------------------------------
# J7 — recency (pure function).
# ---------------------------------------------------------------------------
def test_j7_recency() -> None:
    m = _load_validate_module()
    old = [{"year": y} for y in (2005, 2006, 2007, 2008, 2025)]
    assert m.check_recency(old, 2026)["status"] == "warn", \
        "J7: low recency must warn"
    fresh = [{"year": y} for y in (2023, 2024, 2025)]
    assert m.check_recency(fresh, 2026)["status"] == "ok", \
        "J7: healthy recency must not warn"
    assert m.check_recency([{"title": "x"}], 2026)["status"] == "skipped", \
        "J7: no years must skip"


# ---------------------------------------------------------------------------
# J4 fail-closed — end-to-end: incomplete entry blocks under --fail-on-incomplete.
# ---------------------------------------------------------------------------
def test_j4_fail_closed_end_to_end() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "data").mkdir()
        (root / "drafts").mkdir()
        items = [
            {"global_id": 1, "title": "Good", "pmid": "111", "year": "2024"},
            {"global_id": 2, "title": "", "pmid": "222", "year": "2024"},  # incomplete
        ]
        (root / "data" / "literature_index.json").write_text(json.dumps(items), encoding="utf-8")
        (root / "drafts" / "s.md").write_text("Text [1][2].", encoding="utf-8")
        (root / "state.json").write_text('{"authors": []}', encoding="utf-8")

        blocked = _run(
            ["--drafts-dir", "drafts", "--index-path", "data/literature_index.json",
             "--gates", "--state-path", "state.json", "--current-year", "2026",
             "--fail-on-incomplete"], root)
        assert blocked.returncode == 2, (
            f"J4: incomplete entry must block (rc=2) with --fail-on-incomplete, "
            f"got {blocked.returncode}\n{blocked.stdout}\n{blocked.stderr}")
        assert "[J4-FAIL] global_id=2" in blocked.stdout, \
            f"J4: incomplete entry 2 must be reported\n{blocked.stdout}"

        # Observe mode (no --fail-on-incomplete): rc=0 even with incomplete entry.
        observe = _run(
            ["--drafts-dir", "drafts", "--index-path", "data/literature_index.json",
             "--gates", "--state-path", "state.json", "--current-year", "2026"], root)
        assert observe.returncode == 0, (
            f"J4: without --fail-on-incomplete must be rc=0 (observe), "
            f"got {observe.returncode}\n{observe.stdout}")


# ---------------------------------------------------------------------------
# A4 — bidirectional: zombie (unused) + orphan caught; clean not flagged.
# ---------------------------------------------------------------------------
def test_a4_bidirectional_end_to_end() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "data").mkdir()
        (root / "drafts").mkdir()
        # index has 1,2,3 ; draft cites 1,2 and 99(orphan). 3 = zombie(unused).
        items = [{"global_id": i, "title": f"P{i}", "pmid": str(i), "year": "2024"}
                 for i in (1, 2, 3)]
        (root / "data" / "literature_index.json").write_text(json.dumps(items), encoding="utf-8")
        (root / "drafts" / "s.md").write_text("Text [1][2][99].", encoding="utf-8")

        res = _run(
            ["--drafts-dir", "drafts", "--index-path", "data/literature_index.json",
             "--fail-on-orphan"], root)
        # Orphan 99 present + --fail-on-orphan -> rc=2.
        assert res.returncode == 2, (
            f"A4: orphan citation must block under --fail-on-orphan, "
            f"got {res.returncode}\n{res.stdout}")
        assert "Orphan citations: 99" in res.stdout, \
            f"A4: orphan 99 must be reported\n{res.stdout}"
        assert "Unused index entries: 3" in res.stdout, \
            f"A4: zombie (unused) 3 must be reported\n{res.stdout}"

        # Clean pairing: cite exactly 1,2,3 -> no orphan, no unused, rc=0.
        (root / "drafts" / "s.md").write_text("Text [1][2][3].", encoding="utf-8")
        clean = _run(
            ["--drafts-dir", "drafts", "--index-path", "data/literature_index.json",
             "--fail-on-orphan"], root)
        assert clean.returncode == 0, (
            f"A4: clean pairing must pass (rc=0), got {clean.returncode}\n{clean.stdout}")
        assert "No orphan citations" in clean.stdout, \
            f"A4: clean pairing must report no orphans\n{clean.stdout}"
        assert "No unused index entries" in clean.stdout, \
            f"A4: clean pairing must report no unused\n{clean.stdout}"


# ---------------------------------------------------------------------------
# B3/B4 — 缩略语一致性（移植自 gsw）：双向。
#   B4 首次定义：裸用未定义 → undefined_use 报；先定义后用 → 不报。
#   B3 全文统一：同一缩写在多文件重复定义 → duplicate_definition 报。
#   Title 含缩写 → title_abbreviation 报。
#   fail-closed（默认）有问题 rc=1；--report-only 仅打印 rc=0。
# ---------------------------------------------------------------------------
def test_b3_b4_abbreviation_bidirectional() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "drafts").mkdir()

        # --- 脏稿：标题含缩写 ROS + 重复定义 ROS + 裸用未定义 IL6 ---
        (root / "drafts" / "01.md").write_text(
            "# A Review of ROS in Disease\n\n"
            "We study reactive oxygen species (ROS) here. IL6 appears bare.\n",
            encoding="utf-8")
        (root / "drafts" / "02.md").write_text(
            "## Body\nAgain reactive oxygen species (ROS) redefined here.\n",
            encoding="utf-8")

        fail = _run_abbr(["--drafts-dir", "drafts"], root)
        assert fail.returncode == 1, (
            f"B3/B4: dirty drafts must fail-closed (rc=1), got {fail.returncode}\n"
            f"{fail.stdout}\n{fail.stderr}")
        assert "duplicate_definition: ROS" in fail.stdout, \
            f"B3: ROS redefined in 2 files must report\n{fail.stdout}"
        assert "undefined_use: IL6" in fail.stdout, \
            f"B4: bare IL6 without definition must report\n{fail.stdout}"
        assert "title_abbreviation: ROS" in fail.stdout, \
            f"Title abbreviation ROS must report\n{fail.stdout}"

        # report-only：同样的脏稿 → 仍打印问题，但 rc=0（不阻断）。
        observe = _run_abbr(["--drafts-dir", "drafts", "--report-only"], root)
        assert observe.returncode == 0, (
            f"B3/B4: --report-only must be rc=0, got {observe.returncode}\n{observe.stdout}")
        assert "ABBR_CHECK_FAIL" in observe.stdout, \
            f"--report-only must still print issues\n{observe.stdout}"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "drafts").mkdir()
        # --- 干净稿：标题无缩写；ROS 定义一次后多次裸用；TNF 定义后裸用 ---
        (root / "drafts" / "01.md").write_text(
            "# A Review of Oxidative Stress\n\n"
            "We study reactive oxygen species (ROS) and tumor necrosis factor (TNF).\n",
            encoding="utf-8")
        (root / "drafts" / "02.md").write_text(
            "## Body\nROS drives inflammation while TNF acts downstream.\n",
            encoding="utf-8")
        clean = _run_abbr(["--drafts-dir", "drafts"], root)
        assert clean.returncode == 0, (
            f"B3/B4: clean drafts must pass (rc=0), got {clean.returncode}\n"
            f"{clean.stdout}\n{clean.stderr}")
        assert "ABBR_CHECK_OK" in clean.stdout, \
            f"clean drafts must report OK\n{clean.stdout}"
        assert "ABBR_CHECK_FAIL" not in clean.stdout, \
            f"clean drafts must not report any FAIL\n{clean.stdout}"


# ---------------------------------------------------------------------------
# Bug ① — _pmid_item_valid：NCBI esummary 对不存在 PMID 返回带 uid 但含 error 的
#   占位项；必须排除 error 才算真实存在，否则假 PMID 被当真。
# ---------------------------------------------------------------------------
def test_pmid_item_valid_rejects_error() -> None:
    m = _load_validate_module()
    bad = {"uid": "999999999", "error": "cannot get document summary"}
    assert m._pmid_item_valid(bad) is False, \
        "Bug①: esummary item with error must be invalid (假 PMID 不能当真)"
    good = {"uid": "12345678", "title": "Real Paper", "pubdate": "2020"}
    assert m._pmid_item_valid(good) is True, \
        "Bug①: normal esummary item must be valid"
    assert m._pmid_item_valid({}) is False, "Bug①: empty item invalid"
    assert m._pmid_item_valid(None) is False, "Bug①: non-dict item invalid"


# ---------------------------------------------------------------------------
# Bug ③ — 全角括号定义识别：聚焦超声（focused ultrasound，FUS）应识别为定义，
#   FUS 不报 undefined；半角 Photodynamic Therapy (PDT) 不退化。
# ---------------------------------------------------------------------------
def test_fullwidth_abbreviation_definition() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "drafts").mkdir()
        # 全角定义 + 后续裸用 FUS；半角定义 PDT + 后续裸用 PDT。
        (root / "drafts" / "01.md").write_text(
            "# A Review of Tumor Ablation\n\n"
            "我们采用聚焦超声（focused ultrasound，FUS）进行消融。"
            "Photodynamic Therapy (PDT) is also discussed.\n",
            encoding="utf-8")
        (root / "drafts" / "02.md").write_text(
            "## Body\nFUS shows promise while PDT remains complementary.\n",
            encoding="utf-8")
        res = _run_abbr(["--drafts-dir", "drafts"], root)
        assert res.returncode == 0, (
            f"Bug③: 全角定义后裸用必须通过 (rc=0), got {res.returncode}\n"
            f"{res.stdout}\n{res.stderr}")
        assert "undefined_use: FUS" not in res.stdout, \
            f"Bug③: 全角定义的 FUS 不应报 undefined\n{res.stdout}"
        assert "undefined_use: PDT" not in res.stdout, \
            f"Bug③: 半角定义的 PDT 不应退化报 undefined\n{res.stdout}"
        assert "ABBR_CHECK_OK" in res.stdout, \
            f"Bug③: 全角+半角定义齐全应 OK\n{res.stdout}"


if __name__ == "__main__":
    test_j4_completeness()
    test_j5_self_citation()
    test_j7_recency()
    test_j4_fail_closed_end_to_end()
    test_a4_bidirectional_end_to_end()
    test_b3_b4_abbreviation_bidirectional()
    test_pmid_item_valid_rejects_error()
    test_fullwidth_abbreviation_definition()
    print("OK: all citation-integrity gate regression tests passed (J4/J5/J7/A4 + B3/B4 abbr + Bug①③ locked)")
