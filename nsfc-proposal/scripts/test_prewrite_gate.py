#!/usr/bin/env python3
"""Smoke test：nsfc prewrite_gate.py 开写前置闸门的硬检查（双向）。

自包含、纯 assert、用 tempfile 造合成项目，不改被测脚本。
覆盖 prewrite_gate 的硬检查：上一节完成、consistency_map 就位（含 M）、
experimental_design 素材就位、上一节盲检标记（跨 Phase）、占位符清零。

双向断言：
  合规 → exit 0；违规（缺盲检标记 / 占位符残留 / 素材缺失 / 上一节缺失）→ exit 1。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "prewrite_gate.py"


def _run(root: Path, section: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--section", section, "--root", str(root)],
        capture_output=True, text=True)


def _build_p3_1(root: Path, *, placeholder: bool = False,
                blind_pass: bool = True, ed_entries: bool = True,
                prev_file: bool = True) -> None:
    """造一个 P3_1 开写场景的合成项目，flag 控制各硬检查是否被破坏。"""
    (root / "data").mkdir(exist_ok=True)
    # consistency_map：非空 + 含 M（P3 须建立在 P2 的 M 之上）
    (root / "data" / "consistency_map.json").write_text(json.dumps({
        "H": [{"id": "H1"}], "O": [{"id": "O1"}],
        "M": [{"id": "M1"}],
    }, ensure_ascii=False), encoding="utf-8")
    # experimental_design：P3_1 硬要求 entries 非空
    (root / "data" / "experimental_design.json").write_text(json.dumps({
        "entries": [{"rc": "RC1", "methods": "m"}] if ed_entries else []
    }, ensure_ascii=False), encoding="utf-8")
    # 上一节 P2 文件（P3_1 的 prev 是 P2）
    (root / "sections").mkdir(exist_ok=True)
    if prev_file:
        body = "P2 正文，方案完整。"
        if placeholder:
            body += "\nCITE_PENDING 还没补引文"
        (root / "sections" / "P2_研究内容.md").write_text(body, encoding="utf-8")
    # 跨 Phase 盲检标记：P3_1←P2，需 .review_pass/P2.json passed:true
    if blind_pass:
        (root / ".review_pass").mkdir(exist_ok=True)
        (root / ".review_pass" / "P2.json").write_text(
            json.dumps({"passed": True, "section": "P2"}), encoding="utf-8")


def test_p1_compliant_passes() -> None:
    """首节 P1：只需 consistency_map 非空 → exit 0。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "data").mkdir()
        (root / "data" / "consistency_map.json").write_text(
            json.dumps({"H": [{"id": "H1"}]}, ensure_ascii=False), encoding="utf-8")
        r = _run(root, "P1")
        assert r.returncode == 0, f"P1 compliant should pass\n{r.stdout}\n{r.stderr}"
        payload = json.loads(r.stdout.strip().splitlines()[-1])
        assert payload["ok"] is True, payload


def test_p1_missing_consistency_map_blocks() -> None:
    """P1 缺 consistency_map → 硬拦 exit 1。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        r = _run(root, "P1")
        assert r.returncode == 1, f"missing consistency_map must block\n{r.stdout}"
        assert "consistency_map" in r.stdout, r.stdout


def test_p3_1_compliant_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_p3_1(root)
        r = _run(root, "P3_1")
        assert r.returncode == 0, f"P3_1 compliant should pass\n{r.stdout}\n{r.stderr}"
        payload = json.loads(r.stdout.strip().splitlines()[-1])
        assert payload["ok"] is True, payload
        names = {c["name"]: c["ok"] for c in payload["checks"]}
        assert names.get("blind_review") is True, names
        assert names.get("methodologies_M") is True, names


def test_p3_1_missing_blind_marker_blocks() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_p3_1(root, blind_pass=False)
        r = _run(root, "P3_1")
        assert r.returncode == 1, f"missing blind marker must block\n{r.stdout}"
        assert "blind review not passed" in r.stdout, r.stdout


def test_p3_1_placeholder_blocks() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_p3_1(root, placeholder=True)
        r = _run(root, "P3_1")
        assert r.returncode == 1, f"placeholder in prev section must block\n{r.stdout}"
        assert "placeholder" in r.stdout.lower(), r.stdout


def test_p3_1_missing_prev_and_ed_blocks() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_p3_1(root, prev_file=False, ed_entries=False)
        r = _run(root, "P3_1")
        assert r.returncode == 1, f"missing prev + empty ED must block\n{r.stdout}"
        assert "previous section" in r.stdout or "experimental_design" in r.stdout, r.stdout


if __name__ == "__main__":
    test_p1_compliant_passes()
    test_p1_missing_consistency_map_blocks()
    test_p3_1_compliant_passes()
    test_p3_1_missing_blind_marker_blocks()
    test_p3_1_placeholder_blocks()
    test_p3_1_missing_prev_and_ed_blocks()
    print("OK: prewrite_gate smoke — compliant→exit0, violations→exit1 (blind/placeholder/prev/ED)")
