#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sci2doc 格式契约回归测试（开发者维护工具，非运行时流程）。

固化本轮已修的 4 个 bug，防止以后改正则/字段读取时退化。
纯 assert，无 pytest 依赖，所有输入在测试内现造（字符串 / 内存 docx / tempfile）。
不依赖任何外部真稿路径。

用法：
    python3 test_format_contract.py
失败抛 AssertionError（returncode != 0），全过打印 OK。
"""

import os
import sys
import tempfile

# 本测试文件与被测脚本同目录，确保脚本目录在 import 路径上
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


# ===========================================================================
# 契约 1：reference_renderer raw_vancouver 回退
# bug：SCI 参考库条目常只有完整 raw_vancouver 字符串而无结构化 authors/journal，
#      旧逻辑直接渲染会输出"佚名 / 空刊名"。修复后应回退原样输出 raw_vancouver。
# ===========================================================================

def test_reference_renderer_raw_vancouver_fallback():
    from reference_renderer import render_entry

    # (a) 只有 raw_vancouver、无结构化字段 → 应回退原文，不出现"佚名"
    raw_text = ("Smith J, Doe A, Roe B, et al. A landmark study on tumor immunology. "
                "Nature. 2021;590(7844):123-130. DOI: 10.1038/s41586-021-00001-2.")
    entry_raw = {"id": "ref_1", "raw_vancouver": raw_text}
    rendered = render_entry(entry_raw)
    assert "A landmark study on tumor immunology" in rendered, \
        f"raw_vancouver 片段应原样保留，实际：{rendered!r}"
    assert "佚名" not in rendered, \
        f"无结构化字段时不应出现'佚名'，实际：{rendered!r}"
    assert "Nature" in rendered, \
        f"raw_vancouver 刊名片段应保留，实际：{rendered!r}"

    # 带编号也应保留原文片段
    rendered_idx = render_entry(entry_raw, index=7)
    assert rendered_idx.startswith("[7] "), f"编号前缀缺失：{rendered_idx!r}"
    assert "佚名" not in rendered_idx
    assert "A landmark study on tumor immunology" in rendered_idx

    # (b) 完整结构化字段 → 走正常 GB/T 7714 渲染（不退化为 raw_vancouver 原文）
    entry_struct = {
        "id": "ref_2",
        "type": "journal",
        "authors": ["Zhang S", "Li W", "Wang H"],
        "title": "Structured rendering must still work",
        "journal": "Journal of Test",
        "year": "2022",
        "volume": "10",
        "issue": "3",
        "pages": "200-210",
        "doi": "10.1000/test.2022",
        # 故意附带一个不同的 raw_vancouver，确认正常路径不会误用它
        "raw_vancouver": "RAW_SHOULD_NOT_APPEAR_IN_OUTPUT",
    }
    rendered_struct = render_entry(entry_struct)
    assert "RAW_SHOULD_NOT_APPEAR_IN_OUTPUT" not in rendered_struct, \
        f"有结构化字段时不应退化为 raw_vancouver，实际：{rendered_struct!r}"
    assert "Structured rendering must still work" in rendered_struct
    assert "[J]" in rendered_struct, f"期刊类应带 [J] 标识，实际：{rendered_struct!r}"
    assert "Journal of Test" in rendered_struct
    assert "佚名" not in rendered_struct


# ===========================================================================
# 契约 2：markdown_to_docx 输出 A4 页面
# bug：python-docx 默认 Letter（21.59×27.94cm），check_quality 硬要求 A4。
#      修复后应显式设 page_width≈21.0cm、page_height≈29.7cm。
# ===========================================================================

def test_markdown_to_docx_a4_page_size():
    from markdown_to_docx import markdown_to_docx
    from docx import Document
    from docx.shared import Cm

    md = "# 第1章 绪论\n\n这是一段用于生成最小 docx 的正文内容。\n"

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        ok = markdown_to_docx(md, tmp_path)
        assert ok is True, "markdown_to_docx 应返回 True"

        doc = Document(tmp_path)
        section = doc.sections[0]
        # EMU 容差比较：1cm ≈ 360000 EMU，允许 ±0.05cm（=18000 EMU）误差
        tol = Cm(0.05)
        expected_w = Cm(21.0)
        expected_h = Cm(29.7)
        assert abs(section.page_width - expected_w) <= tol, \
            f"page_width 应≈A4 宽 21.0cm，实际 EMU={section.page_width}"
        assert abs(section.page_height - expected_h) <= tol, \
            f"page_height 应≈A4 高 29.7cm，实际 EMU={section.page_height}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ===========================================================================
# 契约 3：abbreviation_registry 连字符全称
# bug：旧正则全称部分不接受连字符，"Triple-Negative Breast Cancer" 抓不到。
#      修复后含连字符的全称仍能抓到 abbr；无连字符的全称不退化。
# ===========================================================================

def test_abbreviation_hyphenated_full_name():
    from abbreviation_registry import extract_abbreviations

    # (a) 含连字符全称
    found_hyphen = extract_abbreviations('三阴性乳腺癌（Triple-Negative Breast Cancer, TNBC）')
    abbrs = {item["abbr"] for item in found_hyphen}
    assert "TNBC" in abbrs, f"含连字符全称应抓到 TNBC，实际：{found_hyphen!r}"
    tnbc = next(item for item in found_hyphen if item["abbr"] == "TNBC")
    assert "Triple-Negative" in tnbc["full_en"], \
        f"全称应保留连字符片段，实际：{tnbc!r}"

    # (b) 无连字符全称仍正常（不退化）
    found_plain = extract_abbreviations('磁共振成像（Magnetic Resonance Imaging, MRI）')
    abbrs_plain = {item["abbr"] for item in found_plain}
    assert "MRI" in abbrs_plain, f"无连字符全称应正常抓到 MRI，实际：{found_plain!r}"
    mri = next(item for item in found_plain if item["abbr"] == "MRI")
    assert "Magnetic Resonance Imaging" in mri["full_en"], \
        f"全称应完整保留，实际：{mri!r}"


# ===========================================================================
# 契约 4：check_quality 表号 + 图号去重
# bug：同一表/图号被题注 + 正文多次引用时，旧逻辑按出现次数排序导致 expected
#      错位，产生假"不连续"警告。修复后按 (chapter, number) 去重，真缺号仍报错。
# ===========================================================================

def _build_docx_with_paragraphs(lines):
    """在内存里造一个最小 docx Document，每行一段。"""
    from docx import Document
    doc = Document()
    for ln in lines:
        doc.add_paragraph(ln)
    return doc


def _table_issues(issues):
    return [i for i in issues if "表编号不连续" in i.get("message", "")]


def _figure_issues(issues):
    return [i for i in issues if "图编号不连续" in i.get("message", "")]


def test_check_quality_table_figure_dedup():
    from check_quality import check_figure_numbering

    # ---- 表号：4 个连续表号 2-1~2-4，且每个被正文多次引用 → 0 假阳性 ----
    table_ok_lines = [
        "表 2-1：第一张表的题注",
        "如表 2-1 所示，结果良好。",        # 重复引用 2-1
        "表 2-2：第二张表的题注",
        "见表 2-2 与表 2-1 的对比。",        # 重复引用 2-2 和 2-1
        "表 2-3：第三张表的题注",
        "表 2-3 进一步说明问题。",            # 重复引用 2-3
        "表 2-4：第四张表的题注",
        "综合表 2-1 至表 2-4 可知。",        # 同段同时引用 2-1 和 2-4
    ]
    issues_ok = check_figure_numbering(_build_docx_with_paragraphs(table_ok_lines))
    assert _table_issues(issues_ok) == [], \
        f"连续表号被多次引用不应误报，实际表号告警：{_table_issues(issues_ok)!r}"

    # ---- 表号：真缺号 2-1, 2-3（缺 2-2）→ 仍正确报错 ----
    table_gap_lines = [
        "表 2-1：第一张表",
        "表 2-3：第三张表",   # 缺 2-2
    ]
    issues_gap = check_figure_numbering(_build_docx_with_paragraphs(table_gap_lines))
    assert len(_table_issues(issues_gap)) >= 1, \
        f"真缺号（缺表 2-2）应报错，实际：{issues_gap!r}"

    # ---- 图号：4 个连续图号 2-1~2-4，且每个被正文多次引用 → 0 假阳性 ----
    figure_ok_lines = [
        "图 2-1：第一张图的题注",
        "如图 2-1 所示。",                    # 重复引用 2-1
        "图 2-2：第二张图的题注",
        "图 2-2 与图 2-1 对比。",             # 重复引用 2-2 和 2-1
        "图 2-3：第三张图的题注",
        "见图 2-3。",                         # 重复引用 2-3
        "图 2-4：第四张图的题注",
        "图 2-1 至图 2-4 共同说明。",         # 同段引用 2-1 和 2-4
    ]
    issues_fig_ok = check_figure_numbering(_build_docx_with_paragraphs(figure_ok_lines))
    assert _figure_issues(issues_fig_ok) == [], \
        f"连续图号被多次引用不应误报，实际图号告警：{_figure_issues(issues_fig_ok)!r}"

    # ---- 图号：真缺号 2-1, 2-3（缺 2-2）→ 仍正确报错 ----
    figure_gap_lines = [
        "图 2-1：第一张图",
        "图 2-3：第三张图",   # 缺 2-2
    ]
    issues_fig_gap = check_figure_numbering(_build_docx_with_paragraphs(figure_gap_lines))
    assert len(_figure_issues(issues_fig_gap)) >= 1, \
        f"真缺号（缺图 2-2）应报错，实际：{issues_fig_gap!r}"


# ===========================================================================
# 入口
# ===========================================================================

if __name__ == "__main__":
    test_reference_renderer_raw_vancouver_fallback()
    print("OK 契约1 reference_renderer raw_vancouver 回退")

    test_markdown_to_docx_a4_page_size()
    print("OK 契约2 markdown_to_docx A4 页面")

    test_abbreviation_hyphenated_full_name()
    print("OK 契约3 abbreviation_registry 连字符全称")

    test_check_quality_table_figure_dedup()
    print("OK 契约4 check_quality 表号+图号去重")

    print("ALL OK")
