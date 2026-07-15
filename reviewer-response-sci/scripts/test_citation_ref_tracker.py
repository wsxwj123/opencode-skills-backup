#!/usr/bin/env python3
"""Tests for citation_ref_tracker.py range-expansion + validation branches.

  - extract_citation_ids expands ranges: [1-3] and [5,7] -> {1,2,3,5,7};
    a reversed range [3-1] also yields {1,2,3};
  - a citation [9] with original_ref_count=4 and no registry entry 9 is undefined;
    --fail-on-undefined exits non-zero and the report lists 9;
  - citations present but no citation_registry.json -> WARN, exit 0, report status "warn".
Self-contained: tempfile project + inline unit/registry JSON.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import citation_ref_tracker as C  # noqa: E402

SCRIPT = Path(__file__).resolve().parent / "citation_ref_tracker.py"


def test_extract_ids_expands_ranges() -> None:
    ids = C.extract_citation_ids("See [1-3] and [5,7].")
    assert set(ids) == {1, 2, 3, 5, 7}, ids
    # reversed range still expands to the full inclusive set
    assert set(C.extract_citation_ids("[3-1]")) == {1, 2, 3}


def _write_unit(root: Path, uid: str, text: str) -> None:
    p = root / "units" / f"{uid}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"unit_id": uid, "content": {"response_en": text}},
                            ensure_ascii=False), encoding="utf-8")


def test_undefined_ref_fails_on_flag() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(root, "u-1", "See [1-3] and [5,7] and [9].")
        (root / "citation_registry.json").write_text(
            json.dumps({"original_ref_count": 4,
                        "entries": [{"ref_number": 5}, {"ref_number": 7}]}),
            encoding="utf-8")

        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-root", str(root), "--fail-on-undefined"],
            capture_output=True, text=True)
        assert r.returncode != 0, r.stdout  # 9 is undefined (not in 1..4 nor registry {5,7})

        report = json.loads((root / "logs" / "citation_ref_report.json").read_text(encoding="utf-8"))
        assert report["undefined_refs"] == [9], report


def test_no_registry_warns_exit0() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(root, "u-1", "See [1].")
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-root", str(root)],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stdout
        assert "WARN" in r.stdout, r.stdout
        report = json.loads((root / "logs" / "citation_ref_report.json").read_text(encoding="utf-8"))
        assert report["status"] == "warn", report


if __name__ == "__main__":
    test_extract_ids_expands_ranges()
    test_undefined_ref_fails_on_flag()
    test_no_registry_warns_exit0()
    print("OK: citation_ref_tracker — range expansion, undefined fail-on, no-registry warn")
