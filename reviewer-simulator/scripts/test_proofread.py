#!/usr/bin/env python3
"""test_proofread.py — proofread.py 字符级形式层校对器回归测试。

固化：
  1. --fail-on 硬门：命中 misspelling / chinese_punct / subsup_bare 任一
     (count>0) → ok=false、exit 1（含 teh、中文逗号泄漏进英文句、裸写 H2O）。
     无命中 → exit 0。
  2. 计分：从 100 按 severity 权重递减（high=5）；soft 项权重 0 不扣分——仅有
     soft 项(拉丁短语裸写 in vitro)时 score 仍为 100。
  3. BrE/AmE：仅同文件混用才报（colour 单用不报；colour+color 混用才报）。

退出码/JSON 汇总用 subprocess；确定性计分与 BrE/AmE 用 import 直测。
纯 assert、无 pytest、tempfile 自包含。运行：python3 test_proofread.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPTS_DIR / "proofread.py"
FAIL_ON = "misspelling,chinese_punct,subsup_bare"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


p = _load("proofread")


def _run_dir(files: dict) -> subprocess.CompletedProcess:
    d = tempfile.mkdtemp()
    for name, text in files.items():
        Path(d, name).write_text(text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--manuscript-dir", d,
         "--report", os.path.join(d, "report.json"),
         "--fail-on", FAIL_ON],
        capture_output=True, text=True,
    )


def _score(text: str) -> dict:
    d = tempfile.mkdtemp()
    fp = os.path.join(d, "x.md")
    Path(fp).write_text(text, encoding="utf-8")
    return p.check_file(fp)


# ---- --fail-on 硬门 ----

def test_misspelling_fails():
    r = _run_dir({"a.md": "The results were teh best.\n"})
    assert r.returncode == 1, r.stdout + r.stderr
    out = json.loads(r.stdout.splitlines()[0])
    assert out["ok"] is False
    assert out["fail_on_hits"].get("misspelling", 0) >= 1, out


def test_chinese_punct_leak_fails():
    # 英文句内泄漏中文逗号（该行中文字符 <3，不被跳过启发式豁免）
    r = _run_dir({"b.md": "The value was significant，and robust here.\n"})
    assert r.returncode == 1, r.stdout + r.stderr
    out = json.loads(r.stdout.splitlines()[0])
    assert out["fail_on_hits"].get("chinese_punct", 0) >= 1, out


def test_subsup_bare_fails():
    r = _run_dir({"c.md": "We measured H2O uptake in cells.\n"})
    assert r.returncode == 1, r.stdout + r.stderr
    out = json.loads(r.stdout.splitlines()[0])
    assert out["fail_on_hits"].get("subsup_bare", 0) >= 1, out


def test_clean_passes():
    r = _run_dir({"clean.md": "The cells were cultured carefully today morning here.\n"})
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout.splitlines()[0])
    assert out["ok"] is True and out["fail_on_hits"] == {}, out


# ---- 计分 ----

def test_high_issue_deducts_5():
    r = _score("The results were teh best today.")
    assert r["issues_by_type"].get("misspelling") == 1, r
    assert r["score"] == 95, r  # 100 - high(5)


def test_soft_only_keeps_100():
    # 拉丁短语裸写 in vitro = soft(权重0)，无其它命中 → score 仍 100
    r = _score("Cells cultured in vitro carefully today morning here.")
    assert r["issues_by_type"].get("latin_italic_missing") == 1, r
    assert r["score"] == 100, r


# ---- BrE/AmE 仅混用才报 ----

def test_bre_alone_not_flagged():
    assert p.check_bre_ame_mixed("We used colour analysis here.") == []


def test_bre_ame_mixed_flagged():
    issues = p.check_bre_ame_mixed("We used colour and color here.")
    assert [i["type"] for i in issues] == ["bre_ame_mixed"], issues


if __name__ == "__main__":
    test_misspelling_fails()
    test_chinese_punct_leak_fails()
    test_subsup_bare_fails()
    test_clean_passes()
    test_high_issue_deducts_5()
    test_soft_only_keeps_100()
    test_bre_alone_not_flagged()
    test_bre_ame_mixed_flagged()
    print("ALL PASS: test_proofread")
