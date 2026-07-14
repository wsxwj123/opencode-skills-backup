#!/usr/bin/env python3
"""Smoke test for risk_check.py (fail-closed 去AI 硬门禁承重门).

Bidirectional:
  - violation: a comment unit whose response_en contains a decorative em-dash
    (去AI必禁三项之一) → hard risk → exit 1, "RISK_CHECK: FAIL".
  - compliant: clean response_en / revised_excerpt_en → exit 0, "RISK_CHECK: PASS".
Self-contained: synthesizes a minimal units/ dir under tempfile; no real manuscript, no network.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "risk_check.py"


def _write_unit(root: Path, uid: str, response_en: str, revised_en: str = "The revised text is clear.") -> None:
    units = root / "units"
    units.mkdir(parents=True, exist_ok=True)
    unit = {
        "unit_id": uid,
        "section": "major",
        "content": {"response_en": response_en, "revised_excerpt_en": revised_en},
    }
    (units / f"{uid}.json").write_text(json.dumps(unit, ensure_ascii=False), encoding="utf-8")


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(root)],
        capture_output=True, text=True,
    )


def test_em_dash_violation_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Decorative em-dash between words → ai_em_dash hard hit.
        _write_unit(root, "u1", "This result—while preliminary—supports the reviewer's concern.")
        r = _run(root)
        assert r.returncode == 1, f"expected FAIL exit 1, got {r.returncode}\n{r.stdout}"
        assert "RISK_CHECK: FAIL" in r.stdout, r.stdout
        assert "ai_em_dash" in r.stdout, r.stdout


def test_clean_unit_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(
            root, "u2",
            "We agree with the reviewer. We revised the paragraph accordingly. "
            "The updated section now clarifies this point.",
        )
        r = _run(root)
        assert r.returncode == 0, f"expected PASS exit 0, got {r.returncode}\n{r.stdout}"
        assert "RISK_CHECK: FAIL" not in r.stdout, r.stdout
        assert "RISK_CHECK: PASS" in r.stdout or "RISK_CHECK: WARN" in r.stdout, r.stdout


if __name__ == "__main__":
    test_em_dash_violation_fails()
    test_clean_unit_passes()
    print("OK: risk_check — em-dash hard-fails, clean passes")
