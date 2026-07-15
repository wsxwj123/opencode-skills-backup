#!/usr/bin/env python3
"""Tests for a few proofread.py rule checkers (misspelling / Chinese-punct / units).

Just enough to prove the rules fire on a positive and stay silent on a clean line —
these feed the delivery proofreading score, so a rule that silently stops matching is
a real regression.

Pure-import, standalone: `python3 test_proofread_rules.py`.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import proofread as p  # noqa: E402


def test_misspelling_teh_flagged():
    issues = p.check_misspellings("teh cat and teh dog")
    assert len(issues) == 2, issues
    assert all(i["suggest"] == "the" for i in issues)


def test_misspelling_suggests_correction():
    issues = p.check_misspellings("the result occured yesterday")
    assert any(i["suggest"] == "occurred" for i in issues), issues


def test_misspelling_clean_text_silent():
    assert p.check_misspellings("the correct text has no typos") == []


def test_chinese_punct_flagged_in_english_line():
    # A full-width comma stranded in an otherwise-English line (fewer than 3 CJK chars).
    issues = p.check_chinese_punct("The result，however, was surprising.")
    assert any(i["found"] == "，" for i in issues), issues


def test_units_ascii_um_flagged():
    issues = p.check_units("a 5 um particle was observed")
    assert any("μm" in i["suggest"] for i in issues), issues


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: proofread misspelling/chinese-punct/unit rules fire on positives, silent on clean text")
