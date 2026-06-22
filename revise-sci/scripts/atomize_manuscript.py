#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import build_section_markdown, is_heading, normalize_ws, read_docx_paragraphs, slugify, write_json, write_text


def parse_sections(rows: list[dict], prefix: str, out_dir: Path) -> dict:
    sections: list[dict] = []
    current = {"heading": "Front matter", "paragraphs": [], "section_id": f"{prefix}-001"}

    def flush() -> None:
        if not current["paragraphs"] and current["heading"] == "Front matter" and sections:
            return
        section_number = len(sections) + 1
        heading_slug = slugify(current["heading"])
        current["section_id"] = f"{prefix}-{section_number:03d}"
        current["file"] = str(out_dir / f"{section_number:02d}-{heading_slug}.md")
        sections.append(dict(current))

    for row in rows:
        if is_heading(row):
            if current["paragraphs"]:
                flush()
            current = {"heading": row["text"], "paragraphs": [], "section_id": ""}
            continue
        current["paragraphs"].append(
            {
                "paragraph_index": row["paragraph_index"],
                "text": normalize_ws(row["text"]),
                "current_text": normalize_ws(row["text"]),
            }
        )
    flush()

    index_sections = []
    for section in sections:
        file_path = Path(section["file"])
        write_text(file_path, build_section_markdown(section))
        index_sections.append(
            {
                "section_id": section["section_id"],
                "heading": section["heading"],
                "file": str(file_path.relative_to(out_dir.parent)),
                "paragraphs": section["paragraphs"],
            }
        )
    return {"sections": index_sections}


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomize manuscript and SI into markdown sections")
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--si", default="")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    manuscript_dir = project_root / "manuscript_sections"
    si_dir = project_root / "si_sections"
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    si_dir.mkdir(parents=True, exist_ok=True)

    # inline_format=True 让原稿段落的 run 级 斜体/上下标/加粗 以行内标记进入 section
    # text/current_text,经 revise -> export 往返保住语义行内格式(与 polish 口径一致)。
    manuscript_index = parse_sections(read_docx_paragraphs(Path(args.manuscript), inline_format=True), "manuscript", manuscript_dir)
    write_json(project_root / "manuscript_section_index.json", manuscript_index)

    if args.si:
        si_index = parse_sections(read_docx_paragraphs(Path(args.si), inline_format=True), "si", si_dir)
    else:
        si_index = {"sections": []}
    write_json(project_root / "si_section_index.json", si_index)

    print(json.dumps({"ok": True, "manuscript_sections": len(manuscript_index["sections"]), "si_sections": len(si_index["sections"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
