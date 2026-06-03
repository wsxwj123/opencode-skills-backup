#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import re

def clean_markdown(text):
    """
    Remove basic markdown syntax to get a more accurate word count.
    Removes headers, bold/italic markers, links, images, and code blocks.
    """
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r'`[^`]*`', '', text)
    # Remove images
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove links (keep text)
    text = re.sub(r'\[([^\]]+)\]\(.*?\)', r'\1', text)
    # Remove headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r'[*_]{1,3}', '', text)
    return text

def count_text(text, language):
    """Count words (EN) or characters (CN) in cleaned text."""
    cleaned = clean_markdown(text)
    if language == "cn":
        # Chinese character count (CJK Unified Ideographs)
        return len(re.findall(r'[一-鿿]', cleaned))
    else:
        return len(cleaned.split())

def main():
    parser = argparse.ArgumentParser(description="Review Writing Word Counter")
    parser.add_argument("--file", help="Specific file to count")
    parser.add_argument("--language", default="en", choices=["en", "cn"],
                        help="Language mode: en=English words, cn=Chinese characters (default: en)")
    args = parser.parse_args()

    # Define root and drafts directory relative to current working directory
    cwd = Path.cwd()
    drafts_dir = cwd / "drafts"

    if not drafts_dir.exists():
        print(f"Error: 'drafts' directory not found in {cwd}.")
        print("Please run this command from the root of your review project.")
        sys.exit(1)

    total = 0
    current_count = 0
    current_name = "N/A"

    # Count all files in drafts
    for md_file in drafts_dir.glob("**/*.md"):
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading {md_file}: {e}", file=sys.stderr)
            continue
        c = count_text(content, args.language)
        total += c

        # Check if this is the specific file requested
        if args.file:
            req_file = Path(args.file).resolve()
            if md_file.resolve() == req_file:
                current_count = c
                current_name = md_file.name

    # Goal logic based on language
    if args.language == "cn":
        GOAL_MIN = 15000
        GOAL_MAX = 20000
        unit = "chars"
    else:
        GOAL_MIN = 7000
        GOAL_MAX = 10000
        unit = "words"

    progress_pct = (total / GOAL_MAX) * 100

    if total < GOAL_MIN:
        status = "🔴 Too Short"
    elif total > GOAL_MAX:
        status = "🟡 Over Limit"
    else:
        status = "🟢 On Track"

    # Output
    print("[Word Count Report]")
    if args.file:
        print(f"Current Section ({current_name}): {current_count} {unit}")

    print(f"Total Project: {total} {unit}")
    print(f"Progress: {progress_pct:.1f}% of {GOAL_MAX:,} {unit} goal")
    print(f"Status: [{status}]")

if __name__ == "__main__":
    main()
