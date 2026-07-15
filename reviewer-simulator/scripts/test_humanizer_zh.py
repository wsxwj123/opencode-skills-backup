#!/usr/bin/env python3
"""test_humanizer_zh.py — reviewer-simulator 本技能独立副本 humanizer_zh 的回归测试。

固化 B7 去AI裁决核心 humanizer_zh.py 的正则契约（正则脆弱，退化则整个 B7
去AI门失效）：

  scan_text：
    - 正例命中且 severity 正确：BANNED 模板句式 + 去AI必禁三项(装饰破折号/
      scare quotes/解释性冒号) = ERROR；VAGUE 措辞 / bullet 列表 = WARNING。
    - 反例不误报：合法化学连字符 Na—Cl(单破折号) / 术语定义 即"XX"(lookbehind
      抑制) / 数字比例 3：1 / 行尾冒号 / 标题(#)行冒号。
  rhythm_check：中文单句 >50 字触发 cn_sentence_too_long，≤50 不触发。

注意 scare_quotes 正则字符类是半角直双引号，命中直引号包裹的 "黑箱"，不命中
弯引号“黑箱”——测试按当前真实行为断言。

纯 assert、无 pytest、直接 import 被测函数（纯函数）。
运行：python3 test_humanizer_zh.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


h = _load("humanizer_zh")


def _codes(text: str):
    return {(i["severity"], i["code"]) for i in h.scan_text(text)["issues"]}


# ---- scan_text 正例：ERROR 级 ----

def test_banned_template_transition_is_error():
    assert ("ERROR", "template_transition") in _codes("综上所述，本研究完成。")


def test_decorative_dash_is_error():
    assert ("ERROR", "decorative_dash") in _codes("这是一个测试——补充说明内容。")


def test_scare_quotes_straight_is_error():
    # 半角直双引号包裹的非术语短语 → scare_quotes ERROR
    assert ("ERROR", "scare_quotes") in _codes('引入"黑箱"概念。')


def test_explanatory_colon_is_error():
    assert ("ERROR", "explanatory_colon") in _codes("方法：我们采用了新的实验流程来验证。")


# ---- scan_text 正例：WARNING 级 ----

def test_vague_phrase_is_warning():
    codes = _codes("近年来研究很多。")
    assert ("WARNING", "replace_with_exact_year_range") in codes
    # VAGUE 不得升级为 ERROR
    assert not any(sev == "ERROR" for sev, _ in codes)


def test_bullet_is_warning():
    assert ("WARNING", "bullet_list") in _codes("- 第一点内容")


# ---- scan_text 反例：不误报 ----

def test_legal_chemical_hyphen_not_flagged():
    # 单个化学连字符 Na—Cl（非 ——）不应触发 decorative_dash
    assert ("ERROR", "decorative_dash") not in _codes("氯化钠 Na—Cl 结构稳定。")


def test_term_definition_quote_suppressed():
    # 即"XX" / 称为"XX"：术语首次定义标记，lookbehind 抑制 scare_quotes
    assert ("ERROR", "scare_quotes") not in _codes('即"黑箱"的方法。')
    assert ("ERROR", "scare_quotes") not in _codes('称为"黑箱"的方法。')


def test_numeric_ratio_colon_not_flagged():
    # 数字比例 3：1 冒号两侧非中文字，不触发 explanatory_colon
    assert ("ERROR", "explanatory_colon") not in _codes("稀释比例为 3：1 的溶液。")


def test_line_ending_colon_not_flagged():
    # 行尾冒号（列表引导）跳过
    assert ("ERROR", "explanatory_colon") not in _codes("实验分为以下几组：")


def test_heading_colon_not_flagged():
    # 标题行（# 开头）冒号跳过
    assert ("ERROR", "explanatory_colon") not in _codes("# 方法：概述与总体设计说明")


# ---- rhythm_check：中文句长硬上限 ----

def test_cn_sentence_over_50_flagged():
    text = "我" * 51 + "。"
    types = [i["type"] for i in h.rhythm_check(text)["issues"]]
    assert "cn_sentence_too_long" in types


def test_cn_sentence_50_or_less_not_flagged():
    text = "我" * 50 + "。"
    types = [i["type"] for i in h.rhythm_check(text)["issues"]]
    assert "cn_sentence_too_long" not in types


if __name__ == "__main__":
    test_banned_template_transition_is_error()
    test_decorative_dash_is_error()
    test_scare_quotes_straight_is_error()
    test_explanatory_colon_is_error()
    test_vague_phrase_is_warning()
    test_bullet_is_warning()
    test_legal_chemical_hyphen_not_flagged()
    test_term_definition_quote_suppressed()
    test_numeric_ratio_colon_not_flagged()
    test_line_ending_colon_not_flagged()
    test_heading_colon_not_flagged()
    test_cn_sentence_over_50_flagged()
    test_cn_sentence_50_or_less_not_flagged()
    print("ALL PASS: test_humanizer_zh")
