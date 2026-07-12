#!/usr/bin/env python3
"""引文核证 + 接续/决定日志 两个共享件的离线自检。stdlib、无 fixture。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SHARED = Path(__file__).resolve().parent
CLAIM = SHARED / "citation_claim_check.py"
JOURNAL = SHARED / "session_journal.py"
PY = sys.executable or "python"


def _run(script: Path, *args: str, cwd: str | None = None) -> tuple[str, int]:
    p = subprocess.run([PY, str(script), *args], capture_output=True, text=True, cwd=cwd)
    return (p.stdout + p.stderr), p.returncode


def _write_evidence(root: Path, rows: list[dict]) -> None:
    (root / "claim_evidence.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


# ---------- citation_claim_check ----------

def test_claim_support_passes():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_evidence(root, [{
            "section": "3.1", "claim_sentence": "PMG 抑制 HepG2 增殖", "is_load_bearing": True,
            "ref_id": "[12]", "retrieved_abstract": "PMG dose-dependently inhibited HepG2 proliferation...",
            "verdict": "support", "evidence_quote": "inhibited HepG2 proliferation", "user_confirmed": True,
        }])
        out, rc = _run(CLAIM, "--root", str(root))
        assert rc == 0 and json.loads(out.strip().splitlines()[-1])["ok"] is True


def test_claim_contradict_blocks():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_evidence(root, [{
            "section": "3.1", "claim_sentence": "PMG 促进增殖", "is_load_bearing": True, "ref_id": "[12]",
            "retrieved_abstract": "PMG inhibited proliferation", "verdict": "contradict",
            "evidence_quote": "inhibited", "user_confirmed": True,
        }])
        out, rc = _run(CLAIM, "--root", str(root))
        assert rc == 2 and "contradict" in out


def test_claim_missing_abstract_blocks():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_evidence(root, [{
            "section": "3.1", "claim_sentence": "X", "is_load_bearing": True, "ref_id": "[9]",
            "retrieved_abstract": "", "verdict": "support", "user_confirmed": True,
        }])
        out, rc = _run(CLAIM, "--root", str(root))
        assert rc == 2 and "未取到" in out


def test_load_bearing_needs_user_confirm():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_evidence(root, [{
            "section": "3.1", "claim_sentence": "X", "is_load_bearing": True, "ref_id": "[9]",
            "retrieved_abstract": "real abstract text", "verdict": "support", "user_confirmed": False,
        }])
        out, rc = _run(CLAIM, "--root", str(root))
        assert rc == 2 and "人工确认" in out


def test_background_weak_does_not_block():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_evidence(root, [{
            "section": "1.1", "claim_sentence": "背景陈述", "is_load_bearing": False, "ref_id": "[3]",
            "retrieved_abstract": "loosely related", "verdict": "weak", "user_confirmed": False,
        }])
        out, rc = _run(CLAIM, "--root", str(root))
        assert rc == 0, "背景句 weak 不应阻断"


def test_claim_missing_file():
    with tempfile.TemporaryDirectory() as d:
        out, rc = _run(CLAIM, "--root", d)
        assert rc == 2 and "claim_evidence_missing" in out


# ---------- session_journal ----------

def test_journal_log_and_resume():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # state 文件
        (root / "project_state.json").write_text(
            json.dumps({"phase": 3, "completed_sections": ["3.1"], "next_section": "3.2"}), encoding="utf-8")
        # log 两条决定
        _run(JOURNAL, "log", "--root", str(root), "--note", "第3节先讲机制")
        _run(JOURNAL, "log", "--root", str(root), "--note", "别用被动语态开头")
        assert (root / "decisions_log.md").is_file()
        # resume 报告应含 phase + 两条决定
        out, rc = _run(JOURNAL, "resume", "--root", str(root))
        assert rc == 0
        assert "phase" in out and "第3节先讲机制" in out and "别用被动语态开头" in out
        assert "接续握手" in out


def test_journal_log_empty_note_rejected():
    with tempfile.TemporaryDirectory() as d:
        out, rc = _run(JOURNAL, "log", "--root", d, "--note", "   ")
        assert rc == 2


def test_journal_resume_no_state():
    with tempfile.TemporaryDirectory() as d:
        out, rc = _run(JOURNAL, "resume", "--root", d)
        assert rc == 0 and "未找到 state" in out


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"\nALL {len(fns)} PASSED")
