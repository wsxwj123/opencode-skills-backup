#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import read_json, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge revised manuscript sections into a single markdown file")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    output_md = Path(args.output_md)
    index = read_json(project_root / "manuscript_section_index.json", {"sections": []})
    parts: list[str] = []
    for section in index.get("sections", []):
        parts.append((project_root / section["file"]).read_text(encoding="utf-8").strip())
    write_text(output_md, "\n\n".join(part for part in parts if part).strip() + "\n")
    print(json.dumps({"ok": True, "output_md": str(output_md.resolve()), "sections_merged": len(index.get("sections", []))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
