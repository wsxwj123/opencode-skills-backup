#!/usr/bin/env python3
"""Part3 自检：baked templates/reference.docx 正文段前段后清零，Bibliography 未被清零。

读回技能里已 bake 的模板，断言：
  - Normal / Body Text / First Paragraph 的 space_before/after == Pt(0)；
  - Bibliography 的 space_after 保留（>0），条目间不粘连；
  - body 字体仍为 Times New Roman（未被间距改动误伤）。
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "reference.docx"


def test_body_zero_bibliography_kept():
    doc = Document(str(TEMPLATE))
    names = {s.name for s in doc.styles}

    for n in ["Normal", "Body Text", "First Paragraph"]:
        assert n in names, f"缺 body 样式 {n}"
        pf = doc.styles[n].paragraph_format
        assert pf.space_before == Pt(0), f"{n} space_before 非 0: {pf.space_before}"
        assert pf.space_after == Pt(0), f"{n} space_after 非 0: {pf.space_after}"

    assert doc.styles["Normal"].font.name == "Times New Roman", "body 字体被误伤"

    if "Bibliography" in names:
        after = doc.styles["Bibliography"].paragraph_format.space_after
        assert after is not None and after > Pt(0), \
            f"Bibliography 被清零会导致条目粘连: {after}"


if __name__ == "__main__":
    test_body_zero_bibliography_kept()
    print("OK: reference.docx 正文零段距 + Bibliography 保留间距 + body 字体不变")
