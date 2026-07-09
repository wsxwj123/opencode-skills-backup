#!/usr/bin/env python3
"""Regression guard: every scripts/*.py the SKILL.md workflow invokes at project
runtime must be in init_project.REQUIRED_SCRIPTS, or Phase 3/4/5 crashes with
'No such file' because init_project only copies the whitelist into the project.

Allowlist (NOT copied into the project, by design):
  - init_project.py: the bootstrap script itself, run from SKILL_DIR to CREATE
    the project; it never runs from inside the project.
  - make_reference_docx.py: dev-time template baker, only referenced in a note
    ("该模板由 ... 烘焙"); the baked templates/reference.docx is shipped instead.
"""
from __future__ import annotations

import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
BOOTSTRAP_OR_DEV = {"init_project.py", "make_reference_docx.py"}


def called_scripts() -> set[str]:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    return {m + ".py" for m in re.findall(r"scripts/([a-zA-Z_][a-zA-Z0-9_]*)\.py", text)}


def required_scripts() -> set[str]:
    text = (SKILL_DIR / "scripts" / "init_project.py").read_text(encoding="utf-8")
    block = re.search(r"REQUIRED_SCRIPTS\s*=\s*\[(.*?)\]", text, re.DOTALL)
    assert block, "REQUIRED_SCRIPTS list not found in init_project.py"
    return set(re.findall(r'"([a-zA-Z_][a-zA-Z0-9_]*\.py)"', block.group(1)))


def test_all_called_runtime_scripts_are_copied() -> None:
    uncopied = called_scripts() - required_scripts() - BOOTSTRAP_OR_DEV
    assert not uncopied, (
        f"SKILL.md calls scripts/ not in REQUIRED_SCRIPTS (will crash in-project): "
        f"{sorted(uncopied)}"
    )


def test_reference_docx_template_exists() -> None:
    # export_docx.py needs it copied into proj/templates/; it must exist upstream.
    assert (SKILL_DIR / "templates" / "reference.docx").exists()


if __name__ == "__main__":
    test_all_called_runtime_scripts_are_copied()
    test_reference_docx_template_exists()
    print("OK: all runtime scripts copied + reference.docx present")
