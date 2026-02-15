#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def normalize(text):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", str(text).lower()).strip()


def extract_sections(storyline_path):
    p = Path(storyline_path)
    if not p.exists():
        return []
    if p.suffix.lower() == ".json":
        payload = json.loads(p.read_text(encoding="utf-8"))
        raw = payload.get("sections", []) if isinstance(payload, dict) else []
        sections = []
        for item in raw:
            if isinstance(item, str):
                title = item.strip()
            elif isinstance(item, dict):
                title = item.get("section_id") or item.get("title") or item.get("name") or item.get("id")
                title = str(title).strip() if title else ""
            else:
                title = ""
            if title:
                sections.append(title)
        return sections

    text = p.read_text(encoding="utf-8")
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


def _paper_identity(item):
    doi = str(item.get("doi", "")).strip().lower()
    pmid = str(item.get("pmid", "")).strip()
    title = normalize(item.get("title", ""))
    return {"doi": doi, "pmid": pmid, "title": title}


def _load_overrides(path):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_section_list(value):
    if not isinstance(value, list):
        return []
    out = []
    seen = set()
    for section in value:
        if not isinstance(section, str):
            continue
        title = section.strip()
        key = normalize(title)
        if not title or not key or key in seen:
            continue
        seen.add(key)
        out.append(title)
    return out


def _apply_override(current_sections, rule):
    out = list(current_sections)
    if not isinstance(rule, dict):
        return out

    set_sections = _normalize_section_list(rule.get("set"))
    if set_sections:
        out = list(set_sections)

    add_sections = _normalize_section_list(rule.get("add"))
    if add_sections:
        existing = {normalize(x) for x in out}
        for section in add_sections:
            key = normalize(section)
            if key not in existing:
                existing.add(key)
                out.append(section)

    remove_set = {normalize(x) for x in _normalize_section_list(rule.get("remove"))}
    if remove_set:
        out = [x for x in out if normalize(x) not in remove_set]

    return out


def main():
    parser = argparse.ArgumentParser(description="Auto-tag literature entries with related_sections")
    parser.add_argument("--storyline", default="storyline.md")
    parser.add_argument("--index", default="data/literature_index.json")
    parser.add_argument("--overrides", default="data/section_overrides.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}")

    sections = extract_sections(args.storyline)
    if not sections and args.storyline.endswith(".md"):
        sections = extract_sections(str(Path(args.storyline).with_suffix(".json")))
    section_kw = {s: section_keywords(s) for s in sections}
    overrides = _load_overrides(args.overrides)
    by_global_id = overrides.get("by_global_id", {}) if isinstance(overrides, dict) else {}
    by_doi = overrides.get("by_doi", {}) if isinstance(overrides, dict) else {}
    by_pmid = overrides.get("by_pmid", {}) if isinstance(overrides, dict) else {}
    by_title = overrides.get("by_title", {}) if isinstance(overrides, dict) else {}

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

        ident = _paper_identity(item)
        rule = None
        gid = item.get("global_id")
        if isinstance(gid, int):
            rule = by_global_id.get(str(gid))
        if rule is None and ident["doi"]:
            rule = by_doi.get(ident["doi"])
        if rule is None and ident["pmid"]:
            rule = by_pmid.get(ident["pmid"])
        if rule is None and ident["title"]:
            rule = by_title.get(ident["title"])
        if rule is not None:
            merged = _apply_override(merged, rule)

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
