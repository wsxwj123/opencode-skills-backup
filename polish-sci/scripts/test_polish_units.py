#!/usr/bin/env python3
"""Regression for polish_units.py — the advisory per-paragraph red-line layer.

validate_unit is the FIRST red-line pass (independent of strict_gate's delivery
gate). It must flag out-of-bounds edits (numeric change, citation-set change,
certainty upgrade) and stay silent on pure rewording. cmd_verify then folds those
signals into unit_ok with the soft/hard split, PLACEHOLDER guard, and
meaning_changed guard.

Baseline = current code behavior (notably: validate_unit's numeric guard catches
NUMBER changes, not unit-word swaps like µM→nM — that boundary is locked here and
noted; the µM→nM catch lives in strict_gate.check_unit, covered elsewhere).

Runs standalone (`python3`) or via pytest.
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

import polish_units as P
from strict_gate import is_soft_ai_marker

R = P.DEFAULT_RULES


def _flags(raw: str, pol: str, section="discussion", nonprose=False):
    return P.validate_unit(raw, pol, R, section, nonprose)["polish_risk_flags"]


# ── validate_unit red-line signals ────────────────────────────────────────────
def test_numeric_change_flagged() -> None:
    assert any("numeric changed" in f for f in _flags("Response was 12% here.", "Response was 21% here."))


def test_citation_change_flagged() -> None:
    assert any("citation set changed" in f for f in _flags("Finding A [3].", "Finding A [4]."))


def test_certainty_upgrade_flagged() -> None:
    assert any("certainty upgraded" in f
               for f in _flags("X may be associated with Y.", "X induces Y."))


def test_clean_reword_no_flags() -> None:
    assert _flags("The results were significant here.", "The findings were significant here.") == []


def test_unit_word_swap_not_caught_by_validate_unit() -> None:
    # 边界锁定:validate_unit 的数值守卫只比数字,不比单位词;µM→nM 数字未变故此层零 flag。
    # (µM→nM 由 strict_gate.check_unit 拦,见 test_redline_guards。)未来若重构误以为此层已覆盖,本用例会红。
    assert _flags("We added 10 µM inhibitor.", "We added 10 nM inhibitor.") == []


# ── soft/hard marker split ────────────────────────────────────────────────────
def test_em_dash_is_hard_marker() -> None:
    flags = _flags("The effect was clear here.", "The effect was clear—striking—here.")
    assert any("ai markers" in f and "em dash" in f for f in flags)
    assert not is_soft_ai_marker("em dash")  # 破折号硬拦


def test_long_sentence_is_soft() -> None:
    long_pol = "alpha " * 35 + "here."
    flags = _flags("Short sentence.", long_pol)
    assert any("sentence >" in f for f in flags)
    assert is_soft_ai_marker("sentence >30 words")


def test_nonprose_suppresses_ai_and_length_but_keeps_numeric() -> None:
    long_pol = "alpha " * 35 + "here."
    assert _flags("x.", long_pol, nonprose=True) == []  # 长句/去AI 对非散文豁免
    assert any("numeric changed" in f
               for f in _flags("val 12.", "val 21.", nonprose=True))  # 数字仍查


# ── cmd_verify unit_ok contract (subprocess) ──────────────────────────────────
def _run_verify(polished_units: list[dict]) -> dict:
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "polished"), exist_ok=True)
    index = {"units": [{"idx": u["idx"]} for u in polished_units]}
    with open(os.path.join(root, "units_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    for u in polished_units:
        with open(os.path.join(root, "polished", f"{u['idx']}.json"), "w", encoding="utf-8") as f:
            json.dump(u, f, ensure_ascii=False)
    cmd = [sys.executable, os.path.join(_SCRIPT_DIR, "polish_units.py"), "verify",
           "--project-root", root]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return json.loads(out)


def _u(idx, raw, pol, **kw):
    base = {"idx": idx, "section_type": "discussion", "prose": True, "raw_text": raw,
            "polished_text": pol, "meaning_changed": False, "polished_by": "ai"}
    base.update(kw)
    return base


def test_verify_unit_ok_matrix() -> None:
    units = [
        _u(0, "The cells grew fast.", "The cells grew fast.", polished_by="PLACEHOLDER"),  # placeholder
        _u(1, "The cells grew fast.", "The cells proliferated rapidly."),                   # clean -> ok
        _u(2, "The effect was clear.", "The effect was clear—striking—here."),              # hard em dash
        _u(3, "Short sentence.", "alpha " * 35 + "here."),                                  # soft long only
        _u(4, "Response was 12%.", "Response was 21%."),                                    # numeric change
        _u(5, "The cells grew.", "The cells grew.", meaning_changed=True),                  # meaning flag
    ]
    res = _run_verify(units)
    ok = {r["idx"]: r["ok"] for r in res["units"]}
    assert ok[0] is False, "PLACEHOLDER must not pass"
    assert ok[1] is True, "clean polish must pass"
    assert ok[2] is False, "hard em dash must fail unit"
    assert ok[3] is True, "soft long sentence alone must not fail unit"
    assert ok[4] is False, "numeric change must fail unit"
    assert ok[5] is False, "meaning_changed=true must fail unit"
    assert res["ok"] is False, "overall ok false when any unit fails"


def test_verify_all_clean_overall_ok() -> None:
    units = [
        _u(0, "The cells grew fast.", "The cells proliferated rapidly."),
        _u(1, "We observed a strong signal.", "A strong signal was observed."),
    ]
    res = _run_verify(units)
    assert res["ok"] is True
    assert all(r["ok"] for r in res["units"])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("OK: polish_units validate_unit signals + cmd_verify unit_ok contract")
