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


if __name__ == "__main__":
    test_abbreviation_lowercase_filename_and_lowercase_definition()
    test_abbreviation_uppercase_definition_still_detected()
    test_bare_abbr_pattern_greek_suffix_not_truncated()
    test_figure_gate_plural_section_ids_pass_and_block()
    test_make_reference_docx_output_flag_does_not_touch_template()
    print("OK: all format-contract regression tests passed (3 bugs locked)")
