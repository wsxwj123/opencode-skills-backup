#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_quality.py 新增检查器的单元测试：
- check_table_format
- check_inline_citations
- check_writing_style
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, PropertyMock
from lxml import etree

# 确保 scripts 目录在 sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from check_quality import check_inline_citations, check_writing_style, check_table_format


# ---------------------------------------------------------------------------
# helpers: 构造 mock Document
# ---------------------------------------------------------------------------

def _make_para(text, style_name="Normal"):
    """构造一个 mock 段落。"""
    p = MagicMock()
    p.text = text
    style = MagicMock()
    style.name = style_name
    p.style = style
    return p


def _make_doc(paragraphs, tables=None):
    """构造一个 mock Document。"""
    doc = MagicMock()
    doc.paragraphs = paragraphs
    doc.tables = tables or []
    return doc


NSMAP = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _make_cell(borders_dict=None):
    """
    构造一个 mock table cell，带有 XML 边框定义。

    borders_dict: {"top": (val, sz), "bottom": (val, sz), "left": ..., "right": ...}
    """
    cell = MagicMock()
    tc = etree.Element(f'{{{NSMAP["w"]}}}tc')
    if borders_dict:
        tcPr = etree.SubElement(tc, f'{{{NSMAP["w"]}}}tcPr')
        tcBorders = etree.SubElement(tcPr, f'{{{NSMAP["w"]}}}tcBorders')
        for edge, (val, sz) in borders_dict.items():
            el = etree.SubElement(tcBorders, f'{{{NSMAP["w"]}}}{edge}')
            el.set(f'{{{NSMAP["w"]}}}val', val)
            el.set(f'{{{NSMAP["w"]}}}sz', str(sz))
    cell._tc = tc
    return cell


def _make_row(cells):
    row = MagicMock()
    row.cells = cells
    return row


def _make_table(rows):
    table = MagicMock()
    table.rows = rows
    return table


# ===========================================================================
# check_inline_citations
# ===========================================================================

class TestCheckInlineCitations(unittest.TestCase):
    """引用格式检测测试。"""

    def test_valid_citations_no_issues(self):
        """合法引用不应产生问题。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("研究表明[1]，该方法有效[2,3]。"),
            _make_para("多项研究[4-6]支持这一结论[1,3,7-9]。"),
        ])
        issues = check_inline_citations(doc)
        self.assertEqual(len(issues), 0)

    def test_missing_comma(self):
        """[6 7] 缺少逗号应报错。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("如文献[6 7]所述。"),
        ])
        issues = check_inline_citations(doc)
        errors = [i for i in issues if i['level'] == 'error']
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("缺少逗号" in e['message'] for e in errors))

    def test_chinese_comma(self):
        """[6，7] 中文逗号应报错。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("如文献[6，7]所述。"),
        ])
        issues = check_inline_citations(doc)
        errors = [i for i in issues if i['level'] == 'error']
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("中文逗号" in e['message'] for e in errors))

    def test_chinese_brackets(self):
        """（6）中文括号应报错。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("如文献（6）所述。"),
        ])
        issues = check_inline_citations(doc)
        errors = [i for i in issues if i['level'] == 'error']
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("中文括号" in e['message'] for e in errors))

    def test_reverse_range(self):
        """[8-3] 逆序范围应报错。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("如文献[8-3]所述。"),
        ])
        issues = check_inline_citations(doc)
        errors = [i for i in issues if i['level'] == 'error']
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("逆序" in e['message'] for e in errors))

    def test_unsorted_numbers(self):
        """[8,3] 未排序应产生 warning。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("如文献[8,3]所述。"),
        ])
        issues = check_inline_citations(doc)
        warnings = [i for i in issues if i['level'] == 'warning']
        self.assertGreaterEqual(len(warnings), 1)
        self.assertTrue(any("升序" in w['message'] for w in warnings))

    def test_skip_references_section(self):
        """参考文献区域内的文本不应被检测。"""
        doc = _make_doc([
            _make_para("参考文献", "Heading 1"),
            _make_para("[1] 张三. 论文标题. 期刊, 2024."),
            _make_para("[6 7] 格式不规范但在参考文献区域内。"),
        ])
        issues = check_inline_citations(doc)
        self.assertEqual(len(issues), 0)

    def test_complex_valid_citation(self):
        """复杂合法引用 [1,2,3-5,8] 不应报错。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("综合多项研究[1,2,3-5,8]可知。"),
        ])
        issues = check_inline_citations(doc)
        self.assertEqual(len(issues), 0)


# ===========================================================================
# check_writing_style
# ===========================================================================

class TestCheckWritingStyle(unittest.TestCase):
    """写作风格检测测试。"""

    def test_clean_text_no_issues(self):
        """规范正文不应产生问题。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("本研究采用深度学习方法对图像进行分类。"),
            _make_para("实验结果表明该方法具有较高的准确率。"),
        ])
        issues = check_writing_style(doc)
        self.assertEqual(len(issues), 0)

    def test_em_dash_error(self):
        """破折号（——）应报 error。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("该方法——基于卷积神经网络——取得了良好效果。"),
        ])
        issues = check_writing_style(doc)
        errors = [i for i in issues if i['level'] == 'error' and i['category'] == '标点规范']
        self.assertGreaterEqual(len(errors), 1)

    def test_question_mark_warning(self):
        """正文中的问号应报 warning。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("为什么该方法效果更好？"),
        ])
        issues = check_writing_style(doc)
        warnings = [i for i in issues if i['category'] == '陈述规范']
        self.assertGreaterEqual(len(warnings), 1)

    def test_metaphor_error(self):
        """比喻词（如同、犹如等）应报 error。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("该算法犹如一把利剑切入问题核心。"),
        ])
        issues = check_writing_style(doc)
        errors = [i for i in issues if i['level'] == 'error' and i['category'] == '修辞规范']
        self.assertGreaterEqual(len(errors), 1)

    def test_metaphor_noun_error(self):
        """比喻性名词（...的桥梁/基石等）应报 error。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("深度学习是人工智能发展的基石。"),
        ])
        issues = check_writing_style(doc)
        errors = [i for i in issues if i['level'] == 'error' and '比喻' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    def test_subjective_language_warning(self):
        """主观夸大表述应报 warning。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("实验结果令人震惊，远超预期。"),
        ])
        issues = check_writing_style(doc)
        warnings = [i for i in issues if i['category'] == '客观性']
        self.assertGreaterEqual(len(warnings), 1)

    def test_overly_formal_warning(self):
        """过度书面化表述应报 warning。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("有鉴于此，本文提出了新方法。"),
        ])
        issues = check_writing_style(doc)
        warnings = [i for i in issues if i['category'] == '语言通俗性']
        self.assertGreaterEqual(len(warnings), 1)

    def test_parallelism_warning(self):
        """连续3句以相同前缀开头应报排比 warning。"""
        doc = _make_doc([
            _make_para("第一章 绪论", "Heading 1"),
            _make_para("实验结果表明该方法有效。实验结果证实了假设成立。实验结果显示精度提升。"),
        ])
        issues = check_writing_style(doc)
        parallel = [i for i in issues if '排比' in i['message']]
        self.assertGreaterEqual(len(parallel), 1)

    def test_skip_references_section(self):
        """参考文献区域不应被检测。"""
        doc = _make_doc([
            _make_para("参考文献", "Heading 1"),
            _make_para("该方法——基于卷积神经网络——取得了良好效果。"),
        ])
        issues = check_writing_style(doc)
        self.assertEqual(len(issues), 0)


# ===========================================================================
# check_table_format
# ===========================================================================

class TestCheckTableFormat(unittest.TestCase):
    """三线表格式检测测试。"""

    def _three_line_table(self):
        """构造一个合规的三线表。"""
        header_borders = {
            "top": ("single", 12),      # 1.5pt
            "bottom": ("single", 4),    # 0.5pt 表头分隔线
            "left": ("none", 0),
            "right": ("none", 0),
        }
        body_borders = {
            "top": ("none", 0),
            "bottom": ("none", 0),
            "left": ("none", 0),
            "right": ("none", 0),
        }
        last_borders = {
            "top": ("none", 0),
            "bottom": ("single", 12),   # 1.5pt
            "left": ("none", 0),
            "right": ("none", 0),
        }
        header_row = _make_row([_make_cell(header_borders), _make_cell(header_borders)])
        body_row = _make_row([_make_cell(body_borders), _make_cell(body_borders)])
        last_row = _make_row([_make_cell(last_borders), _make_cell(last_borders)])
        return _make_table([header_row, body_row, last_row])

    def test_valid_three_line_table(self):
        """合规三线表不应产生问题。"""
        table = self._three_line_table()
        doc = _make_doc([], tables=[table])
        issues = check_table_format(doc)
        self.assertEqual(len(issues), 0)

    def test_missing_top_border(self):
        """首行缺少顶部边框应报错。"""
        no_top = {
            "bottom": ("single", 4),
            "left": ("none", 0),
            "right": ("none", 0),
        }
        last = {
            "bottom": ("single", 12),
            "left": ("none", 0),
            "right": ("none", 0),
        }
        header_row = _make_row([_make_cell(no_top)])
        last_row = _make_row([_make_cell(last)])
        table = _make_table([header_row, last_row])
        doc = _make_doc([], tables=[table])
        issues = check_table_format(doc)
        errors = [i for i in issues if '顶部边框' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    def test_missing_bottom_border(self):
        """末行缺少底部边框应报错。"""
        header = {
            "top": ("single", 12),
            "bottom": ("single", 4),
            "left": ("none", 0),
            "right": ("none", 0),
        }
        no_bottom = {
            "left": ("none", 0),
            "right": ("none", 0),
        }
        header_row = _make_row([_make_cell(header)])
        last_row = _make_row([_make_cell(no_bottom)])
        table = _make_table([header_row, last_row])
        doc = _make_doc([], tables=[table])
        issues = check_table_format(doc)
        errors = [i for i in issues if '底部边框' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    def test_vertical_lines_error(self):
        """存在竖线应报错。"""
        header = {
            "top": ("single", 12),
            "bottom": ("single", 4),
            "left": ("single", 4),   # 竖线！
            "right": ("single", 4),  # 竖线！
        }
        last = {
            "bottom": ("single", 12),
            "left": ("single", 4),
            "right": ("single", 4),
        }
        header_row = _make_row([_make_cell(header)])
        last_row = _make_row([_make_cell(last)])
        table = _make_table([header_row, last_row])
        doc = _make_doc([], tables=[table])
        issues = check_table_format(doc)
        vert = [i for i in issues if '竖线' in i['message']]
        self.assertGreaterEqual(len(vert), 1)

    def test_thin_top_border_warning(self):
        """首行顶部边框过细应报 warning。"""
        thin_top = {
            "top": ("single", 4),       # 0.5pt，太细
            "bottom": ("single", 4),
            "left": ("none", 0),
            "right": ("none", 0),
        }
        last = {
            "bottom": ("single", 12),
            "left": ("none", 0),
            "right": ("none", 0),
        }
        header_row = _make_row([_make_cell(thin_top)])
        last_row = _make_row([_make_cell(last)])
        table = _make_table([header_row, last_row])
        doc = _make_doc([], tables=[table])
        issues = check_table_format(doc)
        warnings = [i for i in issues if i['level'] == 'warning' and '顶部边框过细' in i['message']]
        self.assertGreaterEqual(len(warnings), 1)

    def test_single_row_table_skipped(self):
        """单行表格应被跳过。"""
        row = _make_row([_make_cell()])
        table = _make_table([row])
        doc = _make_doc([], tables=[table])
        issues = check_table_format(doc)
        self.assertEqual(len(issues), 0)

    def test_missing_header_separator(self):
        """缺少表头分隔线应报错。"""
        no_sep = {
            "top": ("single", 12),
            "bottom": ("none", 0),   # 无分隔线
            "left": ("none", 0),
            "right": ("none", 0),
        }
        last = {
            "bottom": ("single", 12),
            "left": ("none", 0),
            "right": ("none", 0),
        }
        header_row = _make_row([_make_cell(no_sep)])
        last_row = _make_row([_make_cell(last)])
        table = _make_table([header_row, last_row])
        doc = _make_doc([], tables=[table])
        issues = check_table_format(doc)
        errors = [i for i in issues if '表头分隔线' in i['message']]
        self.assertGreaterEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
