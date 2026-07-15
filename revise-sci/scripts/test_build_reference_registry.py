#!/usr/bin/env python3
"""Tests for build_reference_registry.py parsing + citation-gap detection.

Guards against two silent-data-loss failure modes: dropping real reference entries
(bib/ris parse, entry recognition, section split) and mis-detecting which in-text
citation numbers are missing from the reference source.

Pure-import tests where possible; bib/ris use tempfile. Standalone:
`python3 test_build_reference_registry.py`.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import build_reference_registry as b  # noqa: E402


# --- looks_like_reference_entry: reference-shaped lines accepted, prose rejected ---
def test_looks_like_reference_entry_accepts_doi_and_etal():
    assert b.looks_like_reference_entry("Smith J. A study. Nature. DOI: 10.1000/x")
    assert b.looks_like_reference_entry("Smith J, et al. Some findings 2019.")


def test_looks_like_reference_entry_rejects_prose():
    assert not b.looks_like_reference_entry("the quick brown fox jumps")
    assert not b.looks_like_reference_entry("")


# --- split_reference_section: isolate the References block from body ---
def test_split_reference_section_finds_heading_and_entries():
    text = "Intro paragraph.\n\n## References\n\n1. Smith J. Nature. 2019.\n2. Doe A. Cell. 2020."
    body, refs, found = b.split_reference_section(text)
    assert found is True
    assert len(refs) == 2, refs
    assert "Intro paragraph." in body and "Smith" not in body


def test_split_reference_section_absent():
    body, refs, found = b.split_reference_section("Just body text, no references at all.")
    assert found is False and refs == []


# --- detect_cited_numbers: expand ranges/lists, ignore duplicates ---
def test_detect_cited_numbers_expands_ranges_and_dedupes():
    assert b.detect_cited_numbers("We show X [1,3] and Y [5-7] and again [3].") == [1, 3, 5, 6, 7]


# --- merge_missing_numeric_references: import only genuinely-missing numbers ---
def test_merge_missing_numeric_references_fills_only_missing():
    current = [{"reference_number": 1, "raw_text": "A"}, {"reference_number": 3, "raw_text": "C"}]
    source = [{"reference_number": 2, "raw_text": "B"}, {"reference_number": 3, "raw_text": "C-source"}]
    merged, imported = b.merge_missing_numeric_references(current, source, [2, 3])
    assert imported == [2], imported  # 3 already present -> not overwritten
    assert [e["reference_number"] for e in merged] == [1, 2, 3]
    # existing entry 3 kept as-is, not replaced by source
    assert next(e for e in merged if e["reference_number"] == 3)["raw_text"] == "C"


def test_merge_missing_numeric_references_noop_when_none_missing():
    current = [{"reference_number": 1, "raw_text": "A"}]
    merged, imported = b.merge_missing_numeric_references(current, [], [])
    assert imported == [] and merged is current


# --- bib/ris parsing: exact entry count, no silent drop ---
def test_parse_seed_bib_counts_entries():
    bib = (
        "@article{a1, author={Smith, J}, title={First title}, journal={Nature}, year={2019}}\n"
        "@article{a2, author={Doe, A}, title={Second title}, journal={Cell}, year={2020}}\n"
    )
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.bib"
        p.write_text(bib, encoding="utf-8")
        lines = b.parse_seed_bib(p)
        assert len(lines) == 2, lines
        assert any("First title" in ln for ln in lines)


def test_parse_seed_ris_counts_records():
    ris = (
        "TY  - JOUR\nAU  - Smith, J\nTI  - First RIS title\nJO  - Nature\nPY  - 2019\nER  - \n"
        "TY  - JOUR\nAU  - Doe, A\nTI  - Second RIS title\nJO  - Cell\nPY  - 2020\nER  - \n"
    )
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.ris"
        p.write_text(ris, encoding="utf-8")
        lines = b.parse_seed_ris(p)
        assert len(lines) == 2, lines
        assert any("First RIS title" in ln for ln in lines)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: reference registry entry/section detection, cited-number gaps, bib/ris counts")
