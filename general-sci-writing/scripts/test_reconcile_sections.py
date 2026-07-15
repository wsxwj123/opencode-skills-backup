#!/usr/bin/env python3
"""cross_section_consistency.py 的 section 对账门禁回归测试 — standalone 可跑。

test_format_contract 覆盖的是数值漂移（B1/B2）；本文件补**从未被测**的
--reconcile-sections 逻辑：storyline.json 的 section_id ↔ manuscripts/*.md 双向对账。
门禁语义：全齐 exit 0；漏建/孤儿 exit 1。跑偏会让"漏写一节"或"多出野文件"静默。
  reconcile_sections:
    - 一一对应 → ok True
    - storyline 有、稿子缺 → missing_in_manuscripts（漏建）
    - 稿子有、storyline 无 → orphan_manuscripts（孤儿）
    - _file_covers_section 变体匹配（results_3.1 ↔ 04_results_3.1.md 文件名边界）
  CLI --reconcile-sections：齐→rc0，缺→rc1

Run: python3 test_reconcile_sections.py   (rc=0 = 全过)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cross_section_consistency as X

SCRIPT = Path(__file__).resolve().parent / "cross_section_consistency.py"


def _project(td, sections, files):
    """sections: list[str] → storyline ids; files: {name: content}."""
    root = Path(td)
    (root / "manuscripts").mkdir()
    (root / "storyline.json").write_text(
        json.dumps({"sections": [{"id": s} for s in sections]}), encoding="utf-8")
    for name, content in files.items():
        (root / "manuscripts" / name).write_text(content, encoding="utf-8")
    return str(root)


def test_reconcile_matched():
    with tempfile.TemporaryDirectory() as td:
        root = _project(
            td, ["intro", "results_3.1"],
            {"02_intro.md": "# Intro\nbody\n",
             "04_results_3.1.md": "# Results\nresults_3.1 body\n"})
        r = X.reconcile_sections(root)
        assert r["ok"] is True, r
        assert r["missing_in_manuscripts"] == [] and r["orphan_manuscripts"] == []


def test_reconcile_missing_section():
    # storyline 列了 results_3.1 但没有对应稿子 → 漏建
    with tempfile.TemporaryDirectory() as td:
        root = _project(
            td, ["intro", "results_3.1"],
            {"02_intro.md": "# Intro\nbody\n"})
        r = X.reconcile_sections(root)
        assert r["ok"] is False, r
        assert "results_3.1" in r["missing_in_manuscripts"], r


def test_reconcile_orphan_file():
    # 稿子里有 99_extra.md，不匹配任何 storyline section → 孤儿
    with tempfile.TemporaryDirectory() as td:
        root = _project(
            td, ["intro"],
            {"02_intro.md": "# Intro\nbody\n",
             "99_extra.md": "# Extra\nunrelated ghost content\n"})
        r = X.reconcile_sections(root)
        assert r["ok"] is False, r
        assert "99_extra.md" in r["orphan_manuscripts"], r
        assert r["missing_in_manuscripts"] == [], "intro 有对应稿子，不应算漏建"


def test_file_covers_section_variants():
    # 文件名分隔符变体：results_3.1 应匹配 04_results_3.1.md（点/下划线互换）
    assert X._file_covers_section("04_results_3.1.md", "", "results_3.1") is True
    assert X._file_covers_section("04_results_3_1.md", "", "results_3.1") is True
    # 正文含 section_id 字符串也算覆盖（文件名不含时）
    assert X._file_covers_section("random.md", "this covers results_3.1 inline", "results_3.1") is True
    # 完全不相关 → 不覆盖
    assert X._file_covers_section("random.md", "nothing relevant", "results_3.1") is False


def test_cli_exit_codes():
    with tempfile.TemporaryDirectory() as td:
        root = _project(
            td, ["intro"], {"02_intro.md": "# Intro\nbody\n"})
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", root, "--reconcile-sections"],
            capture_output=True, text=True)
        assert r.returncode == 0, f"齐应 rc0\n{r.stdout}\n{r.stderr}"
        # 加一个孤儿文件 → rc1
        (Path(root) / "manuscripts" / "77_ghost.md").write_text(
            "# Ghost\nunrelated\n", encoding="utf-8")
        r2 = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", root, "--reconcile-sections"],
            capture_output=True, text=True)
        assert r2.returncode == 1, f"有孤儿应 rc1\n{r2.stdout}\n{r2.stderr}"


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
