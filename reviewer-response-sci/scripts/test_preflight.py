#!/usr/bin/env python3
"""Tests for preflight.py project-owner fail-closed guard.

project_state.json carries the owning skill. Pointing reviewer-response at a
project owned by revise-sci must fail-closed (the two unit schemas differ):
  - owner "revise-sci" -> sys.exit with a conflict message (unless --force-shared);
  - --force-shared bypasses the ownership guard (proceeds to docx checks);
  - own skill / missing / malformed state -> guard does not block (proceeds).
The docx inputs are intentionally missing, so a non-blocked run reaches the docx
stage and reports PREFLIGHT: FAIL — distinct from the ownership sys.exit path.
Self-contained: tempfile project dirs, bogus docx paths.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "preflight.py"

_CONFLICT_MARK = "PROJECT_ROOT 冲突"


def _run(root: Path, *extra: str) -> subprocess.CompletedProcess:
    bogus = str(root / "nope.docx")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--comments", bogus, "--manuscript", bogus,
         "--project-root", str(root), "--output-html", str(root / "o.html"), *extra],
        capture_output=True, text=True)


def _state(root: Path, text: str) -> None:
    (root / "project_state.json").write_text(text, encoding="utf-8")


def test_foreign_owner_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _state(root, '{"skill": "revise-sci"}')
        r = _run(root)
        assert r.returncode != 0, r.stdout
        assert _CONFLICT_MARK in (r.stdout + r.stderr), r.stdout + r.stderr


def test_force_shared_bypasses_guard() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _state(root, '{"skill": "revise-sci"}')
        r = _run(root, "--force-shared")
        # ownership no longer blocks; run proceeds to docx checks and fails there instead.
        assert _CONFLICT_MARK not in (r.stdout + r.stderr), r.stdout
        assert "PREFLIGHT: FAIL" in r.stdout, r.stdout


def test_own_skill_and_malformed_do_not_block() -> None:
    for state_text in ('{"skill": "reviewer-response-sci"}', "{not json", ""):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _state(root, state_text)
            r = _run(root)
            assert _CONFLICT_MARK not in (r.stdout + r.stderr), (state_text, r.stdout)
            assert "PREFLIGHT: FAIL" in r.stdout, (state_text, r.stdout)

    # No project_state.json at all -> guard is a no-op, docx stage runs.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        r = _run(root)
        assert _CONFLICT_MARK not in (r.stdout + r.stderr), r.stdout
        assert "PREFLIGHT: FAIL" in r.stdout, r.stdout


if __name__ == "__main__":
    test_foreign_owner_fails_closed()
    test_force_shared_bypasses_guard()
    test_own_skill_and_malformed_do_not_block()
    print("OK: preflight — foreign-owner fail-closed, --force-shared bypass, own/missing/malformed pass")
