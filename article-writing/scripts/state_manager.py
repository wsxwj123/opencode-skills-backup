import argparse
import json
import os
import sys
import shutil
import glob
import re
from pathlib import Path

# Define state files map
STATE_FILES = {
    "project_config": "project_config.json",
    "storyline": "storyline.json",
    "writing_progress": "writing_progress.json",
    "context_memory": "context_memory.md",
    "literature_index": "literature_index.json",
    "figures_database": "figures_database.json",
    "reviewer_concerns": "reviewer_concerns.json",
    "version_history": "version_history.json",
    "si_database": "si_database.json"
}

def calculate_word_counts():
    """Calculates word counts for all markdown files in manuscripts/ directory."""
    word_counts = {
        "total": 0,
        "sections": {}
    }
    
    manuscript_dir = "manuscripts"
    if not os.path.exists(manuscript_dir):
        return word_counts
        
    files = glob.glob(os.path.join(manuscript_dir, "*.md"))
    
    for file_path in files:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple word count: split by whitespace
                # Remove markdown headers/formatting for better accuracy if needed, 
                # but raw split is usually sufficient for draft estimation
                # Excluding references list could be an improvement, but keeping it simple for now
                words = len(content.split())
                word_counts["sections"][filename] = words
                word_counts["total"] += words
        except Exception:
            word_counts["sections"][filename] = 0
            
    return word_counts

def load_state(target_files=None, compact=False):
    """Reads state files.
    Args:
        target_files (list): Optional list of specific keys to load (e.g. ['storyline', 'literature_index']).
        compact (bool): If True, removes bulky fields like 'abstract' to save tokens.
    """
    combined_state = {}
    
    # Determine which files to load
    keys_to_load = target_files if target_files else STATE_FILES.keys()
    
    # 1. Load standard state files
    for key in keys_to_load:
        if key not in STATE_FILES:
            continue
            
        filename = STATE_FILES[key]
        if os.path.exists(filename):
            try:
                if filename.endswith(".json"):
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        data = json.loads(content) if content else {}
                        
                        # Apply compaction logic
                        if compact:
                            if key == "literature_index" and isinstance(data, list):
                                for item in data:
                                    # Keep only critical info for citation
                                    keep_keys = {"ref_id", "title", "year", "author", "journal", "citation_key"}
                                    for k in list(item.keys()):
                                        if k not in keep_keys:
                                            item.pop(k, None)
                            elif key == "storyline":
                                # Maybe just keep section titles? For now keep full structure as it's logic
                                pass
                                
                        combined_state[key] = data
                else:
                    with open(filename, 'r', encoding='utf-8') as f:
                        # For context_memory.md, maybe just read last 50 lines?
                        content = f.read()
                        if compact and key == "context_memory":
                            lines = content.split('\n')
                            if len(lines) > 50:
                                combined_state[key] = "...(truncated)...\n" + "\n".join(lines[-50:])
                            else:
                                combined_state[key] = content
                        else:
                            combined_state[key] = content
            except Exception as e:
                combined_state[key] = f"<Error loading {filename}: {str(e)}>"
        else:
            combined_state[key] = None
            
    # 2. Inject Real-time Word Counts (Only if loading progress or generic load)
    if not target_files or "writing_progress" in target_files:
        combined_state["live_word_counts"] = calculate_word_counts()
            
    print(json.dumps(combined_state, indent=2, ensure_ascii=False))

def rotate_context_memory_versions():
    """Handles versioning for context_memory.md (v-1, v-2)."""
    base_file = "context_memory.md"
    v1_file = "context_memory_v-1.md"
    v2_file = "context_memory_v-2.md"

    if os.path.exists(v1_file):
        shutil.copy2(v1_file, v2_file)
    
    if os.path.exists(base_file):
        shutil.copy2(base_file, v1_file)

def update_state(payload_path):
    """Updates state files based on a JSON payload file."""
    if not os.path.exists(payload_path):
        print(f"Error: Payload file '{payload_path}' not found.")
        sys.exit(1)

    try:
        with open(payload_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in payload file: {e}")
        sys.exit(1)

    updated_files = []

    for key, content in payload.items():
        if key not in STATE_FILES:
            print(f"Warning: Unknown key '{key}' in payload. Skipping.")
            continue
        
        filename = STATE_FILES[key]
        
        try:
            # Special handling for context_memory versioning
            if key == "context_memory":
                # Only rotate if content actually changed or if file exists
                if os.path.exists(filename):
                     rotate_context_memory_versions()
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            
            # JSON files
            elif filename.endswith(".json"):
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2, ensure_ascii=False)
            
            # Text/Markdown files
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            
            updated_files.append(filename)
            
        except Exception as e:
            print(f"Error writing to {filename}: {e}")

    print(f"Successfully updated: {', '.join(updated_files)}")
    
    # Auto-delete payload file to keep directory clean
    try:
        os.remove(payload_path)
    except:
        pass

def backup_project_state(backup_dir="backups"):
    """Creates a full project snapshot including all state files and manuscripts."""
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = os.path.join(backup_dir, f"snapshot_{timestamp}")
    
    if not os.path.exists(snapshot_dir):
        os.makedirs(snapshot_dir)
        
    # 1. Backup State Files
    for key, filename in STATE_FILES.items():
        if os.path.exists(filename):
            shutil.copy2(filename, snapshot_dir)
            
    # 2. Backup Manuscripts
    manuscript_dir = "manuscripts"
    if os.path.exists(manuscript_dir):
        target_manuscript_dir = os.path.join(snapshot_dir, "manuscripts")
        shutil.copytree(manuscript_dir, target_manuscript_dir)
        
    print(f"✅ Full project snapshot created at: {snapshot_dir}")
    return snapshot_dir

def main():
    parser = argparse.ArgumentParser(description="Manage state files for Article Writing Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Load command
    load_parser = subparsers.add_parser("load", help="Load state files")
    load_parser.add_argument("--files", help="Comma-separated list of files to load (e.g. 'storyline,progress')")
    load_parser.add_argument("--compact", action="store_true", help="Remove bulky fields like abstracts")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update state files from a payload")
    update_parser.add_argument("payload_file", help="Path to the JSON file containing updates")

    # Snapshot command
    subparsers.add_parser("snapshot", help="Create a full project backup")

    args = parser.parse_args()

    if args.command == "load":
        files = args.files.split(",") if args.files else None
        load_state(target_files=files, compact=args.compact)
    elif args.command == "update":
        update_state(args.payload_file)
    elif args.command == "snapshot":
        backup_project_state()

if __name__ == "__main__":
    main()
