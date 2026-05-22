#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_words.py 的单元测试：
- strip_markdown_syntax
- count_words_in_text
- count_words_in_md
- count_words_in_atomic_dir
- count_words (统一入口)
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from count_words import (
    strip_markdown_syntax,
    count_words_in_text,
    count_words_in_md,
    count_words_in_atomic_dir,
    count_words,
)


# ---------------------------------------------------------------------------
# strip_markdown_syntax
# ---------------------------------------------------------------------------

class TestStripMarkdownSyntax(unittest.TestCase):

    def test_headings(self):
        self.assertEqual(strip_markdown_syntax("# 标题一").strip(), "标题一")
        self.assertEqual(strip_markdown_syntax("### 三级标题").strip(), "三级标题")

    def test_bold_italic(self):
        self.assertIn("加粗", strip_markdown_syntax("**加粗**"))
        self.assertNotIn("**", strip_markdown_syntax("**加粗**"))
        self.assertIn("斜体", strip_markdown_syntax("*斜体*"))
        self.assertNotIn("*", strip_markdown_syntax("正常 *斜体* 文本").replace("正常", "").replace("文本", ""))

    def test_inline_code(self):
        result = strip_markdown_syntax("使用 `print()` 函数")
        self.assertIn("print()", result)
        self.assertNotIn("`", result)

    def test_links(self):
        result = strip_markdown_syntax("[链接文本](https://example.com)")
        self.assertIn("链接文本", result)
        self.assertNotIn("https://", result)

    def test_images(self):
        result = strip_markdown_syntax("![图片描述](img.png)")
        self.assertIn("图片描述", result)
        self.assertNotIn("img.png", result)

    def test_table_separator_removed(self):
        result = strip_markdown_syntax("|---|---|---|")
        self.assertEqual(result.strip(), "")

    def test_table_content_kept(self):
        result = strip_markdown_syntax("| 名称 | 数值 |")
        self.assertIn("名称", result)
        self.assertIn("数值", result)

    def test_blockquote(self):
        result = strip_markdown_syntax("> 引用内容")
        self.assertIn("引用内容", result)
        self.assertNotIn(">", result)

    def test_unordered_list(self):
        result = strip_markdown_syntax("- 列表项")
        self.assertIn("列表项", result)

    def test_ordered_list(self):
        result = strip_markdown_syntax("1. 有序列表")
        self.assertIn("有序列表", result)

    def test_horizontal_rule(self):
        self.assertEqual(strip_markdown_syntax("---").strip(), "")
        self.assertEqual(strip_markdown_syntax("***").strip(), "")

    def test_html_tags(self):
        result = strip_markdown_syntax("<br/>换行<b>粗体</b>")
        self.assertIn("换行", result)
        self.assertIn("粗体", result)
        self.assertNotIn("<", result)

    def test_strikethrough(self):
        result = strip_markdown_syntax("~~删除线~~")
        self.assertIn("删除线", result)
        self.assertNotIn("~~", result)

    def test_footnote_ref(self):
        result = strip_markdown_syntax("正文内容[^1]后续")
        self.assertIn("正文内容", result)
        self.assertNotIn("[^1]", result)

    def test_plain_text_unchanged(self):
        text = "这是一段普通的中文文本，没有任何格式标记。"
        self.assertEqual(strip_markdown_syntax(text).strip(), text)


# ---------------------------------------------------------------------------
# count_words_in_text
# ---------------------------------------------------------------------------

class TestCountWordsInText(unittest.TestCase):

    def test_chinese_only(self):
        r = count_words_in_text("中文测试文本")
        self.assertEqual(r["chinese_chars"], 6)  # 中文测试文本 = 6
        self.assertEqual(r["english_words"], 0)

    def test_english_only(self):
        r = count_words_in_text("hello world test")
        self.assertEqual(r["chinese_chars"], 0)
        self.assertEqual(r["english_words"], 3)

    def test_mixed(self):
        r = count_words_in_text("中文 hello 测试 world")
        self.assertEqual(r["chinese_chars"], 4)
        self.assertEqual(r["english_words"], 2)

    def test_empty(self):
        r = count_words_in_text("")
        self.assertEqual(r["chinese_chars"], 0)
        self.assertEqual(r["english_words"], 0)

    def test_punctuation_excluded(self):
        r = count_words_in_text("你好，世界！")
        self.assertEqual(r["chinese_chars"], 4)  # 你好世界


# ---------------------------------------------------------------------------
# count_words_in_md
# ---------------------------------------------------------------------------

class TestCountWordsInMd(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_md(self, name, content):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_basic_chinese(self):
        path = self._write_md("test.md", "这是一段测试文本")
        r = count_words_in_md(path)
        self.assertTrue(r["success"])
        self.assertEqual(r["source_type"], "markdown")
        self.assertEqual(r["body_text"]["chinese_chars"], 8)  # 这是一段测试文本 = 8

    def test_heading_counted(self):
        path = self._write_md("test.md", "# 第一章 绪论\n\n正文内容在这里")
        r = count_words_in_md(path)
        self.assertTrue(r["success"])
        # 标题 "第一章绪论" = 4 + 空格不算 + 正文 "正文内容在这里" = 6 = 但 "第一章 绪论" 实际 classify 后标题也计入
        total_cn = r["total"]["chinese_chars"]
        self.assertGreater(total_cn, 0)
        # 验证标题和正文都被计入
        self.assertGreaterEqual(total_cn, 10)

    def test_sections_detected(self):
        content = "# 第一章 绪论\n\n绪论内容\n\n# 第二章 实验方法\n\n实验内容"
        path = self._write_md("test.md", content)
        r = count_words_in_md(path)
        self.assertTrue(r["success"])
        self.assertGreaterEqual(len(r["sections"]), 2)

    def test_references_excluded(self):
        content = "# 第一章 绪论\n\n正文内容\n\n# 参考文献\n\n张三等人的研究"
        path = self._write_md("test.md", content)
        r = count_words_in_md(path, exclude_references=True)
        self.assertTrue(r["success"])
        # 参考文献部分不计入 body；body 包含标题+正文
        body_cn = r["body_text"]["chinese_chars"]
        ref_section = [s for s in r["sections"] if s["type"] == "references"]
        self.assertTrue(len(ref_section) > 0)
        # body 不含参考文献内容
        total_ref_cn = sum(s["chinese_chars"] for s in ref_section)
        self.assertGreater(total_ref_cn, 0)
        # body 应只含绪论相关
        self.assertGreater(body_cn, 0)

    def test_references_included(self):
        content = "# 第一章 绪论\n\n正文内容\n\n# 参考文献\n\n张三等人的研究"
        path = self._write_md("test.md", content)
        r = count_words_in_md(path, exclude_references=False)
        self.assertTrue(r["success"])
        # 参考文献也计入 body
        self.assertGreater(r["body_text"]["chinese_chars"], 6)

    def test_markdown_syntax_stripped(self):
        content = "**加粗文本** 和 *斜体* 以及 `代码`"
        path = self._write_md("test.md", content)
        r = count_words_in_md(path)
        self.assertTrue(r["success"])
        # 加粗文本 和 斜体 以及 代码 — 中文字符: 加粗文本和斜体以及代码 = 9, 但 strip 后 "和" "以及" 也算
        # 关键：不应把 ** * ` 计为内容
        cn = r["body_text"]["chinese_chars"]
        self.assertGreater(cn, 0)
        # 验证英文标记符号没被计入（无英文单词）
        self.assertEqual(r["body_text"]["english_words"], 0)

    def test_table_separator_not_counted(self):
        content = "| 名称 | 数值 |\n|---|---|\n| 测试 | 数据 |"
        path = self._write_md("test.md", content)
        r = count_words_in_md(path)
        self.assertTrue(r["success"])
        # 名称 数值 测试 数据 = 8 chars (each 2 chars)
        self.assertEqual(r["body_text"]["chinese_chars"], 8)

    def test_file_not_found(self):
        r = count_words_in_md("/nonexistent/path.md")
        self.assertFalse(r["success"])

    def test_completion_rate(self):
        path = self._write_md("test.md", "中" * 40000)
        r = count_words_in_md(path, body_target_chars=80000)
        self.assertTrue(r["success"])
        self.assertAlmostEqual(r["targets"]["body_completion_rate"], 0.5, places=2)

    def test_review_section(self):
        content = "# 第一章 文献综述\n\n综述内容在这里"
        path = self._write_md("test.md", content)
        r = count_words_in_md(path)
        self.assertTrue(r["success"])
        self.assertGreater(r["review"]["chinese_chars"], 0)
        self.assertEqual(r["body_text"]["chinese_chars"], 0)


# ---------------------------------------------------------------------------
# count_words_in_atomic_dir
# ---------------------------------------------------------------------------

class TestCountWordsInAtomicDir(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_section(self, subdir, name, content):
        d = os.path.join(self.tmpdir, subdir) if subdir else self.tmpdir
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_single_chapter_dir(self):
        self._write_section("", "2.1_引言.md", "# 2.1 引言\n\n引言内容在这里")
        self._write_section("", "2.2_方法.md", "# 2.2 方法\n\n方法内容在这里")
        r = count_words_in_atomic_dir(self.tmpdir)
        self.assertTrue(r["success"])
        self.assertEqual(r["source_type"], "atomic_dir")
        self.assertEqual(r["file_count"], 2)
        self.assertGreater(r["total"]["chinese_chars"], 0)
        self.assertEqual(len(r["per_file"]), 2)

    def test_multi_chapter_root(self):
        self._write_section("第2章", "2.1_引言.md", "引言内容")
        self._write_section("第2章", "2.2_方法.md", "方法内容")
        self._write_section("第3章", "3.1_结果.md", "结果内容")
        r = count_words_in_atomic_dir(self.tmpdir)
        self.assertTrue(r["success"])
        self.assertEqual(r["file_count"], 3)
        self.assertEqual(len(r["per_file"]), 3)

    def test_non_matching_files_ignored(self):
        self._write_section("", "2.1_引言.md", "引言内容")
        self._write_section("", "README.md", "这不是小节文件")
        self._write_section("", "notes.txt", "这也不是")
        r = count_words_in_atomic_dir(self.tmpdir)
        self.assertTrue(r["success"])
        self.assertEqual(r["file_count"], 1)

    def test_empty_dir(self):
        r = count_words_in_atomic_dir(self.tmpdir)
        self.assertFalse(r["success"])
        self.assertIn("未找到", r["error"])

    def test_nonexistent_dir(self):
        r = count_words_in_atomic_dir("/nonexistent/dir")
        self.assertFalse(r["success"])

    def test_aggregation_correct(self):
        self._write_section("", "1.1_节一.md", "中" * 100)
        self._write_section("", "1.2_节二.md", "中" * 200)
        r = count_words_in_atomic_dir(self.tmpdir)
        self.assertTrue(r["success"])
        self.assertEqual(r["body_text"]["chinese_chars"], 300)

    def test_per_file_details(self):
        self._write_section("", "1.1_节一.md", "中" * 50)
        self._write_section("", "1.2_节二.md", "中" * 80)
        r = count_words_in_atomic_dir(self.tmpdir)
        self.assertTrue(r["success"])
        pf = r["per_file"]
        self.assertEqual(len(pf), 2)
        totals = [p["total_count"] for p in pf]
        self.assertIn(50, totals)
        self.assertIn(80, totals)


# ---------------------------------------------------------------------------
# count_words (统一入口)
# ---------------------------------------------------------------------------

class TestCountWordsUnified(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_md_file(self):
        path = os.path.join(self.tmpdir, "test.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("测试内容")
        r = count_words(path)
        self.assertTrue(r["success"])
        self.assertEqual(r["source_type"], "markdown")

    def test_directory(self):
        d = os.path.join(self.tmpdir, "atomic")
        os.makedirs(d)
        with open(os.path.join(d, "1.1_节一.md"), "w", encoding="utf-8") as f:
            f.write("测试内容")
        r = count_words(d)
        self.assertTrue(r["success"])
        self.assertEqual(r["source_type"], "atomic_dir")

    def test_unsupported_extension(self):
        path = os.path.join(self.tmpdir, "test.txt")
        with open(path, "w") as f:
            f.write("hello")
        r = count_words(path)
        self.assertFalse(r["success"])
        self.assertIn("不支持", r["error"])

    def test_docx_rejected(self):
        # docx 不再支持，应返回"不支持的文件类型"
        r = count_words("/nonexistent/file.docx")
        self.assertFalse(r["success"])
        self.assertIn("不支持", r.get("error", ""))


if __name__ == "__main__":
    unittest.main()
