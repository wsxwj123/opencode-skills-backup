#!/usr/bin/env python3
"""test_scan_report_humanize.py — B7 脚本兜底 scan_report_humanize.py 回归测试。

固化两件事：
  1. extract_body_text 的正文提取契约：
     - 剥掉 head/script/style/footer/nav 与 skip-link（正例：<script> 内套话不进
       正文、<footer> 版权套话不进正文）。
     - 保留可见审稿正文文本。
     - HTML 实体最小还原（&amp;→& 等）。
     - 块级标签边界使各 DOM 文本节点各自成段（反例：相邻短元素不被拼成假长句，
       不误触发 cn_sentence_too_long）。
  2. CLI 退出码：含 ERROR 套话的 HTML → exit 1；干净 HTML → exit 0。

extract_body_text 用 import 直接测；退出码用 subprocess。纯 assert、无 pytest、
tempfile 自包含。运行：python3 test_scan_report_humanize.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPTS_DIR / "scan_report_humanize.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


s = _load("scan_report_humanize")


def _run(html: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "report.html"
        p.write_text(html, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(p)],
            capture_output=True, text=True,
        )


# ---- extract_body_text 契约 ----

def test_script_footer_skiplink_stripped():
    html = (
        '<html><head><style>.x{}</style>'
        '<script>var t="综上所述";</script></head>'
        '<body><a class="skip-link" href="#m">跳到正文</a>'
        "<h2>审稿意见</h2><p>本研究方法可靠。</p>"
        "<footer>版权所有 综上所述 2020</footer></body></html>"
    )
    body = s.extract_body_text(html)
    # script 内、footer 内的套话都不进正文
    assert "综上所述" not in body, body
    assert "跳到正文" not in body, body
    # 可见审稿正文保留
    assert "审稿意见" in body and "本研究方法可靠" in body, body


def test_html_entities_restored():
    assert s.extract_body_text("<p>A &amp; B &lt;x&gt;</p>") == "A & B <x>"


def test_adjacent_short_elements_not_glued():
    # 两个各 30 字的短块级元素，分段后各自 30 字，不拼成 >50 假长句
    html = "<p>" + "甲" * 30 + "</p><p>" + "乙" * 30 + "</p>"
    body = s.extract_body_text(html)
    segments = [seg for seg in body.split("\n\n") if seg.strip()]
    assert [len(seg) for seg in segments] == [30, 30], body
    h = _load("humanizer_zh")
    types = [i["type"] for i in h.rhythm_check(body)["issues"]]
    assert "cn_sentence_too_long" not in types, types


# ---- CLI 退出码 ----

def test_dirty_html_exit1():
    html = "<html><body><h2>意见</h2><p>综上所述，本文可接收。</p></body></html>"
    r = _run(html)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "HUMANIZE_FAILED" in r.stdout, r.stdout


def test_clean_html_exit0():
    # 套话仅出现在 script/footer（被剥离），可见正文干净 → exit 0
    html = (
        '<html><head><script>var x="综上所述";</script></head>'
        '<body><a class="skip-link" href="#m">跳到正文</a>'
        "<p>本研究方法可靠。</p><p>数据完整规范。</p>"
        "<footer>版权 革命性的 2020</footer></body></html>"
    )
    r = _run(html)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "HUMANIZE_OK" in r.stdout, r.stdout


if __name__ == "__main__":
    test_script_footer_skiplink_stripped()
    test_html_entities_restored()
    test_adjacent_short_elements_not_glued()
    test_dirty_html_exit1()
    test_clean_html_exit0()
    print("ALL PASS: test_scan_report_humanize")
