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
    idx = 0
    for block in blocks:
        if block["kind"] == "heading":
            current_heading = block["text"]
            current_type = infer_section_type(current_heading)
            continue
        raw = block["text"]
        units.append(
            {
                "idx": idx,
                "raw_text": raw,
                "heading": current_heading,
                "section_type": current_type,
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
