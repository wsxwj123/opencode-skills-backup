#!/usr/bin/env python3
"""test_format_contract.py — 回归测试：固化本轮已修的 3 个 bug，防止退化。

纯 assert、无 pytest、自包含合成输入（tempfile/字符串现造，不依赖外部真稿）。
运行：python3 test_format_contract.py
失败抛 AssertionError；全过打印 OK。

覆盖 3 条契约（注释标 bug）：

  bug1  abbreviation_consistency.py — 小写文件名 full_manuscript.md 必须被排除
        （否则合并稿与原子节文件双双含首展 → duplicate_definition 假阳性）；
        且小写首展 "reactive oxygen species (ROS)" 必须被识别为定义
        （否则 undefined_use 假阳性）。大写全称 PDT 仍须识别（不退化）。

  bug2  figure_analysis_gate.py — 复数 section_ids 数组字段必须被识别
        （否则门禁找不到该 section 的图 → 静默放行失效）。有图且就绪 → rc=0；
        删掉 figure_analysis 后 → rc!=0（证明门禁真的拦得住）。

  bug3  make_reference_docx.py — 必须支持 --output；产物落在 --output 指定路径，
        且 skill 的 templates/reference.docx 不被写（调用前后 sha256 不变）。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "reference.docx"

ABBR_SCRIPT = SCRIPTS_DIR / "abbreviation_consistency.py"
FIGURE_GATE_SCRIPT = SCRIPTS_DIR / "figure_analysis_gate.py"
MAKE_REF_SCRIPT = SCRIPTS_DIR / "make_reference_docx.py"
XSEC_SCRIPT = SCRIPTS_DIR / "cross_section_consistency.py"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True, text=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# bug1: abbreviation_consistency — 小写 full_manuscript.md 排除 + 小写首展识别
# ---------------------------------------------------------------------------
def test_abbreviation_lowercase_filename_and_lowercase_definition() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        man = root / "manuscripts"
        man.mkdir()

        # 原子节文件：含小写首展 ROS 与大写全称 PDT 的定义。
        (man / "03_results.md").write_text(
            "We measured reactive oxygen species (ROS) in treated cells. "
            "Subsequent ROS accumulation drove apoptosis. "
            "Photodynamic Therapy (PDT) was applied; PDT efficacy increased.\n",
            encoding="utf-8",
        )
        # 小写文件名的合并稿：内容是原子节的副本（同样含两处首展）。
        # 若 collect_manuscript_files 不按 .lower() 排除，ROS/PDT 会被算作
        # "在多个文件首次定义" → duplicate_definition 假阳性。
        (man / "full_manuscript.md").write_text(
            "We measured reactive oxygen species (ROS) in treated cells. "
            "Subsequent ROS accumulation drove apoptosis. "
            "Photodynamic Therapy (PDT) was applied; PDT efficacy increased.\n",
            encoding="utf-8",
        )
        # 提供一份 abbreviations.json（即便为空 list 也走完整流程）。
        (root / "abbreviations.json").write_text(
            json.dumps([
                {"abbr": "ROS", "full_name": "reactive oxygen species"},
                {"abbr": "PDT", "full_name": "Photodynamic Therapy"},
            ]),
            encoding="utf-8",
        )

        proc = _run([str(ABBR_SCRIPT), "--root", str(root)])
        out = proc.stdout + proc.stderr

        # ① 小写合并稿被排除 → 无 duplicate_definition 假阳性。
        assert "duplicate_definition" not in out, (
            "lowercase full_manuscript.md NOT excluded → duplicate_definition "
            f"false positive.\n--- output ---\n{out}"
        )
        # ② 小写首展 ROS 被识别为定义 → 不报 undefined_use。
        assert "undefined_use: ROS" not in out, (
            "lowercase first-expansion 'reactive oxygen species (ROS)' not "
            f"recognized → undefined_use false positive.\n--- output ---\n{out}"
        )
        # ③ 大写全称 PDT 仍被识别（不退化）→ 不报 undefined_use。
        assert "undefined_use: PDT" not in out, (
            "uppercase 'Photodynamic Therapy (PDT)' regression → undefined_use "
            f"false positive.\n--- output ---\n{out}"
        )
        # 整体应通过（rc=0），证明无任何门禁误报。
        assert proc.returncode == 0, (
            f"expected rc=0 (clean), got {proc.returncode}\n--- output ---\n{out}"
        )


def test_abbreviation_uppercase_definition_still_detected() -> None:
    """纯正向：仅大写全称定义存在，且无重复 → 必须 rc=0 且不误报 PDT。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        man = root / "manuscripts"
        man.mkdir()
        (man / "01_intro.md").write_text(
            "Photodynamic Therapy (PDT) is a clinical modality. "
            "PDT relies on photosensitizers.\n",
            encoding="utf-8",
        )
        (root / "abbreviations.json").write_text("[]", encoding="utf-8")

        proc = _run([str(ABBR_SCRIPT), "--root", str(root)])
        out = proc.stdout + proc.stderr
        assert proc.returncode == 0, (
            f"uppercase definition path should pass clean, got rc="
            f"{proc.returncode}\n--- output ---\n{out}"
        )
        assert "undefined_use: PDT" not in out, (
            f"uppercase PDT definition not recognized.\n--- output ---\n{out}"
        )


# ---------------------------------------------------------------------------
# bug1b: abbreviation_consistency — BARE_ABBR_PATTERN 希腊字母截断
#        IFN-γ / TGF-β 等须完整捕获，绝不产生以 "-" 结尾的残缺缩写。
# ---------------------------------------------------------------------------
def test_bare_abbr_pattern_greek_suffix_not_truncated() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "abbreviation_consistency", str(ABBR_SCRIPT)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pat = mod.BARE_ABBR_PATTERN

    # 含希腊字母后缀的缩写必须被完整抓取（而非残缺的 "IFN-" / "TGF-"）。
    for text, expected in [("IFN-γ", "IFN-γ"), ("TGF-β", "TGF-β"),
                           ("TNF-α", "TNF-α"), ("IL-1β", "IL-1β")]:
        tokens = [m.group(1) for m in pat.finditer(text)]
        assert tokens == [expected], (
            f"{text!r} should capture {expected!r}, got {tokens!r}"
        )
        # 绝不出现以 "-" 结尾的残缺缩写。
        assert not any(tok.endswith("-") for tok in tokens), (
            f"dangling trailing hyphen in {tokens!r} for {text!r}"
        )

    # 不退化：纯大写缩写仍抓，单字母不抓。
    assert [m.group(1) for m in pat.finditer("PCR ELISA P53")] == \
        ["PCR", "ELISA", "P53"], "plain uppercase abbreviations regressed"
    assert [m.group(1) for m in pat.finditer("A cat and I left")] == [], \
        "single letters A/I must not be captured"
    # 残缺输入 "IFN-" 须抓到干净的 "IFN"（不带悬空 "-"）。
    assert [m.group(1) for m in pat.finditer("IFN- alone")] == ["IFN"], \
        "trailing-hyphen input must yield clean 'IFN'"


# ---------------------------------------------------------------------------
# bug2: figure_analysis_gate — 复数 section_ids 数组字段 + 门禁真能拦截
# ---------------------------------------------------------------------------
def test_figure_gate_plural_section_ids_pass_and_block() -> None:
    section = "results_3.2"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fa = root / "figure_analysis"
        fa.mkdir()

        # 用复数 section_ids 数组字段（非单数 section）描述图归属。
        (root / "figures_database.json").write_text(
            json.dumps([
                {
                    "figure_id": "Figure 2",
                    "section_ids": ["results_3.1", "results_3.2"],
                }
            ]),
            encoding="utf-8",
        )
        fa_file = fa / "figure_2.md"
        fa_file.write_text(
            "## Figure 2 analysis\nPanel A shows dose-response.\n",
            encoding="utf-8",
        )

        # 有图且就绪 → 门禁通过 rc=0（证明 section_ids 数组被正确识别）。
        proc_ok = _run([
            str(FIGURE_GATE_SCRIPT), "--section", section, "--root", str(root)
        ])
        out_ok = proc_ok.stdout + proc_ok.stderr
        assert proc_ok.returncode == 0, (
            "plural section_ids not matched → gate failed to find ready figure.\n"
            f"--- output ---\n{out_ok}"
        )
        assert "FIGURE_ANALYSIS_OK" in out_ok, (
            f"expected FIGURE_ANALYSIS_OK.\n--- output ---\n{out_ok}"
        )
        # "no associated figures" 说明 section_ids 没匹配上 → 静默放行（错误）。
        assert "has no associated figures" not in out_ok, (
            "section_ids array silently unmatched → gate would pass vacuously.\n"
            f"--- output ---\n{out_ok}"
        )

        # 删掉 figure_analysis → 门禁必须拦截 rc!=0（证明不静默失效）。
        fa_file.unlink()
        proc_block = _run([
            str(FIGURE_GATE_SCRIPT), "--section", section, "--root", str(root)
        ])
        out_block = proc_block.stdout + proc_block.stderr
        assert proc_block.returncode != 0, (
            "missing figure_analysis should BLOCK (rc!=0) but gate passed.\n"
            f"--- output ---\n{out_block}"
        )
        assert "FIGURE_ANALYSIS_NOT_READY" in out_block, (
            f"expected FIGURE_ANALYSIS_NOT_READY.\n--- output ---\n{out_block}"
        )


# ---------------------------------------------------------------------------
# bug3: make_reference_docx — 支持 --output，不写 skill 模板
# ---------------------------------------------------------------------------
def test_make_reference_docx_output_flag_does_not_touch_template() -> None:
    assert TEMPLATE_PATH.exists(), (
        f"baseline template missing, cannot run test: {TEMPLATE_PATH}"
    )
    sha_before = _sha256(TEMPLATE_PATH)

    with tempfile.TemporaryDirectory() as tmp:
        out_docx = Path(tmp) / "reference_out.docx"
        proc = _run([str(MAKE_REF_SCRIPT), "--output", str(out_docx)])
        out = proc.stdout + proc.stderr

        # 脚本支持 --output 且成功退出。
        assert proc.returncode == 0, (
            f"make_reference_docx --output failed rc={proc.returncode}\n"
            f"--- output ---\n{out}"
        )
        # 产物落在 --output 指定的 tempfile 路径。
        assert out_docx.exists() and out_docx.stat().st_size > 0, (
            f"output docx not written to {out_docx}\n--- output ---\n{out}"
        )

    # skill 的 templates/reference.docx 未被写（sha256 不变）。
    sha_after = _sha256(TEMPLATE_PATH)
    assert sha_before == sha_after, (
        "skill templates/reference.docx was modified by --output run "
        "(sha256 changed) — template must stay pristine."
    )


# ---------------------------------------------------------------------------
# Citation-integrity gates (J4 completeness / J5 self-citation / J7 recency /
# A4 bidirectional). Pure-function assertions over citation_guard_core.
# ---------------------------------------------------------------------------
def test_j4_completeness() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "citation_guard_core", str(SCRIPTS_DIR / "citation_guard_core.py")
    )
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)

    # Missing field caught: no title -> incomplete.
    assert core.check_completeness({"doi": "10.1/x"})["status"] == "incomplete", \
        "J4: missing title must be incomplete"
    # No identifier and no raw fallback -> incomplete (identifier listed).
    r = core.check_completeness({"title": "X", "authors": ["A B"]})
    assert r["status"] == "incomplete" and "identifier" in r["missing_fields"], \
        "J4: no DOI/PMID/raw must be incomplete"
    # Complete article: not flagged.
    full = {"title": "X", "authors": ["Smith J"], "journal": "Nat",
            "year": 2020, "volume": "1", "pages": "1-9", "doi": "10.1/x"}
    assert core.check_completeness(full)["status"] == "ok", \
        "J4: complete article must not be flagged"
    assert core.check_completeness(full)["missing_fields"] == [], \
        "J4: complete article must have no missing fields"
    # raw_only entry (PPE-style: only raw_vancouver + identifier) NOT incomplete.
    raw_entry = {"title": "X", "raw_vancouver": "BRAY F. ...", "doi": "10.1/x"}
    assert core.check_completeness(raw_entry)["status"] == "raw_only", \
        "J4: raw_only entry must not be judged incomplete"


def test_j5_self_citation() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "citation_guard_core", str(SCRIPTS_DIR / "citation_guard_core.py")
    )
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)

    # Empty authors -> skipped (never errors / never blocks existing projects).
    assert core.check_self_citation([{"authors": ["A"]}], [])["status"] == "skipped", \
        "J5: empty manuscript_authors must skip"
    # High self-citation (2/3) -> warn. "Smith J" must match "John Smith".
    high = [{"authors": ["Smith J", "Lee K"]}, {"authors": ["Doe A"]},
            {"authors": ["Smith J", "Wu Q"]}]
    res = core.check_self_citation(high, ["John Smith"])
    assert res["status"] == "warn" and res["count"] == 2, \
        f"J5: high self-citation must warn, got {res}"
    # Low self-citation (1/10) -> ok (no false alarm).
    low = [{"authors": ["Smith J"]}] + [{"authors": [f"X{i} Y"]} for i in range(9)]
    assert core.check_self_citation(low, ["John Smith"])["status"] == "ok", \
        "J5: low self-citation must not warn"


def test_j7_recency() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "citation_guard_core", str(SCRIPTS_DIR / "citation_guard_core.py")
    )
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)

    # Low recency (1/5 within window) -> warn.
    old = [{"year": y} for y in (2005, 2006, 2007, 2008, 2025)]
    assert core.check_recency(old, 2026)["status"] == "warn", \
        "J7: low recency must warn"
    # Healthy recency -> ok.
    fresh = [{"year": y} for y in (2023, 2024, 2025)]
    assert core.check_recency(fresh, 2026)["status"] == "ok", \
        "J7: healthy recency must not warn"
    # No usable years -> skipped.
    assert core.check_recency([{"title": "x"}], 2026)["status"] == "skipped", \
        "J7: no years must skip"


def test_a4_bidirectional() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "citation_guard_core", str(SCRIPTS_DIR / "citation_guard_core.py")
    )
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)

    # Zombie (listed-not-cited) + orphan (cited-not-listed) both caught.
    res = core.check_bidirectional({1, 2, 99}, {1, 2, 3})
    assert res["status"] == "fail", "A4: broken pairing must fail"
    assert res["orphans"] == [99], f"A4: orphan must be [99], got {res['orphans']}"
    assert res["zombies"] == [3], f"A4: zombie must be [3], got {res['zombies']}"
    # Clean pairing -> ok, no false positives.
    clean = core.check_bidirectional({1, 2, 3}, {1, 2, 3})
    assert clean["status"] == "ok" and not clean["orphans"] and not clean["zombies"], \
        "A4: clean pairing must not be flagged"


# ---------------------------------------------------------------------------
# A5 — 内部交叉引用有效性（proofread.check_crossref_validity）：双向。
#   引用存在的 Section/Figure/Table/Appendix → 不报；
#   引用不存在的目标（断链）→ warn 报。保守：断链全 warn。
# ---------------------------------------------------------------------------
def test_a5_crossref_validity_bidirectional() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "proofread", str(SCRIPTS_DIR / "proofread.py")
    )
    pf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pf)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # 干净稿：所有交叉引用目标都有定义（题注 / 标题）→ 零断链。
        (root / "res.md").write_text(
            "## 2 Results\n\n"
            "As shown in Figure 1, see Section 2.1 for details.\n\n"
            "**Figure 1.** Overview.\n\n"
            "### 2.1 Sub\nTable 1 lists params. Details in Appendix A.\n\n"
            "**Table 1.** Params.\n",
            encoding="utf-8")
        (root / "app.md").write_text(
            "## Appendix A Supplementary\nData in Appendix A above.\n",
            encoding="utf-8")
        clean = pf.check_crossref_validity([str(root / "res.md"), str(root / "app.md")])
        assert clean == [], \
            f"A5: valid cross-refs must not be flagged: {[i['found'] for i in clean]}"

        # 脏稿：Section/Figure/Table/Appendix 均断链。
        (root / "bad.md").write_text(
            "## 1 Intro\n\n"
            "But Figure 9 does not exist. See Section 8.8 missing.\n"
            "Refer to Appendix Z. Table 7 is dangling.\n",
            encoding="utf-8")
        dirty = pf.check_crossref_validity([str(root / "bad.md")])
        founds = " ".join(i["found"] for i in dirty)
        assert "Figure 9" in founds, f"A5: dangling Figure 9 must report: {founds}"
        assert "Section 8.8" in founds, f"A5: dangling Section 8.8 must report: {founds}"
        assert "Table 7" in founds, f"A5: dangling Table 7 must report: {founds}"
        assert "Appendix Z" in founds, f"A5: dangling Appendix Z must report: {founds}"
        assert all(i["severity"] == "warn" for i in dirty), \
            f"A5: dangling refs must all be warn (conservative): {dirty}"


# ---------------------------------------------------------------------------
# B1/B2: cross_section_consistency — 跨段数值漂移嫌疑（半自动 WARN）。
# 双向断言：同标签 + 不同值 → 报嫌疑；一致 / 不同标签 → 不报。WARN 级 rc=0。
# ---------------------------------------------------------------------------
def _run_xsec(root: Path, extra: list[str] | None = None) -> dict:
    proc = _run([str(XSEC_SCRIPT), "--root", str(root), *(extra or [])])
    assert proc.returncode == 0, (
        f"xsec must be WARN-level (rc=0), got {proc.returncode}\n{proc.stderr}"
    )
    return json.loads(proc.stdout)


def _xsec_project(tmp: str, abstract: str, body: str) -> Path:
    root = Path(tmp)
    man = root / "manuscripts"
    man.mkdir()
    (man / "01_abstract.md").write_text(abstract, encoding="utf-8")
    (man / "03_results.md").write_text(body, encoding="utf-8")
    return root


def test_xsec_flags_same_label_drift() -> None:
    # 摘要 survival rate 45%，正文 survival rate 47% → 同标签不同值 → 报嫌疑。
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_project(
            tmp,
            "The survival rate was 45% in the treated cohort.\n",
            "## Results\n\nUltimately the survival rate reached 47% overall.\n",
        )
        res = _run_xsec(root)
    labels = {s["label"] for s in res["suspicions"]}
    assert "survival rate" in labels, (
        f"45% vs 47% under same 'survival rate' label must be flagged; got "
        f"{json.dumps(res['suspicions'], ensure_ascii=False)}"
    )
    susp = next(s for s in res["suspicions"] if s["label"] == "survival rate")
    vals = {v["value"] for v in susp["values"]}
    assert vals == {"45", "47"}, f"both drifting values must appear, got {vals}"


def test_xsec_no_flag_when_consistent() -> None:
    # 两段同标签同值 45% → 一致 → 不报（无假阳性）。
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_project(
            tmp,
            "The survival rate was 45% in the treated cohort.\n",
            "## Results\n\nThe survival rate remained 45% at follow-up.\n",
        )
        res = _run_xsec(root)
    assert res["suspicions"] == [], (
        f"consistent 45%/45% must NOT be flagged; got "
        f"{json.dumps(res['suspicions'], ensure_ascii=False)}"
    )


def test_xsec_no_flag_for_different_labels() -> None:
    # 不同标签的不同值（survival 45% vs response 47%）→ 不是同一指标 → 不报。
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_project(
            tmp,
            "The survival rate was 45% in the treated cohort.\n",
            "## Results\n\nThe response rate reached 47% overall.\n",
        )
        res = _run_xsec(root)
    assert res["suspicions"] == [], (
        f"different labels (survival vs response) must NOT be flagged; got "
        f"{json.dumps(res['suspicions'], ensure_ascii=False)}"
    )


def test_xsec_cn_drift_flagged_and_action_words_ignored() -> None:
    # 中文：同标签'存活率'45% vs 47% → 报；动作词'加入'4% vs 实验参数 → 不报。
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_project(
            tmp,
            "实验组存活率为45%，对照组明显偏低。\n",
            "## 结果\n\n随访期末存活率降至47%。\n另取一组加入4%多聚甲醛固定细胞。\n",
        )
        res = _run_xsec(root)
    labels = {s["label"] for s in res["suspicions"]}
    assert "存活率" in labels, (
        f"中文同标签'存活率'45/47 漂移必须报；got "
        f"{json.dumps(res['suspicions'], ensure_ascii=False)}"
    )
    assert "加入" not in labels, (
        f"动作尾词'加入'必须被排除，不得作标签；got {labels}"
    )


def test_xsec_ignores_reference_block_pmids() -> None:
    # References 块里的 PMID/编号数字（含 %）不得参与聚类 → 不报。
    with tempfile.TemporaryDirectory() as tmp:
        root = _xsec_project(
            tmp,
            "Efficacy of 45% was observed.\n",
            "## Results\n\nNo numeric claim here.\n\n"
            "## References\n\n"
            "- [1] Some paper reporting 45% something. 2020. PMID 12345678.\n"
            "- [2] Another reporting 99% else. 2021. PMID 87654321.\n",
        )
        res = _run_xsec(root)
    # 仅摘要一处 45%，References 内的数字被剔除 → 无跨段冲突。
    assert res["suspicions"] == [], (
        f"reference-block numerics must be excluded; got "
        f"{json.dumps(res['suspicions'], ensure_ascii=False)}"
    )


if __name__ == "__main__":
    test_abbreviation_lowercase_filename_and_lowercase_definition()
    test_abbreviation_uppercase_definition_still_detected()
    test_bare_abbr_pattern_greek_suffix_not_truncated()
    test_figure_gate_plural_section_ids_pass_and_block()
    test_make_reference_docx_output_flag_does_not_touch_template()
    test_j4_completeness()
    test_j5_self_citation()
    test_j7_recency()
    test_a4_bidirectional()
    test_a5_crossref_validity_bidirectional()
    test_xsec_flags_same_label_drift()
    test_xsec_no_flag_when_consistent()
    test_xsec_no_flag_for_different_labels()
    test_xsec_cn_drift_flagged_and_action_words_ignored()
    test_xsec_ignores_reference_block_pmids()
    print("OK: all format-contract regression tests passed "
          "(3 bugs + 4 citation gates + 5 cross-section checks + A5 crossref locked)")
