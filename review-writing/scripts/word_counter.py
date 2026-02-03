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

def count_words_in_file(file_path):
    try:
        content = file_path.read_text(encoding='utf-8')
        cleaned = clean_markdown(content)
        # Split by whitespace
        words = cleaned.split()
        return len(words)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0

def main():
    parser = argparse.ArgumentParser(description="Review Writing Word Counter")
    parser.add_argument("--file", help="Specific file to count")
    args = parser.parse_args()

    # Define root and drafts directory relative to current working directory
    # (Assuming the user runs this from their project root)
    cwd = Path.cwd()
    drafts_dir = cwd / "drafts"

    if not drafts_dir.exists():
        print(f"Error: 'drafts' directory not found in {cwd}.")
        print("Please run this command from the root of your review project.")
        sys.exit(1)

    total_words = 0
    current_file_count = 0
    current_file_name = "N/A"

    # Count all files in drafts
    for md_file in drafts_dir.glob("**/*.md"):
        count = count_words_in_file(md_file)
        total_words += count
        
        # Check if this is the specific file requested
        if args.file:
            req_file = Path(args.file).resolve()
            if md_file.resolve() == req_file:
                current_file_count = count
                current_file_name = md_file.name

    # Goal logic
    GOAL_MIN = 7000
    GOAL_MAX = 10000
    progress_pct = (total_words / GOAL_MAX) * 100
    
    if total_words < GOAL_MIN:
        status = "🔴 Too Short"
    elif total_words > GOAL_MAX:
        status = "🟡 Over Limit" # Optional nuance
    else:
        status = "🟢 On Track"

    # Output
    print("[Word Count Report]")
    if args.file:
        print(f"Current Section ({current_file_name}): {current_file_count} words")
    
    print(f"Total Project: {total_words} words")
    print(f"Progress: {progress_pct:.1f}% of 10k goal")
    print(f"Status: [{status}]")

if __name__ == "__main__":
    main()
