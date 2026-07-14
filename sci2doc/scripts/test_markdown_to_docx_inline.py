#!/usr/bin/env python3
"""markdown_to_docx 行内解析 + 列表 + h5/h6 收敛 + 排版保真冒烟测试（Part3）。

改用共享 md_runs 后应满足：
  - 正文/标题/列表里 **粗**/__下划线__/`code`/[链接] 的字面标记全部去净，
    无残留 `*`/`#`/`` ` ``/`_`/`](http`。
  - `## 标题` 层级正确（Heading 2）；`##### h5` 收敛到 Heading 3 且不泄漏 `#`。
  - `- ` → List Bullet 段落、`1. ` → List Number 段落。
  - **粗** 渲染为 run.bold（不是字面星号）。
  - 排版仍走 style_profile：正文 run 中文字体=宋体(SimSun)、首行缩进未清零、行距未清零。

standalone: `python3 test_markdown_to_docx_inline.py`。
"""
from __future__ import annotations

import os
import sys
import tempfile

from docx import Document
from docx.oxml.ns import qn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from markdown_to_docx import markdown_to_docx  # noqa: E402

MD = """# 第一章 转换测试

## 二级标题 __下划线__ 与 **粗体**

这是正文段落，含 **粗体** 和 __下划线强调__ 与 `code` 及 [链接](http://example.com)。

- 第一个要点 **重点**
- 第二个要点 __强调__

1. 有序第一条 `代码`
2. 有序第二条

##### 五级标题不应泄漏井号
"""


def _run_east_asia(run):
    rpr = run._element.find(qn("w:rPr"))
    if rpr is None:
        return None
    rfonts = rpr.find(qn("w:rFonts"))
    return rfonts.get(qn("w:eastAsia")) if rfonts is not None else None


def main():
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.docx")
        ok = markdown_to_docx(MD, out, project_root=td)
        assert ok, "markdown_to_docx 返回 False"
        doc = Document(out)

        paras = doc.paragraphs
        full = "".join(p.text for p in paras)

        # 1. 字面标记去净
        assert "**" not in full, f"残留 **: {full!r}"
        assert "__" not in full, f"残留 __: {full!r}"
        assert "#" not in full, f"残留 #: {full!r}"
        assert "`" not in full, f"残留反引号: {full!r}"
        assert "](http" not in full, f"残留链接语法: {full!r}"
        assert "_" not in full, f"残留下划线: {full!r}"
        assert "http://example.com" not in full, "链接 URL 未丢弃（应只留文字）"
        assert "链接" in full, "链接文字丢失"
        assert "五级标题不应泄漏井号" in full

        # 2. 标题层级
        def _find(text_sub):
            return next(p for p in paras if text_sub in p.text)

        assert _find("第一章 转换测试").style.name == "Heading 1"
        assert _find("二级标题").style.name == "Heading 2"
        # h5 收敛到已有最深层级 Heading 3
        assert _find("五级标题不应泄漏井号").style.name == "Heading 3", \
            _find("五级标题不应泄漏井号").style.name

        # 3. 列表样式
        bullet_paras = [p for p in paras if p.style.name == "List Bullet"]
        number_paras = [p for p in paras if p.style.name == "List Number"]
        assert len(bullet_paras) == 2, [p.text for p in bullet_paras]
        assert len(number_paras) == 2, [p.text for p in number_paras]
        assert "第一个要点" in bullet_paras[0].text and "**" not in bullet_paras[0].text

        # 4. 粗体是 run（不是字面星号）
        body = _find("这是正文段落")
        assert any(r.bold and "粗体" in r.text for r in body.runs), \
            [(r.text, r.bold) for r in body.runs]

        # 5. 排版保真：正文 run 宋体 + 首行缩进/行距未清零
        assert _run_east_asia(body.runs[0]) == "SimSun", _run_east_asia(body.runs[0])
        pf = body.paragraph_format
        assert pf.first_line_indent is not None and pf.first_line_indent > 0, \
            f"首行缩进被清零: {pf.first_line_indent}"
        assert pf.line_spacing is not None, "行距被清零"

    print("OK: markdown_to_docx inline via md_runs — markers stripped, h5→h3, "
          "list styles, bold-as-run, 宋体/首行缩进/行距 未被清零")


if __name__ == "__main__":
    main()
