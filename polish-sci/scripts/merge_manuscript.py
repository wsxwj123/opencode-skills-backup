#!/usr/bin/env python3
"""Merge polished units in order into polished_manuscript.md.

按 units_index 顺序合并 polished/<idx>.json 的 polished_text,在 section_type
变化处插入对应小节标题。可选 --docx 导出(需 python-docx;失败仅警告,md 仍产出)。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import read_json, write_text

SECTION_TITLE = {
    "abstract": "Abstract",
    "intro": "Introduction",
    "methods": "Methods",
    "results": "Results",
    "discussion": "Discussion",
    "other": "",
}


def build_markdown(project_root: Path) -> tuple[str, list[dict]]:
    index = read_json(project_root / "units_index.json", {"units": []})
    polished_dir = project_root / "polished"
    parts: list[str] = []
    ordered_units: list[dict] = []
    last_heading = None
    for entry in index.get("units", []):
        idx = entry["idx"]
        unit = read_json(polished_dir / f"{idx}.json", None)
        if unit is None:
            continue
        heading = unit.get("heading") or entry.get("heading") or ""
        if not heading:
            heading = SECTION_TITLE.get(unit.get("section_type", "other"), "")
        if heading and heading != last_heading:
            parts.append(f"## {heading}")
            last_heading = heading
        text = unit.get("polished_text", "").strip()
        if text:
            parts.append(text)
        ordered_units.append(unit)
    return "\n\n".join(p for p in parts if p).strip() + "\n", ordered_units


def export_docx(md_text: str, docx_path: Path) -> bool:
    try:
        from docx import Document
    except ImportError:
        return False
    doc = Document()
    for block in md_text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("## "):
            doc.add_heading(block[3:].strip(), level=1)
        else:
            doc.add_paragraph(block)
    doc.save(str(docx_path))
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge polished units into manuscript")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-md", default="")
    parser.add_argument("--docx", default="", help="optional docx output path")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    output_md = Path(args.output_md) if args.output_md else project_root / "polished_manuscript.md"
    md_text, units = build_markdown(project_root)
    write_text(output_md, md_text)

    docx_ok = None
    if args.docx:
        docx_ok = export_docx(md_text, Path(args.docx))

    print(json.dumps(
        {"ok": True, "output_md": str(output_md.resolve()), "units": len(units),
         "docx": (str(Path(args.docx).resolve()) if args.docx else None), "docx_ok": docx_ok},
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
