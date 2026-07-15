#!/usr/bin/env python3
"""Tests for state_manager.py rollback + aggregate-edit-plan (data-safety承重).

rollback:
  - snapshot -> mutate a unit -> rollback restores the original unit content;
  - index.json / project_state.json restore to the project ROOT, never into units/;
  - no snapshot -> exit 1 and units/ is left intact (fail-closed, no wipe).

aggregate-edit-plan:
  - a filled revised_excerpt_en replaces its [PENDING Step 7] placeholder;
  - "无" becomes "无改动";
  - a still-placeholder unit stays PENDING and forces exit 2;
  - a uid absent from the plan is silently skipped (no crash / no stray write).
Self-contained: tempfile project dirs, JSON units written inline.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "state_manager.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_rollback_restores_and_routes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        unit_p = root / "units" / "u-001.json"
        _write(unit_p, {"unit_id": "u-001", "section": "major",
                        "content": {"revised_excerpt_en": "ORIGINAL"}})
        _write(root / "index.json", {"a": 1})
        _write(root / "project_state.json", {"skill": "reviewer-response-sci"})

        assert _run("snapshot", "--project-root", str(root)).returncode == 0

        # Mutate the unit and delete a tracked root file.
        _write(unit_p, {"unit_id": "u-001", "section": "major",
                        "content": {"revised_excerpt_en": "MUTATED"}})
        (root / "index.json").unlink()

        r = _run("rollback", "--project-root", str(root))
        assert r.returncode == 0, r.stdout + r.stderr

        restored = json.loads(unit_p.read_text(encoding="utf-8"))
        assert restored["content"]["revised_excerpt_en"] == "ORIGINAL", restored
        # index.json comes back at root, NOT under units/.
        assert (root / "index.json").exists(), "index.json not restored to root"
        assert not (root / "units" / "index.json").exists(), "index.json wrongly restored into units/"


def test_rollback_no_snapshot_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        unit_p = root / "units" / "x.json"
        _write(unit_p, {"unit_id": "x", "section": "major", "content": {}})
        r = _run("rollback", "--project-root", str(root))
        assert r.returncode == 1, r.stdout
        assert "STATE_ROLLBACK: FAIL" in r.stdout, r.stdout
        # units/ must be untouched — no snapshot must never wipe live units.
        assert unit_p.exists(), "units/ wiped on failed rollback"


def test_aggregate_edit_plan_fill_nochange_pending() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "units" / "u-001.json", {"unit_id": "u-001", "section": "major",
               "content": {"revised_excerpt_en": "Real new text."}})
        _write(root / "units" / "u-002.json", {"unit_id": "u-002", "section": "major",
               "content": {"revised_excerpt_en": "无"}})
        _write(root / "units" / "u-003.json", {"unit_id": "u-003", "section": "major",
               "content": {"revised_excerpt_en": "[PENDING Step 7]"}})
        # u-999 is filled but never appears in the plan -> must be silently skipped.
        _write(root / "units" / "u-999.json", {"unit_id": "u-999", "section": "major",
               "content": {"revised_excerpt_en": "Orphan text."}})
        plan = root / "manuscript_edit_plan.md"
        plan.write_text(
            "- u-001: [PENDING Step 7]\n- u-002: [PENDING Step 7]\n- u-003: [PENDING Step 7]\n",
            encoding="utf-8",
        )

        r = _run("aggregate-edit-plan", "--project-root", str(root))
        # A still-PENDING unit forces exit 2 (WARN).
        assert r.returncode == 2, r.stdout

        out = plan.read_text(encoding="utf-8")
        assert "- u-001: Real new text." in out, out
        assert "- u-002: 无改动" in out, out
        assert "- u-003: [PENDING Step 7]" in out, out
        # Orphan uid must not have been appended anywhere.
        assert "Orphan text." not in out, "u-999 (absent from plan) wrongly written into plan"


if __name__ == "__main__":
    test_rollback_restores_and_routes()
    test_rollback_no_snapshot_fails_closed()
    test_aggregate_edit_plan_fill_nochange_pending()
    print("OK: state_manager — rollback restore/route/fail-closed, aggregate-edit-plan fill/nochange/pending")
