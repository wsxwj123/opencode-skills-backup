#!/usr/bin/env python3
"""test_delegate_review.py — reviewer-simulator 盲检委托 pack/verify 烟测。

固化 delegate_review.py 的 fail-closed 契约:
  pack   读 checklist 指定 gate → 打印盲检任务包(含每个 item id),exit 0。
  verify 校验子代理返回:
    - 每个硬项(未标 severity)必须被裁决、verdict∈{pass,fail,na}、evidence 非空。
    - 缺漏硬项 / verdict=fail / 硬项空证据 → exit 1(阻断"声明完成")。
    - 软项(severity=soft)fail/缺裁决/空证据只汇报不阻断退出码。

双向:合规返回 → exit 0 + ok=true;违规返回 → exit≠0。

纯 assert、无 pytest、自包含合成输入(tempfile)。验证用 subprocess.run(...).returncode。
运行:python3 test_delegate_review.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "delegate_review.py"

# 最小 checklist:两个硬项 + 一个软项,自包含不依赖 references/。
CHECKLIST = {
    "skill": "reviewer-simulator",
    "gates": {
        "g1": {
            "title": "烟测 gate",
            "items": [
                {"id": "H1", "name": "硬项一", "check": "check-1"},
                {"id": "H2", "name": "硬项二", "check": "check-2"},
                {"id": "S1", "name": "软项", "check": "check-s", "severity": "soft"},
            ],
        }
    },
}


def _setup(d: Path) -> tuple[Path, Path]:
    checklist = d / "checklist.json"
    checklist.write_text(json.dumps(CHECKLIST, ensure_ascii=False), encoding="utf-8")
    target = d / "unit.json"
    target.write_text("{}", encoding="utf-8")
    return checklist, target


def _pack(d: Path, checklist: Path, target: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "pack",
         "--checklist", str(checklist), "--gate", "g1",
         "--files", str(target), "--workdir", str(d)],
        capture_output=True, text=True,
    )


def _verify(d: Path, checklist: Path, returned: list) -> subprocess.CompletedProcess:
    (d / ".review_return_g1.json").write_text(
        json.dumps(returned, ensure_ascii=False), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "verify",
         "--checklist", str(checklist), "--gate", "g1", "--workdir", str(d)],
        capture_output=True, text=True,
    )


def test_pack_lists_items():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        checklist, target = _setup(d)
        r = _pack(d, checklist, target)
        assert r.returncode == 0, r.stderr
        assert "H1" in r.stdout and "H2" in r.stdout, r.stdout
        # pack 不再落盘记录文件(无消费者)
        assert not list(d.glob(".review_pkg_*.json")), "pack 不应写 .review_pkg 记录"


def test_verify_all_hard_pass_ok():
    # 两个硬项都 pass+evidence;软项缺裁决只是 soft_flag,不阻断。
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        checklist, target = _setup(d)
        returned = [
            {"id": "H1", "verdict": "pass", "evidence": "证据1"},
            {"id": "H2", "verdict": "pass", "evidence": "证据2"},
        ]
        r = _verify(d, checklist, returned)
        assert r.returncode == 0, r.stdout + r.stderr
        assert '"ok": true' in r.stdout, r.stdout


def test_verify_missing_hard_item_fails():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        checklist, target = _setup(d)
        returned = [{"id": "H1", "verdict": "pass", "evidence": "证据1"}]  # 缺 H2
        r = _verify(d, checklist, returned)
        assert r.returncode == 1, r.stdout
        assert '"ok": false' in r.stdout, r.stdout


def test_verify_hard_fail_blocks():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        checklist, target = _setup(d)
        returned = [
            {"id": "H1", "verdict": "pass", "evidence": "证据1"},
            {"id": "H2", "verdict": "fail", "evidence": "有问题"},
        ]
        r = _verify(d, checklist, returned)
        assert r.returncode == 1, r.stdout


def test_verify_empty_evidence_on_hard_blocks():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        checklist, target = _setup(d)
        returned = [
            {"id": "H1", "verdict": "pass", "evidence": "证据1"},
            {"id": "H2", "verdict": "pass", "evidence": ""},  # 空证据
        ]
        r = _verify(d, checklist, returned)
        assert r.returncode == 1, r.stdout


if __name__ == "__main__":
    test_pack_lists_items()
    test_verify_all_hard_pass_ok()
    test_verify_missing_hard_item_fails()
    test_verify_hard_fail_blocks()
    test_verify_empty_evidence_on_hard_blocks()
    print("ALL PASS: test_delegate_review")
