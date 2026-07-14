#!/usr/bin/env python3
"""test_validate_report_html.py — reviewer-simulator 审稿报告 HTML 运行时校验器烟测。

固化 validate_report_html.py 的四道运行时硬门(对生成后的报告 HTML 逐份校验):
  1. 残留占位符  {{...}}(剥离 <script>/<style> 后仍存在)→ 拦截
  2. decisionVerdict / finalRecommendationText 必须 ∈ {拒稿/大修/小修/接收}
  3. header verdict 与第十节 finalRecommendationText 必须完全一致
  4. #decisionVerdict 的 verdict-* class 必须与 verdict 一一对应

双向:违规 HTML → exit≠0 + VALIDATION_FAILED;合规 HTML → exit 0 + VALIDATION_OK。

纯 assert、无 pytest、自包含合成输入(tempfile)。验证用 subprocess.run(...).returncode。
运行:python3 test_validate_report_html.py

注意:本文件测的是**运行时报告校验器**,不是只测 HTML 模板资产的
template_regression_test.py。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "validate_report_html.py"


def _run(html: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "report.html"
        p.write_text(html, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(p)],
            capture_output=True, text=True,
        )


def _html(verdict: str, verdict_class: str, final: str, extra_body: str = "") -> str:
    return (
        "<html><body>"
        f'<h1 id="decisionVerdict" class="{verdict_class}">{verdict}</h1>'
        f'<p id="finalRecommendationText">{final}</p>'
        f"{extra_body}"
        "</body></html>"
    )


# ---- 合规:应通过(exit 0)----

def test_compliant_passes():
    r = _run(_html("大修", "verdict-major", "大修"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "VALIDATION_OK" in r.stdout, r.stdout


def test_script_placeholder_not_flagged():
    # 模板自带的预览脚本硬编码 {{...}} 字面量,剥离 <script> 后不应误报。
    body = "<script>var t='{{UNRESOLVED}}';</script>"
    r = _run(_html("接收", "verdict-accept", "接收", extra_body=body))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "VALIDATION_OK" in r.stdout, r.stdout


# ---- 违规:应拦截(exit != 0)----

def test_residual_placeholder_fails():
    r = _run(_html("小修", "verdict-minor", "小修", extra_body="<p>{{MANUSCRIPT_TITLE}}</p>"))
    assert r.returncode != 0, r.stdout
    assert "Unreplaced placeholders" in r.stdout, r.stdout


def test_invalid_verdict_fails():
    r = _run(_html("需要大修", "verdict-major", "需要大修"))
    assert r.returncode != 0, r.stdout
    assert "decisionVerdict" in r.stdout, r.stdout


def test_verdict_mismatch_fails():
    # header=大修 但第十节=拒稿 → 不一致拦截
    r = _run(_html("大修", "verdict-major", "拒稿"))
    assert r.returncode != 0, r.stdout
    assert "mismatch" in r.stdout.lower(), r.stdout


def test_verdict_class_mismatch_fails():
    # verdict=大修 但 class 是 verdict-accept → VERDICT_CLASS 不匹配
    r = _run(_html("大修", "verdict-accept", "大修"))
    assert r.returncode != 0, r.stdout
    assert "VERDICT_CLASS" in r.stdout, r.stdout


if __name__ == "__main__":
    test_compliant_passes()
    test_script_placeholder_not_flagged()
    test_residual_placeholder_fails()
    test_invalid_verdict_fails()
    test_verdict_mismatch_fails()
    test_verdict_class_mismatch_fails()
    print("ALL PASS: test_validate_report_html")
