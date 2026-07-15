#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_words.py 回归测试（开发者维护工具，非运行时流程）。

覆盖：
- count_words_in_text：中英混排分别计中文字符数 / 英文词数
- strip_markdown_syntax：去标题/粗体/链接/列表/表格标记但不误删正文文字

纯 assert，无框架依赖。用法：python3 test_count_words.py
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from count_words import count_words_in_text, strip_markdown_syntax  # noqa: E402


def test_count_words_mixed():
    r = count_words_in_text("你好 world 测试 hello world")
    assert r["chinese_chars"] == 4, r          # 你好 + 测试
    assert r["english_words"] == 3, r          # world hello world


def test_count_words_pure_chinese():
    r = count_words_in_text("研究结果表明")
    assert r["chinese_chars"] == 6
    assert r["english_words"] == 0


def test_count_words_punctuation_not_counted_as_word():
    r = count_words_in_text("PMG, 20 mg/mL.")
    # 标点被切开，但 PMG/mg/mL 等字母串算英文词；数字不算英文词
    assert r["chinese_chars"] == 0
    assert r["english_words"] >= 2


def test_strip_markdown_keeps_body_text():
    md = (
        "# 标题一\n"
        "这是**加粗**和*斜体*正文，含[链接](http://x)与`代码`。\n"
        "- 列表项内容\n"
        "> 引用内容\n"
        "| 列A | 列B |\n"
        "|-----|-----|\n"
        "| 甲 | 乙 |\n"
        "![图](img.png)图注\n"
    )
    out = strip_markdown_syntax(md)
    # 正文文字保留
    assert "标题一" in out
    assert "加粗" in out and "斜体" in out
    assert "正文" in out
    assert "链接" in out and "代码" in out
    assert "列表项内容" in out
    assert "引用内容" in out
    assert "甲" in out and "乙" in out
    # 标记被去除
    assert "#" not in out
    assert "**" not in out
    assert "http://x" not in out
    assert "`" not in out
    assert "](img.png)" not in out
    # 表格分隔行整行被丢弃
    assert "-----" not in out


def test_strip_markdown_then_count_excludes_markup():
    md = "# 结果\n**显著**提升 45%。"
    stripped = strip_markdown_syntax(md)
    r = count_words_in_text(stripped)
    # “结果显著提升” = 6 个中文字（# 与 ** 已去除，不引入额外字符）
    assert r["chinese_chars"] == 6, (stripped, r)


if __name__ == "__main__":
    test_count_words_mixed()
    print("OK count_words 中英混排")
    test_count_words_pure_chinese()
    print("OK count_words 纯中文")
    test_count_words_punctuation_not_counted_as_word()
    print("OK count_words 标点/数字处理")
    test_strip_markdown_keeps_body_text()
    print("OK strip_markdown 保留正文去标记")
    test_strip_markdown_then_count_excludes_markup()
    print("OK strip+count 不含标记")
    print("ALL OK")
