#!/usr/bin/env python3
"""Smoke test for preflight.py (environment precheck, BLOCKED vs OK).

Bidirectional, self-contained, standalone (`python3 test_preflight_gate.py`):
- OK: readable .docx comments + .docx manuscript, no other errors
      -> exit 0, JSON {"ok": true}. (si/attachments/reference absent are
      recorded as missing_items, not errors.)
- BLOCKED: comments with a non-.docx/.html suffix -> exit 1, JSON {"ok": false}
      with an errors list.

preflight only checks the manuscript's suffix + existence (not docx validity),
and detect_comments_input_mode() falls back to a supported branch for an
unreadable .docx, so byte-stub .docx files are enough to exercise the gate.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PREFLIGHT = SCRIPTS / "preflight.py"


def _run(comments: Path, manuscript: Path, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PREFLIGHT),
         "--comments", str(comments),
         "--manuscript", str(manuscript),
         "--project-root", str(root),
         "--output-md", str(root / "out.md"),
         "--output-docx", str(root / "out.docx")],
        capture_output=True, text=True,
    )


def test_ok_when_inputs_present():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        comments = tmp / "comments.docx"
        comments.write_bytes(b"stub")
        manuscript = tmp / "manuscript.docx"
        manuscript.write_bytes(b"stub")
        root = tmp / "proj"
        r = _run(comments, manuscript, root)
        assert r.returncode == 0, r.stdout + r.stderr
        payload = json.loads(r.stdout.splitlines()[-1])
        assert payload["ok"] is True, payload


def test_blocked_on_bad_comments_suffix():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        comments = tmp / "comments.txt"   # unsupported suffix
        comments.write_text("not a docx", encoding="utf-8")
        manuscript = tmp / "manuscript.docx"
        manuscript.write_bytes(b"stub")
        root = tmp / "proj"
        r = _run(comments, manuscript, root)
        assert r.returncode == 1, r.stdout
        payload = json.loads(r.stdout.splitlines()[-1])
        assert payload["ok"] is False and payload["errors"], payload


def test_blocked_on_missing_manuscript():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        comments = tmp / "comments.docx"
        comments.write_bytes(b"stub")
        manuscript = tmp / "nope.docx"    # does not exist
        root = tmp / "proj"
        r = _run(comments, manuscript, root)
        assert r.returncode == 1, r.stdout
        payload = json.loads(r.stdout.splitlines()[-1])
        assert payload["ok"] is False, payload


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: preflight blocks bad inputs, passes clean inputs")
