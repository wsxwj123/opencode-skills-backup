#!/usr/bin/env python3
"""test_calibration.py — calibration.py 判定校准模式回归测试（低危补齐）。

约定：positive class = reject（映射后 大修/拒稿->reject，接收/小修->accept）。

固化：
  1. compute 对已知 truth/predicted 返回正确 TP/FP/TN/FN（4 条各一 → 1/1/1/1）。
  2. 空输入 → status="empty" 不崩、exit 0。
  3. main 输出的 FNR/FPR/balanced_accuracy 数值正确（TP=FP=TN=FN=1 →
     FNR=0.5、FPR=0.5、balanced_accuracy=0.5）。
  4. 无 reject 样本时 FNR=None(JSON null)，并进 warnings 提示 FNR 不可计算。

compute 用 import 直测；status/FNR/warnings 逻辑在 main()，用 subprocess 读
stdout JSON。纯 assert、无 pytest。运行：python3 test_calibration.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPTS_DIR / "calibration.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


c = _load("calibration")


def _run_stdin(records) -> dict:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", "-"],
        input=json.dumps(records), capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


# ---- compute ----

def test_compute_confusion_matrix():
    recs = [
        {"truth": "reject", "predicted": "reject"},   # TP
        {"truth": "accept", "predicted": "reject"},   # FP
        {"truth": "accept", "predicted": "accept"},   # TN
        {"truth": "reject", "predicted": "accept"},   # FN
    ]
    tp, fp, tn, fn, skipped = c.compute(recs)
    assert (tp, fp, tn, fn) == (1, 1, 1, 1), (tp, fp, tn, fn)
    assert skipped == []


def test_compute_empty_no_crash():
    assert c.compute([]) == (0, 0, 0, 0, [])


# ---- main() JSON ----

def test_empty_input_status():
    out = _run_stdin([])
    assert out["status"] == "empty", out


def test_metrics_values():
    out = _run_stdin([
        {"truth": "reject", "predicted": "reject"},
        {"truth": "accept", "predicted": "reject"},
        {"truth": "accept", "predicted": "accept"},
        {"truth": "reject", "predicted": "accept"},
    ])
    assert out["status"] == "ok"
    assert out["FNR"] == 0.5, out
    assert out["FPR"] == 0.5, out
    assert out["balanced_accuracy"] == 0.5, out


def test_no_reject_fnr_none_warns():
    out = _run_stdin([{"truth": "accept", "predicted": "accept"}])
    assert out["FNR"] is None, out
    assert any("FNR" in w for w in out["warnings"]), out


if __name__ == "__main__":
    test_compute_confusion_matrix()
    test_compute_empty_no_crash()
    test_empty_input_status()
    test_metrics_values()
    test_no_reject_fnr_none_warns()
    print("ALL PASS: test_calibration")
