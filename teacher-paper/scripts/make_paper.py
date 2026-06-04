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
  "answers": [ <block>, ... ],   # 参考答案及解析的有序内容块
  "meta":    { "page_number": true, ... }  # 可选；page_number=false 关闭页码
}

block 类型（type 字段）——试卷与答案通用：
  {"type":"title","text":"..."}                          大标题（居中,黑体小二）
  {"type":"subtitle","text":"（满分120分 时间120分钟）"}  副标题（居中,小四）
  {"type":"info"}                                         学校/班级/姓名/考号/座位号 填写行
  {"type":"sealing"}                                      密封线（印刷版横排虚线，仅试卷）
  {"type":"notice","items":["...","..."]}                注意事项编号列表
  {"type":"section","text":"一、积累运用（20分）"}        大题标题（黑体四号）
  {"type":"sub","text":"（一）积累"}                      小标题（黑体五号）
  {"type":"para","text":"...","indent":true}             正文段落,indent=首行缩进
  {"type":"material","label":"【材料一】","title":"老街","author":"",
   "paras":["...","..."],"source":"（选自《读者》2024年第6期）",
   "layout":"prose","font":"楷体"}                        阅读选文（楷体正文）
        - label "【材料一】" 左对齐顶格（宋体）
        - title/author 楷体居中（所有材料一律居中——文言文/小说/散文/古诗词都如此）
        - paras 正文：
            layout="verse"   → 古诗词，整段居中（每行 5/7 字整齐）
            其它/默认/classical → 楷体两端对齐 + 首行缩进2字（更易读）
        - source → 出处标注，右对齐宋体（非连/小说/古诗文/名著必标）
        - 选文正文默认楷体，可用 font 覆盖
  {"type":"table","rows":[["a","b"],["c","d"]],"header":true}  表格
  {"type":"question","num":"1","score":"（2分）","text":"..."}  题干
  {"type":"options","items":["A. ...","B. ...","C. ...","D. ..."]}  选项（每项一行）
  {"type":"blank_lines","count":3}                       答题横线 N 行
  {"type":"essay_grid","note":"...","cols":20,"rows":30}  作文方格纸(真格子,默认20×30=600格)
  {"type":"figure","kind":"function","funcs":["x**2-2*x-3"],"xrange":[-3,5],"alt":"..."}
        理科/地理配图：kind=function/geometry/number_line/bar/line/pie/scatter/vector/climate/pyramid → matplotlib自动画；
        或给 "src":"图片路径"(用户提供的电路/化学结构/装置图)直接插入；都没有则降级［图：alt］占位。
  {"type":"formula","latex":"\\int_0^1 x^2\\,dx=\\frac13","alt":"..."}  复杂公式(mathtext渲图);简单公式直接Unicode写题干
  {"type":"answer","num":"1","score":"（2分）","text":"..."}    答案条目
  {"type":"analysis","text":"..."}                       解析/评分说明
  {"type":"spacer"}                                      空行
  {"type":"pagebreak"}                                   分页
"""

# Windows 控制台默认 GBK：强制 stdout/stderr 用 UTF-8，避免中文 print 乱码（幂等，mac/Linux 无副作用）
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
import sys
import os
import re
import json

try:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("[缺少依赖] 需要 python-docx。请运行：pip3 install python-docx")
    sys.exit(1)


# 字体常量（对标 2025 长沙中考真题原卷版排版）：
# 标题/大题/小题用宋体加粗，正文题干用宋体，阅读选文正文用楷体。
SONGTI = "宋体"
HEITI = "黑体"
KAITI = "楷体"

_CJK = re.compile(r"[一-鿿]")


def _num(v, default):
    """把可能是字符串/None 的数值安全转 float，失败回退 default（防 Cm(非数值) 崩）。"""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def normalize_quotes(text):
    """规范中文引号，修正部分模型（如 deepseek）把书名/称谓写成单引号 '我的母亲'
    的问题。规则（保守，避免破坏正确的引号嵌套与英文缩写）：
    1. ASCII 直双引号 " → 交替成中文弯双引号 “ ”；
    2. 含中文、且成对（偶数个）的 ASCII 直单引号 ' → 交替成中文双引号（命题里
       单引号包中文基本都是该用双引号的误写）；
    3. 文本只有中文单引号 ‘ ’ 而无中文双引号时，单引号被误当主引号 → 升级为双引号。
    正确的双内嵌单（如 “他说‘好’”）因双引号已存在而被原样保留。"""
    if not text or not _CJK.search(text):
        return text  # 不含中文的纯英文/数字文本不动，避免误伤英文撇号
    if '"' in text:                                   # 1) ASCII 直双引号交替
        out, open_d = [], True
        for ch in text:
            if ch == '"':
                out.append("“" if open_d else "”")
                open_d = not open_d
            else:
                out.append(ch)
        text = "".join(out)
    sgl = text.count("'")                              # 2) 成对 ASCII 直单引号
    if sgl >= 2 and sgl % 2 == 0:
        out, open_d = [], True
        for ch in text:
            if ch == "'":
                out.append("“" if open_d else "”")
                open_d = not open_d
            else:
                out.append(ch)
        text = "".join(out)
    if ("‘" in text or "’" in text) and ("“" not in text and "”" not in text):
        text = text.replace("‘", "“").replace("’", "”")  # 3) 单引号误当主引号
    return text


def set_font(run, name=SONGTI, size=10.5, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    # 用官方 API 确保 rPr 存在，避免依赖赋值副作用隐式创建（否则 rPr 为 None 会崩）
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)


def add_para(doc, text="", align=None, indent_chars=0, size=10.5,
             name=SONGTI, bold=False, space_after=4):
    """段落输出。align 默认 None → 两端对齐（justify），符合中文试卷惯例；
    指定 'center'/'right' 用于标题/出处；'left' 显式左对齐（极少用）。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.5
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif align == "left":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    else:
        # 默认两端对齐：中文试卷的题干/选项/解析都按 justify 排版才整齐
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent_chars:
        p.paragraph_format.first_line_indent = Pt(size * indent_chars)
    if text:
        # 先规范中文引号，再保留文本内换行：拆成多行，行间插软换行，避免 \n 被吞成空格
        parts = normalize_quotes(str(text)).split("\n")
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


def add_essay_lines(doc, line_count=30):
    """生成作文横线作答区：line_count 行下划线，每行约一行字宽。
    替代方格纸——按教师反馈，方格纸排版易错且打印后学生未必受用；
    Word 横线作答更通用。line_count 夹紧到 1-80 行，避免异常输入卡死。"""
    try:
        n = int(line_count)
    except (TypeError, ValueError):
        n = 30
    n = max(1, min(n, 80))
    for _ in range(n):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 2.0   # 行距留出书写空间
        r = p.add_run("_" * 46)
        set_font(r, size=10.5)


_KNOWN_TYPES = {"title", "subtitle", "info", "sealing", "notice", "section",
                "sub", "para", "material", "table", "question", "options",
                "blank_lines", "essay_grid", "answer", "analysis", "figure",
                "formula", "spacer", "pagebreak"}


def render(doc, blocks):
    for b in blocks:
        if not isinstance(b, dict):
            print(f"[make_paper 警告] 跳过非 dict 脏块：{type(b).__name__}={b!r}"[:120],
                  file=sys.stderr)
            continue
        t = b.get("type")
        if t not in _KNOWN_TYPES:
            # 未知 type 静默丢弃会让题目「凭空消失」却 build 报成功——必须明确报。
            preview = (b.get("text") or b.get("title")
                       or str(b.get("spec", "")) or "")[:60]
            print(f"[make_paper 警告] 未知 block type={t!r}（已忽略，内容：{preview}）。"
                  f"合法 type 见 make_paper.py 顶部文档；"
                  f"常见错用：stem→question, choice→options。", file=sys.stderr)
            continue
        if t == "title":
            # 真题：大标题 宋体三号(16)加粗居中
            add_para(doc, b.get("text", ""), align="center", size=16, name=SONGTI,
                     bold=True, space_after=6)
        elif t == "subtitle":
            add_para(doc, b.get("text", ""), align="center", size=12, space_after=8)
        elif t == "info":
            add_para(doc,
                     "学校__________ 班级__________ 姓名__________ "
                     "考号__________ 座位号______",
                     align="center", size=10.5, space_after=10)
        elif t == "sealing":
            _add_sealing_line(doc)
        elif t == "notice":
            # 真题：注意事项 宋体小四(12)加粗
            add_para(doc, "注意事项：", size=12, name=SONGTI, bold=True,
                     space_after=2)
            for i, it in enumerate(b.get("items", []), 1):
                add_para(doc, f"{i}.{it}", size=10.5, space_after=1)
        elif t == "section":
            # 真题：大题标题 宋体小四(12)加粗
            add_para(doc, b.get("text", ""), size=12, name=SONGTI, bold=True,
                     space_after=4)
        elif t == "sub":
            # 真题：小标题 宋体小四(12)加粗
            add_para(doc, b.get("text", ""), size=12, name=SONGTI, bold=True,
                     space_after=3)
        elif t == "para":
            add_para(doc, b.get("text", ""), indent_chars=2 if b.get("indent") else 0)
        elif t == "material":
            # 真题排版（按教师约定）：
            #   - 所有材料的 label/title/author 一律居中（无论文体）
            #   - 正文：
            #       layout="verse"  古诗词 → 整段居中（每行 5/7 字整齐）
            #       其它（prose/classical/默认）→ 楷体两端对齐 + 首行缩进 2 字
            #     文言文/小说/散文/非连/作文材料统一走两端对齐，长段更易读。
            #   - 出处：右对齐宋体（独立段）
            # layout 兼容旧 "classical"——按 prose 渲染（不再让文言文整段居中）。
            layout = b.get("layout", "prose")
            pfont = b.get("font", KAITI)
            label = b.get("label", "")
            if label:
                # 【材料一】这类标签：左对齐顶格（不居中，对标真题）
                add_para(doc, label, align="left", size=10.5, name=SONGTI,
                         space_after=2)
            if b.get("title"):
                add_para(doc, b["title"], align="center", size=10.5, name=pfont,
                         space_after=1)
            if b.get("author"):
                add_para(doc, b["author"], align="center", size=10.5, name=pfont,
                         space_after=2)
            for para in b.get("paras", []):
                if layout == "verse":
                    add_para(doc, para, align="center", size=10.5, name=pfont)
                else:
                    # prose / classical / 其它 → 楷体两端对齐 + 首行缩进 2 字
                    add_para(doc, para, indent_chars=2, size=10.5, name=pfont)
            if b.get("source"):
                # 出处标注：右对齐宋体（如"（节选自《科学之友》2024年第6期）"）
                add_para(doc, b["source"], align="right", size=10.5,
                         name=SONGTI, space_after=4)
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
            # 历史 block 名保留以兼容；现统一按"横线作答"渲染（替代方格纸）。
            # 字段：line_count（行数，默认 30，按字数下限折算：约 600 字→ 30 行）；
            # 也接受老字段 rows 作为别名；cols 已无意义，忽略。
            note = b.get("note", "请在下面横线上作答。")
            add_para(doc, note, size=10.5, space_after=4)
            n = b.get("line_count") or b.get("rows") or 30
            add_essay_lines(doc, line_count=n)
        elif t == "answer":
            num = b.get("num", "")
            score = b.get("score", "")
            head = f"{num}. " if num else ""
            add_para(doc, f"{head}{score}{b.get('text','')}", size=10.5,
                     space_after=3)
        elif t == "analysis":
            add_para(doc, b.get("text", ""), size=10.5, space_after=4)
        elif t == "figure":
            # figure 块的 alt/src/caption/width_cm/kind 直接写在块顶层（见文档与 SKILL.md）；
            # 兼容历史上可能的 spec 嵌套写法。
            _render_figure(doc, b.get("spec", b))
        elif t == "formula":
            _render_formula(doc, b)
        elif t == "spacer":
            add_para(doc, "", space_after=4)
        elif t == "pagebreak":
            doc.add_page_break()


# 配图输出目录（main 按输出路径设定；理科配图渲染器 make_figure.py 后续接入）
FIG_DIR = None


def _render_figure(doc, spec):
    """插入配图，三级优先：① spec.src 指向已有图片（用户提供，如电路图/化学结构/
    历史地图）→ 直接插入；② 否则若 spec.kind 在 make_figure 可画范围（函数/几何/
    数轴/统计/受力）→ matplotlib 自动渲染；③ 都不行 → "［图：alt］" 文字占位，
    绝不阻断出卷。"""
    src = spec.get("src")
    width = _num(spec.get("width_cm"), 6.0)   # 字符串/None 宽度回退默认，不致好图被降级
    png = None
    if src and os.path.exists(src):
        png = src
    else:
        try:
            from make_figure import render_figure
            out_dir = FIG_DIR or os.getcwd()
            os.makedirs(out_dir, exist_ok=True)
            png = render_figure(spec, out_dir)
        except Exception as ex:
            # spec 字段错（如 geometry 的 points 应是 dict 却写成 list）会在此抛错
            # ——必须把异常透传，否则用户只看到无图，找不到原因。
            print(f"[make_figure 异常] kind={spec.get('kind')!r} spec 字段不符："
                  f"{type(ex).__name__}: {ex}。spec 示例见 SKILL.md 配图块小节"
                  f"（如 geometry 的 points 必须是 dict {{\"A\":[x,y]}}）。",
                  file=sys.stderr)
            png = None
    if png and os.path.exists(png):
        try:
            doc.add_picture(png, width=Cm(width))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if spec.get("caption"):
                add_para(doc, spec["caption"], align="center", size=9,
                         space_after=4)
            return
        except Exception:
            pass
    # 降级：占位 + alt 文字（无障碍/可手动补图）；同时向 stderr 出声，避免"静默没图"
    alt = spec.get("alt", "此处应有配图，请手动补充")
    print(f"[配图降级] 『{alt}』未渲染为图片，已用文字占位 ［图：{alt}］——"
          f"请确认已装 matplotlib 且 kind 受支持，或提供 src 图片后重跑。",
          file=sys.stderr)
    add_para(doc, f"［图：{alt}］", align="center", size=9, space_after=4)


def _render_formula(doc, b):
    """渲染数学/理科公式：复杂公式用 make_figure.render_formula（matplotlib mathtext）
    渲成图片居中插入；渲染不可用时降级为 alt 或 latex 原文文字。
    简单公式应直接用 Unicode 写进题干文本，不必走本块。"""
    latex = b.get("latex") or b.get("text", "")
    png = None
    try:
        from make_figure import render_formula
        out_dir = FIG_DIR or os.getcwd()
        os.makedirs(out_dir, exist_ok=True)
        png = render_formula(latex, out_dir)
    except Exception:
        png = None
    if png and os.path.exists(png):
        try:
            w = _num(b.get("width_cm"), 0)
            kw = {"width": Cm(w)} if w > 0 else {}
            doc.add_picture(png, **kw)  # 不指定则按 PNG 内嵌 dpi 取自然尺寸
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            return
        except Exception:
            pass
    add_para(doc, b.get("alt") or latex, align="center", size=10.5)


def _add_sealing_line(doc):
    """密封线（横排印刷版）：填写区下方一条带提示的虚线，提示密封线内不要答题。
    真考卷的竖排左边距密封线在 Word 里实现脆弱，这里用可靠的横排印刷版替代。"""
    add_para(doc,
             "…………………………密封…………线…………内…………不…………要…………"
             "答…………题…………………………",
             align="center", size=9, name=SONGTI, space_after=2)


def _add_page_footer(doc):
    """给每个 section 的页脚加居中页码「第 X 页　共 Y 页」（用 Word 域，打开自动更新）。"""
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in list(p.runs):                       # 清空已有内容
            r._element.getparent().remove(r._element)

        def _field(instr):
            run = p.add_run()
            set_font(run, size=9)
            begin = OxmlElement("w:fldChar")
            begin.set(qn("w:fldCharType"), "begin")
            instr_el = OxmlElement("w:instrText")
            instr_el.set(qn("xml:space"), "preserve")
            instr_el.text = instr
            end = OxmlElement("w:fldChar")
            end.set(qn("w:fldCharType"), "end")
            run._r.append(begin)
            run._r.append(instr_el)
            run._r.append(end)

        r1 = p.add_run("第 ")
        set_font(r1, size=9)
        _field("PAGE")
        r2 = p.add_run(" 页　共 ")
        set_font(r2, size=9)
        _field("NUMPAGES")
        r3 = p.add_run(" 页")
        set_font(r3, size=9)


def new_doc():
    doc = Document()
    sec = doc.sections[0]
    # 页边距对标 2025 长沙中考真题原卷版（上1.61/下2.54/左右1.91 cm）
    sec.top_margin = Cm(1.61)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(1.91)
    sec.right_margin = Cm(1.91)
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

    # 配图缓存目录：输出目录下的 figures/
    global FIG_DIR
    FIG_DIR = os.path.join(
        os.path.dirname(os.path.abspath(data.get("paper_path", "."))), "figures")

    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    want_page_num = meta.get("page_number", True)  # 默认加页码

    paper = new_doc()
    render(paper, data.get("paper", []))
    if want_page_num:
        _add_page_footer(paper)
    paper_path = data.get("paper_path", "试卷.docx")
    _ensure_dir(paper_path)
    paper.save(paper_path)

    ans = new_doc()
    render(ans, data.get("answers", []))
    if want_page_num:
        _add_page_footer(ans)
    ans_path = data.get("answer_path", "参考答案及解析.docx")
    _ensure_dir(ans_path)
    ans.save(ans_path)

    print(f"[完成] 试卷已生成：{paper_path}")
    print(f"[完成] 参考答案及解析已生成：{ans_path}")


if __name__ == "__main__":
    main()
