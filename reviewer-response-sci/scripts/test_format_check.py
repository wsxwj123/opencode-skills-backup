#!/usr/bin/env python3
"""Smoke test for format_check.py (output-structure承重门, fail-closed).

format_check requires: exactly 3 fenced code blocks, both 🔴 and 🟡 markers, and a
Part-4 / 修改说明 heading. Bidirectional:
  - violation: text with only 1 code block and no markers → exit 1, "FORMAT_CHECK: FAIL".
  - compliant: 3 code blocks + 🔴 + 🟡 + 修改说明 → exit 0, "FORMAT_CHECK: PASS".
Self-contained: writes a synthetic response text file under tempfile.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "format_check.py"

_BLOCK = "```\nsample block content\n```"

_COMPLIANT = f"""Part 1
{_BLOCK}

Part 2
{_BLOCK}

Part 4 修改说明
🔴 core note
🟡 support note
{_BLOCK}
"""

_VIOLATION = f"""Some response with a single block and no markers.
{_BLOCK}
"""


def _run(text: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        return subprocess.run(
            [sys.executable, str(SCRIPT), path], capture_output=True, text=True
        )
    finally:
        Path(path).unlink(missing_ok=True)


def test_violation_fails() -> None:
    r = _run(_VIOLATION)
    assert r.returncode == 1, f"expected FAIL exit 1, got {r.returncode}\n{r.stdout}"
    assert "FORMAT_CHECK: FAIL" in r.stdout, r.stdout


def test_compliant_passes() -> None:
    r = _run(_COMPLIANT)
    assert r.returncode == 0, f"expected PASS exit 0, got {r.returncode}\n{r.stdout}"
    assert "FORMAT_CHECK: PASS" in r.stdout, r.stdout


if __name__ == "__main__":
    test_violation_fails()
    test_compliant_passes()
    print("OK: format_check — malformed fails, well-formed passes")
