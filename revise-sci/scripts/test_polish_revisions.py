#!/usr/bin/env python3
"""Tests for polish_revisions.py payload validation + fragment application.

validate_output_payload is the gate that rejects a bad polish回包 (unknown id,
missing fragment, meaning changed, scope violated); apply_polished_fragment writes
the polished text back at the right scope while leaving untouched context alone.

Pure-import, standalone: `python3 test_polish_revisions.py`.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import polish_revisions as p  # noqa: E402


CANDIDATES = [{"comment_id": "C1"}, {"comment_id": "C2"}]


def test_validate_complete_payload_has_no_errors():
    payload = {"results": [
        {"comment_id": "C1", "polished_fragment": "x", "meaning_changed": False, "scope_respected": True},
    ]}
    assert p.validate_output_payload(payload, CANDIDATES) == []


def test_validate_accepts_bare_list_form():
    rows = [{"comment_id": "C2", "polished_fragment": "y"}]
    assert p.validate_output_payload(rows, CANDIDATES) == []


def test_validate_unknown_comment_id():
    errs = p.validate_output_payload([{"comment_id": "ZZ", "polished_fragment": "x"}], CANDIDATES)
    assert any("unknown comment_id" in e for e in errs), errs


def test_validate_missing_fragment():
    errs = p.validate_output_payload([{"comment_id": "C1", "polished_fragment": ""}], CANDIDATES)
    assert any("missing polished_fragment" in e for e in errs), errs


def test_validate_meaning_changed_rejected():
    errs = p.validate_output_payload(
        [{"comment_id": "C1", "polished_fragment": "x", "meaning_changed": True}], CANDIDATES)
    assert any("meaning_changed" in e for e in errs), errs


def test_validate_non_list_payload():
    errs = p.validate_output_payload("not a payload", CANDIDATES)
    assert errs and "list" in errs[0]


# --- apply_polished_fragment: scope-correct write-back ---
def test_apply_sentence_replace_keeps_other_sentences():
    plan = {"scope": "sentence_replace", "paragraph_before": "One. Two. Three.", "target_sentence_index": 1}
    assert p.apply_polished_fragment(plan, "NEW.") == "One. NEW. Three."


def test_apply_sentence_append():
    plan = {"scope": "sentence_append", "paragraph_before": "One."}
    assert p.apply_polished_fragment(plan, "Two.") == "One. Two."


def test_apply_paragraph_replace():
    plan = {"scope": "paragraph_replace", "paragraph_before": "old text"}
    assert p.apply_polished_fragment(plan, "brand new paragraph") == "brand new paragraph"


def test_apply_unknown_scope_falls_back_to_raw_after():
    plan = {"scope": "", "paragraph_before": "before", "paragraph_after_raw": "after raw"}
    assert p.apply_polished_fragment(plan, "ignored") == "after raw"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: polish payload validation flags bad returns; fragment application respects scope")
