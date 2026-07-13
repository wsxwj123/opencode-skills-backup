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

import sys as _sys
try:  # Windows GBK 控制台/管道捕获下 emoji print 防 UnicodeEncodeError
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
import argparse
import pathlib
import shutil
import subprocess
import sys

# Minimum-viable set: full copy below mirrors ALL scripts/*.py, so this list is
# only a post-copy sanity assertion (not the copy source). No drift risk if it
# lags behind SKILL.md — a new script still gets copied by the glob.
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
    "proofread.py",  # Phase 3 R21 字符级机器硬门禁(可阻断)
    "consolidate_references.py",  # Phase 4 合并参考文献为单一列表
    "export_docx.py",  # Phase 5d 最终 docx 交付物(需 templates/reference.docx)
]

STATE_JSON = '{"phase": 0, "completed_sections": [], "zotero_root_key": "", "authors": []}\n'

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

    # Full copy: mirror ALL scripts/*.py into the project (except tests and this
    # bootstrap itself). Root-causes whitelist drift — SKILL.md adding/renaming a
    # script (or an import dependency) can never silently miss a copy again.
    copied = 0
    for src in sorted((skill_dir / "scripts").glob("*.py")):
        if src.name.startswith("test_") or src.name == "init_project.py":
            continue
        shutil.copy(src, proj / "scripts" / src.name)
        copied += 1

    # REQUIRED_SCRIPTS kept as a minimum-viable-set assertion: full copy should
    # already include them; if any is absent the skill install is broken.
    missing = [n for n in REQUIRED_SCRIPTS if not (proj / "scripts" / n).exists()]
    if missing:
        sys.exit(f"❌ Missing required scripts after copy: {missing}. Verify --skill-dir={skill_dir}")

    # export_docx.py resolves templates/reference.docx as __file__.parent.parent/
    # templates/reference.docx — i.e. proj/templates/reference.docx once copied.
    # Ship the baked house-style template so Phase 5d docx export does not crash.
    ref_docx = skill_dir / "templates" / "reference.docx"
    if ref_docx.exists():
        (proj / "templates").mkdir(parents=True, exist_ok=True)
        shutil.copy(ref_docx, proj / "templates" / "reference.docx")

    print(f"✅ Project created at: {proj}")
    print(f"   Copied {copied} scripts (full scripts/*.py mirror)")

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

    # 强制门禁 hook 自动安装 + 打印结构签字命令（共享，跨全部学术技能）。
    _install_gate_hook(proj)

    print(f"\nNext: cd into {proj} before any Phase 1–4 command.")


def _install_gate_hook(proj) -> None:
    """调共享安装器 install_gate_hook.py 自动装强制门禁 hook（备份/校验/回滚 +
    心跳探测），回显其人话状态；并打印结构签字命令 SIGNOFF_CMD（绝对路径 + 项目根）。
    定位:本文件在 skills/review-writing/scripts/ → resolve().parents[2]=skills/ →
    _shared/。任何异常全吞——门禁自检绝不能反过来卡住技能。"""
    import json as _json
    import subprocess as _sp
    try:
        installer = pathlib.Path(__file__).resolve().parents[2] / "_shared" / "install_gate_hook.py"
        if not installer.is_file():
            return
        proc = _sp.run([sys.executable or "python", str(installer)],
                       capture_output=True, text=True, timeout=30)
        line = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout.strip() else ""
        res = _json.loads(line) if line else {}
        status, msg = res.get("status", ""), res.get("message", "")
        icon = {"active": "🛡️", "installed": "🛡️", "degraded": "⚠️", "error": "ℹ️"}.get(status, "ℹ️")
        if msg:
            print(f"{icon} 门禁保护[{status}]: {msg}")
        signoff = installer.parent / "structure_signoff_gate.py"
        if signoff.is_file():
            print(f'SIGNOFF_CMD: python "{signoff}" confirm --root "{proj}" --note "<用户确认原话>"')
        # 接续报告 + 引文核证命令（照 SIGNOFF_CMD 样式打印绝对路径，供 SKILL 开头/写节前直接调用）
        journal = installer.parent / "session_journal.py"
        if journal.is_file():
            print(f'RESUME_CMD: python "{journal}" resume --root "{proj}"')
        citecheck = installer.parent / "citation_claim_check.py"
        if citecheck.is_file():
            print(f'CITATION_CHECK_CMD: python "{citecheck}" --root "{proj}"')
    except Exception:
        pass


if __name__ == "__main__":
    main()
