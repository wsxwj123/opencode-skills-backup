import argparse
import json
import os
import sys
import shutil
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

def load_state():
    """Reads all state files and returns a consolidated JSON object to stdout."""
    combined_state = {}
    
    for key, filename in STATE_FILES.items():
        if os.path.exists(filename):
            try:
                if filename.endswith(".json"):
                    with open(filename, 'r', encoding='utf-8') as f:
                        # Handle empty files gracefully
                        content = f.read().strip()
                        combined_state[key] = json.loads(content) if content else {}
                else:
                    with open(filename, 'r', encoding='utf-8') as f:
                        combined_state[key] = f.read()
            except Exception as e:
                combined_state[key] = f"<Error loading {filename}: {str(e)}>"
        else:
            combined_state[key] = None  # Explicitly mark as missing
            
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

def main():
    parser = argparse.ArgumentParser(description="Manage state files for Article Writing Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Load command
    subparsers.add_parser("load", help="Load and print all state files as JSON")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update state files from a payload")
    update_parser.add_argument("payload_file", help="Path to the JSON file containing updates")

    args = parser.parse_args()

    if args.command == "load":
        load_state()
    elif args.command == "update":
        update_state(args.payload_file)

if __name__ == "__main__":
    main()
