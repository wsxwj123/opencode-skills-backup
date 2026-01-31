import argparse
import json
import os
import sys
import shutil
from pathlib import Path

# Define state files map for Review Writing Project
STATE_FILES = {
    "project_info": "project_info.md",          # Basic project info (RQ, PICO)
    "storyline": "storyline.md",                # Outline and status
    "progress": "progress.json",                # Quantitative progress (citations count, stage)
    "literature_index": "data/literature_index.json", # The core database of papers
    "synthesis_matrix": "data/synthesis_matrix.json", # New: Matrix for synthesis
    "figure_index": "figures/figure_index.md",  # Figure planning
    "context_memory": "logs/context_memory.md", # Conversation history snapshot
    "si_database": "data/si_database.json"      # Supplementary info tracking
}

def load_state(section=None):
    """Reads all state files and returns a consolidated JSON object to stdout.
    
    Args:
        section (str, optional): If provided, filters literature_index to relevant entries.
    """
    combined_state = {}
    
    for key, filename in STATE_FILES.items():
        if os.path.exists(filename):
            try:
                if filename.endswith(".json"):
                    with open(filename, 'r', encoding='utf-8') as f:
                        # Handle empty files gracefully
                        content = f.read().strip()
                        data = json.loads(content) if content else {}
                        
                        # Smart Loading: Filter literature_index if section is provided
                        if key == "literature_index" and section and isinstance(data, list):
                            filtered_data = []
                            for item in data:
                                # Ensure global_id is present (even if None/missing in legacy data)
                                if "global_id" not in item:
                                    item["global_id"] = None
                                
                                # Check if 'related_sections' exists and contains the section
                                if "related_sections" in item and isinstance(item["related_sections"], list):
                                    if section in item["related_sections"]:
                                        filtered_data.append(item)
                                # Fallback: if 'sections' tag exists
                                elif "sections" in item and isinstance(item["sections"], list):
                                    if section in item["sections"]:
                                        filtered_data.append(item)
                            
                            # If filtering returned nothing or section logic not found, 
                            # maybe return recent ones as fallback?
                            if not filtered_data and data:
                                # Fallback: return last 20 items if specific filtering yielded 0
                                filtered_data = data[-20:]
                                
                            combined_state[key] = filtered_data
                        else:
                            combined_state[key] = data
                else:
                    with open(filename, 'r', encoding='utf-8') as f:
                        combined_state[key] = f.read()
            except Exception as e:
                combined_state[key] = f"<Error loading {filename}: {str(e)}>"
        else:
            combined_state[key] = None  # Explicitly mark as missing
            
    print(json.dumps(combined_state, indent=2, ensure_ascii=False))

def compact_memory():
    """Compacts the context_memory.md file if it gets too large."""
    memory_file = STATE_FILES["context_memory"]
    
    if not os.path.exists(memory_file):
        print("Context memory file not found.")
        return

    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Thresholds
        MAX_LINES = 100
        KEEP_RECENT = 20
        
        if len(lines) <= MAX_LINES:
            print("Memory is within limits. No compaction needed.")
            return

        # Simple Compaction Strategy:
        # Keep first 5 lines (header/intro)
        # Keep last KEEP_RECENT lines
        # Replace middle with summary stub
        
        header = lines[:5]
        recent = lines[-KEEP_RECENT:]
        
        # Backup original before overwriting
        rotate_context_memory_versions()
        
        with open(memory_file, 'w', encoding='utf-8') as f:
            f.writelines(header)
            f.write(f"\nArchived Context: [{len(lines) - 5 - KEEP_RECENT} lines hidden]\n\n")
            f.writelines(recent)
            
        print(f"Compacted memory from {len(lines)} lines to {len(header) + 1 + len(recent)} lines.")

    except Exception as e:
        print(f"Error compacting memory: {e}")

def rotate_context_memory_versions():
    """Handles versioning for context_memory.md (v-1, v-2)."""
    base_file = "logs/context_memory.md"
    v1_file = "logs/context_memory_v-1.md"
    v2_file = "logs/context_memory_v-2.md"
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(base_file), exist_ok=True)

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
        
        # ID Assignment Logic for literature_index
        if key == "literature_index" and isinstance(content, list):
            current_max_id = 0
            # 1. Load EXISTING file first to determine max_id
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f_read:
                        existing_data = json.load(f_read)
                        if isinstance(existing_data, list):
                            # Calculate current max_id from existing papers
                            for item in existing_data:
                                gid = item.get("global_id")
                                if isinstance(gid, int) and gid > current_max_id:
                                    current_max_id = gid
                except Exception as e:
                    print(f"Warning reading existing literature index for max_id: {e}")
            
            # 2. Assign IDs to new items in payload
            for item in content:
                # If new item (no global_id), assign next available ID
                if "global_id" not in item:
                    current_max_id += 1
                    item["global_id"] = current_max_id
                else:
                    # If item already has an ID (update/existing), track it for max_id
                    # This handles cases where payload contains existing items with IDs
                    gid = item["global_id"]
                    if isinstance(gid, int) and gid > current_max_id:
                        current_max_id = gid

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)

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
    parser = argparse.ArgumentParser(description="Manage state files for Review Writing Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Load command
    load_parser = subparsers.add_parser("load", help="Load and print all state files as JSON")
    load_parser.add_argument("--section", help="Optional: Section name to filter relevant literature", default=None)

    # Update command
    update_parser = subparsers.add_parser("update", help="Update state files from a payload")
    update_parser.add_argument("payload_file", help="Path to the JSON file containing updates")

    # Compact command
    subparsers.add_parser("compact", help="Compact the context memory file if too large")

    args = parser.parse_args()

    if args.command == "load":
        load_state(section=args.section)
    elif args.command == "update":
        update_state(args.payload_file)
    elif args.command == "compact":
        compact_memory()

if __name__ == "__main__":
    main()
