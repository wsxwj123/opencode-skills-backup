#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def normalize(text):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", str(text).lower()).strip()


def extract_sections(storyline_path):
    text = Path(storyline_path).read_text(encoding="utf-8")
    sections = []
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            if title:
                sections.append(title)
    return sections


def section_keywords(section):
    words = [w for w in normalize(section).split() if len(w) >= 3]
    # Prefer the most discriminative first 6 keywords
    return words[:6]


def main():
    parser = argparse.ArgumentParser(description="Auto-tag literature entries with related_sections")
    parser.add_argument("--storyline", default="storyline.md")
    parser.add_argument("--index", default="data/literature_index.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}")

    sections = extract_sections(args.storyline)
    section_kw = {s: section_keywords(s) for s in sections}

    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("literature_index must be a list")

    updated = 0
    for item in data:
        if not isinstance(item, dict):
            continue
        text = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("abstract", "")),
                " ".join(item.get("keywords", [])) if isinstance(item.get("keywords"), list) else str(item.get("keywords", "")),
            ]
        )
        norm_text = normalize(text)

        matched = []
        for section, kws in section_kw.items():
            if not kws:
                continue
            hits = sum(1 for kw in kws if kw in norm_text)
            if hits >= 1:
                matched.append(section)

        existing = item.get("related_sections")
        existing = existing if isinstance(existing, list) else []
        merged = sorted(set(existing + matched))

        if merged != existing:
            item["related_sections"] = merged
            updated += 1

    if args.dry_run:
        print(f"Would update {updated} entries")
        return

    index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {updated} entries with related_sections")


if __name__ == "__main__":
    main()
