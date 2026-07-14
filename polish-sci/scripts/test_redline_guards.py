#!/usr/bin/env python3
"""Regression for the semantic red-line guards added to strict_gate.

Locks that the delivery gate catches meaning-changing edits the old set-based
checks let through: value/citation swaps (order), causal-verb upgrades, and
proper-noun / unit alterations. Runs standalone or via pytest.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from common import find_ai_style_markers
from strict_gate import check_unit, independent_meaning_verdict, is_soft_ai_marker


def _unit(raw: str, polished: str) -> dict:
    return {"raw_text": raw, "polished_text": polished, "polished_by": "ai", "prose": True}


def _fails_with(raw: str, polished: str, needle: str) -> None:
    ok, problems = check_unit(_unit(raw, polished))
    assert not ok, f"expected FAIL but passed: {raw!r} -> {polished!r}"
    assert any(needle in p for p in problems), f"missing {needle!r} in {problems}"


def _passes(raw: str, polished: str) -> None:
    ok, problems = check_unit(_unit(raw, polished))
    assert ok, f"expected PASS but failed: {problems}"


def test_numeric_swap_caught_even_though_set_identical() -> None:
    # {12%,34%} set is unchanged; the 12↔34 subject swap only shows in order.
    _fails_with(
        "Response was 12% in the experimental group and 34% in controls.",
        "Response was 34% in the experimental group and 12% in controls.",
        "numeric order changed",
    )


def test_citation_swap_caught() -> None:
    _fails_with(
        "Finding A [3] preceded finding B [5].",
        "Finding B [5] preceded finding A [3].",
        "citation order changed",
    )


def test_causal_upgrade_caught() -> None:
    _fails_with("X may be associated with Y.", "X induces Y.", "certainty upgraded")


def test_gene_altered_caught() -> None:
    _fails_with("*TP53* was frequently mutated.", "*TP52* was frequently mutated.", "named/unit changed")


def test_unit_altered_caught() -> None:
    _fails_with("We added 10 µM of the inhibitor.", "We added 10 nM of the inhibitor.", "named/unit changed")


def test_clean_language_polish_passes() -> None:
    # Reword non-numeric prose, numbers/citations/units/genes untouched, in order.
    _passes(
        "The results were significant in *TP53* mutants (12% vs 34%) [3].",
        "The findings were significant in *TP53* mutants (12% vs 34%) [3].",
    )


# --- 破折号硬门禁:禁止使用,check_unit 命中即 fail ---
def test_em_dash_blocks_delivery() -> None:
    # 破折号是硬门禁,check_unit 应因它判 fail。
    _fails_with(
        "The effect was clear in *TP53* mutants.",
        "The effect was clear—striking, even—in *TP53* mutants.",
        "ai markers",
    )


def test_ai_cliche_still_blocks() -> None:
    # 套话主干仍硬拦。
    _fails_with(
        "We examined the role of the gene.",
        "We delve into the pivotal role of the gene.",
        "ai markers",
    )


def test_soft_marker_predicate() -> None:
    assert not is_soft_ai_marker("em dash")  # 破折号硬门禁,不在软集
    assert is_soft_ai_marker("sentence >30 words")
    assert not is_soft_ai_marker("cliche: delve into")
    assert not is_soft_ai_marker("delve into")


# --- 去AI必禁三项的其余两项:scare quotes / 解释性冒号 也硬拦 ---
def test_scare_quotes_marker_produced_and_hard() -> None:
    # find_ai_style_markers 确实产出 'scare quotes';且它非软、硬拦阻断交付。
    assert "scare quotes" in find_ai_style_markers('The so-called "gold standard" method was applied.')
    assert not is_soft_ai_marker("scare quotes")
    _fails_with(
        "The so-called gold standard method was applied.",
        'The so-called "gold standard" method was applied.',
        "ai markers",
    )


def test_explanatory_colon_marker_produced_and_hard() -> None:
    # find_ai_style_markers 确实产出 'explanatory colon';且它非软、硬拦阻断交付。
    assert "explanatory colon" in find_ai_style_markers("We used one approach: the samples were incubated overnight.")
    assert not is_soft_ai_marker("explanatory colon")
    _fails_with(
        "We used one approach where the samples were incubated overnight.",
        "We used one approach: the samples were incubated overnight.",
        "ai markers",
    )


# --- ⑥ meaning_changed 只认独立 PL-G11 盲检,自填 false 不作数 ---
def _root_with_return(entries) -> Path:
    root = Path(tempfile.mkdtemp())
    if entries is not None:
        (root / ".review_return_polish-dod.json").write_text(
            json.dumps(entries, ensure_ascii=False), encoding="utf-8"
        )
    return root


def test_meaning_verdict_missing_return_fails() -> None:
    ok, reason = independent_meaning_verdict(_root_with_return(None))
    assert not ok and "缺独立 PL-G11" in reason


def test_meaning_verdict_pass_with_evidence_ok() -> None:
    root = _root_with_return([{"id": "PL-G11", "verdict": "pass", "evidence": "逐句比对语义等价"}])
    ok, _ = independent_meaning_verdict(root)
    assert ok


def test_meaning_verdict_pass_without_evidence_fails() -> None:
    root = _root_with_return([{"id": "PL-G11", "verdict": "pass", "evidence": ""}])
    ok, reason = independent_meaning_verdict(root)
    assert not ok and "证据为空" in reason


def test_meaning_verdict_fail_blocks() -> None:
    root = _root_with_return([{"id": "PL-G11", "verdict": "fail", "evidence": "第3段把'提示'改成'证实'"}])
    ok, _ = independent_meaning_verdict(root)
    assert not ok


def test_meaning_verdict_missing_plg11_item_fails() -> None:
    root = _root_with_return([{"id": "PL-G1", "verdict": "pass", "evidence": "x"}])
    ok, reason = independent_meaning_verdict(root)
    assert not ok and "缺 PL-G11" in reason


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("OK: red-line binding guards catch swaps/upgrades/named-token edits")
