#!/usr/bin/env python3
"""Scan for high-risk phrases suggesting fabricated claims or overpromises."""

from __future__ import annotations

import argparse
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


def read_text(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Risk phrase checker")
    parser.add_argument("file", nargs="?", help="Path to response text file")
    args = parser.parse_args()

    text = read_text(args.file)

    hits: list[tuple[str, str]] = []
    for category, patterns in RISK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append((category, pattern))

    if hits:
        print("RISK_CHECK: WARN")
        for category, pattern in hits:
            print(f"- {category}: matched /{pattern}/")
        return 1

    print("RISK_CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
