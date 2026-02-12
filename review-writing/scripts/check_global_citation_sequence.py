#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def collect_ids(drafts_dir):
    ids = []
    for md in sorted(Path(drafts_dir).glob("**/*.md")):
        text = md.read_text(encoding="utf-8")
        ids.extend(int(x) for x in CITATION_PATTERN.findall(text))
    return ids


def main():
    parser = argparse.ArgumentParser(description="Check global citation sequence continuity")
    parser.add_argument("--drafts-dir", default="drafts")
    args = parser.parse_args()

    ids = collect_ids(args.drafts_dir)
    if not ids:
        print("No citations found.")
        return

    uniq = sorted(set(ids))
    min_id, max_id = uniq[0], uniq[-1]
    expected = set(range(min_id, max_id + 1))
    missing = sorted(expected - set(uniq))
    duplicates = sorted({x for x in ids if ids.count(x) > 1})

    print("Citation Sequence Report")
    print(f"Range: [{min_id}..{max_id}]  Unique: {len(uniq)}  Total mentions: {len(ids)}")

    if missing:
        print("[CRITICAL] Missing sequence numbers:", ", ".join(str(x) for x in missing))
        raise SystemExit(2)

    if min_id != 1:
        print(f"[WARNING] Sequence starts at {min_id}, expected 1")

    if duplicates:
        print("[INFO] Reused citation IDs:", ", ".join(str(x) for x in duplicates))

    print("[OK] Citation sequence is continuous")


if __name__ == "__main__":
    main()
