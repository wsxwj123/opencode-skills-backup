#!/usr/bin/env python3
"""Smoke test for delegate_review.py (blind-review delegation, fail-closed).

Bidirectional, self-contained, standalone (`python3 test_delegate_review_gate.py`):
- pack  -> exit 0, prints the checklist ids into the task package (no record file written).
- verify with a fully-adjudicated return -> exit 0 (合规).
- verify with a hard item verdict=fail -> exit 1 (违规, fail-closed).
- verify with a hard item missing from the return -> exit 1 (违规, 缺漏未裁决).
- soft item (severity=soft) missing/fail -> does NOT block (only soft_flags).

Builds its own tiny checklist fixture so it does not depend on the real
references/dod_checklist.json contents.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
DR = SCRIPTS / "delegate_review.py"

CHECKLIST = {
    "skill": "revise-sci-smoke",
    "gates": {
        "g1": {
            "title": "Smoke gate",
            "items": [
                {"id": "A1", "name": "hard item", "check": "must hold"},
                {"id": "A2", "name": "soft item", "check": "nice", "severity": "soft"},
            ],
        }
    },
}


def _write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(DR), *args], capture_output=True, text=True)


def _setup(tmp: Path) -> tuple[Path, Path]:
    ck = tmp / "checklist.json"
    _write(ck, CHECKLIST)
    files = tmp / "unit.json"
    _write(files, {})
    return ck, files


def _pack(tmp: Path, ck: Path, files: Path) -> subprocess.CompletedProcess:
    return _run("pack", "--checklist", str(ck), "--gate", "g1",
                "--files", str(files), "--workdir", str(tmp))


def test_pack_emits_task_package():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ck, files = _setup(tmp)
        r = _pack(tmp, ck, files)
        assert r.returncode == 0, r.stderr
        assert "A1" in r.stdout and "A2" in r.stdout, r.stdout
        assert not list(tmp.glob(".review_pkg_*.json")), "pack 不应写 .review_pkg 记录(无消费者)"


def test_verify_all_adjudicated_passes():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ck, files = _setup(tmp)
        _pack(tmp, ck, files)
        _write(tmp / ".review_return_g1.json", [
            {"id": "A1", "verdict": "pass", "evidence": "checked the file, holds"},
            {"id": "A2", "verdict": "pass", "evidence": "ok"},
        ])
        r = _run("verify", "--checklist", str(ck), "--gate", "g1", "--workdir", str(tmp))
        assert r.returncode == 0, r.stdout + r.stderr


def test_verify_hard_fail_blocks():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ck, files = _setup(tmp)
        _pack(tmp, ck, files)
        _write(tmp / ".review_return_g1.json", [
            {"id": "A1", "verdict": "fail", "evidence": "sample size not addressed"},
            {"id": "A2", "verdict": "pass", "evidence": "ok"},
        ])
        r = _run("verify", "--checklist", str(ck), "--gate", "g1", "--workdir", str(tmp))
        assert r.returncode == 1, r.stdout


def test_verify_hard_missing_blocks():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ck, files = _setup(tmp)
        _pack(tmp, ck, files)
        # A1 (hard) omitted entirely; A2 (soft) present.
        _write(tmp / ".review_return_g1.json", [
            {"id": "A2", "verdict": "pass", "evidence": "ok"},
        ])
        r = _run("verify", "--checklist", str(ck), "--gate", "g1", "--workdir", str(tmp))
        assert r.returncode == 1, r.stdout


def test_verify_soft_fail_does_not_block():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ck, files = _setup(tmp)
        _pack(tmp, ck, files)
        # A1 hard passes; A2 soft fails with no evidence -> only a soft flag.
        _write(tmp / ".review_return_g1.json", [
            {"id": "A1", "verdict": "pass", "evidence": "holds"},
            {"id": "A2", "verdict": "fail", "evidence": ""},
        ])
        r = _run("verify", "--checklist", str(ck), "--gate", "g1", "--workdir", str(tmp))
        assert r.returncode == 0, r.stdout
        summary = json.loads(r.stdout)
        assert summary["soft_flags"], summary


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: delegate_review pack/verify fail-closed both directions")
