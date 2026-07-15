#!/usr/bin/env python3
"""test_manuscript_index.py — manuscript_index.py 交叉索引抽取回归测试。

固化：
  1. looks_like_reference_entry：DOI / PMID / Vancouver 编号条目 → True；
     正文散文段 → False。
  2. strip_list_prefix：去掉 `- [1] ` 的列表前缀后，编号仍能被 REF_NUMBER_PREFIX
     解析出 "1"。
  3. md 分支端到端：合成小 md 稿（正文引用 [1]/[2,3] + `## References` 下 `- [n]`
     列表条目）→ reference_index.json 抽出的 ref 编号集合 == {1,2,3}，
     total_refs=3、orphans=0。

纯函数用 import；md 端到端用 subprocess（避开 docx 分支的 python-docx 依赖）。
纯 assert、无 pytest、tempfile 自包含。运行：python3 test_manuscript_index.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPTS_DIR / "manuscript_index.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mi = _load("manuscript_index")


# ---- looks_like_reference_entry ----

def test_doi_entry_true():
    assert mi.looks_like_reference_entry("Smith J. Nature. doi: 10.1000/abc")


def test_pmid_entry_true():
    assert mi.looks_like_reference_entry("Doe A. Cell. PMID: 12345678")


def test_vancouver_entry_true():
    assert mi.looks_like_reference_entry("[1] Smith J. A study. Nature. 2020;12:3-5.")


def test_prose_false():
    assert not mi.looks_like_reference_entry(
        "We found that the treatment worked well in mice."
    )


# ---- strip_list_prefix ----

def test_strip_list_prefix_then_number():
    stripped = mi.strip_list_prefix("- [1] Smith J. 2020.")
    assert stripped == "[1] Smith J. 2020.", stripped
    m = mi.REF_NUMBER_PREFIX_RE.match(stripped)
    assert m and m.group(1) == "1", stripped


# ---- md 端到端 ----

def test_md_reference_index():
    md = (
        "# Introduction\n\n"
        "We build on prior work [1] and later results [2,3].\n\n"
        "## References\n\n"
        "- [1] Smith J. A study. Nature. 2020. doi:10.1000/abc\n"
        "- [2] Doe A. Another finding. Cell. 2021.\n"
        "- [3] Roe B. Third study. Science. 2019.\n"
    )
    with tempfile.TemporaryDirectory() as d:
        mpath = Path(d) / "m.md"
        mpath.write_text(md, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--manuscript", str(mpath), "--project-root", d],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        idx = json.loads((Path(d) / "reference_index.json").read_text(encoding="utf-8"))
    nums = sorted(e["ref_number"] for e in idx["entries"])
    assert nums == [1, 2, 3], nums
    assert idx["summary"]["total_refs"] == 3, idx["summary"]
    assert idx["summary"]["orphans"] == 0, idx["summary"]


if __name__ == "__main__":
    test_doi_entry_true()
    test_pmid_entry_true()
    test_vancouver_entry_true()
    test_prose_false()
    test_strip_list_prefix_then_number()
    test_md_reference_index()
    print("ALL PASS: test_manuscript_index")
