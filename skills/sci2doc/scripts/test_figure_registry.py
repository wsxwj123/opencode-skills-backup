#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
figure_registry.py 单元测试
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

# 确保 scripts 目录在 sys.path 中
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from figure_registry import (
    letter_to_number,
    number_to_letter,
    parse_source_figure,
    make_cn_figure_id,
    parse_cn_figure_id,
    load_figure_map,
    save_figure_map,
    register_figure,
    unregister_figure,
    list_figures,
    validate_figure_map,
    cross_validate_with_markdown,
    export_figure_table,
)


class TestLetterConversion(unittest.TestCase):
    """字母 ↔ 数字转换"""

    def test_letter_to_number_basic(self):
        self.assertEqual(letter_to_number("A"), 1)
        self.assertEqual(letter_to_number("B"), 2)
        self.assertEqual(letter_to_number("Z"), 26)

    def test_letter_to_number_lowercase(self):
        self.assertEqual(letter_to_number("a"), 1)
        self.assertEqual(letter_to_number("f"), 6)

    def test_letter_to_number_invalid(self):
        self.assertIsNone(letter_to_number(""))
        self.assertIsNone(letter_to_number(None))
        self.assertIsNone(letter_to_number("AB"))
        self.assertIsNone(letter_to_number("1"))

    def test_number_to_letter_basic(self):
        self.assertEqual(number_to_letter(1), "A")
        self.assertEqual(number_to_letter(6), "F")
        self.assertEqual(number_to_letter(26), "Z")

    def test_number_to_letter_invalid(self):
        self.assertIsNone(number_to_letter(0))
        self.assertIsNone(number_to_letter(27))
        self.assertIsNone(number_to_letter(-1))

    def test_roundtrip(self):
        for i in range(1, 27):
            self.assertEqual(letter_to_number(number_to_letter(i)), i)


class TestParseSourceFigure(unittest.TestCase):
    """SCI 原图标识解析"""

    def test_figure_with_subfigure(self):
        r = parse_source_figure("Figure 1A")
        self.assertEqual(r["figure_num"], 1)
        self.assertEqual(r["subfigure"], "A")
        self.assertEqual(r["subfigure_seq"], 1)

    def test_fig_dot_format(self):
        r = parse_source_figure("Fig. 3C")
        self.assertEqual(r["figure_num"], 3)
        self.assertEqual(r["subfigure"], "C")
        self.assertEqual(r["subfigure_seq"], 3)

    def test_figure_no_subfigure(self):
        r = parse_source_figure("Figure 10")
        self.assertEqual(r["figure_num"], 10)
        self.assertIsNone(r["subfigure"])
        self.assertIsNone(r["subfigure_seq"])

    def test_lowercase_subfigure(self):
        r = parse_source_figure("Fig 4b")
        self.assertEqual(r["subfigure"], "B")
        self.assertEqual(r["subfigure_seq"], 2)

    def test_invalid_input(self):
        self.assertIsNone(parse_source_figure(""))
        self.assertIsNone(parse_source_figure(None))
        self.assertIsNone(parse_source_figure("Table 1"))

    def test_embedded_in_text(self):
        r = parse_source_figure("As shown in Figure 2D, the results...")
        self.assertEqual(r["figure_num"], 2)
        self.assertEqual(r["subfigure"], "D")


class TestCnFigureId(unittest.TestCase):
    """中文图编号生成与解析"""

    def test_make_cn_figure_id(self):
        self.assertEqual(make_cn_figure_id(2, 3), "图2-3")
        self.assertEqual(make_cn_figure_id(1, 1), "图1-1")

    def test_parse_cn_figure_id(self):
        r = parse_cn_figure_id("图3-2")
        self.assertEqual(r["chapter"], 3)
        self.assertEqual(r["seq"], 2)

    def test_parse_with_space(self):
        r = parse_cn_figure_id("图 5-1")
        self.assertEqual(r["chapter"], 5)
        self.assertEqual(r["seq"], 1)

    def test_parse_invalid(self):
        self.assertIsNone(parse_cn_figure_id(""))
        self.assertIsNone(parse_cn_figure_id(None))
        self.assertIsNone(parse_cn_figure_id("表2-1"))


class TestFigureMapCRUD(unittest.TestCase):
    """注册表增删查"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_empty(self):
        fm = load_figure_map(self.tmpdir)
        self.assertEqual(fm, {})

    def test_save_and_load(self):
        data = {"图1-1": {"source_figure": "Figure 1A", "chapter": 1, "seq": 1}}
        save_figure_map(self.tmpdir, data)
        loaded = load_figure_map(self.tmpdir)
        self.assertEqual(loaded["图1-1"]["source_figure"], "Figure 1A")

    def test_register_success(self):
        result = register_figure(self.tmpdir, 2, 1, "Figure 1A", title="细胞形态")
        self.assertTrue(result["ok"])
        self.assertEqual(result["cn_id"], "图2-1")
        fm = load_figure_map(self.tmpdir)
        self.assertIn("图2-1", fm)
        self.assertEqual(fm["图2-1"]["title"], "细胞形态")

    def test_register_conflict(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        result = register_figure(self.tmpdir, 2, 1, "Figure 1B")
        self.assertFalse(result["ok"])
        self.assertIn("冲突", result["message"])

    def test_register_overwrite(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        result = register_figure(self.tmpdir, 2, 1, "Figure 1B", overwrite=True)
        self.assertTrue(result["ok"])
        fm = load_figure_map(self.tmpdir)
        self.assertEqual(fm["图2-1"]["source_figure"], "Figure 1B")

    def test_register_source_conflict(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        result = register_figure(self.tmpdir, 2, 2, "Figure 1A")
        self.assertFalse(result["ok"])
        self.assertIn("源图冲突", result["message"])

    def test_register_invalid_source(self):
        result = register_figure(self.tmpdir, 2, 1, "not a figure")
        self.assertFalse(result["ok"])
        self.assertIn("无法解析", result["message"])

    def test_unregister(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        result = unregister_figure(self.tmpdir, "图2-1")
        self.assertTrue(result["ok"])
        fm = load_figure_map(self.tmpdir)
        self.assertNotIn("图2-1", fm)

    def test_unregister_nonexistent(self):
        result = unregister_figure(self.tmpdir, "图9-9")
        self.assertFalse(result["ok"])

    def test_list_all(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        register_figure(self.tmpdir, 3, 1, "Figure 2A")
        results = list_figures(self.tmpdir)
        self.assertEqual(len(results), 2)

    def test_list_by_chapter(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        register_figure(self.tmpdir, 3, 1, "Figure 2A")
        results = list_figures(self.tmpdir, chapter=2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["cn_id"], "图2-1")


class TestValidation(unittest.TestCase):
    """映射表验证"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_validate_empty(self):
        result = validate_figure_map(self.tmpdir)
        self.assertTrue(result["ok"])

    def test_validate_continuous(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        register_figure(self.tmpdir, 2, 2, "Figure 1B")
        register_figure(self.tmpdir, 2, 3, "Figure 1C")
        result = validate_figure_map(self.tmpdir)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_gap(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        register_figure(self.tmpdir, 2, 3, "Figure 1C")
        result = validate_figure_map(self.tmpdir)
        self.assertFalse(result["ok"])
        self.assertTrue(any("不连续" in e for e in result["errors"]))

    def test_validate_bad_source(self):
        fm = {"图2-1": {"source_figure": "bad", "chapter": 2, "seq": 1}}
        save_figure_map(self.tmpdir, fm)
        result = validate_figure_map(self.tmpdir)
        self.assertFalse(result["ok"])
        self.assertTrue(any("无法解析" in e for e in result["errors"]))


class TestCrossValidation(unittest.TestCase):
    """与 atomic_md 交叉验证"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # 创建 atomic_md 结构
        ch_dir = os.path.join(self.tmpdir, "atomic_md", "第2章")
        os.makedirs(ch_dir)
        with open(os.path.join(ch_dir, "2.1_引言.md"), "w", encoding="utf-8") as f:
            f.write("如图2-1所示，实验结果表明...\n如图2-2所示，进一步分析...\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_all_registered(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        register_figure(self.tmpdir, 2, 2, "Figure 1B")
        result = cross_validate_with_markdown(self.tmpdir, chapter=2)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["unregistered"]), 0)

    def test_unregistered_figure(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        # 图2-2 在 md 中引用但未注册
        result = cross_validate_with_markdown(self.tmpdir, chapter=2)
        self.assertFalse(result["ok"])
        self.assertIn("图2-2", result["unregistered"])

    def test_unreferenced_figure(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        register_figure(self.tmpdir, 2, 2, "Figure 1B")
        register_figure(self.tmpdir, 2, 3, "Figure 1C")
        result = cross_validate_with_markdown(self.tmpdir, chapter=2)
        self.assertTrue(result["ok"])
        self.assertIn("图2-3", result["unreferenced"])

    def test_no_atomic_dir(self):
        shutil.rmtree(os.path.join(self.tmpdir, "atomic_md"))
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        result = cross_validate_with_markdown(self.tmpdir)
        self.assertTrue(result["ok"])


class TestExport(unittest.TestCase):
    """导出功能"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_export_empty(self):
        out = export_figure_table(self.tmpdir, fmt="markdown")
        self.assertIn("无图映射", out)

    def test_export_markdown(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A", title="细胞形态")
        out = export_figure_table(self.tmpdir, fmt="markdown")
        self.assertIn("图2-1", out)
        self.assertIn("Figure 1A", out)
        self.assertIn("细胞形态", out)

    def test_export_json(self):
        register_figure(self.tmpdir, 2, 1, "Figure 1A")
        out = export_figure_table(self.tmpdir, fmt="json")
        data = json.loads(out)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["cn_id"], "图2-1")


if __name__ == "__main__":
    unittest.main()
