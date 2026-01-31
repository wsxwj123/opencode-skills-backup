import os
import re

import json

def scan_drafts(root_dir):
    used_ids = set()
    pattern = re.compile(r'\[(\d+)\]')
    
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".md"):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = pattern.findall(content)
                    used_ids.update(matches)
    return used_ids

def load_index(index_path):
    with open(index_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Assuming list of dicts with 'global_id'
    # Handle both string and int in json, return strings for consistency
    return {str(item.get('global_id')) for item in data if 'global_id' in item}

def validate(used_ids, index_ids):
    orphans = used_ids - index_ids
    unused = index_ids - used_ids
    return orphans, unused

def main():
    base_dir = os.getcwd()
    drafts_dir = os.path.join(base_dir, "drafts")
    index_path = os.path.join(base_dir, "data", "literature_index.json")

    if not os.path.exists(drafts_dir):
        print(f"Error: Drafts directory not found at {drafts_dir}")
        return
    
    if not os.path.exists(index_path):
        print(f"Error: Index file not found at {index_path}")
        return

    print("Scanning drafts...")
    used_ids = scan_drafts(drafts_dir)
    print(f"Found {len(used_ids)} unique citations in drafts.")

    print("Loading index...")
    try:
        index_ids = load_index(index_path)
    except Exception as e:
        print(f"Error loading index: {e}")
        return
    print(f"Found {len(index_ids)} entries in index.")

    orphans, unused = validate(used_ids, index_ids)

    print("-" * 30)
    print("VALIDATION REPORT")
    print("-" * 30)
    
    if orphans:
        print(f"[CRITICAL] Found {len(orphans)} orphaned citations (used but not in index):")
        print(", ".join(sorted(orphans, key=lambda x: int(x) if x.isdigit() else x)))
    else:
        print("[OK] No orphaned citations.")

    if unused:
        print(f"[WARNING] Found {len(unused)} unused index entries:")
        print(", ".join(sorted(unused, key=lambda x: int(x) if x.isdigit() else x)))
    else:
        print("[OK] All index entries are cited.")
        
    print("-" * 30)

if __name__ == "__main__":
    main()
