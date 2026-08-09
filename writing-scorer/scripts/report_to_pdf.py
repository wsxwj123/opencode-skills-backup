#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评分报告 → PDF（纯机械转换：只排版转 PDF，不生成内容）。

用法：
  python3 report_to_pdf.py <报告文本文件|-> <输出PDF路径>
  python3 report_to_pdf.py --self-test <输出PDF路径>
  <报告文本文件> 传 "-" 时报告从 stdin 读入（仅供测试/管道；SKILL.md 一律走临时文件）。

行级轻量 markdown 识别：`#`~`###` 标题 / `【维度：…】` 维度 / `原文证据：…`、`>` 引用 /
`- `、`数字.` 列表 / 段落；`---` 忽略；未识别一律按段落，不报错不丢弃。
正文先 XML 转义（html.escape 内部保证 `&amp;` 最先转），杜绝 reportlab Paragraph
解析裸 `& < >` 报错，也避免字面 `&lt;` 二次转义。

退出码：0=成功（stdout 无输出，--self-test 除外输出产物路径）；
1=E-P2~E-P5；2=E-P1（参数数≠2 且非 --self-test）。错误文案精确照 .devflow/INTERFACE-PDF.md 第2节，
由脚本自身输出，SKILL.md 原样转发。
"""
import html
import os
import re
import sys

USAGE = "用法：python3 report_to_pdf.py <报告文本文件|-> <输出PDF路径>"

# 系统字体两级回退（本机已验证 STHeiti subfontIndex=0 渲染中文；缺时回退 Light）
FONT_CANDIDATES = (
    ("STHeitiMedium", "/System/Library/Fonts/STHeiti Medium.ttc", 0),
    ("STHeitiLight", "/System/Library/Fonts/STHeiti Light.ttc", 0),
)
TRIED_FONTS = "、".join(p for _, p, _ in FONT_CANDIDATES)

try:
    from reportlab.lib import colors, pagesizes
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
except ImportError:  # E-P4 覆盖 reportlab 导入失败
    print(f"PDF生成失败：中文字体不可用（{TRIED_FONTS}）")
    sys.exit(1)

SELF_TEST_SAMPLE = (
    "# 评分报告样例\n"
    "## 内容分析\n"
    "\n"
    "【维度：内容分析（13/16，档位：优秀，正常）】\n"
    "定分理由：深入段数3故取13分\n"
    "原文证据：[\"首段立论明确\"，\"论证层层推进\"]（一字不改）\n"
    "> 引用示例：论证结构完整、首尾呼应\n"
    "- 列表项一：论据充分，例证贴切\n"
    "- 列表项二：语言流畅，衔接自然\n"
    "3. 数字列表：综合评分 28/30\n"
    "普通段落：含特殊字符 & < > 与字面 &lt; 的转义测试。\n"
    "---\n"
    "末尾分隔线后的段落也应渲染。\n"
)


class InputError(Exception):   # E-P2 报告输入无效
    pass


class OutputError(Exception):  # E-P3 无法写入PDF
    pass


class FontError(Exception):    # E-P4 字体不可用
    pass


def sanitize_line(text):
    """剥离行内 markdown 标记后做 XML 转义。

    先剥 markdown 再转义（转义会引入 `&amp;` 等，干扰后续 markdown 正则）；XML 转义内部
    先转 `&` 再转 `<` `>`，保证 &amp; 最先转、不二次转义。
    """
    return html.escape(strip_inline_md(text))


def strip_inline_md(text):
    """剥离行内 markdown 标记，保留文字内容（行首标记已由 render 的行级识别处理）。

    顺序重要：先 `**` 后 `*`（否则 `**x**` 被 `*` 规则拆坏）。孤立 `*`（不成对）保留。
    """
    # 先处理成对粗体/斜体/删除线/代码：标记剥掉、中间文字保留
    for pat in (r"\*\*(.+?)\*\*", r"\*(.+?)\*", r"`(.+?)`", r"~~(.+?)~~"):
        text = re.sub(pat, r"\1", text)
    # 链接 [文本](url) → 文本
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 行内 `#`（非行首）：移除井号标记
    text = re.sub(r"(?<!^)#", "", text)
    return text


def register_font():
    """两级回退注册系统字体；都失败抛 FontError（E-P4）。"""
    tried = []
    for name, path, idx in FONT_CANDIDATES:
        if not os.path.exists(path):
            tried.append(path)
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, path, subfontIndex=idx))
            return name
        except Exception:
            tried.append(path)
    raise FontError("、".join(tried))


def render(text, font):
    """逐行分类成 Flowable；`---` 忽略；过滤后无可渲染抛 InputError。样式写死常量，零参数化。"""
    styles = {
        "title":     ParagraphStyle("title", fontName=font, fontSize=20, leading=28,
                                    alignment=TA_CENTER, spaceAfter=12),
        "heading":   ParagraphStyle("heading", fontName=font, fontSize=15, leading=22,
                                    spaceBefore=8, spaceAfter=4),
        "dimension": ParagraphStyle("dimension", fontName=font, fontSize=12, leading=20,
                                    spaceBefore=4, spaceAfter=4),
        "quote":     ParagraphStyle("quote", fontName=font, fontSize=10.5, leading=16,
                                    leftIndent=24, spaceAfter=4,
                                    textColor=colors.HexColor("#666666")),
        "list":      ParagraphStyle("list", fontName=font, fontSize=11, leading=18,
                                    leftIndent=18, spaceAfter=3),
        "body":      ParagraphStyle("body", fontName=font, fontSize=11, leading=18,
                                    spaceAfter=6),
    }
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or re.fullmatch(r"-{3,}", s):
            continue
        m = re.match(r"^(#{1,3})\s*(.*)$", s)
        if m:
            body = sanitize_line(m.group(2).strip())
            if not body:
                continue
            key = "title" if len(m.group(1)) == 1 else "heading"
            out.append(Paragraph(body, styles[key]))
            if key == "title":
                out.append(Spacer(1, 6))
            continue
        if s.startswith("【维度："):
            out.append(Paragraph(sanitize_line(s), styles["dimension"]))
            continue
        if s.startswith("原文证据："):
            # "原文证据：" 是报告内容标签而非 markdown 语法，保留整行不丢弃
            out.append(Paragraph(sanitize_line(s), styles["quote"]))
            continue
        m = re.match(r">\s*(.*)$", s)
        if m:
            body = sanitize_line(m.group(1).strip())
            if body:
                out.append(Paragraph(body, styles["quote"]))
            continue
        m = re.match(r"^([-*])\s+(.*)$", s)
        if m:
            out.append(Paragraph("• " + sanitize_line(m.group(2).strip()), styles["list"]))
            continue
        m = re.match(r"^(\d+[.、])\s*(.*)$", s)
        if m:
            out.append(Paragraph(f"{m.group(1)} " + sanitize_line(m.group(2).strip()), styles["list"]))
            continue
        out.append(Paragraph(sanitize_line(s), styles["body"]))
    if not out:
        raise InputError("报告为空或过滤后无可渲染内容")
    return out


def read_report(src):
    """读报告文本；`-` 走 stdin。不可读/为空 → InputError（E-P2）。"""
    if src == "-":
        text = sys.stdin.read()
        if not text.strip():
            raise InputError("报告为空")
        return text
    if not os.path.exists(src):
        raise InputError(f"文件不存在：{src}")
    if os.path.isdir(src):
        raise InputError(f"{src}是目录")
    if not os.access(src, os.R_OK):
        raise InputError(f"无法读取：{src}（权限不足）")
    with open(src, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if not text.strip():
        raise InputError("报告为空")
    return text


def write_pdf(out, flowables):
    """写 PDF；输出路径不可写 → OutputError（E-P3）。不自动建目录、不补 `.pdf` 后缀。"""
    if os.path.isdir(out):
        raise OutputError("路径是已存在的目录")
    parent = os.path.dirname(os.path.abspath(out))
    if not os.path.exists(parent):
        raise OutputError(f"父目录不存在：{parent}")
    if not os.access(parent, os.W_OK):
        raise OutputError(f"父目录无写权限：{parent}")
    doc = SimpleDocTemplate(out, pagesize=pagesizes.A4,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    doc.build(flowables)


def run(get_text, out):
    """渲染+写盘统一出口：契约异常映射为契约文案+退出码；意外异常走 E-P5（禁裸 traceback）。"""
    try:
        font = register_font()          # E-P4
        text = get_text()               # E-P2（不可读/为空）
        flowables = render(text, font)  # E-P2（过滤后无可渲染）
        write_pdf(out, flowables)       # E-P3
    except InputError as e:
        print(f"报告输入无效：{e}")
        sys.exit(1)
    except OutputError as e:
        print(f"无法写入PDF：{out}（{e}）")
        sys.exit(1)
    except FontError as e:
        print(f"PDF生成失败：中文字体不可用（{e}）")
        sys.exit(1)
    except Exception as e:              # E-P5 意外异常兜底
        print(f"PDF生成失败：{e}")
        sys.exit(1)


def main():
    argv = sys.argv[1:]
    if len(argv) == 2 and argv[0] == "--self-test":
        # 参数校验前特判：恰好 2 参数，不触发 E-P1
        run(lambda: SELF_TEST_SAMPLE, argv[1])
        print(argv[1])  # stdout 输出产物路径
        sys.exit(0)
    if len(argv) != 2:
        print(USAGE)                    # E-P1
        sys.exit(2)
    run(lambda: read_report(argv[0]), argv[1])
    sys.exit(0)


if __name__ == "__main__":
    main()
