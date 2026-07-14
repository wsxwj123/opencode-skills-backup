#!/usr/bin/env python3
"""Smoke test for strict_gate.py's citation-claim hard gate + exit-code contract.

strict_gate PASS requires a fully-built delivery project (dozens of artifacts),
so the compliant direction is asserted at the load-bearing-citation logic the
gate reuses from the shared citation_claim_check._row_blockers, and the
exit-code contract is asserted by driving the real CLI on an empty project.

Bidirectional, self-contained, standalone (`python3 test_strict_gate_citation.py`):
- 违规: a load-bearing (承重) citation row that is support-but-unconfirmed
        -> _citation_claim_failures returns a blocker (承重句须逐条人工确认).
- 违规: no claim_evidence.json at all -> returns the "require claim_evidence.json" blocker.
- 合规: the same row with user_confirmed=true + retrieved abstract -> no blocker.
- exit-code: strict_gate.py on an empty project root -> STRICT_GATE: FAIL, exit != 0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import strict_gate  # noqa: E402


def _row(confirmed: bool) -> dict:
    return {
        "section": "Discussion",
        "claim_sentence": "Drug X reduces mortality by 30%.",
        "is_load_bearing": True,
        "ref_id": "R1",
        "retrieved_abstract": "A trial reporting a mortality reduction with drug X.",
        "verdict": "support",
        "user_confirmed": confirmed,
    }


def _write_evidence(root: Path, rows) -> None:
    (root / "claim_evidence.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8"
    )


def test_load_bearing_unconfirmed_is_blocked():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_evidence(root, [_row(confirmed=False)])
        failures = strict_gate._citation_claim_failures(root)
        assert failures, "unconfirmed load-bearing citation must be blocked"
        assert any("citation_claim_check" in f for f in failures), failures


def test_missing_claim_evidence_is_blocked():
    with tempfile.TemporaryDirectory() as d:
        failures = strict_gate._citation_claim_failures(Path(d))
        assert failures, "missing claim_evidence.json must be blocked"
        assert any("claim_evidence.json" in f for f in failures), failures


def test_confirmed_load_bearing_passes():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_evidence(root, [_row(confirmed=True)])
        failures = strict_gate._citation_claim_failures(root)
        assert failures == [], failures


def test_cli_fails_on_empty_project():
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(
            [sys.executable, str(Path(_SCRIPT_DIR) / "strict_gate.py"),
             "--project-root", d],
            capture_output=True, text=True,
        )
        assert r.returncode != 0, r.stdout
        assert "STRICT_GATE: FAIL" in r.stdout, r.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: strict_gate blocks unconfirmed load-bearing citations, fails empty project")
