#!/usr/bin/env python3
"""为 pandoc 生成国自然中文标书的 reference.docx 样式模板。

锁定字体规范（国自然中文标书惯例）：
  - 正文：中文宋体、西文 Times New Roman、小四（12pt）
  - 各级标题：中文黑体、西文 Times New Roman，三号/小三/四号
  - 中文必须显式设置 w:eastAsia，否则 Word 会用默认字体回退（中文不走宋体/黑体）

幂等：对 templates/reference.docx 原地改样式后存回，重复运行结果一致。
字体/字号改这里的常量即可。
"""

from __future__ import annotations

from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.shared import Pt

# ── 字体常量 ───────────────────────────────────────────────
WESTERN_FONT = "Times New Roman"   # 全文西文字体
BODY_EAST_ASIA = "宋体"             # 正文中文字体（SimSun）
HEADING_EAST_ASIA = "黑体"          # 标题中文字体（SimHei）

# ── 字号常量（国自然习惯）────────────────────────────────
BODY_PT = 12   # 小四 = 12pt（正文）
H1_PT = 16     # 三号 ≈ 16pt
H2_PT = 15     # 小三 ≈ 15pt
H3_PT = 14     # 四号 ≈ 14pt
TITLE_PT = H1_PT

# 正文类样式（西文 TNR + eastAsia 宋体 + 小四）
BODY_STYLES = ["Normal", "Body Text", "First Paragraph", "Compact"]

# 标题类样式：(样式名, 字号, 是否加粗)
# 黑体本身够区分层级，国自然标题习惯不强制加粗，统一 bold=False
HEADING_STYLES = [
    ("Heading 1", H1_PT, False),
    ("Heading 2", H2_PT, False),
    ("Heading 3", H3_PT, False),
    ("Title", TITLE_PT, False),
]

REFERENCE_DOCX = Path(__file__).resolve().parent.parent / "templates" / "reference.docx"


def _set_east_asia(style, font_name: str) -> None:
    """显式写入 w:eastAsia，控制中文字体不回退。"""
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), font_name)


def _apply_western_and_size(style, size_pt: int) -> None:
    style.font.name = WESTERN_FONT  # 写 w:ascii / w:hAnsi
    style.font.size = Pt(size_pt)


def apply_styles(doc) -> None:
    for name in BODY_STYLES:
        style = doc.styles[name]
        _apply_western_and_size(style, BODY_PT)
        _set_east_asia(style, BODY_EAST_ASIA)

    for name, size_pt, bold in HEADING_STYLES:
        style = doc.styles[name]
        _apply_western_and_size(style, size_pt)
        _set_east_asia(style, HEADING_EAST_ASIA)
        style.font.bold = bold


def main() -> int:
    if not REFERENCE_DOCX.exists():
        raise SystemExit(
            f"未找到 {REFERENCE_DOCX}\n"
            "请先运行：pandoc --print-default-data-file reference.docx > "
            f"{REFERENCE_DOCX}"
        )
    doc = docx.Document(str(REFERENCE_DOCX))
    apply_styles(doc)
    doc.save(str(REFERENCE_DOCX))
    print(f"已写入字体样式：{REFERENCE_DOCX}")
    print(f"  正文 {BODY_STYLES}: 西文={WESTERN_FONT} 中文={BODY_EAST_ASIA} {BODY_PT}pt")
    print(f"  标题 H1/H2/H3/Title: 西文={WESTERN_FONT} 中文={HEADING_EAST_ASIA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
