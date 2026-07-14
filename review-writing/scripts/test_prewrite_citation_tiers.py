#!/usr/bin/env python3
"""按标题层级的每小节文献密度门（prewrite_gate check3）自检。

覆盖两件事：
  1) 正则兼容四级 id：outline 里的 `2.1.1` 不被截成 `2.1`（load_outline_order）。
  2) check3 分层硬地板 + 只卡叶子 + 软目标 warn：
     - 三级叶子 n<6 硬拦、=6 过、<10 仅 warn、≥10 无 warn；
     - 四级叶子 n<3 硬拦、=3 过、<5 仅 warn、≥5 无 warn；
     - 容器父节（大纲里有更深子节）放宽到 ≥1，不卡。

用子进程跑真门禁、解析 stdout JSON 里的 literature_matrix check 与 warnings，
与 prev/盲检 等其它检查解耦（只断言 check3 这一项与软目标 warn）。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "prewrite_gate.py"


def _lm_check_and_warnings(root: Path, section: str):
    """跑门禁，返回 (literature_matrix check dict, warnings list)。忽略整体 exit。"""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--section", section, "--root", str(root)],
        capture_output=True, text=True)
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("{"))
    data = json.loads(line)
    lm = next(c for c in data["checks"] if c["name"] == "literature_matrix")
    return lm, data["warnings"]


def _build(root: Path, outline_sections, target: str, rows: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "outline.md").write_text(
        "".join(f"## {s} heading\n" for s in outline_sections), encoding="utf-8")
    (root / "state.json").write_text(json.dumps({"completed_sections": []}),
                                     encoding="utf-8")
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / "synthesis_matrix.json").write_text(
        json.dumps([{"related_sections": [target], "pmid": str(i)} for i in range(rows)]),
        encoding="utf-8")
    (root / "drafts").mkdir(exist_ok=True)


def _scenario(outline_sections, target, rows):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build(root, outline_sections, target, rows)
        return _lm_check_and_warnings(root, target)


def _has_soft_warn(warnings) -> bool:
    return any("软目标" in w for w in warnings)


def test_regex_keeps_four_level_id():
    from prewrite_gate import load_outline_order
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "outline.md").write_text(
            "## 2.1 parent\n## 2.1.1 child\n", encoding="utf-8")
        order = load_outline_order(str(root))
    assert order == ["2.1", "2.1.1"], f"四级 id 被截断: {order}"


def test_three_level_leaf_floor_and_soft():
    # 三级叶子（无更深子节）：floor=6，软目标 10
    lm, w = _scenario(["3.1"], "3.1", 5)
    assert lm["ok"] is False and lm["floor"] == 6 and lm["level"] == 3, lm

    lm, w = _scenario(["3.1"], "3.1", 6)
    assert lm["ok"] is True and lm["floor"] == 6, lm
    assert _has_soft_warn(w), f"n=6<10 应有软目标 warn: {w}"

    lm, w = _scenario(["3.1"], "3.1", 10)
    assert lm["ok"] is True, lm
    assert not _has_soft_warn(w), f"n=10 不应有软目标 warn: {w}"


def test_four_level_leaf_floor_and_soft():
    # 四级叶子：outline 里 3.1 是父，3.1.1 是叶；floor=3，软目标 5
    sects = ["3.1", "3.1.1"]
    lm, w = _scenario(sects, "3.1.1", 2)
    assert lm["ok"] is False and lm["floor"] == 3 and lm["level"] == 4, lm

    lm, w = _scenario(sects, "3.1.1", 3)
    assert lm["ok"] is True and lm["floor"] == 3, lm
    assert _has_soft_warn(w), f"n=3<5 应有软目标 warn: {w}"

    lm, w = _scenario(sects, "3.1.1", 5)
    assert lm["ok"] is True, lm
    assert not _has_soft_warn(w), f"n=5 不应有软目标 warn: {w}"


def test_container_parent_relaxed():
    # 容器父节 3.1（下有 3.1.1）：floor 放宽到 1，1 条即过、无软目标 warn
    lm, w = _scenario(["3.1", "3.1.1"], "3.1", 1)
    assert lm["ok"] is True and lm["floor"] == 1 and lm.get("container") is True, lm
    assert not _has_soft_warn(w), f"容器节不应触发软目标 warn: {w}"


if __name__ == "__main__":
    test_regex_keeps_four_level_id()
    test_three_level_leaf_floor_and_soft()
    test_four_level_leaf_floor_and_soft()
    test_container_parent_relaxed()
    print("OK: 分层文献密度门 — 正则兼容四级 + 三/四级硬地板 + 软目标 warn + 容器豁免")
