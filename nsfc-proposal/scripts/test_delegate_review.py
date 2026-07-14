#!/usr/bin/env python3
"""Smoke test：nsfc delegate_review.py 盲检委托（双向），不改被测脚本。

自包含、纯 assert、tempfile 造合成 checklist + 子代理返回。
覆盖 pack（生成任务包 + 记录）、verify 的 fail-closed 语义、以及 verify
通过带 --section 时的 .review_pass 标记落盘。

双向断言：
  合规返回（每项 pass 且附证据）→ verify exit 0 + 落盘通过标记；
  违规（缺裁决 / verdict=fail / 空证据）→ verify exit 1。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "delegate_review.py"

CHECKLIST = {
    "skill": "nsfc-test",
    "gates": {
        "g": {
            "title": "测试闸口",
            "items": [
                {"id": "A1", "name": "占位符清零", "check": "无 CITE_PENDING"},
                {"id": "A2", "name": "字数达标", "check": "≥100 字"},
            ],
        }
    },
}


def _write_checklist(root: Path) -> Path:
    p = root / "checklist.json"
    p.write_text(json.dumps(CHECKLIST, ensure_ascii=False), encoding="utf-8")
    return p


def _verify(checklist: Path, root: Path, ret: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "verify",
         "--checklist", str(checklist), "--gate", "g",
         "--return", str(ret), "--workdir", str(root), *extra],
        capture_output=True, text=True)


def test_pack_writes_record() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write_checklist(root)
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "pack",
             "--checklist", str(checklist), "--gate", "g",
             "--files", "sections/x.md", "--workdir", str(root)],
            capture_output=True, text=True)
        assert r.returncode == 0, f"pack should exit 0\n{r.stderr}"
        assert not list(root.glob(".review_pkg_*.json")), "pack 不应写 .review_pkg 记录(无消费者)"
        assert "盲检任务包" in r.stdout and "A1" in r.stdout and "A2" in r.stdout, r.stdout


def test_verify_compliant_passes_and_writes_marker() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write_checklist(root)
        ret = root / "return.json"
        ret.write_text(json.dumps([
            {"id": "A1", "verdict": "pass", "evidence": "全文无占位符"},
            {"id": "A2", "verdict": "pass", "evidence": "共 320 字"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(checklist, root, ret, "--section", "P1", "--root", str(root))
        assert r.returncode == 0, f"compliant return should pass\n{r.stdout}\n{r.stderr}"
        summary = json.loads(r.stdout)
        assert summary["ok"] is True and not summary["fails"], summary
        marker = json.loads((root / ".review_pass" / "P1.json").read_text(encoding="utf-8"))
        assert marker["passed"] is True and marker["section"] == "P1", marker


def test_verify_missing_item_blocks() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write_checklist(root)
        ret = root / "return.json"
        ret.write_text(json.dumps([
            {"id": "A1", "verdict": "pass", "evidence": "ok"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(checklist, root, ret)
        assert r.returncode == 1, f"missing A2 must fail-closed\n{r.stdout}"
        assert "A2" in r.stdout, r.stdout


def test_verify_fail_verdict_blocks() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write_checklist(root)
        ret = root / "return.json"
        ret.write_text(json.dumps([
            {"id": "A1", "verdict": "fail", "evidence": "发现 CITE_PENDING"},
            {"id": "A2", "verdict": "pass", "evidence": "ok"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(checklist, root, ret)
        assert r.returncode == 1, f"verdict=fail must block\n{r.stdout}"
        summary = json.loads(r.stdout)
        assert summary["fails"], summary


def test_verify_empty_evidence_blocks() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = _write_checklist(root)
        ret = root / "return.json"
        ret.write_text(json.dumps([
            {"id": "A1", "verdict": "pass", "evidence": ""},
            {"id": "A2", "verdict": "pass", "evidence": "ok"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(checklist, root, ret)
        assert r.returncode == 1, f"empty evidence must block (no rubber-stamp)\n{r.stdout}"
        assert "evidence" in r.stdout, r.stdout


if __name__ == "__main__":
    test_pack_writes_record()
    test_verify_compliant_passes_and_writes_marker()
    test_verify_missing_item_blocks()
    test_verify_fail_verdict_blocks()
    test_verify_empty_evidence_blocks()
    print("OK: delegate_review smoke — pack records; verify pass→exit0+marker, fail/missing/empty→exit1")
