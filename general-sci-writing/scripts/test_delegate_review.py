#!/usr/bin/env python3
"""delegate_review.py 双向 smoke test — 自包含、tempfile 造输入、standalone 可跑。

覆盖盲检委托的 pack/verify 两步(fail-closed):
  pack: 读 checklist gate → 打印任务包 + 写 .review_pkg_<gate>.json，exit 0
  verify 合规: 每项 verdict=pass 且附证据 → exit 0，并落 .review_pass/<section>.json
  verify 违规1: verdict=fail → exit 1(fail-closed)
  verify 违规2: 漏裁一项 → exit 1(缺漏未裁决)
  verify 违规3: pass 但证据为空 → exit 1(空证据视为未裁决)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "delegate_review.py"

CHECKLIST = {
    "skill": "general-sci-writing",
    "gates": {
        "g1": {
            "title": "Smoke Gate",
            "items": [
                {"id": "A1", "name": "citations", "check": "每句有据"},
                {"id": "A2", "name": "no_placeholder", "check": "无占位符"},
            ],
        }
    },
}


def _write_checklist(root: Path) -> Path:
    p = root / "checklist.json"
    p.write_text(json.dumps(CHECKLIST, ensure_ascii=False), encoding="utf-8")
    return p


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=str(root))


def _verify(root: Path, checklist: Path, section: str = "3.1") -> subprocess.CompletedProcess:
    return _run(root, "verify", "--checklist", str(checklist), "--gate", "g1",
                "--workdir", str(root), "--section", section)


def test_delegate_review_bidirectional() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write_checklist(root)

        # --- pack → exit 0 + 写任务包记录 ---
        target = root / "manuscripts_section.md"
        target.write_text("draft content\n", encoding="utf-8")
        r = _run(root, "pack", "--checklist", str(checklist), "--gate", "g1",
                 "--files", str(target), "--workdir", str(root))
        assert r.returncode == 0, f"pack should exit 0\n{r.stderr}"
        assert (root / ".review_pkg_g1.json").exists(), "pack must write pkg record"
        return_path = root / ".review_return_g1.json"

        # --- verify 合规: 全 pass + 证据 → exit 0，落盘通过标记 ---
        return_path.write_text(json.dumps([
            {"id": "A1", "verdict": "pass", "evidence": "L3 有引文 [1]"},
            {"id": "A2", "verdict": "pass", "evidence": "grep 无 CITE_PENDING"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(root, checklist)
        assert r.returncode == 0, f"all-pass should verify\n{r.stdout}\n{r.stderr}"
        marker = json.loads((root / ".review_pass" / "3.1.json").read_text(encoding="utf-8"))
        assert marker.get("passed") is True, marker

        # --- verify 违规1: 有 fail → exit 1 ---
        return_path.write_text(json.dumps([
            {"id": "A1", "verdict": "fail", "evidence": "L5 无据"},
            {"id": "A2", "verdict": "pass", "evidence": "干净"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(root, checklist)
        assert r.returncode == 1, f"a fail must block\n{r.stdout}"

        # --- verify 违规2: 漏裁 A2 → exit 1 ---
        return_path.write_text(json.dumps([
            {"id": "A1", "verdict": "pass", "evidence": "ok"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(root, checklist)
        assert r.returncode == 1, f"missing verdict must block\n{r.stdout}"

        # --- verify 违规3: pass 但空证据 → exit 1 ---
        return_path.write_text(json.dumps([
            {"id": "A1", "verdict": "pass", "evidence": ""},
            {"id": "A2", "verdict": "pass", "evidence": "ok"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(root, checklist)
        assert r.returncode == 1, f"empty evidence on pass must block\n{r.stdout}"


if __name__ == "__main__":
    test_delegate_review_bidirectional()
    print("OK: delegate_review — pack ok; verify pass; fail/missing/empty-evidence blocks")
