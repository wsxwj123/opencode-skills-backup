#!/usr/bin/env python3
"""Unit tests for revise_units.py's core sentence-surgery + response rendering.

These are the pure functions that actually rewrite a user sentence in place, so
their safety invariants (clamp instead of raise, no duplicate citation, idempotent
append, no silently-dropped comment in the reviewer response) are asserted directly
by import — no pipeline scaffold needed.

Self-contained, standalone: `python3 test_revise_units_fns.py` (exit 0 == all pass).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import revise_units as ru  # noqa: E402


# --- replace_sentence_at: out-of-range index must clamp to the last sentence, ---
# --- never raise and never drop a sentence. ---
def test_replace_sentence_clamps_high_index():
    para = "One. Two. Three."
    out = ru.replace_sentence_at(para, 9, "NEW.")
    assert out == "One. Two. NEW.", out  # clamped to last, first two intact


def test_replace_sentence_clamps_negative_index():
    para = "One. Two. Three."
    out = ru.replace_sentence_at(para, -5, "NEW.")
    assert out == "NEW. Two. Three.", out  # clamped to first


def test_replace_sentence_middle():
    out = ru.replace_sentence_at("One. Two. Three.", 1, "NEW.")
    assert out == "One. NEW. Three.", out


def test_replace_sentence_empty_paragraph_returns_new():
    out = ru.replace_sentence_at("", 0, "Just this.")
    assert out == "Just this.", out


# --- inject_citation_into_sentence: append after terminal punctuation, and never ---
# --- inject a citation that is already present. ---
def test_inject_citation_after_period():
    out = ru.inject_citation_into_sentence("The effect was strong.", "[12]")
    assert out == "The effect was strong [12].", out


def test_inject_citation_no_terminal_punct():
    out = ru.inject_citation_into_sentence("No period here", "[3]")
    assert out == "No period here [3]", out


def test_inject_citation_not_duplicated():
    already = "The effect was strong [12]."
    assert ru.inject_citation_into_sentence(already, "[12]") == already


# --- append_sentence_to_paragraph: idempotent (re-appending the same sentence is ---
# --- a no-op), and appends with a single separating space otherwise. ---
def test_append_sentence_idempotent():
    base = "A cat sat."
    assert ru.append_sentence_to_paragraph(base, "A cat sat.") == base


def test_append_sentence_new():
    assert ru.append_sentence_to_paragraph("A cat sat.", "It purred.") == "A cat sat. It purred."


def test_append_sentence_into_empty():
    assert ru.append_sentence_to_paragraph("", "First.") == "First."


# --- render_response_to_reviewers: every unit yields exactly one Comment block ---
# --- (no silent drop) grouped under its reviewer heading. ---
def _unit(cid: str, reviewer: str, severity: str) -> dict:
    return {
        "comment_id": cid,
        "reviewer": reviewer,
        "severity": severity,
        "reviewer_comment_en": f"Comment body for {cid}.",
        "reviewer_comment_original": f"Comment body for {cid}.",
        "reviewer_comment_zh_literal": "审稿意见直译。",
        "reviewer_comment_lang": "en",
        "intent_zh": "意图",
        "response_zh": "回应",
        "response_en": "Response.",
        "atomic_location": {
            "section_heading": "Methods",
            "paragraph_index": 2,
            "matched_sentence": "anchor",
            "section_file": "manuscript_sections/methods.md",
            "manuscript_section_id": "m1",
        },
        "modification_actions": [{"action": "edit", "reason": "clarity"}],
        "original_excerpt_en": f"orig-{cid}",
        "revised_excerpt_en": f"revised-{cid}",
        "revised_excerpt_zh": "修订",
        "notes_core_zh": ["core"],
        "notes_support_zh": ["support"],
        "evidence_sources": [{"provider_family": "paper-search", "source": "PMID:1"}],
    }


def test_render_one_block_per_unit_no_drop():
    units = [
        _unit("R1-Major-01", "Reviewer #1", "major"),
        _unit("R1-Minor-01", "Reviewer #1", "minor"),
        _unit("R2-Major-01", "Reviewer #2", "major"),
    ]
    md = ru.render_response_to_reviewers(units)
    assert md.count("### Comment") == len(units), md.count("### Comment")
    assert "# Reviewer #1" in md and "# Reviewer #2" in md
    # Each unit's revised excerpt lands in the response exactly once (no drop, no dup).
    for u in units:
        assert md.count(u["revised_excerpt_en"]) == 1, u["comment_id"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: revise_units sentence surgery clamps/dedupes/idempotent, response renders every unit")
