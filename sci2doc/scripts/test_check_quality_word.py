#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_word_format_compliance 单元测试

覆盖：
1. 合规文档（零 issue）
2. 页面布局违规（纸张尺寸 / 页边距）
3. 标题样式违规（字号 / 加粗 / 对齐 / 行距 / 段前段后）
4. 正文违规（字号 / 首行缩进）
5. 字体名称违规（西文字体 / 东亚字体）
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from check_quality import check_word_format_compliance

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
EMU_PER_CM = 360000

# A4 纸张 & 标准页边距（EMU）
A4_WIDTH = int(21.0 * EMU_PER_CM)
A4_HEIGHT = int(29.7 * EMU_PER_CM)
MARGIN_TOP = int(2.54 * EMU_PER_CM)
MARGIN_BOTTOM = int(2.54 * EMU_PER_CM)
MARGIN_LEFT = int(3.17 * EMU_PER_CM)
MARGIN_RIGHT = int(3.17 * EMU_PER_CM)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _make_pt(value):
    """构造一个带 .pt 属性的对象（模拟 docx 的 Pt / Length）。"""
    obj = MagicMock()
    obj.pt = value
    obj.__float__ = lambda self: float(value)
    obj.__int__ = lambda self: int(value)
    obj.__abs__ = lambda self: abs(value)
    obj.__sub__ = lambda self, other: value - (other.pt if hasattr(other, 'pt') else other)
    obj.__rsub__ = lambda self, other: (other.pt if hasattr(other, 'pt') else other) - value
    return obj


def _make_emu(value):
    """构造一个 EMU 值对象（int 即可，但需要支持 hasattr 检查）。"""
    return value  # check_word_format_compliance 直接用 int(fi) 和除法


def _make_run(font_size_pt=None, bold=None, font_name=None):
    """构造一个 mock Run。"""
    run = MagicMock()
    font = MagicMock()

    if font_size_pt is not None:
        font.size = _make_pt(font_size_pt)
    else:
        font.size = None

    font.bold = bold
    font.name = font_name

    run.font = font
    # _element 用于 _get_east_asian_font，默认返回 None
    run._element = MagicMock()
    run._element.find.return_value = None
    return run


def _make_paragraph_format(
    alignment=None,
    line_spacing_pt_val=None,
    space_before_pt=None,
    space_after_pt=None,
    first_line_indent=None,
):
    """构造 mock paragraph_format。"""
    pf = MagicMock()
    pf.alignment = alignment

    if line_spacing_pt_val is not None:
        pf.line_spacing = _make_pt(line_spacing_pt_val)
    else:
        pf.line_spacing = None

    if space_before_pt is not None:
        pf.space_before = _make_pt(space_before_pt)
    else:
        pf.space_before = None

    if space_after_pt is not None:
        pf.space_after = _make_pt(space_after_pt)
    else:
        pf.space_after = None

    pf.first_line_indent = first_line_indent
    return pf


def _make_para(text, style_name, runs=None, paragraph_format=None):
    """构造 mock 段落。"""
    p = MagicMock()
    p.text = text
    style = MagicMock()
    style.name = style_name
    p.style = style
    p.runs = runs or []
    p.paragraph_format = paragraph_format or _make_paragraph_format()
    return p


def _make_section(
    page_width=A4_WIDTH,
    page_height=A4_HEIGHT,
    top_margin=MARGIN_TOP,
    bottom_margin=MARGIN_BOTTOM,
    left_margin=MARGIN_LEFT,
    right_margin=MARGIN_RIGHT,
):
    """构造 mock section。"""
    sec = MagicMock()
    sec.page_width = page_width
    sec.page_height = page_height
    sec.top_margin = top_margin
    sec.bottom_margin = bottom_margin
    sec.left_margin = left_margin
    sec.right_margin = right_margin
    return sec


def _make_doc(sections=None, paragraphs=None):
    """构造 mock Document。"""
    doc = MagicMock()
    doc.sections = sections or [_make_section()]
    doc.paragraphs = paragraphs or []
    return doc


# ---------------------------------------------------------------------------
# 构造一个完全合规的文档
# ---------------------------------------------------------------------------

def _build_compliant_doc():
    """
    构造一个完全合规的 mock 文档：
    - A4 页面 + 标准页边距
    - Heading 1: 16pt, bold, CENTER(1), 行距 20pt, 段前 18pt, 段后 12pt
    - Heading 2: 14pt, not bold, LEFT(0), 行距 20pt, 段前 10pt, 段后 8pt
    - Heading 3: 12pt, not bold, LEFT(0), 行距 20pt, 段前 10pt, 段后 8pt
    - Normal: 12pt, 行距 20pt, 首行缩进 ~240000 EMU
    """
    h1_run = _make_run(font_size_pt=16.0, bold=True, font_name='Times New Roman')
    h1_pf = _make_paragraph_format(
        alignment=1, line_spacing_pt_val=20.0,
        space_before_pt=18.0, space_after_pt=12.0,
    )
    h1 = _make_para("第一章 绪论", "Heading 1", runs=[h1_run], paragraph_format=h1_pf)

    h2_run = _make_run(font_size_pt=14.0, bold=False, font_name='Times New Roman')
    h2_pf = _make_paragraph_format(
        alignment=0, line_spacing_pt_val=20.0,
        space_before_pt=10.0, space_after_pt=8.0,
    )
    h2 = _make_para("1.1 研究背景", "Heading 2", runs=[h2_run], paragraph_format=h2_pf)

    h3_run = _make_run(font_size_pt=12.0, bold=False, font_name='Times New Roman')
    h3_pf = _make_paragraph_format(
        alignment=0, line_spacing_pt_val=20.0,
        space_before_pt=10.0, space_after_pt=8.0,
    )
    h3 = _make_para("1.1.1 国内研究现状", "Heading 3", runs=[h3_run], paragraph_format=h3_pf)

    normal_run = _make_run(font_size_pt=12.0, bold=None, font_name='Times New Roman')
    normal_pf = _make_paragraph_format(
        alignment=None, line_spacing_pt_val=20.0,
        first_line_indent=240000,
    )
    normal = _make_para("本研究采用深度学习方法。", "Normal", runs=[normal_run], paragraph_format=normal_pf)

    return _make_doc(
        sections=[_make_section()],
        paragraphs=[h1, h2, h3, normal],
    )


# ===========================================================================
# 测试用例
# ===========================================================================

class TestValidDocument(unittest.TestCase):
    """1. 合规文档应零 issue。"""

    @patch('check_quality._get_east_asian_font', return_value='SimHei')
    def test_compliant_doc_no_issues(self, mock_ea):
        doc = _build_compliant_doc()
        issues = check_word_format_compliance(doc)
        self.assertEqual(len(issues), 0, f"Expected 0 issues, got: {issues}")


class TestPageLayoutViolations(unittest.TestCase):
    """2. 页面布局违规。"""

    def test_wrong_page_width(self):
        """纸张宽度不符应报 error。"""
        bad_section = _make_section(page_width=int(20.0 * EMU_PER_CM))
        doc = _make_doc(sections=[bad_section], paragraphs=[])
        issues = check_word_format_compliance(doc)
        errors = [i for i in issues if i['level'] == 'error' and '纸张宽度' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    def test_wrong_page_height(self):
        """纸张高度不符应报 error。"""
        bad_section = _make_section(page_height=int(25.0 * EMU_PER_CM))
        doc = _make_doc(sections=[bad_section], paragraphs=[])
        issues = check_word_format_compliance(doc)
        errors = [i for i in issues if i['level'] == 'error' and '纸张高度' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    def test_wrong_margins(self):
        """页边距不符应报 error。"""
        bad_section = _make_section(
            top_margin=int(1.0 * EMU_PER_CM),
            left_margin=int(5.0 * EMU_PER_CM),
        )
        doc = _make_doc(sections=[bad_section], paragraphs=[])
        issues = check_word_format_compliance(doc)
        margin_errors = [i for i in issues if i['level'] == 'error' and '边距' in i['message']]
        self.assertGreaterEqual(len(margin_errors), 1)


class TestHeadingStyleViolations(unittest.TestCase):
    """3. 标题样式违规。"""

    @patch('check_quality._get_east_asian_font', return_value='SimHei')
    def test_heading1_wrong_font_size(self, mock_ea):
        """Heading 1 字号 14pt（应为 16pt）→ error。"""
        run = _make_run(font_size_pt=14.0, bold=True, font_name='Times New Roman')
        pf = _make_paragraph_format(
            alignment=1, line_spacing_pt_val=20.0,
            space_before_pt=18.0, space_after_pt=12.0,
        )
        h1 = _make_para("第一章 绪论", "Heading 1", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[h1])
        issues = check_word_format_compliance(doc)
        errors = [i for i in issues if i['level'] == 'error' and '字号' in i['message'] and '一级标题' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    @patch('check_quality._get_east_asian_font', return_value='SimHei')
    def test_heading2_wrong_bold(self, mock_ea):
        """Heading 2 bold=True（应为 False）→ error。"""
        run = _make_run(font_size_pt=14.0, bold=True, font_name='Times New Roman')
        pf = _make_paragraph_format(
            alignment=0, line_spacing_pt_val=20.0,
            space_before_pt=10.0, space_after_pt=8.0,
        )
        h2 = _make_para("1.1 研究背景", "Heading 2", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[h2])
        issues = check_word_format_compliance(doc)
        errors = [i for i in issues if i['level'] == 'error' and '加粗' in i['message'] and '二级标题' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    @patch('check_quality._get_east_asian_font', return_value='SimHei')
    def test_heading1_wrong_alignment(self, mock_ea):
        """Heading 1 左对齐（应为居中）→ error。"""
        run = _make_run(font_size_pt=16.0, bold=True, font_name='Times New Roman')
        pf = _make_paragraph_format(
            alignment=0,  # LEFT, should be 1 (CENTER)
            line_spacing_pt_val=20.0,
            space_before_pt=18.0, space_after_pt=12.0,
        )
        h1 = _make_para("第一章 绪论", "Heading 1", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[h1])
        issues = check_word_format_compliance(doc)
        errors = [i for i in issues if i['level'] == 'error' and '对齐' in i['message'] and '一级标题' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    @patch('check_quality._get_east_asian_font', return_value='SimHei')
    def test_heading1_wrong_line_spacing(self, mock_ea):
        """Heading 1 行距 30pt（应为 20pt）→ warning。"""
        run = _make_run(font_size_pt=16.0, bold=True, font_name='Times New Roman')
        pf = _make_paragraph_format(
            alignment=1,
            line_spacing_pt_val=30.0,  # wrong
            space_before_pt=18.0, space_after_pt=12.0,
        )
        h1 = _make_para("第一章 绪论", "Heading 1", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[h1])
        issues = check_word_format_compliance(doc)
        warnings = [i for i in issues if i['level'] == 'warning' and '行距' in i['message'] and '一级标题' in i['message']]
        self.assertGreaterEqual(len(warnings), 1)

    @patch('check_quality._get_east_asian_font', return_value='SimHei')
    def test_heading1_wrong_space_before_after(self, mock_ea):
        """Heading 1 段前/段后间距不符 → warning。"""
        run = _make_run(font_size_pt=16.0, bold=True, font_name='Times New Roman')
        pf = _make_paragraph_format(
            alignment=1, line_spacing_pt_val=20.0,
            space_before_pt=6.0,   # should be 18.0
            space_after_pt=30.0,   # should be 12.0
        )
        h1 = _make_para("第一章 绪论", "Heading 1", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[h1])
        issues = check_word_format_compliance(doc)
        space_warnings = [i for i in issues if i['level'] == 'warning' and '间距' in i['message']]
        self.assertGreaterEqual(len(space_warnings), 2, f"Expected >=2 spacing warnings, got: {space_warnings}")


class TestNormalTextViolations(unittest.TestCase):
    """4. 正文违规。"""

    @patch('check_quality._get_east_asian_font', return_value=None)
    def test_normal_wrong_font_size(self, mock_ea):
        """Normal 字号 10pt（应为 12pt）→ error。"""
        run = _make_run(font_size_pt=10.0, bold=None, font_name='Times New Roman')
        pf = _make_paragraph_format(
            line_spacing_pt_val=20.0, first_line_indent=240000,
        )
        normal = _make_para("本研究采用深度学习方法。", "Normal", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[normal])
        issues = check_word_format_compliance(doc)
        errors = [i for i in issues if i['level'] == 'error' and '字号' in i['message'] and '正文' in i['message']]
        self.assertGreaterEqual(len(errors), 1)

    @patch('check_quality._get_east_asian_font', return_value=None)
    def test_normal_wrong_first_indent(self, mock_ea):
        """Normal 首行缩进过大 → warning。"""
        run = _make_run(font_size_pt=12.0, bold=None, font_name='Times New Roman')
        pf = _make_paragraph_format(
            line_spacing_pt_val=20.0,
            first_line_indent=500000,  # way too large
        )
        normal = _make_para("本研究采用深度学习方法。", "Normal", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[normal])
        issues = check_word_format_compliance(doc)
        warnings = [i for i in issues if i['level'] == 'warning' and '缩进' in i['message']]
        self.assertGreaterEqual(len(warnings), 1)


class TestFontNameViolations(unittest.TestCase):
    """5. 字体名称违规。"""

    @patch('check_quality._get_east_asian_font', return_value='SimHei')
    def test_heading_wrong_latin_font(self, mock_ea):
        """Heading 1 西文字体 Calibri（应为 Times New Roman）→ info。"""
        run = _make_run(font_size_pt=16.0, bold=True, font_name='Calibri')
        pf = _make_paragraph_format(
            alignment=1, line_spacing_pt_val=20.0,
            space_before_pt=18.0, space_after_pt=12.0,
        )
        h1 = _make_para("第一章 绪论", "Heading 1", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[h1])
        issues = check_word_format_compliance(doc)
        infos = [i for i in issues if i['level'] == 'info' and '西文字体' in i['message']]
        self.assertGreaterEqual(len(infos), 1)

    @patch('check_quality._get_east_asian_font', return_value='SimSun')
    def test_heading_wrong_east_asian_font(self, mock_ea):
        """Heading 1 东亚字体 SimSun（应为 SimHei/黑体）→ info。"""
        run = _make_run(font_size_pt=16.0, bold=True, font_name='Times New Roman')
        pf = _make_paragraph_format(
            alignment=1, line_spacing_pt_val=20.0,
            space_before_pt=18.0, space_after_pt=12.0,
        )
        h1 = _make_para("第一章 绪论", "Heading 1", runs=[run], paragraph_format=pf)
        doc = _make_doc(paragraphs=[h1])
        issues = check_word_format_compliance(doc)
        infos = [i for i in issues if i['level'] == 'info' and '中文字体' in i['message']]
        self.assertGreaterEqual(len(infos), 1)


if __name__ == "__main__":
    unittest.main()
