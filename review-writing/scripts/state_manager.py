import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Define state files map for Review Writing Project
STATE_FILES = {
    "project_info": "project_info.md",          # Basic project info (RQ, PICO)
    "storyline": "storyline.md",                # Outline and status
    "progress": "progress.json",                # Quantitative progress (citations count, stage)
    "literature_index": "data/literature_index.json",  # The core database of papers
    "synthesis_matrix": "data/synthesis_matrix.json",  # Matrix for synthesis
    "figure_index": "figures/figure_index.md",  # Figure planning
    "context_memory": "logs/context_memory.md",  # Conversation history snapshot
    "si_database": "data/si_database.json",      # Supplementary info tracking
}


def _normalize_text(text):
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _read_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else {}


def _load_json_list(path):
    if not os.path.exists(path):
        return []
    try:
        data = _read_json_file(path)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _find_section_draft(section):
    if not section:
        return None
    drafts_dir = Path("drafts")
    if not drafts_dir.exists():
        return None

    section_norm = _normalize_text(section)
    for path in drafts_dir.glob("**/*.md"):
        if section_norm and section_norm in _normalize_text(path.stem):
            try:
                content = path.read_text(encoding="utf-8")
            except Exception as e:
                content = f"<Error reading {path}: {e}>"
            return {"file": str(path), "content": content}
    return None


def load_state(section=None, fallback_recent=False, minimal=False):
    """Reads state files and returns a consolidated JSON object to stdout."""
    combined_state = {}

    for key, filename in STATE_FILES.items():
        if os.path.exists(filename):
            try:
                if filename.endswith(".json"):
                    combined_state[key] = _read_json_file(filename)
                else:
                    with open(filename, "r", encoding="utf-8") as f:
                        combined_state[key] = f.read()
            except Exception as e:
                combined_state[key] = f"<Error loading {filename}: {e}>"
        else:
            combined_state[key] = None

    if section:
        lit_data = combined_state.get("literature_index")
        if isinstance(lit_data, list):
            filtered_lit = []
            for item in lit_data:
                if "global_id" not in item:
                    item["global_id"] = None

                related_sections = item.get("related_sections")
                legacy_sections = item.get("sections")

                if isinstance(related_sections, list) and section in related_sections:
                    filtered_lit.append(item)
                elif isinstance(legacy_sections, list) and section in legacy_sections:
                    filtered_lit.append(item)

            if fallback_recent and not filtered_lit and lit_data:
                filtered_lit = lit_data[-20:]

            combined_state["literature_index"] = filtered_lit

            relevant_ids = {
                item.get("global_id")
                for item in filtered_lit
                if item.get("global_id") is not None
            }
            matrix_data = combined_state.get("synthesis_matrix")
            if isinstance(matrix_data, list):
                filtered_rows = []
                for row in matrix_data:
                    if row.get("global_id") not in relevant_ids:
                        continue
                    row_section = row.get("section_id")
                    # If section_id exists in row, enforce exact section match.
                    if row_section is not None and row_section != section:
                        continue
                    filtered_rows.append(row)
                combined_state["synthesis_matrix"] = filtered_rows

    if minimal:
        minimal_state = {
            "progress": combined_state.get("progress"),
            "literature_index": combined_state.get("literature_index"),
            "synthesis_matrix": combined_state.get("synthesis_matrix"),
            "section_draft": _find_section_draft(section),
        }
        print(json.dumps(minimal_state, indent=2, ensure_ascii=False))
        return

    print(json.dumps(combined_state, indent=2, ensure_ascii=False))


def rotate_context_memory_versions():
    """Handles versioning for context_memory.md (v-1, v-2)."""
    base_file = "logs/context_memory.md"
    v1_file = "logs/context_memory_v-1.md"
    v2_file = "logs/context_memory_v-2.md"

    os.makedirs(os.path.dirname(base_file), exist_ok=True)

    if os.path.exists(v1_file):
        shutil.copy2(v1_file, v2_file)
    if os.path.exists(base_file):
        shutil.copy2(base_file, v1_file)


def _extract_memory_markers(lines):
    markers = {
        "decisions": [],
        "open_questions": [],
        "next_actions": [],
        "risks": [],
    }
    patterns = {
        "decisions": re.compile(r"\b(decision|decided|结论)\b", re.IGNORECASE),
        "open_questions": re.compile(r"\b(question|unknown|待确认|待定)\b", re.IGNORECASE),
        "next_actions": re.compile(r"\b(todo|next|action|下一步)\b", re.IGNORECASE),
        "risks": re.compile(r"\b(risk|blocker|阻塞|风险)\b", re.IGNORECASE),
    }

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        for key, pattern in patterns.items():
            if pattern.search(line):
                markers[key].append(line)

    for key in markers:
        markers[key] = markers[key][-20:]
    return markers


def compact_memory():
    """Compacts context_memory.md and writes a structured memory summary."""
    memory_file = STATE_FILES["context_memory"]

    if not os.path.exists(memory_file):
        print("Context memory file not found.")
        return

    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        max_lines = 100
        keep_recent = 20

        if len(lines) <= max_lines:
            print("Memory is within limits. No compaction needed.")
            return

        header = lines[:5]
        recent = lines[-keep_recent:]

        rotate_context_memory_versions()

        with open(memory_file, "w", encoding="utf-8") as f:
            f.writelines(header)
            f.write(f"\nArchived Context: [{len(lines) - 5 - keep_recent} lines hidden]\n\n")
            f.writelines(recent)

        summary = {
            "updated_at": datetime.now().isoformat(),
            "line_count_before": len(lines),
            "line_count_after": len(header) + 1 + len(recent),
            "markers": _extract_memory_markers(lines),
        }
        os.makedirs("logs", exist_ok=True)
        with open("logs/context_memory_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(
            f"Compacted memory from {len(lines)} lines to {len(header) + 1 + len(recent)} lines."
        )

    except Exception as e:
        print(f"Error compacting memory: {e}")


def _paper_identity(item):
    doi = str(item.get("doi", "")).strip().lower()
    pmid = str(item.get("pmid", "")).strip()
    title = str(item.get("title", "")).strip().lower()
    if doi:
        return f"doi:{doi}"
    if pmid:
        return f"pmid:{pmid}"
    if title:
        return f"title:{title}"
    return None


def _merge_literature(existing, incoming):
    existing = [x for x in existing if isinstance(x, dict)]
    incoming = [x for x in incoming if isinstance(x, dict)]

    by_id = {}
    by_identity = {}
    max_id = 0

    for item in existing:
        gid = item.get("global_id")
        if isinstance(gid, int) and gid > 0:
            by_id[gid] = item
            max_id = max(max_id, gid)
        ident = _paper_identity(item)
        if ident:
            by_identity[ident] = item

    for item in incoming:
        gid = item.get("global_id")
        ident = _paper_identity(item)

        target = None
        if isinstance(gid, int) and gid > 0 and gid in by_id:
            target = by_id[gid]
        elif ident and ident in by_identity:
            target = by_identity[ident]

        if target is not None:
            target.update(item)
            continue

        if not (isinstance(gid, int) and gid > 0 and gid not in by_id):
            max_id += 1
            item["global_id"] = max_id
        else:
            max_id = max(max_id, gid)

        by_id[item["global_id"]] = item
        ident = _paper_identity(item)
        if ident:
            by_identity[ident] = item

    return [by_id[k] for k in sorted(by_id.keys())]


def _merge_matrix(existing, incoming):
    existing = [x for x in existing if isinstance(x, dict)]
    incoming = [x for x in incoming if isinstance(x, dict)]

    by_id = {}
    no_id = []

    for row in existing:
        gid = row.get("global_id")
        if isinstance(gid, int) and gid > 0:
            by_id[gid] = row
        else:
            no_id.append(row)

    for row in incoming:
        gid = row.get("global_id")
        if isinstance(gid, int) and gid > 0:
            if gid in by_id:
                by_id[gid].update(row)
            else:
                by_id[gid] = row
        else:
            no_id.append(row)

    return [by_id[k] for k in sorted(by_id.keys())] + no_id


def update_state(payload_path, merge=True):
    """Updates state files based on a JSON payload file."""
    if not os.path.exists(payload_path):
        print(f"Error: Payload file '{payload_path}' not found.")
        sys.exit(1)

    try:
        with open(payload_path, "r", encoding="utf-8") as f:
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

        if merge and key == "literature_index" and isinstance(content, list):
            content = _merge_literature(_load_json_list(filename), content)
        elif merge and key == "synthesis_matrix" and isinstance(content, list):
            content = _merge_matrix(_load_json_list(filename), content)
        elif key == "literature_index" and isinstance(content, list):
            current_max_id = 0
            if os.path.exists(filename):
                try:
                    existing_data = _read_json_file(filename)
                    if isinstance(existing_data, list):
                        for item in existing_data:
                            gid = item.get("global_id")
                            if isinstance(gid, int) and gid > current_max_id:
                                current_max_id = gid
                except Exception as e:
                    print(f"Warning reading existing literature index for max_id: {e}")

            for item in content:
                gid = item.get("global_id")
                if (
                    ("global_id" not in item)
                    or (gid is None)
                    or (not isinstance(gid, int))
                    or (gid <= 0)
                ):
                    current_max_id += 1
                    item["global_id"] = current_max_id
                elif gid > current_max_id:
                    current_max_id = gid

        try:
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)

            if key == "context_memory":
                if os.path.exists(filename):
                    rotate_context_memory_versions()
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(str(content))
            elif filename.endswith(".json"):
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=2, ensure_ascii=False)
            else:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(str(content))

            updated_files.append(filename)

        except Exception as e:
            print(f"Error writing to {filename}: {e}")

    print(f"Successfully updated: {', '.join(updated_files)}")

    try:
        os.remove(payload_path)
    except Exception:
        pass


def snapshot_state(output_path=None):
    """Write a point-in-time snapshot of all state files to JSON."""
    snapshot = {}
    for key, filename in STATE_FILES.items():
        if os.path.exists(filename):
            try:
                if filename.endswith(".json"):
                    snapshot[key] = _read_json_file(filename)
                else:
                    with open(filename, "r", encoding="utf-8") as f:
                        snapshot[key] = f.read()
            except Exception as e:
                snapshot[key] = f"<Error loading {filename}: {e}>"
        else:
            snapshot[key] = None

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join("logs", "snapshots", f"state_snapshot_{ts}.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"Snapshot written: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Manage state files for Review Writing Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    load_parser = subparsers.add_parser("load", help="Load and print all state files as JSON")
    load_parser.add_argument("--section", help="Optional: Section name to filter relevant literature", default=None)
    load_parser.add_argument(
        "--fallback-recent",
        action="store_true",
        help="Fallback to last 20 literature entries if section filter is empty (legacy behavior)",
    )
    load_parser.add_argument(
        "--minimal",
        action="store_true",
        help="Return only progress, section-filtered literature/matrix, and matching section draft",
    )

    update_parser = subparsers.add_parser("update", help="Update state files from a payload")
    update_parser.add_argument(
        "payload_file",
        nargs="?",
        default="state_update_payload.json",
        help="Path to the JSON file containing updates (default: state_update_payload.json)",
    )
    update_parser.add_argument(
        "--replace",
        action="store_true",
        help="Disable merge mode and replace file content from payload.",
    )

    subparsers.add_parser("compact", help="Compact the context memory file if too large")

    snapshot_parser = subparsers.add_parser("snapshot", help="Write a full state snapshot JSON")
    snapshot_parser.add_argument(
        "--out",
        default=None,
        help="Optional snapshot output path (default: logs/snapshots/state_snapshot_<timestamp>.json)",
    )

    args = parser.parse_args()

    if args.command == "load":
        load_state(section=args.section, fallback_recent=args.fallback_recent, minimal=args.minimal)
    elif args.command == "update":
        if not os.path.exists(args.payload_file):
            print(
                f"Error: Payload file '{args.payload_file}' not found. "
                "Create this file or pass an explicit path."
            )
            sys.exit(1)
        update_state(args.payload_file, merge=not args.replace)
    elif args.command == "compact":
        compact_memory()
    elif args.command == "snapshot":
        snapshot_state(output_path=args.out)


if __name__ == "__main__":
    main()
