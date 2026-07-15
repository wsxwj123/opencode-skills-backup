#!/usr/bin/env python3
"""Tests for consistency_check.py branches not yet covered.

  - forbidden_phrase_patterns hit -> CONSISTENCY_CHECK: FAIL (exit 1);
  - --fail-on-conflict escalates a forbidden-phrase conflict to exit 2;
  - conflict_term_sets co-existence (two members) -> conflict FAIL;
  - a unit carrying content.cross_ref promising "we added X" with no local landing
    PASSes (the cross-referenced canonical unit carries the landing).
Self-contained: tempfile project + inline rules JSON (bypasses references/ default).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "consistency_check.py"


def _run(root: Path, rules: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(root), "--rules", str(rules), *extra],
        capture_output=True, text=True,
    )


def _write_unit(root: Path, uid: str, content: dict) -> None:
    p = root / "units" / f"{uid}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    base = {"modification_actions": [], "revised_excerpt_en": ""}
    base.update(content)
    p.write_text(json.dumps({"unit_id": uid, "section": "major", "content": base},
                            ensure_ascii=False), encoding="utf-8")


def _rules(root: Path, name: str, forbidden=(), conflict_sets=()) -> Path:
    p = root / name
    p.write_text(json.dumps({
        "forbidden_phrase_patterns": list(forbidden),
        "conflict_term_sets": [list(s) for s in conflict_sets],
        "required_markers": [],
    }, ensure_ascii=False), encoding="utf-8")
    return p


def test_forbidden_phrase_fails_and_escalates() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(root, "u-1", {"response_en": "This contains BADPHRASE here."})
        rules = _rules(root, "rules.json", forbidden=["BADPHRASE"])

        r = _run(root, rules)
        assert r.returncode == 1, r.stdout
        assert "CONSISTENCY_CHECK: FAIL" in r.stdout, r.stdout
        assert "Forbidden phrase" in r.stdout, r.stdout

        r2 = _run(root, rules, "--fail-on-conflict")
        assert r2.returncode == 2, r2.stdout  # conflict escalates only under the flag


def test_conflict_term_sets_coexist() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(root, "u-1", {"response_en": "We discuss alpha and omega together."})
        rules = _rules(root, "rules.json", conflict_sets=[("alpha", "omega")])
        r = _run(root, rules)
        assert r.returncode == 1, r.stdout
        assert "Conflicting terms co-exist" in r.stdout, r.stdout


def test_cross_ref_carries_landing_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Substantive add-promise with revised="无" and no local action, but cross_ref set.
        _write_unit(root, "u-2", {
            "response_en": "As noted in our response to Reviewer 1, we added a new experiment.",
            "cross_ref": "u-1",
            "revised_excerpt_en": "无",
        })
        rules = _rules(root, "rules.json")
        r = _run(root, rules)
        assert r.returncode == 0, r.stdout
        assert "CONSISTENCY_CHECK: PASS" in r.stdout, r.stdout


def test_substantive_add_without_landing_fails() -> None:
    """Guard the other side: same promise WITHOUT cross_ref/landing must FAIL."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(root, "u-2", {
            "response_en": "We added a new experiment.",
            "revised_excerpt_en": "无",
        })
        rules = _rules(root, "rules.json")
        r = _run(root, rules)
        assert r.returncode == 1, r.stdout
        assert "MISSING LANDING" in r.stdout, r.stdout


if __name__ == "__main__":
    test_forbidden_phrase_fails_and_escalates()
    test_conflict_term_sets_coexist()
    test_cross_ref_carries_landing_passes()
    test_substantive_add_without_landing_fails()
    print("OK: consistency_check — forbidden/conflict/fail-on-conflict/cross-ref landing")
