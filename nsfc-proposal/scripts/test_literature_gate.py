#!/usr/bin/env python3
"""Smoke test：nsfc gate-check 的总量文献硬门（citation_targets.min_total）。

自包含、纯 assert、tempfile 造合成项目，不改被测脚本。
只验证新接上的总量门逻辑（与引文核验/矩阵/评审等其余门解耦）：
  - literature_index 总量 < min_total → literature 门 ok=False，整体 ok=False，CLI exit≠0
  - 总量 ≥ min_total → literature 门 ok=True
总量门只数条目、不依赖联网核验，故用 --offline 跑。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "state_manager.py"


def _init(root: Path) -> None:
    subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), "init"],
                   capture_output=True, text=True, check=True)


def _write_index(root: Path, n: int) -> None:
    entries = [
        {"ref_number": i, "title": f"Paper {i}", "authors": ["A"], "year": 2024,
         "journal": "J", "used_in_sections": ["P1_立项依据"]}
        for i in range(1, n + 1)
    ]
    (root / "data" / "literature_index.json").write_text(
        json.dumps({"metadata": {"verification_status": "pending"}, "entries": entries},
                   ensure_ascii=False), encoding="utf-8")


def _gate(root: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "gate-check", "--offline"],
        capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


def main() -> int:
    # 场景 A：总量 10 < 30 → 硬门拦截
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _init(root)
        _write_index(root, 10)
        code, rep = _gate(root)
        assert rep["literature"]["ok"] is False, f"总量10应不过门: {rep['literature']}"
        assert rep["literature"]["total_count"] == 10, rep["literature"]
        assert rep["literature"]["min_total"] == 30, rep["literature"]
        assert rep["ok"] is False, "总量不足整体应失败"
        assert code != 0, f"总量不足 CLI 应 exit≠0，实际 {code}"

    # 场景 B：总量 30 ≥ 30 → 总量门通过
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _init(root)
        _write_index(root, 30)
        _, rep = _gate(root)
        assert rep["literature"]["ok"] is True, f"总量30应过门: {rep['literature']}"
        assert rep["literature"]["total_count"] == 30, rep["literature"]

    print("test_literature_gate: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
