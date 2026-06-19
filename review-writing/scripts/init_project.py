#!/usr/bin/env python3
"""
init_project.py — Phase 0.5 project scaffolding for the review-writing skill.

Creates the project folder structure, copies the active scripts, runs git init +
initial commit (if git is available), and writes the initial state.json + outline.md.
Replaces the inline `python3 << PYEOF ... PYEOF` block that previously lived in SKILL.md
Phase 0.5 — same effect, no placeholder-substitution-in-Python risk.

Usage (AI passes the three resolved paths/values):
  python3 scripts/init_project.py \
    --title "Review Title" \
    --base  "/path/to/project/base"      \   # default: current working directory
    --skill-dir "/Users/<name>/.claude/skills/review-writing"

Cross-platform: pure pathlib, no shell heredoc. Works on Mac/Linux/Windows.
The AI fills outline.md Parameters/Environment fields AFTER this runs (this only writes
the template skeleton, identical to the previous inline version).
"""

import argparse
import pathlib
import shutil
import subprocess
import sys

# keep aligned with SKILL.md Phase 0.2 Step 8 required[] and Phase 0.5 REQUIRED_SCRIPTS
REQUIRED_SCRIPTS = [
    "zotero_manager.py",
    "export_bibtex.py",
    "matrix_manager.py",
    "word_counter.py",
    "citation_guard.py",
    "validate_citations.py",
    "check_global_citation_sequence.py",
    "citation_utils.py",
    "citation_guard_core.py",  # imported by citation_guard.py
    "state_manager.py",  # used in Phase 2.5 None Mode (reindex) + set-phase/complete-section
    "prewrite_gate.py",  # Phase 3 Per-Section Cycle 开写前置闸门
    "delegate_review.py",  # Phase 3 section-dod 盲检委托 pack/verify
    "style_checker.py",  # 去 AI 风格检测
]

STATE_JSON = '{"phase": 0, "completed_sections": [], "zotero_root_key": ""}\n'

OUTLINE_TEMPLATE = """# Review Configuration (READ THIS FILE at the start of every phase)

## Parameters
- Title: [user input]
- Target Journal: [user input]
- Language: [English / Chinese]
- Reference Manager: [Zotero / None / EndNote]
- Word Count Target: [EN: 7,000–10,000 words / CN: 15,000–20,000 chars]
- Citation Requirements: ≥150 total (Original≥80, Review≥50, Preprint≥20)
- Discipline: [Medical-Biomedical / CS-AI / Interdisciplinary]

## Environment (filled after detection, read directly in later phases)
- os: [Darwin / Linux / Windows]
- git_available: [true / false]
- pubmed_proxy: [none / http://127.0.0.1:XXXX]
- zotero_lib_id: [numeric ID]
- search_fallback: [paper-search-mcp (when edirect unavailable)]
- subagent_model: [model name / same as main session]

## Research Question
- RQ / PICO: [filled after user confirms]

## Outline (filled after confirmation)
### 1. Introduction
#### 1.1 Background
#### 1.2 Scope
...

## Current Status
- Phase: Phase 0 complete
- Completed sections: none
- Zotero root collection key: [filled after Phase 1]
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 0.5 project scaffolding")
    parser.add_argument("--title", required=True, help="Review title (becomes project folder name)")
    parser.add_argument("--base", default=".", help="Project base location (default: current working directory)")
    parser.add_argument("--skill-dir", required=True, help="Directory containing this skill (scripts/ live here)")
    args = parser.parse_args()

    base = pathlib.Path(args.base).expanduser().resolve()
    skill_dir = pathlib.Path(args.skill_dir).expanduser().resolve()
    proj = base / args.title

    for d in ["drafts", "exports", "scripts", "data", "tmp", "figures"]:
        (proj / d).mkdir(parents=True, exist_ok=True)

    # Initialize figures index (needed by Phase 3 Step 3 in ALL modes)
    fig_index = proj / "figures" / "figure_index.md"
    if not fig_index.exists():
        fig_index.write_text("# Figure Index\n\n", encoding="utf-8")

    # Whitelist: copy ONLY the scripts the SKILL.md workflow actively calls.
    missing = []
    for name in REQUIRED_SCRIPTS:
        src = skill_dir / "scripts" / name
        if not src.exists():
            missing.append(name)
            continue
        shutil.copy(src, proj / "scripts" / name)
    if missing:
        sys.exit(f"❌ Missing scripts in SKILL_DIR: {missing}. Verify --skill-dir={skill_dir}")

    print(f"✅ Project created at: {proj}")
    print(f"   Copied {len(REQUIRED_SCRIPTS)} active scripts")

    # state.json + outline.md
    (proj / "state.json").write_text(STATE_JSON, encoding="utf-8")
    (proj / "outline.md").write_text(OUTLINE_TEMPLATE, encoding="utf-8")
    print("✅ Wrote state.json + outline.md")

    # Git auto-checkpoint init (skip if git not available)
    if shutil.which("git"):
        subprocess.run(["git", "init"], cwd=str(proj), check=True)
        gitignore = proj / ".gitignore"
        gitignore.write_text(".DS_Store\nThumbs.db\n__pycache__/\n*.pyc\nlogs/\n*.lock\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(proj), check=True)
        subprocess.run(["git", "commit", "-m", "[review] Phase 0: project initialized"], cwd=str(proj), check=True)
        print("✅ Git repo initialized with initial commit")
    else:
        print("ℹ️  Git not found — auto-checkpoint disabled (no rollback)")

    print(f"\nNext: cd into {proj} before any Phase 1–4 command.")


if __name__ == "__main__":
    main()
