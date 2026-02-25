#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown 转 Word 工具（应用中南大学样式）

功能：
1. 解析 Markdown 文本
2. 转换为 Word 文档
3. 自动应用中南大学博士论文样式
4. 处理图表占位符

作者：Sci2Doc Team
日期：2024-03-15
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import re
import sys
import os


# ---------------------------------------------------------------------------
# 三线表边框工具
# ---------------------------------------------------------------------------

def _set_cell_border(cell, **kwargs):
    """
    设置单元格边框。
    kwargs 示例: top={"sz": 12, "val": "single", "color": "000000"}
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn('w:tcBorders'))
    if tcBorders is None:
        tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}></w:tcBorders>')
        tcPr.append(tcBorders)
    for edge, attrs in kwargs.items():
        element = tcBorders.find(qn(f'w:{edge}'))
        if element is None:
            element = parse_xml(
                f'<w:{edge} {nsdecls("w")} w:val="{attrs["val"]}" '
                f'w:sz="{attrs["sz"]}" w:space="0" w:color="{attrs["color"]}"/>'
            )
            tcBorders.append(element)
        else:
            element.set(qn('w:val'), attrs['val'])
            element.set(qn('w:sz'), str(attrs['sz']))
            element.set(qn('w:color'), attrs['color'])


def apply_three_line_table_borders(table, header_rows=1):
    """
    对 Word 表格应用三线表边框：
    - 顶部边框 1.5pt (sz=12, 单位为 1/8 pt)
    - 表头与表体分隔线 0.5pt (sz=4)
    - 底部边框 1.5pt (sz=12)
    - 无竖线，无其他横线
    """
    THICK = {"sz": 12, "val": "single", "color": "000000"}  # 1.5pt
    THIN = {"sz": 4, "val": "single", "color": "000000"}    # 0.5pt
    NONE = {"sz": 0, "val": "none", "color": "FFFFFF"}

    num_rows = len(table.rows)
    for r_idx, row in enumerate(table.rows):
        for cell in row.cells:
            borders = {}
            # 竖线全部清除
            borders['left'] = NONE
            borders['right'] = NONE

            # 顶部边框：第一行顶部 1.5pt
            if r_idx == 0:
                borders['top'] = THICK
            else:
                borders['top'] = NONE

            # 表头分隔线：header_rows-1 行的底部 0.5pt
            if r_idx == header_rows - 1:
                borders['bottom'] = THIN
            # 底部边框：最后一行底部 1.5pt
            elif r_idx == num_rows - 1:
                borders['bottom'] = THICK
            else:
                borders['bottom'] = NONE

            _set_cell_border(cell, **borders)


# ---------------------------------------------------------------------------
# Markdown 管道表格解析
# ---------------------------------------------------------------------------

_PIPE_TABLE_RE = re.compile(r'^\|(.+)\|$')
_SEPARATOR_RE = re.compile(r'^[\|\s\-:]+$')


def _parse_pipe_row(line):
    """解析管道表格行，返回单元格文本列表。支持 \\| 转义。"""
    stripped = line.strip()
    m = _PIPE_TABLE_RE.match(stripped)
    if not m:
        return None
    inner = m.group(1)
    # 先将转义管道替换为占位符，分割后再还原
    placeholder = '\x00PIPE\x00'
    inner = inner.replace('\\|', placeholder)
    cells = [c.strip().replace(placeholder, '|') for c in inner.split('|')]
    return cells


def _is_separator_row(line):
    """判断是否为分隔行（如 |---|---|）"""
    return bool(_SEPARATOR_RE.match(line.strip()))


def parse_markdown_line(line):
    """
    解析 Markdown 行，识别类型
    
    Returns:
        tuple: (type, content, level)
    """
    line = line.rstrip()
    
    # 空行
    if not line.strip():
        return ('empty', '', 0)
    
    # 一级标题 # Title
    if line.startswith('# ') and not line.startswith('## '):
        return ('heading1', line[2:].strip(), 1)
    
    # 二级标题 ## Title
    elif line.startswith('## ') and not line.startswith('### '):
        return ('heading2', line[3:].strip(), 2)
    
    # 三级标题 ### Title
    elif line.startswith('### '):
        return ('heading3', line[4:].strip(), 3)
    
    # 图片占位符 [图 1-1：标题]
    elif re.match(r'\[图\s*\d+-\d+[：:].+\]', line):
        return ('figure', line.strip(), 0)
    
    # 表格占位符 [表 1-1：标题]
    elif re.match(r'\[表\s*\d+-\d+[：:].+\]', line):
        return ('table', line.strip(), 0)
    
    # 正文段落
    else:
        return ('paragraph', line.strip(), 0)


def set_run_font(run, latin, east_asia, size_pt, bold=None):
    """
    同时设置拉丁字体和东亚字体，避免 Word 回退到意外字体。
    """
    run.font.name = latin
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn('w:eastAsia'), east_asia)
    run.font.size = Pt(size_pt)
    if bold is not None:
        run.font.bold = bold


def apply_csu_heading1_style(paragraph):
    """应用一级标题样式"""
    paragraph.style = "Heading 1"
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(18)
    paragraph.paragraph_format.space_after = Pt(12)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    paragraph.paragraph_format.line_spacing = Pt(20)
    paragraph.paragraph_format.first_line_indent = Cm(0)
    
    for run in paragraph.runs:
        set_run_font(run, latin='Times New Roman', east_asia='SimHei', size_pt=16, bold=True)
        run.font.color.rgb = RGBColor(0, 0, 0)


def apply_csu_heading2_style(paragraph):
    """应用二级标题样式"""
    paragraph.style = "Heading 2"
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_before = Pt(10)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    paragraph.paragraph_format.line_spacing = Pt(20)
    paragraph.paragraph_format.first_line_indent = Cm(0)
    
    for run in paragraph.runs:
        set_run_font(run, latin='Times New Roman', east_asia='SimSun', size_pt=14, bold=False)


def apply_csu_heading3_style(paragraph):
    """应用三级标题样式"""
    paragraph.style = "Heading 3"
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_before = Pt(10)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    paragraph.paragraph_format.line_spacing = Pt(20)
    paragraph.paragraph_format.first_line_indent = Cm(0)
    
    for run in paragraph.runs:
        set_run_font(run, latin='Times New Roman', east_asia='SimSun', size_pt=12, bold=False)


def apply_csu_normal_style(paragraph):
    """应用正文样式"""
    paragraph.style = "Normal"
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    paragraph.paragraph_format.line_spacing = Pt(20)
    paragraph.paragraph_format.first_line_indent = Cm(0.74)  # 2字符
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    
    for run in paragraph.runs:
        set_run_font(run, latin='Times New Roman', east_asia='SimSun', size_pt=12, bold=False)


def apply_csu_caption_style(paragraph):
    """应用图表题注样式"""
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(12)
    
    for run in paragraph.runs:
        set_run_font(run, latin='Times New Roman', east_asia='KaiTi', size_pt=10.5, bold=False)


def markdown_to_docx(md_content, output_path, chapter_num=None):
    """
    将 Markdown 内容转换为 Word 文档
    
    Args:
        md_content: Markdown 文本内容
        output_path: 输出文件路径
        chapter_num: 章节号（可选）
    
    Returns:
        bool: 转换是否成功
    """
    try:
        # 创建文档
        doc = Document()
        
        # 设置页面
        section = doc.sections[0]
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(3.17)
        
        # 逐行解析，支持管道表格块
        lines = md_content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            line_type, content, level = parse_markdown_line(line)
            
            # 检测管道表格起始
            if _parse_pipe_row(line) is not None:
                # 收集连续的管道表格行
                table_lines = []
                while i < len(lines) and (_parse_pipe_row(lines[i]) is not None or _is_separator_row(lines[i])):
                    table_lines.append(lines[i])
                    i += 1
                
                # 解析表头和数据行（跳过分隔行）
                data_rows = []
                for tl in table_lines:
                    if _is_separator_row(tl):
                        continue
                    cells = _parse_pipe_row(tl)
                    if cells:
                        data_rows.append(cells)
                
                if data_rows:
                    # 统一列数
                    max_cols = max(len(r) for r in data_rows)
                    for r in data_rows:
                        while len(r) < max_cols:
                            r.append('')
                    
                    # 创建 Word 表格
                    table = doc.add_table(rows=len(data_rows), cols=max_cols)
                    for r_idx, row_data in enumerate(data_rows):
                        for c_idx, cell_text in enumerate(row_data):
                            cell = table.cell(r_idx, c_idx)
                            cell.text = cell_text
                            # 设置单元格字体
                            for paragraph in cell.paragraphs:
                                paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                for run in paragraph.runs:
                                    set_run_font(run, 'Times New Roman', 'SimSun', 10.5,
                                                 bold=(r_idx == 0))
                    
                    # 应用三线表边框
                    apply_three_line_table_borders(table, header_rows=1)
                continue
            
            if line_type == 'empty':
                i += 1
                continue
            
            elif line_type == 'heading1':
                para = doc.add_heading(content, level=1)
                apply_csu_heading1_style(para)
            
            elif line_type == 'heading2':
                para = doc.add_heading(content, level=2)
                apply_csu_heading2_style(para)
            
            elif line_type == 'heading3':
                para = doc.add_heading(content, level=3)
                apply_csu_heading3_style(para)
            
            elif line_type == 'figure' or line_type == 'table':
                para = doc.add_paragraph(content)
                apply_csu_caption_style(para)
            
            elif line_type == 'paragraph':
                if content:
                    para = doc.add_paragraph(content)
                    apply_csu_normal_style(para)
            
            i += 1
        
        # 保存文档
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        doc.save(output_path)
        print(f"✅ 转换成功：{output_path}")
        return True
    
    except Exception as e:
        print(f"❌ 转换失败：{str(e)}")
        return False


def convert_markdown_file(md_file_path, output_path=None):
    """
    转换 Markdown 文件
    
    Args:
        md_file_path: Markdown 文件路径
        output_path: 输出文件路径（可选）
    """
    if not os.path.exists(md_file_path):
        print(f"❌ 文件不存在：{md_file_path}")
        return False
    
    # 读取 Markdown 文件
    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 确定输出路径
    if output_path is None:
        output_path = md_file_path.replace('.md', '.docx')
    
    # 提取章节号（如果文件名包含）
    chapter_num = None
    match = re.search(r'第(\d+)章', os.path.basename(md_file_path))
    if match:
        chapter_num = int(match.group(1))
    
    # 执行转换
    return markdown_to_docx(md_content, output_path, chapter_num)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Markdown 转 Word（中南大学样式）')
    parser.add_argument('input', help='输入 Markdown 文件路径')
    parser.add_argument('-o', '--output', help='输出 Word 文件路径（可选）')
    parser.add_argument('-c', '--chapter', type=int, help='章节号（可选）')
    
    args = parser.parse_args()
    
    # 执行转换
    success = convert_markdown_file(args.input, args.output)
    
    if success:
        print("\n📋 样式说明：")
        print("  - 一级标题：三号黑体加粗，居中")
        print("  - 二级标题：四号宋体，顶格")
        print("  - 三级标题：小四号宋体，顶格")
        print("  - 正文：小四号宋体/Times New Roman，首行缩进")
        print("  - 图表题注：五号楷体，居中")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
