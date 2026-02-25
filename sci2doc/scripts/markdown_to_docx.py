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
<<<<<<< Updated upstream
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
=======
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
>>>>>>> Stashed changes
import re
import sys
import os

try:
    from abbreviation_registry import load_registry, get_all as get_all_abbreviations
except Exception:  # pragma: no cover
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    if _script_dir not in sys.path:
        sys.path.insert(0, _script_dir)
    try:
        from abbreviation_registry import load_registry, get_all as get_all_abbreviations
    except ImportError:
        load_registry = None
        get_all_abbreviations = None


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


# ---------------------------------------------------------------------------
# 三线表工具
# ---------------------------------------------------------------------------


def _set_cell_border(cell, **kwargs):
    """
    设置单元格边框。

    kwargs 示例: top={"sz": 12, "val": "single", "color": "000000"}
    sz 单位为 1/8 pt，所以 12 = 1.5pt, 4 = 0.5pt
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge, attrs in kwargs.items():
        element = OxmlElement(f'w:{edge}')
        for attr_name, attr_val in attrs.items():
            element.set(qn(f'w:{attr_name}'), str(attr_val))
        tcBorders.append(element)
    tcPr.append(tcBorders)


def _no_border():
    return {"sz": "0", "val": "none", "color": "auto"}


def _thick_border():
    return {"sz": "12", "val": "single", "color": "000000"}  # 1.5pt


def _thin_border():
    return {"sz": "4", "val": "single", "color": "000000"}   # 0.5pt


def is_table_row(line):
    """检测是否为 Markdown 表格行: | col1 | col2 |"""
    stripped = line.strip()
    return stripped.startswith('|') and stripped.endswith('|') and stripped.count('|') >= 3


def is_table_separator(line):
    """检测是否为 Markdown 表格分隔行: |---|---|"""
    stripped = line.strip()
    if not (stripped.startswith('|') and stripped.endswith('|')):
        return False
    inner = stripped[1:-1]
    cells = inner.split('|')
    return all(re.match(r'^[\s\-:]+$', c) for c in cells)


def parse_table_rows(lines):
    """
    从连续的 Markdown 表格行中提取表头和数据行。

    Returns:
        tuple: (headers: list[str], rows: list[list[str]])
    """
    headers = []
    rows = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        cells = [c.strip() for c in stripped.strip('|').split('|')]
        if i == 0:
            headers = cells
        elif is_table_separator(line):
            continue
        else:
            rows.append(cells)
    return headers, rows


def create_three_line_table(doc, headers, rows, caption=None):
    """
    创建三线表格式的 Word 表格。

    - 顶线: 1.5pt
    - 表头下线: 0.5pt
    - 底线: 1.5pt
    - 无竖线

    Args:
        doc: Document 对象
        headers: 表头列表
        rows: 数据行列表
        caption: 表格标题（可选，置于表格上方）
    """
    # 添加标题（如果有）
    if caption:
        cap_para = doc.add_paragraph(caption)
        cap_para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_para.paragraph_format.space_before = Pt(6)
        cap_para.paragraph_format.space_after = Pt(3)
        cap_para.paragraph_format.first_line_indent = Cm(0)
        for run in cap_para.runs:
            set_run_font(run, latin='Times New Roman', east_asia='KaiTi', size_pt=10.5, bold=False)

    num_cols = len(headers)
    num_rows = 1 + len(rows)
    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 填充表头
    for j, header_text in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = header_text
        for paragraph in cell.paragraphs:
            paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                set_run_font(run, latin='Times New Roman', east_asia='SimSun', size_pt=10.5, bold=True)

    # 填充数据行
    for i, row_data in enumerate(rows):
        for j, cell_text in enumerate(row_data):
            if j < num_cols:
                cell = table.rows[i + 1].cells[j]
                cell.text = cell_text
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraph.runs:
                        set_run_font(run, latin='Times New Roman', east_asia='SimSun', size_pt=10.5, bold=False)

    # 应用三线表边框
    no = _no_border()
    thick = _thick_border()
    thin = _thin_border()

    for i, row in enumerate(table.rows):
        for j, cell in enumerate(row.cells):
            if i == 0:
                # 表头行：顶线粗，底线细，无竖线
                _set_cell_border(cell, top=thick, bottom=thin, left=no, right=no)
            elif i == num_rows - 1:
                # 最后一行：底线粗，无竖线
                _set_cell_border(cell, top=no, bottom=thick, left=no, right=no)
            else:
                # 中间行：无边框
                _set_cell_border(cell, top=no, bottom=no, left=no, right=no)

    return table


# ---------------------------------------------------------------------------
# 缩略语对照表页
# ---------------------------------------------------------------------------


def create_abbreviation_table_page(doc, project_root):
    """
    在文档中插入缩略语对照表页（三线表格式）。

    Args:
        doc: Document 对象
        project_root: 项目根目录（用于读取注册表）

    Returns:
        bool: 是否成功插入（无缩略语时返回 False）
    """
    if get_all_abbreviations is None:
        return False

    try:
        items = get_all_abbreviations(project_root)
    except Exception:
        return False

    if not items:
        return False

    # 标题
    heading = doc.add_heading("主要缩略语对照表", level=1)
    apply_csu_heading1_style(heading)

    # 构建表格数据
    headers = ["缩略语", "英文全称", "中文全称"]
    rows = []
    for abbr, info in items:
        full_en = info.get("full_en", "") or ""
        full_cn = info.get("full_cn", "") or ""
        rows.append([abbr, full_en, full_cn])

    create_three_line_table(doc, headers, rows)

    # 分页符
    doc.add_page_break()

    return True


def markdown_to_docx(md_content, output_path, chapter_num=None, project_root=None,
                     include_abbreviation_table=False):
    """
    将 Markdown 内容转换为 Word 文档
    
    Args:
        md_content: Markdown 文本内容
        output_path: 输出文件路径
        chapter_num: 章节号（可选）
        project_root: 项目根目录（可选，用于缩略语表）
        include_abbreviation_table: 是否在文档开头插入缩略语对照表
    
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

        # 插入缩略语对照表（如果需要）
        if include_abbreviation_table and project_root:
            create_abbreviation_table_page(doc, project_root)
        
<<<<<<< Updated upstream
        # 逐行解析，支持管道表格块
        lines = md_content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
=======
        # 逐行解析，支持表格累积
        lines = md_content.split('\n')
        table_buffer = []       # 累积连续的表格行
        table_caption = None    # 表格标题（表 X-X）

        def flush_table():
            """将累积的表格行渲染为三线表"""
            nonlocal table_buffer, table_caption
            if not table_buffer:
                return
            headers, rows = parse_table_rows(table_buffer)
            if headers:
                create_three_line_table(doc, headers, rows, caption=table_caption)
            table_buffer = []
            table_caption = None

        for line in lines:
            # 检测是否为表格行
            if is_table_row(line) or (table_buffer and is_table_separator(line)):
                table_buffer.append(line)
                continue

            # 非表格行：先刷新之前累积的表格
            if table_buffer:
                flush_table()

>>>>>>> Stashed changes
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
            
            elif line_type == 'figure':
                para = doc.add_paragraph(content)
                apply_csu_caption_style(para)
            
            elif line_type == 'table':
                # 表格占位符 [表 X-X：标题] — 可能是后续 Markdown 表格的标题
                table_caption = content.strip('[]')
                # 不立即渲染，等待后续表格行
            
            elif line_type == 'paragraph':
                if content:
                    para = doc.add_paragraph(content)
                    apply_csu_normal_style(para)
<<<<<<< Updated upstream
            
            i += 1
=======

        # 文件末尾：刷新残留的表格
        if table_buffer:
            flush_table()
>>>>>>> Stashed changes
        
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


def convert_markdown_file(md_file_path, output_path=None, project_root=None,
                          include_abbreviation_table=False):
    """
    转换 Markdown 文件
    
    Args:
        md_file_path: Markdown 文件路径
        output_path: 输出文件路径（可选）
        project_root: 项目根目录（可选，用于缩略语表）
        include_abbreviation_table: 是否插入缩略语对照表
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
    return markdown_to_docx(
        md_content, output_path, chapter_num=chapter_num,
        project_root=project_root,
        include_abbreviation_table=include_abbreviation_table,
    )


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Markdown 转 Word（中南大学样式）')
    parser.add_argument('input', help='输入 Markdown 文件路径')
    parser.add_argument('-o', '--output', help='输出 Word 文件路径（可选）')
    parser.add_argument('-c', '--chapter', type=int, help='章节号（可选）')
    parser.add_argument('--project-root', help='项目根目录（用于缩略语表）')
    parser.add_argument('--abbreviation-table', action='store_true',
                        help='在文档开头插入缩略语对照表')
    
    args = parser.parse_args()
    
    # 执行转换
    success = convert_markdown_file(
        args.input, args.output,
        project_root=args.project_root,
        include_abbreviation_table=args.abbreviation_table,
    )
    
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
