#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def _read_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _normalize(text):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(text).lower())


def _parse_storyline_sections(storyline_path):
    p = Path(storyline_path)
    if not p.exists():
        return []
    sections = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(##+)\s+(.*)$", line)
        if not m:
            continue
        title = m.group(2).strip()
        if title:
            # Ignore placeholder/template section headers in early drafting.
            if "[" in title and "]" in title:
                continue
            sections.append(title)
    return sections


def _draft_files(drafts_dir):
    d = Path(drafts_dir)
    if not d.exists():
        return []
    return sorted(d.glob("**/*.md"))


def _check_section_coverage(sections, drafts_dir):
    drafts = _draft_files(drafts_dir)
    draft_names = [_normalize(f.stem) for f in drafts]
    missing = []
    for section in sections:
        s = _normalize(section)
        if not s:
            continue
        if not any(s in dn for dn in draft_names):
            missing.append(section)
    return {"total_sections": len(sections), "missing_sections": missing}


def _check_matrix_claim_coverage(matrix_path):
    matrix = _read_json(matrix_path, [])
    rows = [r for r in matrix if isinstance(r, dict)]
    scoped_rows = [r for r in rows if r.get("section_id") not in (None, "", "unassigned")]
    missing_claim = [r for r in scoped_rows if not r.get("claim_id")]
    return {
        "rows": len(scoped_rows),
        "missing_claim_count": len(missing_claim),
    }


def _check_round3_freshness(matrix_path):
    matrix = _read_json(matrix_path, [])
    rows = [r for r in matrix if isinstance(r, dict) and r.get("claim_id")]
    if not rows:
        return {"claim_rows": 0, "updated_round3_ratio": 0.0}
    updated = sum(1 for r in rows if r.get("updated_in_round3") is True)
    return {"claim_rows": len(rows), "updated_round3_ratio": updated / len(rows)}


def _collect_citations(drafts_dir):
    pat = re.compile(r"\[(\d+)\]")
    ids = []
    for f in _draft_files(drafts_dir):
        text = f.read_text(encoding="utf-8")
        ids.extend(int(x) for x in pat.findall(text))
    return ids


def _check_citation_sequence(drafts_dir):
    ids = _collect_citations(drafts_dir)
    if not ids:
        return {"has_citations": False, "missing_numbers": [], "starts_at": None}
    uniq = sorted(set(ids))
    min_id, max_id = uniq[0], uniq[-1]
    missing = sorted(set(range(min_id, max_id + 1)) - set(uniq))
    return {"has_citations": True, "missing_numbers": missing, "starts_at": min_id}


def _check_orphans(index_path, drafts_dir):
    index = _read_json(index_path, [])
    index_ids = {str(x.get("global_id")) for x in index if isinstance(x, dict) and isinstance(x.get("global_id"), int)}
    used_ids = {str(x) for x in _collect_citations(drafts_dir)}
    return sorted(used_ids - index_ids, key=int)


def main():
    parser = argparse.ArgumentParser(description="Final consistency checks for review-writing deliverables")
    parser.add_argument("--storyline", default="storyline.md")
    parser.add_argument("--drafts-dir", default="drafts")
    parser.add_argument("--matrix", default="data/synthesis_matrix.json")
    parser.add_argument("--index", default="data/literature_index.json")
    parser.add_argument("--min-round3-ratio", type=float, default=0.7)
    parser.add_argument("--fail-on-gap", action="store_true")
    args = parser.parse_args()

    sections = _parse_storyline_sections(args.storyline)
    section_cov = _check_section_coverage(sections, args.drafts_dir)
    matrix_cov = _check_matrix_claim_coverage(args.matrix)
    freshness = _check_round3_freshness(args.matrix)
    citation_seq = _check_citation_sequence(args.drafts_dir)
    orphan_ids = _check_orphans(args.index, args.drafts_dir)

    report = {
        "section_coverage": section_cov,
        "matrix_claim_coverage": matrix_cov,
        "round3_freshness": freshness,
        "citation_sequence": citation_seq,
        "orphans": orphan_ids,
        "thresholds": {"min_round3_ratio": args.min_round3_ratio},
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    has_gap = False
    if section_cov["missing_sections"]:
        has_gap = True
    if matrix_cov["missing_claim_count"] > 0:
        has_gap = True
    if citation_seq["has_citations"] and (citation_seq["starts_at"] != 1 or citation_seq["missing_numbers"]):
        has_gap = True
    if orphan_ids:
        has_gap = True
    if freshness["claim_rows"] > 0 and freshness["updated_round3_ratio"] < args.min_round3_ratio:
        has_gap = True

    if args.fail_on_gap and has_gap:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
