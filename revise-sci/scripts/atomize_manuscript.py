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


def count_tracked_changes(docx_path: Path) -> dict:
    """统计 docx 未接受的修订痕迹。python-docx 不读 <w:ins> 插入文本,带修订痕迹的
    稿件会被静默丢字/串字(抽取残缺),原子化前须拦下。"""
    import zipfile, re
    if docx_path.suffix.lower() != ".docx":
        return {"ins": 0, "del": 0}
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
    except Exception:
        return {"ins": 0, "del": 0}
    return {
        "ins": len(re.findall(r"<w:ins[ >]", xml)),
        "del": len(re.findall(r"<w:del[ >]", xml)) + len(re.findall(r"<w:delText[ >]", xml)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomize manuscript and SI into markdown sections")
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--si", default="")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--allow-tracked-changes", action="store_true",
                        help="跳过修订痕迹拦截(仅在确认可接受丢字风险时使用)")
    args = parser.parse_args()

    # 🔴 修订痕迹拦截:tracked changes 会致 python-docx 静默丢字,fail-closed。
    if not args.allow_tracked_changes:
        for label, p in [("manuscript", args.manuscript), ("si", args.si)]:
            if not p:
                continue
            tc = count_tracked_changes(Path(p))
            if tc["ins"] or tc["del"]:
                print(json.dumps({
                    "ok": False, "error": "tracked_changes_present", "which": label,
                    "ins": tc["ins"], "del": tc["del"],
                    "message": (f"{label} docx 含未接受的修订痕迹: {tc['ins']} 插入 / {tc['del']} 删除。"
                                "python-docx 会静默丢弃插入文本致抽取残缺。请先在 Word 里【接受所有修订】"
                                "并关闭修订跟踪后重导入;或明知风险时加 --allow-tracked-changes。"),
                }, ensure_ascii=False))
                return 1

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
