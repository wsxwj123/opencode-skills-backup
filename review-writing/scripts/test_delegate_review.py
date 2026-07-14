#!/usr/bin/env python3
"""Smoke test: delegate_review.py 盲检委托 verify 的 fail-closed 行为。

verify 读子代理返回的裁决 JSON + DoD checklist,逐项校验:每个清单 id 都被裁决、
verdict 合法、evidence 非空;任一缺项 / verdict=fail / 空证据 → exit 1(阻断"声明完成");
全部 pass 且附证据 → exit 0。pack 先生成任务包 + .review_pkg 记录(exit 0)。

双向断言:
  1) 返回含 fail 裁决 → exit 1(拦截);
  2) 全 pass 且带证据 → exit 0(放行)。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "delegate_review.py"

CHECKLIST = {
    "skill": "review-writing",
    "gates": {
        "manuscript-dod": {
            "title": "成稿 DoD",
            "items": [
                {"id": "C1", "name": "引用连续", "check": "编号无跳号"},
                {"id": "C2", "name": "无空洞句", "check": "每句有据"},
            ],
        }
    },
}


def _run(*args: str, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=cwd)


def _verify(td: Path, checklist: Path, ret: Path) -> subprocess.CompletedProcess:
    return _run("verify", "--checklist", str(checklist), "--gate", "manuscript-dod",
                "--return", str(ret), "--workdir", str(td), cwd=str(td))


def test_verify_fail_blocks_and_pass_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checklist = root / "checklist.json"
        checklist.write_text(json.dumps(CHECKLIST, ensure_ascii=False), encoding="utf-8")

        # pack 生成任务包(应 exit 0 并落 .review_pkg 记录)
        r = _run("pack", "--checklist", str(checklist), "--gate", "manuscript-dod",
                 "--files", "drafts/s1.md", "--workdir", str(td), cwd=str(td))
        assert r.returncode == 0, f"pack 应成功,got {r.returncode}\n{r.stderr}"
        assert (root / ".review_pkg_manuscript-dod.json").exists(), "pack 未落任务包记录"

        # 1) 返回含 fail → 拦截
        bad = root / "bad_return.json"
        bad.write_text(json.dumps([
            {"id": "C1", "verdict": "fail", "evidence": "第2段 [3] 跳号"},
            {"id": "C2", "verdict": "pass", "evidence": "逐句核对有据"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(root, checklist, bad)
        assert r.returncode == 1, f"含 fail 必须阻断,got {r.returncode}\n{r.stdout}"
        assert '"ok": false' in r.stdout, r.stdout

        # 2) 全 pass 带证据 → 放行
        good = root / "good_return.json"
        good.write_text(json.dumps([
            {"id": "C1", "verdict": "pass", "evidence": "编号 1..N 连续,脚本 [OK]"},
            {"id": "C2", "verdict": "pass", "evidence": "逐句核对均有引用支撑"},
        ], ensure_ascii=False), encoding="utf-8")
        r = _verify(root, checklist, good)
        assert r.returncode == 0, f"全 pass 应放行,got {r.returncode}\n{r.stdout}\n{r.stderr}"
        assert '"ok": true' in r.stdout, r.stdout


if __name__ == "__main__":
    test_verify_fail_blocks_and_pass_passes()
    print("OK: delegate_review — fail裁决拦截→全pass放行")
