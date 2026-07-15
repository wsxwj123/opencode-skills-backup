#!/usr/bin/env python3
"""Tests for atomize_comments.py comment-id formatting, severity routing, and the
docx parse that turns a reviewer letter into per-comment units.

Guards two things: the comment-id prefix contract (E- for editor vs R<n>- for a
numbered reviewer, severity capitalized, zero-padded index) and that a mixed
R1/R2/editor + major/minor letter atomizes into the right number of units with the
right reviewer/severity on each (no dropped or misrouted comment).

python-docx required for the parse test; if missing the whole module skips (exit 0).
Standalone: `python3 test_atomize_comments.py`.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import atomize_comments as a  # noqa: E402


# --- format_comment_id: prefix + severity + padded index ---
def test_format_comment_id_reviewer_prefix():
    assert a.format_comment_id("Reviewer #1", "major", 1) == "R1-Major-01"
    assert a.format_comment_id("Reviewer #2", "minor", 3) == "R2-Minor-03"


def test_format_comment_id_editor_prefix():
    assert a.format_comment_id("Editor", "major", 1) == "E-Major-01"


def test_is_editor_reviewer():
    assert a.is_editor_reviewer("Editor") and a.is_editor_reviewer("Decision Letter")
    assert not a.is_editor_reviewer("Reviewer #1")


def test_numbered_comment_match_ascii_and_parens():
    assert a.numbered_comment_match("1. First point.")
    assert a.numbered_comment_match("(4) Fourth point.")
    assert a.numbered_comment_match("random line without number") is None


# --- end-to-end docx parse: mixed reviewers + severities ---
def test_parse_docx_comments_routes_reviewers_and_severity():
    try:
        from docx import Document
    except Exception:
        print("SKIP parse test: python-docx not installed")
        return
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "comments.docx"
        doc = Document()
        for line in [
            "Reviewer #1",
            "Major",
            "1. First major point about methods.",
            "Minor",
            "1. A minor wording point.",
            "Reviewer #2",
            "1. Second reviewer main point.",
            "Editor",
            "1. Editor overall point here.",
        ]:
            doc.add_paragraph(line)
        doc.save(str(path))

        rows = a.parse_docx_comments(path)
        by_id = {r["comment_id"]: r for r in rows}
        assert len(rows) == 4, rows

        assert by_id["R1-Major-01"]["reviewer"] == "Reviewer #1"
        assert by_id["R1-Major-01"]["severity"] == "major"
        assert by_id["R1-Minor-01"]["severity"] == "minor"
        assert by_id["R2-Major-01"]["reviewer"] == "Reviewer #2"
        # Editor heading routes to the E- prefix.
        assert "E-Major-01" in by_id
        assert by_id["E-Major-01"]["reviewer"] == "Editor"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: comment-id prefixing + docx reviewer/severity routing")
