#!/usr/bin/env python3
"""Smoke test for delegate_review.py (blind-review verify承重门, fail-closed).

Bidirectional on `verify`:
  - compliant: subagent return marks every checklist id pass with evidence → exit 0, ok:true.
  - violation: a hard item comes back verdict=fail → exit 1, ok:false.
Also exercises `pack` (writes the task package + record, exit 0).
Self-contained: builds a tiny 1-item checklist + return JSON under tempfile.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "delegate_review.py"

_CHECKLIST = {
    "skill": "reviewer-response-sci",
    "gates": {"g1": {"title": "smoke gate", "items": [
        {"id": "A1", "name": "示例项", "check": "文件里应含 X"}
    ]}},
}


def _write(root: Path, name: str, obj) -> Path:
    p = root / name
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return p


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_pack_emits_package() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write(root, "checklist.json", _CHECKLIST)
        target = _write(root, "unit.json", {"unit_id": "c1"})
        r = _run("pack", "--checklist", str(checklist), "--gate", "g1",
                 "--files", str(target), "--workdir", str(root))
        assert r.returncode == 0, f"pack should exit 0\n{r.stderr}"
        assert "盲检任务包" in r.stdout, r.stdout
        assert not list(root.glob(".review_pkg_*.json")), "pack 不应写 .review_pkg 记录(无消费者)"


def test_verify_pass() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write(root, "checklist.json", _CHECKLIST)
        _write(root, ".review_return_g1.json", [{"id": "A1", "verdict": "pass", "evidence": "X 见 unit.json 第 1 行"}])
        r = _run("verify", "--checklist", str(checklist), "--gate", "g1", "--workdir", str(root))
        assert r.returncode == 0, f"expected ok exit 0, got {r.returncode}\n{r.stdout}\n{r.stderr}"
        summary = json.loads(r.stdout)
        assert summary["ok"] is True, summary


def test_verify_fail_is_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write(root, "checklist.json", _CHECKLIST)
        _write(root, ".review_return_g1.json", [{"id": "A1", "verdict": "fail", "evidence": "文件里缺 X"}])
        r = _run("verify", "--checklist", str(checklist), "--gate", "g1", "--workdir", str(root))
        assert r.returncode == 1, f"expected fail-closed exit 1, got {r.returncode}\n{r.stdout}"
        summary = json.loads(r.stdout)
        assert summary["ok"] is False, summary
        assert summary["fails"], summary


if __name__ == "__main__":
    test_pack_emits_package()
    test_verify_pass()
    test_verify_fail_is_fail_closed()
    print("OK: delegate_review — pack emits package, verify pass/fail-closed both hit")
