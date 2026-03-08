#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document

from common import read_json


def doc_for_template(template_path: str) -> Document:
    if template_path:
        return Document(template_path)
    return Document()


def markdown_to_docx(md_path: Path, docx_path: Path, template_path: str = "", page_break_before_comment: bool = False) -> None:
    doc = doc_for_template(template_path)
    lines = md_path.read_text(encoding="utf-8").splitlines()
    first_comment = True
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            doc.add_paragraph("")
            continue
        if line.startswith("### Comment") and page_break_before_comment:
            if first_comment:
                doc.add_page_break()
                first_comment = False
            else:
                doc.add_page_break()
        if line.startswith("#### "):
            doc.add_heading(line[5:], level=4)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        else:
            doc.add_paragraph(line)
    doc.save(str(docx_path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export markdown artifacts to docx")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-docx", required=True)
    parser.add_argument("--reference-docx", default="")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    output_md = Path(args.output_md)
    output_docx = Path(args.output_docx)
    response_md = project_root / "response_to_reviewers.md"
    response_docx = project_root / "response_to_reviewers.docx"

    markdown_to_docx(output_md, output_docx, args.reference_docx, page_break_before_comment=False)
    markdown_to_docx(response_md, response_docx, args.reference_docx, page_break_before_comment=True)

    state = read_json(project_root / "project_state.json", {})
    state.setdefault("outputs", {})
    state["outputs"]["response_md"] = str(response_md.resolve())
    state["outputs"]["response_docx"] = str(response_docx.resolve())
    state["outputs"]["output_md"] = str(output_md.resolve())
    state["outputs"]["output_docx"] = str(output_docx.resolve())
    (project_root / "project_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "response_docx": str(response_docx.resolve()), "output_docx": str(output_docx.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
