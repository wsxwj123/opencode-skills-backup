#!/usr/bin/env python3
"""Tests for unit_glob.py schema-filtered loader.

The shared loader must never silently drop a legitimate reviewer-response unit,
yet must skip (with a stderr warning) foreign or unreadable JSON:
  - a valid reviewer-response unit (has unit_id) is yielded;
  - a revise-sci-style file (comment_id, no unit_id) is skipped;
  - malformed JSON is skipped;
  - the legitimate unit is never lost.
Self-contained: tempfile dir with three JSON files.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from unit_glob import iter_units, load_units  # noqa: E402


def test_filters_foreign_and_broken_keeps_valid() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "good.json").write_text('{"unit_id": "u-1", "content": {}}', encoding="utf-8")
        (d / "revise.json").write_text('{"comment_id": "c-1"}', encoding="utf-8")  # no unit_id
        (d / "broken.json").write_text("{not valid json", encoding="utf-8")

        units = load_units(d)
        ids = [u["unit_id"] for u in units]
        assert ids == ["u-1"], ids  # only the legitimate unit survives

        paths = [p.name for p, _ in iter_units(d)]
        assert paths == ["good.json"], paths


def test_empty_dir_yields_nothing() -> None:
    with tempfile.TemporaryDirectory() as td:
        assert load_units(Path(td)) == []


if __name__ == "__main__":
    test_filters_foreign_and_broken_keeps_valid()
    test_empty_dir_yields_nothing()
    print("OK: unit_glob — keeps valid unit, skips foreign/broken, never drops legit unit")
