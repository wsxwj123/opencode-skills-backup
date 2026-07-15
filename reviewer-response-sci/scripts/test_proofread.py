#!/usr/bin/env python3
"""Tests for proofread.py check functions + --fail-on exit-code contract.

Unit level (direct calls), each with a positive and negative case:
  - check_misspellings: "teh" flags, "the" does not;
  - check_chinese_punct: a full-width comma in an English-only line flags, an
    ASCII comma does not; a full-width comma in a Chinese-heavy line (>=3 CJK
    chars) is deliberately NOT flagged (reverse guard on the heuristic);
  - check_subsup: bare "H2O2" flags, wrapped "H~2~O~2~" does not.
CLI contract (subprocess) locks --fail-on misspelling,chinese_punct,subsup_bare:
  - bare H2O2 -> exit 1 (subsup_bare hit);
  - a clean file -> exit 0.
Self-contained: direct imports + tempfile *.md for the CLI run.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proofread as P  # noqa: E402

SCRIPT = Path(__file__).resolve().parent / "proofread.py"
FAIL_ON = "misspelling,chinese_punct,subsup_bare"


def _types(issues) -> list[str]:
    return [i["type"] for i in issues]


def test_check_misspellings() -> None:
    assert any(i["type"] == "misspelling" for i in P.check_misspellings("teh cat sat"))
    assert not [i for i in P.check_misspellings("the cat sat") if i["type"] == "misspelling"]


def test_check_chinese_punct() -> None:
    # Full-width comma in an English-only line -> flagged.
    assert any(i["type"] == "chinese_punct" for i in P.check_chinese_punct("We did X，then Y here."))
    # Plain ASCII comma -> clean.
    assert not P.check_chinese_punct("We did X, then Y here.")
    # Reverse guard: full-width comma inside a Chinese-heavy line is intentionally skipped.
    assert not P.check_chinese_punct("我们测量了样本，然后分析结果。")


def test_check_subsup() -> None:
    assert any(i["type"] == "subsup_bare" for i in P.check_subsup("We added H2O2 slowly."))
    # Already markdown-subscripted -> no bare-token complaint.
    assert not [i for i in P.check_subsup("We added H~2~O~2~ slowly.") if i["type"] == "subsup_bare"]


def _run_dir(text: str) -> int:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "a.md").write_text(text, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--manuscript-dir", str(d),
             "--report", str(d / "r.json"), "--fail-on", FAIL_ON],
            capture_output=True, text=True)
        return r.returncode


def test_fail_on_exit_contract() -> None:
    assert _run_dir("We treated cells with H2O2 today.\n") == 1  # subsup_bare hit
    assert _run_dir("We treated the cells with hydrogen peroxide today.\n") == 0  # clean


if __name__ == "__main__":
    test_check_misspellings()
    test_check_chinese_punct()
    test_check_subsup()
    test_fail_on_exit_contract()
    print("OK: proofread — misspelling/chinese_punct/subsup checks + fail-on exit contract")
