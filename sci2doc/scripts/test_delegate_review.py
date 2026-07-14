#!/usr/bin/env python3
"""delegate_review.py 冒烟测试 —— pack/verify 双向 + 通过标记落盘。

pack:  读 checklist 的 gate,打印任务包(不落盘记录文件)。
verify(fail-closed):
  - 全 pass + 附证据 → exit 0,且 --section 时在 <root>/.review_pass/<section>.json 落盘 passed:true
  - 硬项 verdict=fail → exit 1(不落标记)
  - 软项(severity=soft) fail → 不阻断 exit 0(soft_flags 记录)
  - 硬项缺裁决 → exit 1

standalone: `python3 test_delegate_review.py`。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "delegate_review.py"

CHECKLIST = {
    "skill": "test",
    "gates": {
        "g1": {
            "title": "冒烟 gate",
            "items": [
                {"id": "A1", "name": "硬项", "check": "必过"},
                {"id": "A2", "name": "软项", "check": "可失败", "severity": "soft"},
            ],
        }
    },
}


def _write_checklist(root: Path) -> Path:
    p = root / "checklist.json"
    p.write_text(json.dumps(CHECKLIST, ensure_ascii=False), encoding="utf-8")
    return p


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


def _write_return(root: Path, gate: str, entries: list) -> Path:
    p = root / f".review_return_{gate}.json"
    p.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return p


def test_pack_writes_record() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cl = _write_checklist(root)
        f = root / "draft.md"
        f.write_text("正文\n", encoding="utf-8")
        r = _run("pack", "--checklist", str(cl), "--gate", "g1",
                 "--files", str(f), "--workdir", str(root))
        assert r.returncode == 0, f"pack failed\n{r.stderr}"
        assert not list(root.glob(".review_pkg_*.json")), "pack 不应写 .review_pkg 记录(无消费者)"
        assert "盲检任务包" in r.stdout and "A1" in r.stdout and "A2" in r.stdout, r.stdout


def test_verify_all_pass_writes_marker() -> None:
    """通过方向:全 pass → exit 0 + 落 .review_pass/<section>.json。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cl = _write_checklist(root)
        _write_return(root, "g1", [
            {"id": "A1", "verdict": "pass", "evidence": "文件第3行"},
            {"id": "A2", "verdict": "pass", "evidence": "无违规"},
        ])
        r = _run("verify", "--checklist", str(cl), "--gate", "g1",
                 "--workdir", str(root), "--section", "2.1", "--root", str(root))
        assert r.returncode == 0, f"all-pass verify must exit 0\n{r.stdout}\n{r.stderr}"
        marker = json.loads((root / ".review_pass" / "2.1.json").read_text(encoding="utf-8"))
        assert marker.get("passed") is True and marker.get("section") == "2.1", marker


def test_verify_hard_fail_blocks_no_marker() -> None:
    """拦截方向:硬项 fail → exit 1,不落标记。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cl = _write_checklist(root)
        _write_return(root, "g1", [
            {"id": "A1", "verdict": "fail", "evidence": "缺证据链"},
            {"id": "A2", "verdict": "pass", "evidence": "ok"},
        ])
        r = _run("verify", "--checklist", str(cl), "--gate", "g1",
                 "--workdir", str(root), "--section", "2.1", "--root", str(root))
        assert r.returncode == 1, f"hard fail must exit 1\n{r.stdout}"
        assert not (root / ".review_pass" / "2.1.json").exists(), "must NOT write marker on fail"


def test_verify_soft_fail_does_not_block() -> None:
    """软项 fail 不阻断:exit 0 且 soft_flags 记录。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cl = _write_checklist(root)
        _write_return(root, "g1", [
            {"id": "A1", "verdict": "pass", "evidence": "ok"},
            {"id": "A2", "verdict": "fail", "evidence": "软项问题"},
        ])
        r = _run("verify", "--checklist", str(cl), "--gate", "g1", "--workdir", str(root))
        assert r.returncode == 0, f"soft fail must not block\n{r.stdout}"
        summary = json.loads(r.stdout)
        assert summary["ok"] is True and summary["soft_flags"], summary


def test_verify_missing_hard_item_blocks() -> None:
    """硬项缺裁决 → exit 1。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cl = _write_checklist(root)
        _write_return(root, "g1", [
            {"id": "A2", "verdict": "pass", "evidence": "ok"},
        ])
        r = _run("verify", "--checklist", str(cl), "--gate", "g1", "--workdir", str(root))
        assert r.returncode == 1, f"missing hard item must exit 1\n{r.stdout}"
        summary = json.loads(r.stdout)
        assert any("A1" in p for p in summary["problems"]), summary


if __name__ == "__main__":
    test_pack_writes_record()
    test_verify_all_pass_writes_marker()
    test_verify_hard_fail_blocks_no_marker()
    test_verify_soft_fail_does_not_block()
    test_verify_missing_hard_item_blocks()
    print("OK: delegate_review pack/verify — pass→marker / hard-fail→block / soft-fail→pass / missing→block (bidirectional)")
