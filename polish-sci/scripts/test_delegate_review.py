#!/usr/bin/env python3
"""Smoke test for polish-sci delegate_review.py (盲检委托 pack/verify 双向).

覆盖:
- pack: 读真实 dod_checklist.json 的 polish-dod gate → 打印盲检任务包
  (含角色框定 + 待检文件 + 逐项清单 + 返回格式,不落盘记录文件),
  并在 stderr 打出 RETURN_PATH=<约定返回路径>。
- verify(全 pass):每个硬项 pass+证据非空 → exit 0(不阻断)。
- verify(遇 fail):某硬项 verdict=fail → exit≠0,阻断"声明本节完成"。

自包含:用 tempfile 造输入,直接 assert;standalone `python3 test_delegate_review.py` 可跑。
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
CHECKLIST = ROOT / "references" / "dod_checklist.json"
GATE = "polish-dod"
SCRIPT = SCRIPTS / "delegate_review.py"


def _run(args: list[str], workdir: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=workdir,
    )


def _gate_item_ids() -> list[str]:
    data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    return [it["id"] for it in data["gates"][GATE]["items"]]


def test_pack_produces_package_and_return_path(tmp: Path) -> None:
    unit = tmp / "u.json"
    unit.write_text("{}", encoding="utf-8")
    r = _run(
        ["pack", "--checklist", str(CHECKLIST), "--gate", GATE,
         "--files", str(unit), "--workdir", str(tmp)],
        str(tmp),
    )
    assert r.returncode == 0, r.stderr
    # 任务包关键结构
    assert "盲检任务包" in r.stdout
    assert "你的角色" in r.stdout and "独立审稿子代理" in r.stdout
    assert str(unit) in r.stdout
    for iid in _gate_item_ids():
        assert iid in r.stdout, f"清单项 {iid} 未出现在任务包"
    # pack 不再落盘记录文件(无消费者)
    assert not list(tmp.glob(".review_pkg_*.json")), "pack 不应写 .review_pkg 记录"
    # RETURN_PATH 打到 stderr,且指向约定的 .review_return_<gate>.json
    ret_line = [l for l in r.stderr.splitlines() if l.startswith("RETURN_PATH=")]
    assert ret_line, "stderr 无 RETURN_PATH"
    assert f".review_return_{GATE}.json" in ret_line[0]


def test_verify_all_pass_exits_zero(tmp: Path) -> None:
    ret = tmp / f".review_return_{GATE}.json"
    payload = [{"id": iid, "verdict": "pass", "evidence": "原文与润色后逐句核对一致"}
               for iid in _gate_item_ids()]
    ret.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    r = _run(
        ["verify", "--checklist", str(CHECKLIST), "--gate", GATE,
         "--return", str(ret), "--workdir", str(tmp)],
        str(tmp),
    )
    assert r.returncode == 0, f"全 pass 应 exit 0\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    summary = json.loads(r.stdout)
    assert summary["ok"] is True and not summary["fails"] and not summary["problems"]


def test_verify_fail_blocks(tmp: Path) -> None:
    ids = _gate_item_ids()
    # 全部 pass,单独把第一项(硬项 PL-G1)翻成 fail
    payload = [{"id": iid, "verdict": "pass", "evidence": "核对一致"} for iid in ids]
    payload[0] = {"id": ids[0], "verdict": "fail", "evidence": "数值 p=0.03 被改成 p<0.05"}
    ret = tmp / f".review_return_{GATE}.json"
    ret.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    r = _run(
        ["verify", "--checklist", str(CHECKLIST), "--gate", GATE,
         "--return", str(ret), "--workdir", str(tmp)],
        str(tmp),
    )
    assert r.returncode != 0, f"遇 fail 应阻断(exit≠0)\nSTDOUT:{r.stdout}"
    summary = json.loads(r.stdout)
    assert summary["ok"] is False
    assert any(ids[0] in f for f in summary["fails"]), "fail 项未记入 summary.fails"


def main() -> int:
    tests = [
        test_pack_produces_package_and_return_path,
        test_verify_all_pass_exits_zero,
        test_verify_fail_blocks,
    ]
    for t in tests:
        with tempfile.TemporaryDirectory() as d:
            t(Path(d))
        print(f"ok  {t.__name__}")
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
