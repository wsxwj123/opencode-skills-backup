#!/usr/bin/env python3
"""Atomize a finished manuscript into per-paragraph polish units.

输入一份已写完的稿子(md 或 docx),按段落原子化成 units/<idx>.json。
每个 unit 记录:raw_text、推断的 section_type、是否含引用/数值。
section_type 由最近的标题文本推断(intro/methods/results/discussion/abstract/other)。
脚本只做拆分与标注,不改任何文字。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import normalize_ws, numeric_tokens, read_docx_paragraphs, write_json

CITATION_RE = re.compile(r"\[\d+(?:\s*[-,]\s*\d+)*\]|\bdoi:\s*10\.\d", re.IGNORECASE)

SECTION_KEYWORDS = (
    ("abstract", ("abstract", "摘要")),
    ("intro", ("introduction", "background", "引言", "前言", "背景")),
    ("methods", ("methods", "materials and methods", "methodology", "experimental",
                 "材料与方法", "方法", "实验")),
    ("results", ("results", "findings", "结果")),
    ("discussion", ("discussion", "conclusion", "conclusions", "讨论", "结论")),
)


def infer_section_type(heading: str) -> str:
    h = normalize_ws(heading).lower()
    # strip leading numbering like "2." / "2.1"
    h = re.sub(r"^[\d.]+\s*", "", h)
    for section_type, keys in SECTION_KEYWORDS:
        for key in keys:
            if h == key or h.startswith(key):
                return section_type
    return "other"


# 内容式标题识别:许多 docx/稿子的标题不是 Word Heading 样式,而是普通短段落
# (如 "1. Introduction" / "2.1 Foo" / "Experimental Section")。
_NUMBERED_HEADING_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+\S")
_SECTION_NAME_RE = re.compile(
    r"^(abstract|introduction|background|results?(?:\s+and\s+discussion)?|discussion|"
    r"conclusions?|summary|methods?|materials\s+and\s+methods|methodology|"
    r"experimental(?:\s+section)?|references|acknowledge?ments|keywords|"
    r"supporting\s+information|author\s+contributions?|conflicts?\s+of\s+interest|"
    r"data\s+availability|"
    r"摘要|引言|前言|背景|方法|材料与方法|实验(?:部分)?|结果(?:与讨论)?|讨论|结论|参考文献|关键词)$",
    re.IGNORECASE,
)
_ABSTRACT_LEADIN_RE = re.compile(r"^(abstract|摘要)\s*[.:：]", re.IGNORECASE)
# 机构/地址行常以编号开头(如 "3 X University / X Key Laboratory of …"),含机构实体词则不算章节标题。
_AFFILIATION_HINT_RE = re.compile(
    r"\b(?:universit|institut|laborator|hospital|college|faculty|academ|ministr)\w*"
    r"|\b(?:department|school|center|centre|division)\s+(?:of|for)\b"
    r"|大学|学院|研究院|研究所|重点实验室|实验室|医院",
    re.IGNORECASE,
)


def looks_like_heading(text: str) -> bool:
    """非样式化的章节标题判定:短段落 + (编号开头 或 整行就是已知章节名)。"""
    t = normalize_ws(text)
    if not t or len(t.split()) > 10:
        return False
    core = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", t).strip().rstrip(".．")
    if (
        _NUMBERED_HEADING_RE.match(t)
        and 1 <= len(core.split()) <= 8
        and not _AFFILIATION_HINT_RE.search(t)  # 编号机构行不算标题
    ):
        return True
    if _SECTION_NAME_RE.match(core) and len(core.split()) <= 6:
        return True
    return False


# 非散文章节:其内容是清单/条目(参考文献、致谢、作者贡献、利益冲突、数据可用性、
# 补充材料、资助),不做语言润色,去AI/句长检测对它们不适用。
_NONPROSE_SECTION_RE = re.compile(
    r"^(references?|bibliography|acknowledge?ments?|author\s+contributions?|"
    r"conflicts?\s+of\s+interest|competing\s+interests?|data\s+availability|"
    r"supporting\s+information|supplementary(?:\s+\w+)?|funding|abbreviations?|"
    r"参考文献|致谢|作者贡献|利益冲突|数据可用性|补充材料|资助|缩略语)$",
    re.IGNORECASE,
)


def is_nonprose_section(heading: str) -> bool:
    core = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", normalize_ws(heading)).strip().rstrip(".．:：")
    return bool(_NONPROSE_SECTION_RE.match(core))


def is_markdown_heading(line: str) -> bool:
    return bool(re.match(r"^#{1,6}\s+\S", line))


def heading_text(line: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", line).strip()


def split_md_paragraphs(text: str) -> list[dict]:
    """Return ordered list of {'kind': 'heading'|'para', 'text': str}."""
    blocks: list[dict] = []
    buf: list[str] = []

    def flush() -> None:
        joined = normalize_ws(" ".join(buf))
        if joined:
            blocks.append({"kind": "para", "text": joined})
        buf.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if is_markdown_heading(line):
            flush()
            blocks.append({"kind": "heading", "text": heading_text(line)})
        elif not line.strip():
            flush()
        else:
            buf.append(line.strip())
    flush()
    return blocks


def split_docx_paragraphs(path: Path) -> list[dict]:
    blocks: list[dict] = []
    for row in read_docx_paragraphs(path):
        style = (row.get("style_name") or "").lower()
        text = normalize_ws(row.get("text", ""))
        if not text:
            continue
        if style.startswith("heading") or style == "title":
            blocks.append({"kind": "heading", "text": text})
        else:
            blocks.append({"kind": "para", "text": text})
    return blocks


def build_units(blocks: list[dict]) -> list[dict]:
    units: list[dict] = []
    current_heading = ""
    current_type = "other"
    current_prose = True
    idx = 0
    for block in blocks:
        # 样式化标题,或内容上像未样式化的章节标题,都当作标题处理
        if block["kind"] == "heading" or (
            block["kind"] == "para" and looks_like_heading(block["text"])
        ):
            current_heading = block["text"]
            current_type = infer_section_type(current_heading)
            current_prose = not is_nonprose_section(current_heading)
            continue
        raw = block["text"]
        # Abstract 常以行内引导词起头("Abstract. ..."),正文与标题同段,单独归类
        is_abstract = bool(_ABSTRACT_LEADIN_RE.match(raw))
        unit_type = "abstract" if is_abstract else current_type
        units.append(
            {
                "idx": idx,
                "raw_text": raw,
                "heading": current_heading,
                "section_type": unit_type,
                # prose=False 的段落(参考文献/致谢等)只保留不润色,去AI/句长检测豁免
                "prose": True if is_abstract else current_prose,
                "has_citation": bool(CITATION_RE.search(raw)),
                "has_numeric": bool(numeric_tokens(raw)),
                "word_count": len(raw.split()),
                "char_count": len(raw),
            }
        )
        idx += 1
    return units


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomize finished manuscript into per-paragraph polish units")
    parser.add_argument("--manuscript", required=True, help="input md or docx")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    src = Path(args.manuscript)
    project_root = Path(args.project_root)
    units_dir = project_root / "units"
    units_dir.mkdir(parents=True, exist_ok=True)

    if src.suffix.lower() == ".docx":
        blocks = split_docx_paragraphs(src)
    else:
        blocks = split_md_paragraphs(src.read_text(encoding="utf-8"))

    units = build_units(blocks)
    for unit in units:
        write_json(units_dir / f"{unit['idx']}.json", unit)

    index = {
        "source": str(src.resolve()),
        "unit_count": len(units),
        "units": [
            {"idx": u["idx"], "section_type": u["section_type"], "heading": u["heading"],
             "has_citation": u["has_citation"], "has_numeric": u["has_numeric"]}
            for u in units
        ],
    }
    write_json(project_root / "units_index.json", index)
    print(json.dumps({"ok": True, "unit_count": len(units)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
