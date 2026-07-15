#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
figure_registry.py 回归测试（开发者维护工具，非运行时流程）。

覆盖：
- letter_to_number：A→1, Z→26, 非法→None
- make_cn_figure_id：章优先 图N-M
- cross_validate_with_markdown：md 引用但未注册的图应报缺（unregistered 命中，ok=False）

纯 assert，无框架依赖。用法：python3 test_figure_registry.py
"""

import os
import sys
import tempfile
import shutil

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import figure_registry as fr


def test_letter_to_number():
    assert fr.letter_to_number("A") == 1
    assert fr.letter_to_number("a") == 1
    assert fr.letter_to_number("Z") == 26
    assert fr.letter_to_number("z") == 26
    assert fr.letter_to_number("1") is None
    assert fr.letter_to_number("AB") is None
    assert fr.letter_to_number("") is None
    assert fr.letter_to_number(None) is None


def test_make_cn_figure_id():
    assert fr.make_cn_figure_id(2, 1) == "图2-1"
    assert fr.make_cn_figure_id(10, 3) == "图10-3"


def test_parse_cn_figure_id_roundtrip():
    parsed = fr.parse_cn_figure_id("图3-2")
    assert parsed == {"chapter": 3, "seq": 2}
    assert fr.parse_cn_figure_id("无编号") is None


def _write_md(root, chapter, fname, text):
    d = os.path.join(root, "atomic_md", f"第{chapter}章")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, fname), "w", encoding="utf-8") as f:
        f.write(text)


def test_cross_validate_reports_unregistered():
    tmp = tempfile.mkdtemp()
    try:
        # 注册 图2-1
        fr.register_figure(tmp, chapter=2, seq=1, source_figure="Figure 1A", title="t")
        # md 里引用 图2-1（已注册）和 图2-2（未注册）
        _write_md(tmp, 2, "1_节.md", "如图2-1所示，另见图2-2。")
        res = fr.cross_validate_with_markdown(tmp, chapter=2)
        assert res["ok"] is False
        assert "图2-2" in res["unregistered"], res
        assert "图2-1" not in res["unregistered"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cross_validate_all_registered_ok():
    tmp = tempfile.mkdtemp()
    try:
        fr.register_figure(tmp, chapter=2, seq=1, source_figure="Figure 1A")
        _write_md(tmp, 2, "1_节.md", "如图2-1所示。")
        res = fr.cross_validate_with_markdown(tmp, chapter=2)
        assert res["ok"] is True
        assert res["unregistered"] == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_letter_to_number()
    print("OK letter_to_number A→1 Z→26")
    test_make_cn_figure_id()
    print("OK make_cn_figure_id 图N-M")
    test_parse_cn_figure_id_roundtrip()
    print("OK parse_cn_figure_id")
    test_cross_validate_reports_unregistered()
    print("OK cross_validate 未注册图报缺")
    test_cross_validate_all_registered_ok()
    print("OK cross_validate 全注册通过")
    print("ALL OK")
