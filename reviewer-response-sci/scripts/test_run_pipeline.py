#!/usr/bin/env python3
"""Tests for run_pipeline.py resume/signature safety invariants.

Running the full pipeline needs real docx inputs, so this locks the two safety
facts the --resume logic depends on (the skip decision itself is a one-liner:
`step in completed and step not in ALWAYS_RUN_STEPS`):
  - _signature changes when an input path changes, so a stale checkpoint from a
    different --comments file cannot make gate steps be skipped (completed only
    carries over when signatures match);
  - render_html is in ALWAYS_RUN_STEPS and present in the steps list, so it re-runs
    on every resume regardless of the checkpoint.
Self-contained: imports run_pipeline (module-level defs only) + reads its source.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_DIR))
import run_pipeline as R  # noqa: E402


def _ns(comments: str) -> argparse.Namespace:
    return argparse.Namespace(
        comments=comments, manuscript="/m.docx", si="", project_root="/p",
        output_html="/o.html", title="T", require_links=False, allow_placeholder=False,
        fail_on_conflict=False, fail_on_gap=False)


def test_signature_invalidates_on_input_change() -> None:
    sig_a = R._signature(_ns("/a.docx"))
    sig_b = R._signature(_ns("/b.docx"))
    assert sig_a != sig_b, "signature must change when --comments changes (else stale checkpoint reused)"
    assert R._signature(_ns("/a.docx")) == sig_a, "signature must be stable for identical inputs"


def test_render_html_always_runs() -> None:
    src = (_DIR / "run_pipeline.py").read_text(encoding="utf-8")
    assert 'ALWAYS_RUN_STEPS = {"render_html"}' in src, "render_html must be in ALWAYS_RUN_STEPS"
    assert '("render_html", render_html_cmd)' in src, "render_html must be a pipeline step"
    # The skip guard must exempt ALWAYS_RUN_STEPS.
    assert "step not in ALWAYS_RUN_STEPS" in src, "resume skip must exempt always-run steps"


if __name__ == "__main__":
    test_signature_invalidates_on_input_change()
    test_render_html_always_runs()
    print("OK: run_pipeline — signature invalidates on input change, render_html always runs")
