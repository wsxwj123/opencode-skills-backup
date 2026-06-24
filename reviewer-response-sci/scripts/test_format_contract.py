#!/usr/bin/env python3
"""Regression tests for reviewer-response-sci citation gates (no pytest).

Run directly:  python3 test_format_contract.py
Pass => prints OK. Fail => raises AssertionError.

Covers the opt-in hard gates that let a DoD turn the default WARN downgrade
back into fail-closed:

1. citation_guard.py --fail-on-unverified: an unverified entry must exit 0 by
   default (lenient) but exit non-zero with the flag. Retraction stays an
   unconditional fail (exit 1) regardless of the flag.

2. citation_ref_tracker.py --fail-on-gap (A2 missing-number detection):
   a numbering gap must be WARN/exit-0 by default but exit non-zero with the
   flag, and must not false-positive on contiguous numbering.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CITATION_GUARD = SCRIPTS_DIR / "citation_guard.py"
REF_TRACKER = SCRIPTS_DIR / "citation_ref_tracker.py"


def _run_guard(tmp: Path, entries: list[dict], extra_args: list[str]) -> int:
    reg = tmp / "citation_registry.json"
    reg.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(CITATION_GUARD), "--project-root", str(tmp), "--offline"]
        + extra_args,
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    return result.returncode


def test_guard_unverified_lenient_by_default() -> None:
    # An entry with no DOI/PMID cannot be verified offline -> failed, but the
    # default contract is lenient (only retraction fails by default).
    entries = [{"ref_number": 5, "title": "Unverifiable thing", "source_provider": "paper-search"}]
    with tempfile.TemporaryDirectory() as tmp:
        rc = _run_guard(Path(tmp), entries, [])
    assert rc == 0, f"unverified entry must be lenient by default (exit 0), got {rc}"


def test_guard_fail_on_unverified_blocks() -> None:
    entries = [{"ref_number": 5, "title": "Unverifiable thing", "source_provider": "paper-search"}]
    with tempfile.TemporaryDirectory() as tmp:
        rc = _run_guard(Path(tmp), entries, ["--fail-on-unverified"])
    assert rc != 0, f"--fail-on-unverified must block an unverified entry, got {rc}"


def test_guard_empty_registry_passes() -> None:
    # Reviewer responses often add no new references; empty registry stays PASS.
    with tempfile.TemporaryDirectory() as tmp:
        rc = _run_guard(Path(tmp), [], ["--fail-on-unverified"])
    assert rc == 0, f"empty registry must PASS even with --fail-on-unverified, got {rc}"


def _run_tracker(tmp: Path, response_text: str, registry: dict, extra_args: list[str]) -> tuple[int, dict]:
    (tmp / "units").mkdir(exist_ok=True)
    (tmp / "units" / "u1.json").write_text(
        json.dumps({"unit_id": "u1", "content": {"response_en": response_text}}),
        encoding="utf-8",
    )
    (tmp / "citation_registry.json").write_text(json.dumps(registry), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REF_TRACKER), "--project-root", str(tmp)] + extra_args,
        cwd=str(SCRIPTS_DIR),
        capture_output=True,
        text=True,
    )
    report = json.loads((tmp / "logs" / "citation_ref_report.json").read_text(encoding="utf-8"))
    return result.returncode, report


def test_tracker_gap_lenient_by_default() -> None:
    # original_ref_count=4, new refs 5 and 7 -> 6 is a gap.
    registry = {"original_ref_count": 4, "entries": [{"ref_number": 5}, {"ref_number": 7}]}
    with tempfile.TemporaryDirectory() as tmp:
        rc, report = _run_tracker(Path(tmp), "See [5] and [7].", registry, [])
    assert rc == 0, f"numbering gap must be WARN/exit-0 by default, got {rc}"
    assert report["numbering_gaps"] == [6], (
        f"gap 6 must be detected, got {report['numbering_gaps']}"
    )


def test_tracker_fail_on_gap_blocks() -> None:
    registry = {"original_ref_count": 4, "entries": [{"ref_number": 5}, {"ref_number": 7}]}
    with tempfile.TemporaryDirectory() as tmp:
        rc, _ = _run_tracker(Path(tmp), "See [5] and [7].", registry, ["--fail-on-gap"])
    assert rc != 0, f"--fail-on-gap must block on a numbering gap, got {rc}"


def test_tracker_fail_on_gap_no_false_positive() -> None:
    registry = {"original_ref_count": 4, "entries": [{"ref_number": 5}, {"ref_number": 6}]}
    with tempfile.TemporaryDirectory() as tmp:
        rc, report = _run_tracker(Path(tmp), "See [5] and [6].", registry, ["--fail-on-gap"])
    assert rc == 0, f"--fail-on-gap must not fire on contiguous refs, got {rc}"
    assert report["numbering_gaps"] == [], (
        f"contiguous refs must report no gaps, got {report['numbering_gaps']}"
    )


def main() -> int:
    test_guard_unverified_lenient_by_default()
    test_guard_fail_on_unverified_blocks()
    test_guard_empty_registry_passes()
    test_tracker_gap_lenient_by_default()
    test_tracker_fail_on_gap_blocks()
    test_tracker_fail_on_gap_no_false_positive()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
