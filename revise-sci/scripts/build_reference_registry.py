#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import normalize_ws, write_json


HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(references|reference|参考文献)\s*$", re.IGNORECASE)
NEXT_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S+")
NUMBERED_REF_RE = re.compile(r"^\s*(\d+)[\.\)]\s+(.*)$")
INLINE_NUMERIC_CITATION_RE = re.compile(r"\[(\d+(?:\s*[-,–]\s*\d+)*)\]")


def split_reference_section(text: str) -> tuple[str, list[str], bool]:
    lines = text.splitlines()
    start = None
    end = len(lines)
    for idx, line in enumerate(lines):
        if HEADING_RE.match(line):
            start = idx
            break
    if start is None:
        return text, [], False
    for idx in range(start + 1, len(lines)):
        if NEXT_HEADING_RE.match(lines[idx]):
            end = idx
            break
    body_lines = lines[:start] + lines[end:]
    reference_lines = [line for line in lines[start + 1 : end] if normalize_ws(line)]
    return "\n".join(body_lines), reference_lines, True


def normalize_reference_key(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"doi:\s*10\.\S+", "", lowered)
    lowered = re.sub(r"pmid:\s*\d+", "", lowered)
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def build_registry(reference_lines: list[str]) -> list[dict]:
    registry: list[dict] = []
    next_number = 1
    for line in reference_lines:
        match = NUMBERED_REF_RE.match(line)
        if match:
            number = int(match.group(1))
            raw_text = normalize_ws(match.group(2))
            next_number = max(next_number, number + 1)
        else:
            number = next_number
            raw_text = normalize_ws(line)
            next_number += 1
        registry.append(
            {
                "reference_number": number,
                "raw_text": raw_text,
                "normalized_key": normalize_reference_key(raw_text),
                "provider_family": "user-provided",
                "source_tier": "manuscript-reference",
                "verified": False,
            }
        )
    return registry


def expand_citation_numbers(payload: str) -> list[int]:
    numbers: list[int] = []
    for chunk in re.split(r"\s*,\s*", payload.replace("–", "-").strip()):
        if not chunk:
            continue
        if "-" in chunk:
            start_str, end_str = [part.strip() for part in chunk.split("-", 1)]
            if start_str.isdigit() and end_str.isdigit():
                start = int(start_str)
                end = int(end_str)
                if start <= end:
                    numbers.extend(range(start, end + 1))
                else:
                    numbers.extend([start, end])
            continue
        if chunk.isdigit():
            numbers.append(int(chunk))
    return numbers


def detect_cited_numbers(body_text: str) -> list[int]:
    cited = set()
    for match in INLINE_NUMERIC_CITATION_RE.finditer(body_text):
        cited.update(expand_citation_numbers(match.group(1)))
    return sorted(cited)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical reference registry and coverage audit from merged manuscript markdown")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    output_md = Path(args.output_md)
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    if not output_md.exists():
        write_json(data_dir / "reference_registry.json", [])
        report = {
            "ok": True,
            "citation_style": "none",
            "references_section_found": False,
            "reference_entries": 0,
            "cited_numbers": [],
            "available_reference_numbers": [],
            "missing_reference_numbers": [],
        }
        write_json(data_dir / "reference_coverage_audit.json", report)
        print(json.dumps({"ok": True, "reference_entries": 0, "cited_numbers": 0}, ensure_ascii=False))
        return 0

    text = output_md.read_text(encoding="utf-8")
    body_text, reference_lines, references_found = split_reference_section(text)
    registry = build_registry(reference_lines)
    write_json(data_dir / "reference_registry.json", registry)

    cited_numbers = detect_cited_numbers(body_text)
    available_numbers = sorted({entry["reference_number"] for entry in registry})
    missing_numbers = [number for number in cited_numbers if number not in set(available_numbers)]
    citation_style = "numeric" if cited_numbers else "none"
    report = {
        "ok": not missing_numbers,
        "citation_style": citation_style,
        "references_section_found": references_found,
        "reference_entries": len(registry),
        "cited_numbers": cited_numbers,
        "available_reference_numbers": available_numbers,
        "missing_reference_numbers": missing_numbers,
        "max_cited_number": max(cited_numbers) if cited_numbers else 0,
    }
    write_json(data_dir / "reference_coverage_audit.json", report)
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "reference_entries": len(registry),
                "cited_numbers": len(cited_numbers),
                "missing_reference_numbers": missing_numbers,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
