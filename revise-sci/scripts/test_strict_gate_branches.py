#!/usr/bin/env python3
"""Tests for strict_gate.py branches OTHER than the citation-claim gate
(that one lives in test_strict_gate_citation.py).

A full green PASS needs dozens of artifacts, so the compliant direction is asserted
on the reusable pure helpers (missing_atomic_fields, completed_citation_units). The
non-citation blocker branches inside main() are asserted by driving the real CLI on
a minimal project that trips exactly one perturbation and checking that blocker's
line shows up among the printed failures (a partial project prints many failures —
we only assert OUR target is present and the gate fails).

Self-contained, standalone: `python3 test_strict_gate_branches.py`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import strict_gate  # noqa: E402

GATE = Path(_HERE) / "strict_gate.py"


# --- pure helper: missing_atomic_fields (atomic_location completeness) ---
def test_missing_atomic_fields_all_present():
    unit = {"atomic_location": {"section_file": "f", "paragraph_index": 1, "matched_sentence": "x"},
            "original_excerpt_en": "real excerpt"}
    assert strict_gate.missing_atomic_fields(unit) == []


def test_missing_atomic_fields_reports_blanks():
    unit = {"atomic_location": {"section_file": "", "paragraph_index": None, "matched_sentence": "x"},
            "original_excerpt_en": "real excerpt"}
    assert sorted(strict_gate.missing_atomic_fields(unit)) == ["paragraph_index", "section_file"]


def test_missing_atomic_fields_exempt_when_no_excerpt():
    # A unit with no rewritten excerpt ("无") is legitimately exempt from anchoring.
    unit = {"atomic_location": {}, "original_excerpt_en": "无"}
    assert strict_gate.missing_atomic_fields(unit) == []


# --- pure helper: completed_citation_units selection ---
def test_completed_citation_units_selects_only_completed_citation():
    units = [
        {"status": "completed", "editorial_intent": "citation"},
        {"status": "completed", "editorial_intent": "clarify"},
        {"status": "needs_author_confirmation", "editorial_intent": "citation"},
    ]
    assert len(strict_gate.completed_citation_units(units)) == 1


def _run_gate(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GATE), "--project-root", str(root)],
                          capture_output=True, text=True)


def _write_unit(root: Path, unit: dict) -> None:
    (root / "units").mkdir(parents=True, exist_ok=True)
    (root / "units" / "u1.json").write_text(json.dumps(unit, ensure_ascii=False), encoding="utf-8")


# --- CLI branch: numeric drift in a completed polished revision must blocker ---
def test_polish_numbers_drift_is_a_blocker():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_unit(root, {
            "comment_id": "R1-Major-01", "status": "completed", "severity": "major",
            "revision_plan": {"scope": "sentence_replace", "polished_fragment": "text here"},
            "polish_applied": True, "polish_driver_mode": "local-heuristic",
            "polish_guard_ok": True, "polish_scope_respected": True,
            "polish_meaning_changed": False, "polish_locked_context_ok": True,
            "polish_numbers_ok": False, "polish_certainty_ok": True,
        })
        r = _run_gate(root)
        assert r.returncode == 1, r.stdout
        assert "polish_numbers_ok is false" in r.stdout, r.stdout


# --- CLI branch: completed new-citation unit with unverified guard rows ---
def test_completed_citation_without_guard_verification_is_a_blocker():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_unit(root, {
            "comment_id": "R1-Major-01", "status": "completed",
            "editorial_intent": "citation", "severity": "major",
        })
        r = _run_gate(root)
        assert r.returncode == 1, r.stdout
        assert "all_rows_guard_verified" in r.stdout, r.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: strict_gate atomic/citation helpers + polish-numbers/guard blocker branches")
