#!/usr/bin/env python3
"""Regression for the semantic red-line guards added to strict_gate.

Locks that the delivery gate catches meaning-changing edits the old set-based
checks let through: value/citation swaps (order), causal-verb upgrades, and
proper-noun / unit alterations. Runs standalone or via pytest.
"""
from __future__ import annotations

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from strict_gate import check_unit


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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("OK: red-line binding guards catch swaps/upgrades/named-token edits")
