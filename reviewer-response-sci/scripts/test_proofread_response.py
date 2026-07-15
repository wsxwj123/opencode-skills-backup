#!/usr/bin/env python3
"""Tests for proofread_response.py field isolation.

proofread_response scans ONLY the author-written reply body (response_en /
response_zh), never the quoted reviewer text (reviewer_comment_*). This prevents
false failures on characters the reviewer wrote:
  - a fail-on trigger ("teh") sitting in reviewer_comment_en -> PASS
    (that field is never extracted);
  - the same trigger in response_en -> the wrapped proofread flags it (exit 1);
  - a unit with no author reply at all -> status "no_author_response", exit 0.
Self-contained: tempfile project, inline unit JSON. Uses "teh" (a proofread
`misspelling`, in proofread_response's --fail-on set) as the isolation probe.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "proofread_response.py"


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(root)],
        capture_output=True, text=True)


def _write_unit(root: Path, uid: str, content: dict) -> None:
    p = root / "units" / f"{uid}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"unit_id": uid, "section": "major", "content": content},
                            ensure_ascii=False), encoding="utf-8")


def test_reviewer_comment_field_not_scanned() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Trigger lives only in the quoted reviewer text; author reply is clean.
        _write_unit(root, "u-1", {
            "reviewer_comment_en": "The authors write teh results incorrectly.",
            "response_en": "We thank the reviewer and clarified the wording.",
        })
        r = _run(root)
        assert r.returncode == 0, r.stdout + r.stderr


def test_response_field_is_scanned() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(root, "u-1", {
            "reviewer_comment_en": "Please clarify the wording.",
            "response_en": "We revised teh Methods section accordingly.",
        })
        r = _run(root)
        assert r.returncode == 1, r.stdout + r.stderr
        assert '"misspelling"' in r.stdout or "misspelling" in r.stdout, r.stdout


def test_no_author_response_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(root, "u-1", {"reviewer_comment_en": "Some comment.",
                                  "response_en": "", "response_zh": ""})
        r = _run(root)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "no_author_response" in r.stdout, r.stdout


if __name__ == "__main__":
    test_reviewer_comment_field_not_scanned()
    test_response_field_is_scanned()
    test_no_author_response_passes()
    print("OK: proofread_response — reviewer field skipped, response field scanned, empty reply passes")
