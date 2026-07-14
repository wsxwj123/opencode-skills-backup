#!/usr/bin/env python3
"""Smoke test for strict_gate.py (structural承重门, fail-closed).

Bidirectional:
  - compliant: a fully-formed atomic project (state + index + one comment unit + one
    manuscript section unit, all required keys, no placeholders) → exit 0, "STRICT_GATE: PASS".
  - violation: same project but the unit's response_en is an AI placeholder
    → exit 1, "STRICT_GATE: FAIL".
Self-contained: builds the whole project tree under tempfile.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "strict_gate.py"


def _build_project(root: Path, response_en: str) -> None:
    (root / "units").mkdir(parents=True, exist_ok=True)
    (root / "manuscript_units").mkdir(parents=True, exist_ok=True)

    (root / "project_state.json").write_text(
        json.dumps({"counts": {"total_units": 1}}, ensure_ascii=False), encoding="utf-8")

    (root / "index.json").write_text(json.dumps({
        "toc": {"reviewers": [{"sections": [{"items": [{"unit_id": "c1"}]}]}]}
    }, ensure_ascii=False), encoding="utf-8")

    unit = {
        "unit_id": "c1",
        "order": 0,
        "reviewer": "Reviewer 1",
        "section": "major",
        "comment_number": "1",
        "title": "Sample size",
        "source": {"comments_docx": "c.docx", "manuscript_docx": "m.docx", "si_docx": ""},
        "links": {"anchors": [], "manuscript_unit_ids": ["m1"], "si_unit_ids": []},
        "content": {
            "reviewer_comment_zh": "样本量不足。",
            "reviewer_comment_en": "Sample size is insufficient.",
            "reviewer_intent_zh": "要求补充样本量说明。",
            "response_en": response_en,
            "response_zh": "我们已补充样本量估算。",
            "original_excerpt_en": "We enrolled patients.",
            "revised_excerpt_en": "We enrolled 60 patients per group (power analysis).",
            "revised_excerpt_zh": "每组纳入 60 例（功效分析）。",
            "atomic_location": {"manuscript_unit_id": "m1", "manuscript_sentence_index": 0},
            "modification_actions": [{"action_type": "添加", "target": "Methods", "reason": "补充样本量"}],
            "notes_core_zh": ["核心：补充样本量估算。"],
            "notes_support_zh": ["支持：引用统计出处。"],
            "evidence": {"text": [], "images": [], "table": {"columns": [], "rows": []}},
        },
        "status": {"response_state": "final", "excerpt_state": "final", "notes_state": "final"},
    }
    (root / "units" / "c1.json").write_text(json.dumps(unit, ensure_ascii=False), encoding="utf-8")

    m_unit = {
        "unit_id": "m1",
        "paragraph_index": 0,
        "text": "We enrolled patients.",
        "unit_type": "section_block",
        "section_unit_id": "sec1",
    }
    (root / "manuscript_units" / "m1.json").write_text(
        json.dumps(m_unit, ensure_ascii=False), encoding="utf-8")


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(root)],
        capture_output=True, text=True,
    )


def test_valid_project_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_project(root, "We added a sample-size justification. It reports n=60 per group. This addresses the concern.")
        r = _run(root)
        assert r.returncode == 0, f"expected PASS exit 0, got {r.returncode}\n{r.stdout}"
        assert "STRICT_GATE: PASS" in r.stdout, r.stdout


def test_placeholder_response_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_project(root, "[AI_FILL_REQUIRED] response to reviewer in english.")
        r = _run(root)
        assert r.returncode == 1, f"expected FAIL exit 1, got {r.returncode}\n{r.stdout}"
        assert "STRICT_GATE: FAIL" in r.stdout, r.stdout
        assert "response_en is placeholder" in r.stdout, r.stdout


if __name__ == "__main__":
    test_valid_project_passes()
    test_placeholder_response_fails()
    print("OK: strict_gate — valid project passes, placeholder response fails")
