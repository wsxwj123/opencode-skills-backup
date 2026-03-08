#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import normalize_ws, read_json, write_json, write_text


HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(references|参考文献)\s*$", re.IGNORECASE)
NEXT_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S+")
NUMBERED_REF_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")


def normalize_reference_key(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"doi:\s*10\.\S+", "", lowered)
    lowered = re.sub(r"pmid:\s*\d+", "", lowered)
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def extract_existing_references(lines: list[str]) -> tuple[int | None, int | None, list[str]]:
    start = None
    end = None
    for idx, line in enumerate(lines):
        if HEADING_RE.match(line):
            start = idx
            break
    if start is None:
        return None, None, []
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if NEXT_HEADING_RE.match(lines[idx]):
            end = idx
            break
    return start, end, [line for line in lines[start + 1 : end] if normalize_ws(line)]


def next_reference_number(existing_lines: list[str]) -> int:
    numbers = []
    for line in existing_lines:
        match = NUMBERED_REF_RE.match(line)
        if match:
            numbers.append(int(match.group(1)))
    return (max(numbers) + 1) if numbers else 1


def completed_citation_rows(project_root: Path) -> list[dict]:
    units = [read_json(path, {}) for path in sorted((project_root / "units").glob("*.json"))]
    validated = read_json(project_root / "paper_search_validated.json", {"results": []})
    row_map = {row.get("comment_id"): row for row in validated.get("results", [])}
    completed = []
    for unit in units:
        if unit.get("status") != "completed":
            continue
        if unit.get("editorial_intent") != "citation":
            continue
        row = row_map.get(unit.get("comment_id"))
        if row and row.get("guard_verified"):
            completed.append({"unit": unit, "row": row})
    return completed


def main() -> int:
    parser = argparse.ArgumentParser(description="Append validated revision citations into the merged manuscript references section")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    output_md = Path(args.output_md)
    if not output_md.exists():
        print('{"ok": true, "references_added": 0, "covered_comment_ids": []}')
        return 0

    text = output_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    start, end, existing_refs = extract_existing_references(lines)
    existing_keys = {normalize_reference_key(line): line for line in existing_refs}
    insertions = []
    covered_comment_ids = []
    next_num = next_reference_number(existing_refs)

    for item in completed_citation_rows(project_root):
        unit = item["unit"]
        row = item["row"]
        row_added = False
        for citation in row.get("citations", []):
            entry = normalize_ws(str(citation.get("reference_entry") or ""))
            if not entry:
                continue
            key = normalize_reference_key(entry)
            if key in existing_keys:
                row_added = True
                continue
            insertions.append(f"{next_num}. {entry}")
            existing_keys[key] = entry
            next_num += 1
            row_added = True
        if row_added:
            covered_comment_ids.append(unit.get("comment_id"))

    if insertions:
        if start is None:
            if lines and normalize_ws(lines[-1]):
                lines.append("")
            lines.extend(["## References", ""])
            lines.extend(insertions)
        else:
            new_lines = lines[:end]
            if new_lines and normalize_ws(new_lines[-1]):
                new_lines.append("")
            new_lines.extend(insertions)
            new_lines.extend(lines[end:])
            lines = new_lines
        write_text(output_md, "\n".join(lines).rstrip() + "\n")

    report = {
        "references_added": len(insertions),
        "covered_comment_ids": covered_comment_ids,
        "has_references_section": HEADING_RE.search(output_md.read_text(encoding="utf-8")) is not None,
    }
    write_json(project_root / "reference_sync_report.json", report)
    print(
        '{"ok": true, "references_added": %d, "covered_comment_ids": %s}'
        % (report["references_added"], covered_comment_ids)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
