#!/usr/bin/env python3
"""Consistency checks across atomic response units."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_unit_text(unit: dict) -> str:
    c = unit.get("content", {})
    parts = [
        c.get("response_en", ""),
        c.get("revised_excerpt_en", ""),
        " ".join(c.get("notes_core_zh", [])),
        " ".join(c.get("notes_support_zh", [])),
    ]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Consistency checker for reviewer-response units")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--rules", default="")
    parser.add_argument("--fail-on-conflict", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root)
    rules_path = Path(args.rules) if args.rules else Path(__file__).resolve().parents[1] / "references" / "consistency-rules.json"
    rules = read_json(rules_path)

    units = [read_json(p) for p in sorted((root / "units").glob("*.json"))]
    text_by_unit = {u.get("unit_id", ""): collect_unit_text(u) for u in units}
    merged_text = "\n".join(text_by_unit.values())

    warnings: list[str] = []
    conflicts: list[str] = []

    for pat in rules.get("forbidden_phrase_patterns", []):
        if re.search(re.escape(pat), merged_text, flags=re.IGNORECASE):
            conflicts.append(f"Forbidden phrase detected: {pat}")

    for term_set in rules.get("conflict_term_sets", []):
        present = [t for t in term_set if re.search(re.escape(t), merged_text, flags=re.IGNORECASE)]
        if len(present) >= 2:
            conflicts.append(f"Conflicting terms co-exist: {', '.join(present)}")

    for marker in rules.get("required_markers", []):
        if marker not in merged_text:
            warnings.append(f"Required marker not found globally: {marker}")

    if conflicts:
        print("CONSISTENCY_CHECK: FAIL")
        for c in conflicts:
            print(f"- {c}")
        if warnings:
            for w in warnings:
                print(f"- WARN: {w}")
        return 2 if args.fail_on_conflict else 1

    print("CONSISTENCY_CHECK: PASS")
    if warnings:
        for w in warnings:
            print(f"- WARN: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
