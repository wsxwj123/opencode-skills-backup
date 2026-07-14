#!/usr/bin/env python3
"""prewrite_gate.py 冒烟测试 —— 重点覆盖「每章首节章边界硬门」四种情形 + 双向。

章边界块(prewrite_gate.py 内 prev_chapter_blind_review 检查):每章首节(sub<=1)
且非第1章,必须先有上一章章级盲检标记 <root>/.review_pass/第<N-1>章.json(passed:true),
否则硬拦 exit≠0。第1章无上一章放行;章内非首节(sub>1)该块 N/A,走既有 per-section 校验。

四种情形:
  1) 第1章首节(1.1)   → 放行(章边界块 N/A:无上一章)
  2) 第2章首节(2.1)   → 缺 第1章 标记 → exit≠0(章边界块硬拦)
  3) 造出 第1章 标记   → 2.1 放行(章边界块通过)
  4) 章内非首节(2.2)   → 章边界块 N/A,走既有校验:
       - 无 第1章 标记仍放行(证明该块对 sub>1 不生效)
       - 抽掉上一节 2.1 盲检标记 → exit≠0(既有 per-section blind_review 触发,非章边界块)

standalone: `python3 test_prewrite_gate.py`。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "prewrite_gate.py"


def _build(root: Path, chapters=("1", "2")) -> None:
    (root / "project_state.json").write_text(
        json.dumps({"outline": {"chapters": [{"chapter": c} for c in chapters]}}),
        encoding="utf-8")


def _write_section(root: Path, chapter: str, sub: int,
                   text: str = "本节内容已完成，无实验数值。\n") -> None:
    d = root / "atomic_md" / f"第{chapter}章"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{chapter}.{sub}_节.md").write_text(text, encoding="utf-8")


def _mark(root: Path, name: str) -> Path:
    """写盲检通过标记。name 形如 '第1章'(章级) 或 '2.1'(节级)。"""
    d = root / ".review_pass"
    d.mkdir(exist_ok=True)
    p = d / f"{name}.json"
    p.write_text(json.dumps({"passed": True}), encoding="utf-8")
    return p


def _run(root: Path, section: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--section", section, "--root", str(root), *extra],
        capture_output=True, text=True)


def _payload(proc: subprocess.CompletedProcess) -> dict:
    for ln in proc.stdout.splitlines():
        if ln.startswith("{"):
            return json.loads(ln)
    raise AssertionError(f"no JSON payload in stdout:\n{proc.stdout}")


def _check(payload: dict, name: str) -> dict | None:
    for c in payload["checks"]:
        if c.get("name") == name:
            return c
    return None


def test_ch1_first_section_passes() -> None:
    """情形1:第1章首节 1.1 放行(章边界块 N/A,无上一章)。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, chapters=("1",))
        r = _run(root, "1.1")
        assert r.returncode == 0, f"ch1 first section must pass\n{r.stdout}\n{r.stderr}"
        ch = _check(_payload(r), "prev_chapter_blind_review")
        assert ch and ch["ok"] is True and "N/A" in ch.get("note", ""), ch


def test_ch2_first_section_missing_prev_chapter_blocks() -> None:
    """情形2:第2章首节 2.1 缺 第1章 标记 → 章边界块硬拦 exit≠0。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, chapters=("1", "2"))
        r = _run(root, "2.1")
        assert r.returncode != 0, f"missing prev-chapter marker must block\n{r.stdout}"
        assert "第1章" in r.stdout, r.stdout
        ch = _check(_payload(r), "prev_chapter_blind_review")
        assert ch and ch["ok"] is False, ch


def test_ch2_first_section_with_marker_passes() -> None:
    """情形3:造出 第1章 标记 → 2.1 放行(章边界块通过)。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, chapters=("1", "2"))
        _mark(root, "第1章")
        r = _run(root, "2.1")
        assert r.returncode == 0, f"with prev-chapter marker must pass\n{r.stdout}"
        ch = _check(_payload(r), "prev_chapter_blind_review")
        assert ch and ch["ok"] is True and ch.get("prev") == "第1章", ch


def test_mid_chapter_section_uses_existing_checks() -> None:
    """情形4:章内非首节 2.2 走既有校验,章边界块 N/A。

    双向:
    - 无 第1章 标记仍放行(章边界块对 sub>1 不生效)。
    - 抽掉 2.1 节级盲检标记 → 既有 per-section blind_review 硬拦(非章边界块)。
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, chapters=("2",))          # 大纲仅含第2章,且无 第1章 标记
        _write_section(root, "2", 1)            # 上一节 2.1 存在且干净
        marker = _mark(root, "2.1")             # 上一节盲检标记

        # 放行方向:章边界块 N/A,尽管无 第1章 标记
        r = _run(root, "2.2")
        assert r.returncode == 0, f"mid-chapter section must pass w/o prev-chapter marker\n{r.stdout}\n{r.stderr}"
        pay = _payload(r)
        ch = _check(pay, "prev_chapter_blind_review")
        assert ch and ch["ok"] is True and "N/A" in ch.get("note", ""), ch
        assert _check(pay, "blind_review")["ok"] is True, pay  # 既有校验确实跑了

        # 拦截方向:抽掉上一节盲检标记 → 既有 per-section 校验触发,章边界块仍 N/A
        marker.unlink()
        r = _run(root, "2.2")
        assert r.returncode != 0, f"missing prev-section marker must block\n{r.stdout}"
        assert "2.1" in r.stdout, r.stdout
        pay = _payload(r)
        assert _check(pay, "blind_review")["ok"] is False, pay
        ch = _check(pay, "prev_chapter_blind_review")
        assert ch and ch["ok"] is True, ch  # 章边界块保持 N/A,非本次失败原因


def test_allow_manual_review_releases_chapter_gate_with_trail() -> None:
    """遗留2:第2章首节 2.1 缺 第1章 章级标记 + --allow-manual-review "理由"
    → 放行 exit0，且落痕 第1章.json(manual:true+reason) + MANUAL_REVIEW_AUDIT.log。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, chapters=("1", "2"))
        r = _run(root, "2.1", "--allow-manual-review", "平台无 academic-blind-reviewer，负责人张三放行")
        assert r.returncode == 0, f"manual override must pass\n{r.stdout}\n{r.stderr}"
        ch = _check(_payload(r), "prev_chapter_blind_review")
        assert ch and ch["ok"] is True and ch.get("manual") is True, ch
        marker = json.loads((root / ".review_pass" / "第1章.json").read_text(encoding="utf-8"))
        assert marker.get("manual") is True and marker.get("passed") is True, marker
        assert "张三" in marker.get("reason", ""), marker
        audit = (root / ".review_pass" / "MANUAL_REVIEW_AUDIT.log").read_text(encoding="utf-8")
        assert "第1章" in audit and "manual_review_override" in audit, audit


def test_allow_manual_review_empty_reason_rejected() -> None:
    """空理由 → 拒绝放行，章级盲检仍硬拦 exit≠0，且不落痕。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, chapters=("1", "2"))
        r = _run(root, "2.1", "--allow-manual-review", "   ")
        assert r.returncode != 0, f"empty reason must be rejected\n{r.stdout}"
        assert "非空理由" in r.stdout, r.stdout
        assert not (root / ".review_pass" / "第1章.json").exists(), "空理由不得落痕"


def test_manual_review_does_not_bypass_other_hard_gates() -> None:
    """逃生口只开盲检门:大纲缺本章等其余硬门照拦。
    大纲仅含第1章 → 2.1 的 outline 检查失败,即便带 --allow-manual-review 仍 exit≠0。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, chapters=("1",))  # outline 无 第2章
        r = _run(root, "2.1", "--allow-manual-review", "盲检子代理不可用")
        assert r.returncode != 0, f"outline hard gate must still block\n{r.stdout}"
        pay = _payload(r)
        assert _check(pay, "outline")["ok"] is False, pay


def test_allow_manual_review_releases_per_section_gate() -> None:
    """per-section 盲检门同样可放行:第2章 2.2 缺 2.1 节级盲检标记
    + --allow-manual-review → 放行并落痕 2.1.json。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, chapters=("2",))
        _write_section(root, "2", 1)  # 上一节 2.1 存在非空(prev_section_done 过)
        r = _run(root, "2.2", "--allow-manual-review", "盲检子代理反复失败，人工放行")
        assert r.returncode == 0, f"per-section manual override must pass\n{r.stdout}\n{r.stderr}"
        ch = _check(_payload(r), "blind_review")
        assert ch and ch["ok"] is True and ch.get("manual") is True, ch
        assert (root / ".review_pass" / "2.1.json").exists(), "per-section 放行须落痕"


if __name__ == "__main__":
    test_ch1_first_section_passes()
    test_ch2_first_section_missing_prev_chapter_blocks()
    test_ch2_first_section_with_marker_passes()
    test_mid_chapter_section_uses_existing_checks()
    test_allow_manual_review_releases_chapter_gate_with_trail()
    test_allow_manual_review_empty_reason_rejected()
    test_manual_review_does_not_bypass_other_hard_gates()
    test_allow_manual_review_releases_per_section_gate()
    print("OK: prewrite_gate chapter-boundary gate — ch1 pass / ch2 block→pass / mid-chapter existing-checks (bidirectional)"
          " + manual-review escape hatch (per-section & per-chapter release w/ trail, empty-reason reject, other hard gates still block)")
