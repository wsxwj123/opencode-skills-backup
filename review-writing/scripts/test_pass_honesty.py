#!/usr/bin/env python3
"""Regression guard: 每个机器门禁脚本在 PASS 分支都必须打印"形式层≠内容层"的
诚实说明，防止 PASS 给出虚假安全感（被误当成论点/科学价值已核验）。

只做源码级存在性检查（无 fixture）：删掉任一诚实行即失败。behavior 与源码等价，
因为这些说明是内联 print/stderr.write 常量。
"""
from __future__ import annotations

from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

# 脚本 -> 该脚本 PASS 诚实说明里必须出现的稳定标记（措辞可微调，标记不动）
HONESTY_MARKERS = {
    "proofread.py": ("PROOFREAD: PASS", "未自动核验"),
    "citation_guard.py": ("CITATION_GUARD: PASS", "未核验"),
    "validate_citations.py": ("PASS 仅覆盖", "未核验"),
    "prewrite_gate.py": ("PREWRITE_GATE: PASS", "未自动核验"),
}


def test_pass_branch_has_honesty_note():
    for script, markers in HONESTY_MARKERS.items():
        src = (SCRIPTS_DIR / script).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in src, f"{script} 缺 PASS 诚实说明标记: {marker!r}"


if __name__ == "__main__":
    test_pass_branch_has_honesty_note()
    print("OK: 4 个门禁脚本 PASS 分支均含诚实说明")
