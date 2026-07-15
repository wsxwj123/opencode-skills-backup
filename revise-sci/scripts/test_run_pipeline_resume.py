#!/usr/bin/env python3
"""Tests for run_pipeline.py resume bookkeeping: which outputs get cleared on a
resume, and whether unchanged inputs are detected as unchanged.

clear_outputs_from_step must wipe the start step and everything downstream while
leaving upstream artifacts intact; resume_inputs_changed must return [] when inputs
are byte-identical and flag the exact key that changed otherwise.

Self-contained via tempfile + argparse.Namespace, standalone:
`python3 test_run_pipeline_resume.py`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import run_pipeline as rp  # noqa: E402


def test_clear_outputs_from_step_wipes_downstream_keeps_upstream():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # upstream (polish, before literature) artifact
        (root / "revision_polish_manifest.json").write_text("{}", encoding="utf-8")
        # literature-step artifact
        (root / "data").mkdir()
        (root / "data" / "literature_index.json").write_text("[]", encoding="utf-8")
        # final_report-step artifact (downstream)
        (root / "final_consistency_report.md").write_text("x", encoding="utf-8")

        rp.clear_outputs_from_step(root, root / "out.md", root / "out.docx", "literature")

        assert (root / "revision_polish_manifest.json").exists(), "upstream polish artifact must survive"
        assert not (root / "data" / "literature_index.json").exists(), "start-step artifact must be cleared"
        assert not (root / "final_consistency_report.md").exists(), "downstream artifact must be cleared"


def _make_args(root: Path, comments: Path, manuscript: Path, refs: Path) -> argparse.Namespace:
    return argparse.Namespace(
        comments=str(comments), manuscript=str(manuscript), si="", attachments_dir="",
        reference_docx="", journal_style="journal-manuscript", paper_search_results="",
        references_source=str(refs), project_root=str(root), reference_search_decision="ask",
        expected_comments_mode="", auto_run_reference_search=False, paper_search_runner="",
        opencode_driver_command="", revision_polish_runner="", context_token_budget=4200,
        context_tail_lines=80,
    )


def test_resume_inputs_unchanged_returns_empty():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        comments = root / "c.docx"; comments.write_text("comment bytes", encoding="utf-8")
        manuscript = root / "m.docx"; manuscript.write_text("manuscript bytes", encoding="utf-8")
        refs = root / "r.bib"; refs.write_text("@a{k,title={T}}", encoding="utf-8")
        args = _make_args(root, comments, manuscript, refs)
        sigs = rp.current_input_signatures(args)
        (root / "project_state.json").write_text(json.dumps({"input_signatures": sigs}), encoding="utf-8")
        assert rp.resume_inputs_changed(root, args) == []


def test_resume_inputs_flags_changed_manuscript():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        comments = root / "c.docx"; comments.write_text("comment bytes", encoding="utf-8")
        manuscript = root / "m.docx"; manuscript.write_text("manuscript bytes", encoding="utf-8")
        refs = root / "r.bib"; refs.write_text("@a{k,title={T}}", encoding="utf-8")
        args = _make_args(root, comments, manuscript, refs)
        sigs = rp.current_input_signatures(args)
        (root / "project_state.json").write_text(json.dumps({"input_signatures": sigs}), encoding="utf-8")
        # Rewrite manuscript with different size + later mtime -> path_signature changes.
        time.sleep(0.01)
        manuscript.write_text("manuscript bytes, now materially longer", encoding="utf-8")
        changed = rp.resume_inputs_changed(root, args)
        assert changed == ["manuscript_docx_path"], changed


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: clear_outputs_from_step scoping + resume input-signature change detection")
