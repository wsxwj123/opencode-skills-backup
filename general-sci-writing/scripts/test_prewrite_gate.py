#!/usr/bin/env python3
"""prewrite_gate.py 双向 smoke test — 自包含、tempfile 造输入、standalone 可跑。

覆盖 gsw 开写前置闸门的硬检查(合规→exit0 / 违规→exit≠0):
  合规: 第二节前，上一节 done + 盲检标记 passed + 无占位符 + 缩略词干净 → exit 0
  违规1: 删掉上一节盲检标记 → exit 1(blind review not passed)
  违规2: 上一节 manuscript 残留 CITE_PENDING 占位符 → exit 1(placeholders)
  违规3: section 不在 storyline.json → exit 1(not found in storyline)

figure_analysis 在本脚本里是"仅信息不阻断"(硬门交给 step0b)，不在此当硬门测。
abbreviation_consistency.py 对无占位/无裸缩写的干净稿会 exit0，故合规态可稳定通过。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "prewrite_gate.py"


def _build_compliant(root: Path) -> None:
    """造一个"写第二节 results_1"的完全合规工程。"""
    (root / "storyline.json").write_text(
        json.dumps({"sections": [{"id": "intro"}, {"id": "results_1"}]}),
        encoding="utf-8")
    (root / "writing_progress.json").write_text(
        json.dumps({"update_history": [{"section": "intro", "status": "done"}]}),
        encoding="utf-8")
    # 上一节盲检通过标记(prewrite_gate 硬校验读它)
    (root / ".review_pass").mkdir(exist_ok=True)
    (root / ".review_pass" / "intro.json").write_text(
        json.dumps({"passed": True, "section": "intro"}), encoding="utf-8")
    # manuscript 干净稿:无占位符、无裸缩写(避免误触 abbreviation 门)
    (root / "manuscripts").mkdir(exist_ok=True)
    (root / "manuscripts" / "02_intro.md").write_text(
        "This is the introduction. It states the study goal in plain words.\n",
        encoding="utf-8")


def _run(root: Path, section: str = "results_1") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--section", section, "--root", str(root)],
        capture_output=True, text=True)


def test_prewrite_gate_bidirectional() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_compliant(root)

        # --- 合规 → exit 0 ---
        r = _run(root)
        assert r.returncode == 0, f"compliant must pass, got {r.returncode}\n{r.stdout}\n{r.stderr}"
        payload = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][0])
        assert payload["ok"] is True, payload

        # --- 违规1: 缺盲检标记 → exit 1 ---
        (root / ".review_pass" / "intro.json").unlink()
        r = _run(root)
        assert r.returncode == 1, f"missing blind marker must block\n{r.stdout}"
        assert "blind review not passed" in r.stdout, r.stdout
        # 复原
        (root / ".review_pass" / "intro.json").write_text(
            json.dumps({"passed": True, "section": "intro"}), encoding="utf-8")

        # --- 违规2: 占位符残留 → exit 1 ---
        (root / "manuscripts" / "02_intro.md").write_text(
            "Intro with a dangling CITE_PENDING marker.\n", encoding="utf-8")
        r = _run(root)
        assert r.returncode == 1, f"placeholder must block\n{r.stdout}"
        assert "placeholder" in r.stdout.lower(), r.stdout
        # 复原
        (root / "manuscripts" / "02_intro.md").write_text(
            "This is the introduction. It states the study goal.\n", encoding="utf-8")

        # --- 违规3: section 不在 storyline → exit 1 ---
        r = _run(root, section="ghost_section")
        assert r.returncode == 1, f"unknown section must block\n{r.stdout}"
        assert "storyline" in r.stdout.lower(), r.stdout


def _build_first_section(root: Path, section_id: str, n_refs: int) -> None:
    """造一个"写首节 section_id"的工程，literature_matrix 给 n_refs 条文献。

    首节无上一节，绕开 done/盲检门，单独隔离软文献门这一条。
    """
    (root / "storyline.json").write_text(
        json.dumps({"sections": [{"id": section_id}, {"id": "results_1"}]}),
        encoding="utf-8")
    (root / "literature_matrix.json").write_text(
        json.dumps({section_id: [f"ref_{i}" for i in range(n_refs)]}),
        encoding="utf-8")


def test_literature_role_floor() -> None:
    """按 section 角色的软文献门：Intro 硬地板6/软10；Methods 不设门。"""
    # Intro n=4 < 硬地板6 → 硬拦
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_first_section(root, "intro", 4)
        r = _run(root, section="intro")
        assert r.returncode == 1, f"intro n=4 must block\n{r.stdout}"
        assert "hard floor" in r.stdout, r.stdout

    # Intro n=7 ∈ [6,10) → 过但 soft warn
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_first_section(root, "intro", 7)
        r = _run(root, section="intro")
        assert r.returncode == 0, f"intro n=7 must pass\n{r.stdout}\n{r.stderr}"
        payload = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][0])
        assert any("soft target" in w for w in payload["warnings"]), payload

    # Methods n=0 → 不设门放行
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_first_section(root, "methods", 0)
        r = _run(root, section="methods")
        assert r.returncode == 0, f"methods any count must pass\n{r.stdout}\n{r.stderr}"
        payload = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][0])
        role_check = next(c for c in payload["checks"] if c["name"] == "literature_role")
        assert role_check["role"] == "other" and role_check.get("note") == "no floor", role_check


if __name__ == "__main__":
    test_prewrite_gate_bidirectional()
    test_literature_role_floor()
    print("OK: prewrite_gate — compliant pass; blind-marker/placeholder/storyline blocks; "
          "literature floor intro-hard/intro-soft/methods-open")
