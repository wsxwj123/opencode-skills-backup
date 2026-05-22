#!/usr/bin/env python3
"""Scan for high-risk phrases suggesting fabricated claims or overpromises."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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
}


def scan_text(text: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for category, patterns in RISK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
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
        for p in sorted(units_dir.glob("*.json")):
            try:
                unit = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            content = unit.get("content", {})
            combined = " ".join(
                str(content.get(k, ""))
                for k in ["response_en", "revised_excerpt_en"]
            )
            for cat, pat in scan_text(combined):
                all_hits.append((unit.get("unit_id", p.name), cat, pat))
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8")
        for cat, pat in scan_text(text):
            all_hits.append((args.file, cat, pat))
    else:
        text = sys.stdin.read()
        for cat, pat in scan_text(text):
            all_hits.append(("stdin", cat, pat))

    if all_hits:
        print("RISK_CHECK: WARN")
        for source, category, pattern in all_hits:
            print(f"- [{source}] {category}: matched /{pattern}/")
        return 1

    print("RISK_CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
