#!/usr/bin/env python3
"""Regression for proofread.py — the PL-G13 mechanical hard gate.

Two things must hold or the gate silently lets defects through:
  · detection: check_misspellings / check_chinese_punct / check_subsup each fire
    on a known-defect string and stay quiet on a clean one.
  · --fail-on exit-code contract: a defect in a named category forces a non-zero
    exit only when that category is passed to --fail-on (missing it = gate off).

Baseline = current code behavior. Runs standalone (`python3`) or via pytest.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from proofread import check_chinese_punct, check_misspellings, check_subsup


def _types(issues) -> set:
    return {i["type"] for i in issues}


# ── detection ────────────────────────────────────────────────────────────────
def test_misspelling_detected() -> None:
    issues = check_misspellings("Teh cells were seperate and occured twice.")
    assert "misspelling" in _types(issues)
    founds = {i["found"].lower() for i in issues}
    assert any(f.startswith("teh") for f in founds)


def test_misspelling_clean() -> None:
    assert check_misspellings("The cells were separate and occurred twice.") == []


def test_chinese_punct_detected() -> None:
    # 全角逗号漏进英文行(该行汉字 <3),命中 chinese_punct
    issues = check_chinese_punct("The result was significant， with p<0.05.")
    assert "chinese_punct" in _types(issues)


def test_chinese_punct_clean_english() -> None:
    assert check_chinese_punct("The result was significant, with p<0.05.") == []


def test_subsup_detected() -> None:
    issues = check_subsup("We measured H2O uptake and CO2 release.")
    assert "subsup_bare" in _types(issues)


def test_subsup_clean_when_wrapped() -> None:
    # 已用 markdown 下标标注,不应再报
    assert check_subsup("We measured H~2~O uptake.") == []


# ── --fail-on exit-code contract (subprocess) ─────────────────────────────────
def _run_proofread(md_text: str, fail_on: str | None) -> int:
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "m.md"), "w", encoding="utf-8") as f:
        f.write(md_text)
    report = os.path.join(d, "report.json")
    cmd = [sys.executable, os.path.join(_SCRIPT_DIR, "proofread.py"),
           "--manuscript-dir", d, "--report", report]
    if fail_on:
        cmd += ["--fail-on", fail_on]
    return subprocess.run(cmd, capture_output=True, text=True).returncode


CLEAN = "The results were significant in mutant cells (p < 0.05).\n"
# 单个 misspelling 只扣 5 分(score 95 ≥ 阈值 70)→ 不加 --fail-on 时凭分数会放行,
# 加 --fail-on misspelling 才拦。正好隔离 --fail-on 契约。
DEFECT_MISSPELL = "The results were significant becuase mutant cells grew.\n"
# H2O 是 warn 级(0 扣分,score 100)→ 只有 --fail-on subsup_bare 能拦。
DEFECT_SUBSUP = "We measured H2O uptake in mutant cells (p < 0.05).\n"


def test_clean_passes_without_failon() -> None:
    assert _run_proofread(CLEAN, None) == 0


def test_clean_passes_with_failon() -> None:
    assert _run_proofread(CLEAN, "misspelling,chinese_punct,subsup_bare") == 0


def test_misspell_passes_score_but_failon_blocks() -> None:
    # 分数够(95),没 --fail-on 就放行;有 --fail-on 就拦。
    assert _run_proofread(DEFECT_MISSPELL, None) == 0
    assert _run_proofread(DEFECT_MISSPELL, "misspelling") == 1


def test_subsup_warn_only_failon_blocks() -> None:
    # H2O 是 warn(不扣分),唯有 --fail-on subsup_bare 触发非零退出。
    assert _run_proofread(DEFECT_SUBSUP, None) == 0
    assert _run_proofread(DEFECT_SUBSUP, "subsup_bare") == 1


def test_failon_unrelated_category_does_not_block() -> None:
    # 只有 subsup 缺陷,但 --fail-on 只列 misspelling → 不该拦(退出 0)。
    assert _run_proofread(DEFECT_SUBSUP, "misspelling,chinese_punct") == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("OK: proofread detection + --fail-on exit-code contract")
