#!/usr/bin/env python3
"""Regression guard: word_counter.py 的字数目标解析与计数纯逻辑。

非门禁、低危，但含真正则逻辑，易在改动时静默退化：
  _read_outline_target —— 从 outline.md 抽 "Word Count Target"：显式区间逐字采用、
    单值走 ±20%、单位从后缀或 language 推断（中文按字、英文按词）。目标错了会误报
    进度状态（🔴/🟡/🟢），误导写作篇幅。
  count_text          —— cn 数汉字、en 数空格词；
  clean_markdown      —— 计数前剥 markdown（代码块/链接/强调），避免把标记算进字数。

纯函数 + tempfile 造 outline.md，独立可跑。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import word_counter as wc


def _target(outline_text: str, language: str):
    with tempfile.TemporaryDirectory() as d:
        Path(d, "outline.md").write_text(outline_text, encoding="utf-8")
        return wc._read_outline_target(Path(d), language)


def test_explicit_range_used_verbatim():
    # 显式区间 5000-8000：min/max 逐字采用，center=上界
    assert _target("Word Count Target: 5000-8000 words", "en") == (5000, 8000, 8000, "words")


def test_single_value_uses_plus_minus_20pct():
    assert _target("Word Count Target: 1000 words", "en") == (800, 1200, 1000, "words")


def test_unit_inference_from_language_and_suffix():
    # 无后缀 + cn 语言 → chars
    assert _target("Word Count Target: 2000", "cn") == (1600, 2400, 2000, "chars")
    # 中文后缀"字"覆盖 en 语言 → chars
    assert _target("Word Count Target: 3000 字", "en") == (2400, 3600, 3000, "chars")


def test_no_target_returns_none():
    assert _target("no target mentioned here", "en") is None


def test_count_text_cn_vs_en():
    # 中文只数汉字（忽略拉丁字母/空格）
    assert wc.count_text("这是一个测试 hello", "cn") == 6
    # 英文按空格分词
    assert wc.count_text("one two three", "en") == 3


def test_clean_markdown_strips_syntax():
    out = wc.clean_markdown("# Head\n`code` [link](http://u) **bold**")
    assert "code" not in out and "http://u" not in out, out
    # 链接可见文字与 heading 文本保留
    assert "link" in out and "Head" in out and "bold" in out, out


if __name__ == "__main__":
    test_explicit_range_used_verbatim()
    test_single_value_uses_plus_minus_20pct()
    test_unit_inference_from_language_and_suffix()
    test_no_target_returns_none()
    test_count_text_cn_vs_en()
    test_clean_markdown_strips_syntax()
    print("OK: word_counter — 目标区间/±20%/单位推断 + cn·en 计数 + markdown 清洗")
