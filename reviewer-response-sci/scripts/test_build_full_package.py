#!/usr/bin/env python3
"""Tests for build_full_package.py pure functions (no docx needed).

Covers the high-risk, silent-corruption surfaces:
  - render_html HTML-escapes user content (<script>/&/") so a unit field can't
    inject markup into the delivered HTML;
  - build_index sorts Editor first, then reviewers by number, and comments by
    numeric (not lexicographic) comment_number, with non-numeric falling to a 999
    bucket without crashing;
  - is_back_matter_heading_text treats a leading heading word ("References") as a
    section start but a mid-sentence occurrence of the word as body text;
  - split_row_by_inline_back_matter_headings splits a trailing inline heading but
    not a start-anchored one;
  - is_figure_caption recognises a figure caption.
Self-contained: builds unit dicts inline (no docx, no python-docx).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_full_package as B  # noqa: E402


def _evidence() -> dict:
    return {
        "text": ["ev"],
        "image_change_required": False,
        "images": [{"src": "", "alt": "a", "caption": "c"}],
        "table": {"columns": ["Item"], "rows": [["x"]]},
    }


def _email_unit() -> dict:
    return {
        "unit_id": "u-000-email", "order": 0, "reviewer": "all", "section": "email",
        "comment_number": "0", "title": "email",
        "links": {"anchors": []},
        "content": {
            "response_en": "hi", "reviewer_comment_en": "", "atomic_location": {},
            "revised_excerpt_en": "", "notes_core_zh": [], "notes_support_zh": [],
            "evidence": _evidence(),
        },
    }


def _comment_unit(uid: str, reviewer: str, num: str, order: int, **overrides) -> dict:
    content = {
        "strategy": "", "reviewer_comment_zh": "z", "reviewer_comment_en": "rc",
        "reviewer_intent_zh": "i", "response_en": "resp", "response_zh": "rz",
        "revision_location_en": "loc", "atomic_location": {}, "original_excerpt_en": "orig",
        "revised_excerpt_en": "rev", "revised_excerpt_zh": "rz2",
        "modification_actions": [{"action_type": "修改", "reason": "r"}],
        "notes_core_zh": ["n"], "notes_support_zh": ["s"], "evidence": _evidence(),
    }
    content.update(overrides)
    return {
        "unit_id": uid, "order": order, "reviewer": reviewer, "section": "major",
        "comment_number": num, "title": f"{reviewer} c{num}",
        "links": {"anchors": [], "manuscript_unit_ids": [], "si_unit_ids": []},
        "content": content,
    }


def test_render_html_escapes_injection() -> None:
    payload = '<script>evil()</script> & "q"'
    c = _comment_unit(
        "u-001", "Reviewer #1", "1", 1,
        response_en=payload,
        revised_excerpt_en='<script>steal</script>',
    )
    c["title"] = 'T <script>alert(1)</script> & "x"'
    idx = B.build_index([c])
    html = B.render_html('Title & <b>', idx, [_email_unit(), c])

    # Raw injected tags must NOT survive into the HTML.
    assert "<script>evil()</script>" not in html, "response_en <script> leaked unescaped"
    assert "<script>steal</script>" not in html, "revised_excerpt_en <script> leaked"
    assert "<script>alert(1)</script>" not in html, "title <script> leaked"
    # Escaped forms must be present.
    assert "&lt;script&gt;evil()&lt;/script&gt;" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    # The only literal <script> tag is the page's own JS block.
    assert html.count("<script>") == 1, "unexpected literal <script> tag(s) in output"


def test_build_index_ordering() -> None:
    units = [
        _comment_unit("a", "Reviewer #2", "10", 1),
        _comment_unit("b", "Reviewer #2", "2", 2),
        _comment_unit("c", "Reviewer #2", "1", 3),
        _comment_unit("d", "Reviewer #1", "1", 4),
        _comment_unit("e", "Editor", "1", 5),
        _comment_unit("f", "Reviewer #2", "xyz", 6),  # non-numeric -> 999 bucket
    ]
    idx = B.build_index(units)
    labels = [r["label"] for r in idx["toc"]["reviewers"]]
    assert labels == ["Editor", "Reviewer #1", "Reviewer #2"], labels

    r2 = next(r for r in idx["toc"]["reviewers"] if r["label"] == "Reviewer #2")
    items = [it["unit_id"] for sec in r2["sections"] for it in sec["items"]]
    # numeric order 1,2,10 then non-numeric (999) last; not lexicographic "1,10,2"
    assert items == ["c", "b", "a", "f"], items


def test_back_matter_heading_vs_body_word() -> None:
    assert B.is_back_matter_heading_text("References") is True
    assert B.is_back_matter_heading_text("6. Author Contributions") is True
    # A sentence merely containing the word (not leading it) is body text.
    assert B.is_back_matter_heading_text("the references show that X") is False
    assert B.is_back_matter_heading_text("") is False


def test_split_row_inline_heading() -> None:
    row = {
        "paragraph_index": 5,
        "text": "Some ending sentence about results. References Smith J 2020.",
        "style_name": "",
    }
    segs = B.split_row_by_inline_back_matter_headings(row)
    assert len(segs) == 2, [s["text"] for s in segs]
    assert segs[1]["text"].startswith("References"), segs[1]["text"]

    # Start-anchored heading (prefix is empty) is not split — handled downstream.
    row2 = {"paragraph_index": 6, "text": "References Smith J 2020.", "style_name": ""}
    assert len(B.split_row_by_inline_back_matter_headings(row2)) == 1


def test_is_figure_caption() -> None:
    assert B.is_figure_caption("Figure 1: A schematic of X") is True
    assert B.is_figure_caption("Fig. S2. Panel showing Y") is True
    assert B.is_figure_caption("This figure demonstrates Z") is False


if __name__ == "__main__":
    test_render_html_escapes_injection()
    test_build_index_ordering()
    test_back_matter_heading_vs_body_word()
    test_split_row_inline_heading()
    test_is_figure_caption()
    print("OK: build_full_package — escaping, index ordering, back-matter/caption detection")
