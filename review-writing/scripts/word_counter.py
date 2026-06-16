#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import re

# Patterns to detect Word Count Target in outline.md
# Matches lines like:
#   Word Count Target: 600 words
#   **Word Count Target:** 600 words
#   - Word Count Target: ~600
_WC_PATTERN = re.compile(
    r"word\s+count\s+target\s*[:：]\s*[~≈]?\s*(\d[\d,]*)\s*(words?|chars?|characters?|词|字)?",
    re.IGNORECASE,
)

def _read_outline_target(cwd, language):
    """Read Word Count Target from outline.md if present.

    Returns (min, max) tuple or None if not found.
    The target is treated as both min and max within ±20%:
      min = target * 0.8,  max = target * 1.2
    """
    for name in ("outline.md", "storyline.md"):
        p = cwd / name
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        m = _WC_PATTERN.search(text)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                target = int(raw)
            except ValueError:
                continue
            # Determine unit from suffix token or language default
            suffix = (m.group(2) or "").lower()
            is_cn_unit = suffix in ("chars", "char", "characters", "character", "词", "字")
            is_en_unit = suffix in ("words", "word")
            if is_cn_unit or (not is_en_unit and language == "cn"):
                # Chinese character target
                return int(target * 0.8), int(target * 1.2), target, "chars"
            else:
                return int(target * 0.8), int(target * 1.2), target, "words"
    return None

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

    # Goal logic: try outline.md first, fall back to hardcoded defaults
    outline_target = _read_outline_target(cwd, args.language)
    if outline_target is not None:
        GOAL_MIN, GOAL_MAX, target_center, unit = outline_target
        goal_label = f"{target_center:,} (outline target ±20%)"
    elif args.language == "cn":
        GOAL_MIN = 15000
        GOAL_MAX = 20000
        unit = "chars"
        goal_label = f"{GOAL_MAX:,} (default)"
    else:
        GOAL_MIN = 7000
        GOAL_MAX = 10000
        unit = "words"
        goal_label = f"{GOAL_MAX:,} (default)"

    progress_pct = (total / GOAL_MAX) * 100 if GOAL_MAX > 0 else 0.0

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
    print(f"Progress: {progress_pct:.1f}% of {goal_label} {unit} goal")
    print(f"Status: [{status}]")

if __name__ == "__main__":
    main()
