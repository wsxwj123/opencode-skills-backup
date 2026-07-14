#!/usr/bin/env python3
"""Smoke test for final_content_gate.py (placeholder-residue承重门, fail-closed).

Bidirectional:
  - violation: a comment unit with an AI_FILL_REQUIRED placeholder in response_en
    → exit 1, "FINAL_CONTENT_GATE: FAIL".
  - compliant: every required scalar filled + non-empty notes + modification_actions
    with a real reason → exit 0, "FINAL_CONTENT_GATE: PASS".
Self-contained: synthesizes units/ under tempfile.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "final_content_gate.py"


def _full_content() -> dict:
    return {
        "reviewer_comment_zh": "审稿人认为样本量不足。",
        "reviewer_intent_zh": "要求补充样本量说明。",
        "response_zh": "我们已在方法学中补充样本量估算。",
        "response_en": "We added a sample-size justification to the Methods section.",
        "revised_excerpt_en": "A power analysis indicated n=60 per group.",
        "revised_excerpt_zh": "功效分析显示每组需 60 例。",
        "notes_core_zh": ["核心：补充样本量估算段落。"],
        "notes_support_zh": ["支持：引用统计学方法出处。"],
        "modification_actions": [{"action_type": "添加", "target": "Methods", "reason": "补充样本量估算"}],
    }


def _write_unit(root: Path, uid: str, content: dict) -> None:
    units = root / "units"
    units.mkdir(parents=True, exist_ok=True)
    unit = {"unit_id": uid, "section": "major", "content": content}
    (units / f"{uid}.json").write_text(json.dumps(unit, ensure_ascii=False), encoding="utf-8")


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(root)],
        capture_output=True, text=True,
    )


def test_placeholder_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        content = _full_content()
        content["response_en"] = "[AI_FILL_REQUIRED] response to reviewer in english."
        _write_unit(root, "u1", content)
        r = _run(root)
        assert r.returncode == 1, f"expected FAIL exit 1, got {r.returncode}\n{r.stdout}"
        assert "FINAL_CONTENT_GATE: FAIL" in r.stdout, r.stdout
        assert "content.response_en" in r.stdout, r.stdout


def test_complete_unit_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_unit(root, "u2", _full_content())
        r = _run(root)
        assert r.returncode == 0, f"expected PASS exit 0, got {r.returncode}\n{r.stdout}"
        assert "FINAL_CONTENT_GATE: PASS" in r.stdout, r.stdout


if __name__ == "__main__":
    test_placeholder_fails()
    test_complete_unit_passes()
    print("OK: final_content_gate — placeholder fails, complete unit passes")
