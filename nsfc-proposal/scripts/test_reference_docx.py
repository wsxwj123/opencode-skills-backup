#!/usr/bin/env python3
"""回归测试：make_reference_docx.py 的 apply_styles 字体/间距锁定 + 幂等。

自包含、纯 assert。以技能自带 templates/reference.docx 为基线，复制到临时目录后改样式再检查
（绝不改动原始模板）；跑完自动清理。需 python-docx，缺则 print skip 并 return 0（不算 fail）。
覆盖：
  apply_styles 后 —— 正文 Normal 西文=Times New Roman / eastAsia=宋体 / 12pt；
                     标题 Heading 1 eastAsia=黑体；Bibliography 段后距=6pt。
  幂等 —— 连跑两次，字体/字号/间距一致。
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

TEMPLATE = _HERE.parent / "templates" / "reference.docx"


def _east_asia(style, qn) -> str | None:
    rpr = style.element.find(qn("w:rPr"))
    if rpr is None:
        return None
    rfonts = rpr.find(qn("w:rFonts"))
    return rfonts.get(qn("w:eastAsia")) if rfonts is not None else None


def main() -> int:
    try:
        import docx
        from docx.oxml.ns import qn
        from docx.shared import Pt
    except ImportError:
        print("test_reference_docx: SKIP (python-docx 未安装)")
        return 0

    import make_reference_docx as mrd

    if not TEMPLATE.exists():
        print(f"test_reference_docx: SKIP (基线模板缺失 {TEMPLATE})")
        return 0

    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "reference.docx"
        shutil.copy2(TEMPLATE, work)

        def apply_and_read() -> dict:
            d = docx.Document(str(work))
            mrd.apply_styles(d)
            d.save(str(work))
            d = docx.Document(str(work))
            normal = d.styles["Normal"]
            return {
                "normal_western": normal.font.name,
                "normal_ea": _east_asia(normal, qn),
                "normal_size": normal.font.size,
                "h1_ea": _east_asia(d.styles["Heading 1"], qn),
                "biblio_after": d.styles["Bibliography"].paragraph_format.space_after,
            }

        first = apply_and_read()
        assert first["normal_western"] == "Times New Roman", first["normal_western"]
        assert first["normal_ea"] == "宋体", first["normal_ea"]
        assert first["normal_size"] == Pt(12), f"正文应 12pt(小四): {first['normal_size']}"
        assert first["h1_ea"] == "黑体", first["h1_ea"]
        assert first["biblio_after"] == Pt(6), f"Bibliography 段后距应 6pt: {first['biblio_after']}"

        # 幂等：再跑一次结果一致
        second = apply_and_read()
        assert second == first, f"apply_styles 非幂等: {first} vs {second}"

    print("apply_styles 字体/间距锁定 + 幂等：OK")
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
