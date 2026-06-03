#!/usr/bin/env python3
"""Check output structure for reviewer-response-sci skill."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CODE_BLOCK_RE = re.compile(r"```(?:txt)?\n[\s\S]*?```", re.MULTILINE)


def read_text(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate response format")
    parser.add_argument("file", nargs="?", help="Path to response text file")
    args = parser.parse_args()

    text = read_text(args.file)
    blocks = CODE_BLOCK_RE.findall(text)

    errors: list[str] = []

    if len(blocks) != 3:
        errors.append(f"Expected exactly 3 code blocks, found {len(blocks)}")

    if "🔴" not in text or "🟡" not in text:
        errors.append("Missing priority markers: both 🔴 and 🟡 are required in notes section")

    if "Part 4" not in text and "修改说明" not in text:
        errors.append("Missing Part 4 modification notes heading")

    if errors:
        print("FORMAT_CHECK: FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("FORMAT_CHECK: PASS")
    print("- Found exactly 3 code blocks")
    print("- Found 🔴 and 🟡 markers")
    print("- Found notes section hint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
