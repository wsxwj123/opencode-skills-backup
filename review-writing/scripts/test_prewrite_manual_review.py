#!/usr/bin/env python3
"""逃生口自检：盲检子代理不可用时 --allow-manual-review 的显式人工放行链路。

模拟"盲检 verify 失败/无法跑 → 用 --allow-manual-review 放行 → prewrite_gate 放
第 2 节通行且留痕"的完整链路，断言：
  1) 缺上一节盲检标记 → 默认硬拦 exit 1；
  2) 带 --allow-manual-review "" 空理由 → 仍硬拦（不许无理由放行）；
  3) 带 --allow-manual-review "<理由>" → exit 0，写 manual 标记 + 审计日志留痕；
  4) 再次普通运行 → 天然 exit 0（标记已在），且 warnings 点名"人工放行"。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "prewrite_gate.py"


def _build_project(root: Path) -> None:
    (root / "outline.md").write_text(
        "## 1.1 Background\n## 1.2 Mechanisms\n", encoding="utf-8")
    (root / "state.json").write_text(
        json.dumps({"completed_sections": ["1.1"]}), encoding="utf-8")
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / "synthesis_matrix.json").write_text(
        json.dumps([{"related_sections": ["1.2"], "pmid": "1"}]), encoding="utf-8")
    (root / "drafts").mkdir(exist_ok=True)
    (root / "drafts" / "section_01_01.md").write_text("clean draft.\n", encoding="utf-8")


def _run(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--section", "1.2", "--root", str(root), *extra],
        capture_output=True, text=True)


def test_manual_review_escape_hatch() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_project(root)

        # 1) 默认：缺盲检标记 → 硬拦
        r = _run(root)
        assert r.returncode == 1, f"expected hard-block, got {r.returncode}\n{r.stdout}"
        assert "blind review not passed" in r.stdout, r.stdout

        # 2) 空理由 → 仍硬拦
        r = _run(root, "--allow-manual-review", "   ")
        assert r.returncode == 1, f"empty reason must not pass\n{r.stdout}"
        assert "非空理由" in r.stdout, r.stdout

        # 3) 有理由 → 放行 + 留痕
        r = _run(root, "--allow-manual-review", "平台无 academic-blind-reviewer，人工已审")
        assert r.returncode == 0, f"manual override should pass\n{r.stdout}\n{r.stderr}"
        marker = json.loads((root / ".review_pass" / "1.1.json").read_text(encoding="utf-8"))
        assert marker.get("manual") is True and marker.get("passed") is True, marker
        assert "人工已审" in marker.get("reason", ""), marker
        audit = (root / ".review_pass" / "MANUAL_REVIEW_AUDIT.log").read_text(encoding="utf-8")
        assert "manual_review_override" in audit and "section=1.1" in audit, audit

        # 4) 再次普通运行 → 标记已在 → 天然通过，且点名人工放行
        r = _run(root)
        assert r.returncode == 0, f"marker present should pass\n{r.stdout}"
        payload = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][0])
        assert any("人工放行" in w for w in payload["warnings"]), payload["warnings"]


if __name__ == "__main__":
    test_manual_review_escape_hatch()
    print("OK: manual-review escape hatch — block→reason-gated pass→audited→loud")
