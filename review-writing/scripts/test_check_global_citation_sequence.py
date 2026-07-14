#!/usr/bin/env python3
"""Smoke test: check_global_citation_sequence.py 全局引用编号连续性门禁。

该脚本扫描 drafts/ 下所有 .md,抽取形如 [1][2,3][4-6] 的引用编号,若编号区间
[min..max] 内出现跳号(缺失某个编号)→ 打 [CRITICAL] 并 SystemExit(2) 拦截;
连续无跳号 → [OK] exit 0 放行。

双向断言:
  1) 跳号 drafts([1][2][4] 缺 3)→ exit != 0(拦截);
  2) 连续 drafts([1][2][3])→ exit 0(放行)。
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_global_citation_sequence.py"


def _run(drafts_dir: Path) -> subprocess.CompletedProcess:
    # cwd=脚本目录,使其能 import 同目录的 citation_utils
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--drafts-dir", str(drafts_dir)],
        capture_output=True, text=True, cwd=str(SCRIPT.parent))


def test_gap_blocks_and_continuous_passes() -> None:
    # 1) 跳号 → 拦截
    with tempfile.TemporaryDirectory() as td:
        drafts = Path(td)
        (drafts / "s1.md").write_text("First claim [1]. Second [2].\n", encoding="utf-8")
        (drafts / "s2.md").write_text("Later claim jumps to [4].\n", encoding="utf-8")
        r = _run(drafts)
        assert r.returncode != 0, f"跳号(缺3)必须拦截,got exit {r.returncode}\n{r.stdout}"
        assert "CRITICAL" in r.stdout and "3" in r.stdout, r.stdout

    # 2) 连续 → 放行
    with tempfile.TemporaryDirectory() as td:
        drafts = Path(td)
        (drafts / "s1.md").write_text("First [1]. Second [2].\n", encoding="utf-8")
        (drafts / "s2.md").write_text("Third claim [3].\n", encoding="utf-8")
        r = _run(drafts)
        assert r.returncode == 0, f"连续编号必须放行,got exit {r.returncode}\n{r.stdout}\n{r.stderr}"
        assert "[OK]" in r.stdout, r.stdout


if __name__ == "__main__":
    test_gap_blocks_and_continuous_passes()
    print("OK: check_global_citation_sequence — 跳号拦截→连续放行")
