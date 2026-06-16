#!/usr/bin/env python3
"""Scan for high-risk phrases suggesting fabricated claims or overpromises."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Categories prefixed with "ai_" are only applied to comment units, not email units.
RISK_PATTERNS = {
    "fabricated_experiment": [
        r"we (have )?conducted additional experiments",
        r"new experiments? (were|was) performed",
    ],
    "fabricated_statistics": [
        r"p\s*[<=>]\s*0\.0[0-9]",
        r"significant at p\s*[<=>]",
        r"we now report .* confidence interval",
    ],
    "overpromise": [
        r"we will definitely",
        r"this proves that",
        r"without any doubt",
    ],
    "ai_hedging": [
        r"it is important to note that",
        r"it should be noted that",
        r"it is worth (noting|mentioning) that",
        r"importantly,",
        r"notably,",
        r"it is crucial to",
        r"needless to say",
    ],
    "ai_appreciation": [
        r"we (greatly|sincerely|deeply) (appreciate|thank)",
        r"we are (deeply |truly )?(grateful|thankful) for",
        r"thank you for (your )?(insightful|valuable|constructive|thoughtful) (comments?|suggestions?|feedback)",
    ],
    "ai_filler": [
        r"in order to\b",
        r"as a matter of fact",
        r"it is worth noting that",
        r"we would like to (point out|emphasize|highlight|note) that",
        r"as (the reviewer )?(rightly|correctly) (pointed out|noted|observed|suggested)",
        r"we completely agree with the reviewer",
        r"this is (indeed )?an excellent (point|suggestion|observation)",
    ],
}

AI_STYLE_CATEGORIES = {"ai_hedging", "ai_appreciation", "ai_filler"}
FABRICATION_CATEGORIES = {"fabricated_experiment", "fabricated_statistics"}


def _check_structural_repetition(units: list[dict]) -> list[tuple[str, str]]:
    """Detect cross-unit response opening repetition (>=3 same pattern)."""
    openings: dict[str, list[str]] = {}
    for unit in units:
        uid = unit.get("unit_id", "")
        response = str(unit.get("content", {}).get("response_en", "")).strip()
        if not response:
            continue
        # Extract first sentence, normalize to pattern
        first = response.split(".")[0].strip().lower() if "." in response else response[:80].strip().lower()
        # Remove specific nouns/numbers to get structural template
        pattern = re.sub(r"\b(figure|table|section|page|line|paragraph)\s*\d+\w*", "REF", first)
        pattern = re.sub(r"\b(reviewer|comment)\s*#?\d+", "REVIEWER", pattern)
        pattern = re.sub(r"\d+", "N", pattern)
        openings.setdefault(pattern, []).append(uid)

    hits: list[tuple[str, str]] = []
    for pattern, uids in openings.items():
        if len(uids) >= 3:
            hits.append(("structural_repetition", f"{len(uids)} units share opening pattern: {uids[:5]}"))
    return hits


def scan_text(text: str, *, skip_ai_style: bool = False, cross_check_text: str = "") -> list[tuple[str, str]]:
    """Scan text for risk patterns.

    cross_check_text: when provided, fabricated_statistics hits are suppressed if
    the same matched substring also appears in cross_check_text (revised_excerpt_en),
    meaning the statistic is grounded in the actual revision rather than invented.
    """
    hits: list[tuple[str, str]] = []
    for category, patterns in RISK_PATTERNS.items():
        if skip_ai_style and category in AI_STYLE_CATEGORIES:
            continue
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if not m:
                continue
            # Exempt fabricated_statistics when the same matched value also appears
            # in revised_excerpt_en — the statistic is being reported faithfully, not invented.
            if category == "fabricated_statistics" and cross_check_text:
                matched_value = m.group(0)
                if re.search(re.escape(matched_value), cross_check_text, flags=re.IGNORECASE):
                    continue  # Grounded in revised excerpt — not fabricated
            hits.append((category, pattern))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Risk phrase checker")
    parser.add_argument("file", nargs="?", help="Path to a single text/HTML file (legacy mode)")
    parser.add_argument("--project-root", default="", help="Scan all units/*.json in a project")
    args = parser.parse_args()

    all_hits: list[tuple[str, str, str]] = []  # (source, category, pattern)

    if args.project_root:
        root = Path(args.project_root)
        units_dir = root / "units"
        if not units_dir.exists():
            print(f"RISK_CHECK: SKIP (no units dir: {units_dir})")
            return 0
        loaded_units = []
        comment_units = []
        for p in sorted(units_dir.glob("*.json")):
            try:
                unit = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            loaded_units.append(unit)
            is_email = unit.get("section") == "email" or "email" in str(unit.get("unit_id", "")).lower()
            if not is_email:
                comment_units.append(unit)
            content = unit.get("content", {})
            response_en = str(content.get("response_en", ""))
            revised_en = str(content.get("revised_excerpt_en", ""))
            # Fabrication patterns only scan response_en.
            # Pass revised_en as cross_check: if the same statistic appears in the revision,
            # it is being reported faithfully and should not be flagged as fabricated.
            for cat, pat in scan_text(response_en, skip_ai_style=is_email, cross_check_text=revised_en):
                all_hits.append((unit.get("unit_id", p.name), cat, pat))
            # AI style + overpromise also scan revised_excerpt (but NOT fabrication categories)
            for cat, pat in scan_text(revised_en, skip_ai_style=is_email):
                if cat not in FABRICATION_CATEGORIES:
                    all_hits.append((unit.get("unit_id", p.name), cat, pat))
        # Structural repetition check across comment units only
        for cat, msg in _check_structural_repetition(comment_units):
            all_hits.append(("cross-unit", cat, msg))
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8")
        for cat, pat in scan_text(text):
            all_hits.append((args.file, cat, pat))
    else:
        text = sys.stdin.read()
        for cat, pat in scan_text(text):
            all_hits.append(("stdin", cat, pat))

    # Separate hard risks (pipeline-blocking) from soft risks (warn-only)
    hard_hits = [(s, c, p) for s, c, p in all_hits if c in FABRICATION_CATEGORIES]
    soft_hits = [(s, c, p) for s, c, p in all_hits if c not in FABRICATION_CATEGORIES]

    if hard_hits:
        print("RISK_CHECK: FAIL (hard risk detected)")
        for source, category, pattern in hard_hits:
            print(f"- [{source}] {category}: matched /{pattern}/")
        if soft_hits:
            print("Additional warnings:")
            for source, category, pattern in soft_hits:
                print(f"- [{source}] {category}: matched /{pattern}/")
        return 1

    if soft_hits:
        print("RISK_CHECK: WARN (non-blocking)")
        for source, category, pattern in soft_hits:
            print(f"- [{source}] {category}: matched /{pattern}/")
        return 0

    print("RISK_CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
