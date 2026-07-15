#!/usr/bin/env python3
"""Regression guard: structure_signoff_gate.py —— "大纲/故事线未经用户确认就不许
写正文"的粗粒度签字门（hook 在写正文产物前 check 它）。

门禁语义必须双向可靠：
  check 无签字     → exit 2（拦截，弱模型跳步写正文时物理挡下）；
  confirm          → 写 structure_signoff.json 并 exit 0（解锁）；
  check 有合法签字 → exit 0（放行）；
  签字损坏(坏JSON) → exit 2；
  confirmed≠true   → exit 2（存在但未真正确认，不许放行）；
  重跑 confirm     → 旧签字进 history（可追溯大纲变更）。

用子进程跑真门禁，只断言退出码与留痕文件，与调用环境解耦。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "structure_signoff_gate.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


def test_full_signoff_lifecycle():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        # 1) 无签字 → check 拦截 exit2
        r = _run("check", "--root", str(root))
        assert r.returncode == 2, f"缺签字必须拦截, got {r.returncode}\n{r.stdout}"

        # 2) confirm → exit0 + 落盘
        r = _run("confirm", "--root", str(root), "--note", "用户口头确认大纲")
        assert r.returncode == 0, f"confirm 应成功, got {r.returncode}\n{r.stderr}"
        signoff = root / "structure_signoff.json"
        assert signoff.is_file(), "confirm 必须写 structure_signoff.json"
        data = json.loads(signoff.read_text(encoding="utf-8"))
        assert data["confirmed"] is True and data["note"] == "用户口头确认大纲", data

        # 3) 有合法签字 → check 放行 exit0
        r = _run("check", "--root", str(root))
        assert r.returncode == 0, f"合法签字应放行, got {r.returncode}\n{r.stdout}"


def test_corrupt_signoff_blocks():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "structure_signoff.json").write_text("{not json", encoding="utf-8")
        r = _run("check", "--root", str(root))
        assert r.returncode == 2, f"坏 JSON 必须拦截, got {r.returncode}\n{r.stdout}"
        assert "损坏" in r.stdout, r.stdout


def test_confirmed_false_blocks():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "structure_signoff.json").write_text(
            json.dumps({"confirmed": False}), encoding="utf-8")
        r = _run("check", "--root", str(root))
        assert r.returncode == 2, f"confirmed=false 必须拦截, got {r.returncode}\n{r.stdout}"


def test_reconfirm_appends_history():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _run("confirm", "--root", str(root), "--note", "v1 大纲")
        _run("confirm", "--root", str(root), "--note", "v2 大纲大改")
        data = json.loads((root / "structure_signoff.json").read_text(encoding="utf-8"))
        assert data["note"] == "v2 大纲大改", data
        assert any(h.get("note") == "v1 大纲" for h in data.get("history", [])), \
            f"重跑 confirm 应把旧签字进 history: {data}"


if __name__ == "__main__":
    test_full_signoff_lifecycle()
    test_corrupt_signoff_blocks()
    test_confirmed_false_blocks()
    test_reconfirm_appends_history()
    print("OK: structure_signoff_gate — 无签字拦截→confirm解锁→放行 + 坏JSON/未确认拦截 + history")
