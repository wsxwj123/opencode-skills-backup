#!/usr/bin/env python3
"""
试卷 Word 生成器 —— teacher-paper skill 自包含组件
输入一个 JSON 文件，输出两个 .docx：① 学生试卷 ② 参考答案及解析。
不依赖任何其它 skill，任何电脑装好 python-docx 即可运行。

用法：
    pip3 install python-docx
    python3 make_paper.py <content.json>

JSON 结构：
{
  "paper_path":  "九年级语文试卷.docx",          # 试卷输出文件名
  "answer_path": "九年级语文参考答案及解析.docx",  # 答案输出文件名
  "paper":   [ <block>, ... ],   # 学生试卷的有序内容块
  "answers": [ <block>, ... ]    # 参考答案及解析的有序内容块
}

block 类型（type 字段）——试卷与答案通用：
  {"type":"title","text":"..."}                          大标题（居中,黑体小二）
  {"type":"subtitle","text":"（满分120分 时间120分钟）"}  副标题（居中,小四）
  {"type":"info"}                                         学校/班级/姓名/考号 填写行
  {"type":"notice","items":["...","..."]}                注意事项编号列表
  {"type":"section","text":"一、积累运用（20分）"}        大题标题（黑体四号）
  {"type":"sub","text":"（一）积累"}                      小标题（黑体五号）
  {"type":"para","text":"...","indent":true}             正文段落,indent=首行缩进
  {"type":"material","label":"【材料一】","title":"老街",
   "author":"","paras":["...","..."]}                    阅读材料（缩进区块）
  {"type":"table","rows":[["a","b"],["c","d"]],"header":true}  表格
  {"type":"question","num":"1","score":"（2分）","text":"..."}  题干
  {"type":"options","items":["A. ...","B. ...","C. ...","D. ..."]}  选项（每项一行）
  {"type":"blank_lines","count":3}                       答题横线 N 行
  {"type":"essay_grid","note":"...","cols":20,"rows":30}  作文方格纸(真格子,默认20×30=600格)
  {"type":"answer","num":"1","score":"（2分）","text":"..."}    答案条目
  {"type":"analysis","text":"..."}                       解析/评分说明
  {"type":"spacer"}                                      空行
  {"type":"pagebreak"}                                   分页
"""
import sys
import os
import json

try:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
except ImportError:
    print("[缺少依赖] 需要 python-docx。请运行：pip3 install python-docx")
    sys.exit(1)


SONGTI = "宋体"
HEITI = "黑体"


def set_font(run, name=SONGTI, size=10.5, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    # 用官方 API 确保 rPr 存在，避免依赖赋值副作用隐式创建（否则 rPr 为 None 会崩）
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)


def add_para(doc, text="", align=None, indent_chars=0, size=10.5,
             name=SONGTI, bold=False, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.5
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if indent_chars:
        p.paragraph_format.first_line_indent = Pt(size * indent_chars)
    if text:
        # 保留文本内的换行符：拆成多行，行间插软换行，避免 \n 被吞成空格
        parts = str(text).split("\n")
        r = p.add_run(parts[0])
        set_font(r, name=name, size=size, bold=bold)
        for seg in parts[1:]:
            r.add_break()
            r = p.add_run(seg)
            set_font(r, name=name, size=size, bold=bold)
    return p


def add_table(doc, rows, header=False):
    rows = [r for r in (rows or []) if r]  # 过滤 None/空行，避免 len(None) 崩溃
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=ncol)
    t.style = "Table Grid"
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci in range(ncol):
            val = row[ci] if ci < len(row) else ""
            cells[ci].text = ""
            para = cells[ci].paragraphs[0]
            run = para.add_run(str(val))
            set_font(run, size=10.5, bold=(header and ri == 0))


def add_essay_grid(doc, cols=20, rows=30):
    """生成作文方格纸：cols×rows 的正方格表格，每格供写一字。
    对异常入参做夹紧：列 8-30、行 1-60，避免 0/负数报错或超大表卡死。"""
    try:
        cols = int(cols)
        rows = int(rows)
    except (TypeError, ValueError):
        cols, rows = 20, 30
    cols = max(8, min(cols, 30))
    rows = max(1, min(rows, 60))
    t = doc.add_table(rows=rows, cols=cols)
    t.style = "Table Grid"
    t.autofit = False
    cell_w = Cm(0.75)  # 每格边长，20列约15cm，适配A4正文宽
    for row in t.rows:
        row.height = cell_w
        for cell in row.cells:
            cell.width = cell_w
            # 收紧单元格内边距，让格子接近正方形
            cell.paragraphs[0].paragraph_format.space_after = Pt(0)
            cell.paragraphs[0].paragraph_format.line_spacing = 1.0


def render(doc, blocks):
    for b in blocks:
        t = b.get("type")
        if t == "title":
            add_para(doc, b["text"], align="center", size=18, name=HEITI,
                     bold=True, space_after=6)
        elif t == "subtitle":
            add_para(doc, b["text"], align="center", size=12, space_after=8)
        elif t == "info":
            add_para(doc,
                     "学校__________ 班级__________ "
                     "姓名__________ 考号__________",
                     align="center", size=10.5, space_after=10)
        elif t == "notice":
            add_para(doc, "注意事项：", size=10.5, name=HEITI, bold=True,
                     space_after=2)
            for i, it in enumerate(b.get("items", []), 1):
                add_para(doc, f"{i}.{it}", size=9, space_after=1)
        elif t == "section":
            add_para(doc, b["text"], size=14, name=HEITI, bold=True,
                     space_after=4)
        elif t == "sub":
            add_para(doc, b["text"], size=10.5, name=HEITI, bold=True,
                     space_after=3)
        elif t == "para":
            add_para(doc, b["text"], indent_chars=2 if b.get("indent") else 0)
        elif t == "material":
            label = b.get("label", "")
            if label:
                add_para(doc, label, size=10.5, name=HEITI, bold=True,
                         space_after=2)
            if b.get("title"):
                add_para(doc, b["title"], align="center", size=12, name=HEITI,
                         bold=True, space_after=1)
            if b.get("author"):
                add_para(doc, b["author"], align="center", size=10.5,
                         space_after=3)
            for para in b.get("paras", []):
                add_para(doc, para, indent_chars=2)
        elif t == "table":
            add_table(doc, b.get("rows", []), header=b.get("header", False))
            add_para(doc, "", space_after=2)
        elif t == "question":
            num = b.get("num", "")
            score = b.get("score", "")
            head = f"{num}. " if num else ""
            text = f"{head}{b.get('text','')}{score}"
            add_para(doc, text, size=10.5, space_after=3)
        elif t == "options":
            for opt in b.get("items", []):
                add_para(doc, opt, indent_chars=2, size=10.5, space_after=1)
        elif t == "blank_lines":
            for _ in range(b.get("count", 3)):
                add_para(doc, "_" * 46, size=10.5, space_after=6)
        elif t == "essay_grid":
            note = b.get("note", "请在作文格内作答。")
            add_para(doc, note, size=10.5, space_after=4)
            # 真作文方格纸：cols 列 × rows 行的网格表格（每格写一字）
            cols = b.get("cols", 20)
            rows = b.get("rows", 30)
            add_essay_grid(doc, cols=cols, rows=rows)
        elif t == "answer":
            num = b.get("num", "")
            score = b.get("score", "")
            head = f"{num}. " if num else ""
            add_para(doc, f"{head}{score}{b.get('text','')}", size=10.5,
                     space_after=3)
        elif t == "analysis":
            add_para(doc, b["text"], size=10.5, space_after=4)
        elif t == "spacer":
            add_para(doc, "", space_after=4)
        elif t == "pagebreak":
            doc.add_page_break()


def new_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)
    # 默认正文字体
    style = doc.styles["Normal"]
    style.font.name = SONGTI
    style.font.size = Pt(10.5)
    # get_or_add_rPr 避免 rPr 为 None 时崩溃（不同 python-docx 版本行为不一）
    style.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), SONGTI)
    return doc


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[错误] content.json 不是合法 JSON：{e}")
        sys.exit(1)
    if not isinstance(data, dict):
        print("[错误] content.json 顶层必须是对象 {paper_path, answer_path, paper, answers}")
        sys.exit(1)

    def _ensure_dir(path):
        d = os.path.dirname(os.path.abspath(path))
        if d:
            os.makedirs(d, exist_ok=True)

    paper = new_doc()
    render(paper, data.get("paper", []))
    paper_path = data.get("paper_path", "试卷.docx")
    _ensure_dir(paper_path)
    paper.save(paper_path)

    ans = new_doc()
    render(ans, data.get("answers", []))
    ans_path = data.get("answer_path", "参考答案及解析.docx")
    _ensure_dir(ans_path)
    ans.save(ans_path)

    print(f"[完成] 试卷已生成：{paper_path}")
    print(f"[完成] 参考答案及解析已生成：{ans_path}")


if __name__ == "__main__":
    main()
