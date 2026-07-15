#!/usr/bin/env python3
"""回归测试：state_manager.py 的 gate_check 优先级链 + sync 新鲜度 + 语义门 + deep_merge。

自包含、纯 assert、tempfile 造合成项目，直接调 state_manager 函数（gate_check 走 offline
避免联网），跑完自动清理，不改被测脚本。

与 test_literature_gate.py（只测总量文献硬门）互补，不重复。

覆盖：
  gate_check failed_at 优先级链 profile→sync→citation→literature_total→matrix→review：
    从一个全绿项目逐维破坏一处，断言 failed_at 精确命中该维、overall ok=False；全绿→"none"。
    另用 CLI 确认 rc 映射（全绿 rc=0、破坏 rc=2）。
  sync_all 新鲜度：phase0/init 豁免 fresh 全 True；非 init 子文件 mtime 早于 project_state 超2s→False。
  _sync_semantic_ok：strict（phase≥1）与非 strict 分支。
  deep_merge：嵌套递归合并 + 标量覆盖 + dict 覆盖标量。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import state_manager as sm  # noqa: E402


def _build_green(root: Path, min_total: int = 1, page_limit: int = 30) -> None:
    """造一个能通过 gate-check（offline）的最小合法项目。"""
    sm.init_project(root)
    prof = json.loads((root / "proposal_profile.json").read_text(encoding="utf-8"))
    prof["science_problem_attribute"] = "鼓励探索、突出原创"
    prof["citation_targets"] = {"min_total": min_total, "min_recent_5yr": 0, "min_cn_journals": 0}
    prof["page_limit"] = page_limit
    (root / "proposal_profile.json").write_text(json.dumps(prof, ensure_ascii=False), encoding="utf-8")

    now = datetime.now(timezone.utc).isoformat()
    idx = {
        "metadata": {"verification_status": "pending"},
        "entries": [{
            "ref_number": 1, "title": "Some Paper Title", "doi": "10.1000/xyz123",
            "pmid": "12345678", "year": 2023, "used_in_sections": ["P1_立项依据"],
            "key_finding": "kf", "search_source": "pubmed",
        }],
    }
    (root / "data/literature_index.json").write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
    mcp = {"metadata": {"schema_version": "1.0"},
           "entries": [{"doi": "10.1000/xyz123", "pmid": "12345678",
                        "title": "Some Paper Title", "verified_at": now, "retracted": False}]}
    (root / "data/mcp_literature_cache.json").write_text(json.dumps(mcp, ensure_ascii=False), encoding="utf-8")

    (root / "sections/P1_立项依据.md").write_text("# P1\n\n研究背景引用[1]，原创首次新发现。\n", encoding="utf-8")
    (root / "sections/REF_参考文献.md").write_text("# 参考文献\n\n[1] Some Paper Title. 2023.\n", encoding="utf-8")
    (root / "sections/00_摘要_中文.md").write_text("本项目研究某问题。" * 3, encoding="utf-8")
    (root / "sections/00_摘要_英文.md").write_text("This project studies a problem in depth.", encoding="utf-8")
    for b in ["B1_预算说明_直接费用.md", "B2_预算说明_合作外拨.md", "B3_预算说明_其他来源.md"]:
        (root / "sections" / b).write_text("预算说明内容。", encoding="utf-8")


def _gate(root: Path) -> dict:
    return sm.gate_check(root, offline=True, require_mcp=False)


def test_gate_green_is_none() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_green(root)
        rep = _gate(root)
        assert rep["ok"] is True, f"全绿应过: failed_at={rep['failed_at']}"
        assert rep["failed_at"] == "none", rep["failed_at"]
    print("gate_check 全绿 → failed_at=none, ok=True：OK")


def test_gate_failed_at_priority_chain() -> None:
    # 每个用例：从全绿破坏一处，断言 failed_at 精确命中该维
    def profile_break(root: Path) -> None:
        p = json.loads((root / "proposal_profile.json").read_text(encoding="utf-8"))
        p["science_problem_attribute"] = None
        (root / "proposal_profile.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")

    def sync_break(root: Path) -> None:
        (root / "context_memory.md").unlink()  # 语义门 has_context_blocks=False

    def citation_break(root: Path) -> None:
        (root / "data/mcp_literature_cache.json").write_text(
            '{"metadata":{"schema_version":"1.0"},"entries":[]}', encoding="utf-8")

    def matrix_break(root: Path) -> None:
        (root / "sections/P1_立项依据.md").write_text(
            "# P1\n\n引用[1]和[2]，原创首次新发现。\n", encoding="utf-8")  # [2] 孤儿引用

    cases = [
        ("profile", profile_break, 1, 30),
        ("sync", sync_break, 1, 30),
        ("citation", citation_break, 1, 30),
        ("literature_total", None, 30, 30),   # min_total=30 > 1 条 → 总量门失败
        ("matrix", matrix_break, 1, 30),
        ("review", None, 1, 0),               # page_limit=0 → 评审 pass_status≠pass
    ]
    for expected, breaker, min_total, page_limit in cases:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_green(root, min_total=min_total, page_limit=page_limit)
            if breaker:
                breaker(root)
            rep = _gate(root)
            assert rep["ok"] is False, f"{expected} 破坏后应 ok=False"
            assert rep["failed_at"] == expected, f"期望 failed_at={expected}，实际 {rep['failed_at']}"
    print("gate_check failed_at 优先级链 6 维逐一命中：OK")


def test_gate_cli_returncode() -> None:
    script = str(_HERE / "state_manager.py")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_green(root)
        r0 = subprocess.run([sys.executable, script, "--root", str(root), "gate-check", "--offline"],
                            capture_output=True, text=True)
        assert r0.returncode == 0, f"全绿 CLI 应 rc=0，实际 {r0.returncode}"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_green(root)
        p = json.loads((root / "proposal_profile.json").read_text(encoding="utf-8"))
        p["science_problem_attribute"] = None
        (root / "proposal_profile.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
        r2 = subprocess.run([sys.executable, script, "--root", str(root), "gate-check", "--offline"],
                            capture_output=True, text=True)
        assert r2.returncode == 2, f"破坏后 CLI 应 rc=2，实际 {r2.returncode}"
    print("gate-check CLI rc 映射（全绿0 / 破坏2）：OK")


def test_sync_all_freshness() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sm.init_project(root)
        # phase0/init 豁免：fresh 全 True，strict_mode False
        s0 = sm.sync_all(root)
        assert all(s0["fresh"].values()), f"phase0 应 fresh 全 True: {s0['fresh']}"
        assert s0["semantic"]["strict_mode"] is False, "phase0 不应 strict"

        # 转 phase1：把某子文件 mtime 设为远早于 project_state（超 2s 宽限）→ fresh=False
        ps = json.loads((root / "project_state.json").read_text(encoding="utf-8"))
        ps["phase"] = "phase1"
        ps["gate"] = "writing"
        (root / "project_state.json").write_text(json.dumps(ps, ensure_ascii=False), encoding="utf-8")
        st = (root / "project_state.json").stat().st_mtime
        stale = st - 100
        os.utime(root / "data/consistency_map.json", (stale, stale))

        s1 = sm.sync_all(root)
        assert s1["fresh"]["data/consistency_map.json"] is False, "陈旧子文件应 fresh=False"
        assert s1["fresh"]["context_memory.md"] is True, "宽限内文件应 fresh=True"
        assert s1["semantic"]["strict_mode"] is True, "phase1 应 strict"
    print("sync_all 新鲜度 phase0豁免 / phase1陈旧判False：OK")


def test_sync_semantic_ok_branches() -> None:
    # 非 strict：仅需 has_context_blocks + has_history
    non_strict_pass = {"strict_mode": False, "has_context_blocks": True, "has_history": True,
                       "cm_has_error": True, "p1_verified": False}
    assert sm._sync_semantic_ok(non_strict_pass) is True, "非strict：忽略 cm_error/p1_verified"
    non_strict_fail = {"strict_mode": False, "has_context_blocks": True, "has_history": False}
    assert sm._sync_semantic_ok(non_strict_fail) is False, "非strict：缺 history 应 False"

    # strict：额外要求 not cm_has_error 且 p1_verified
    strict_pass = {"strict_mode": True, "has_context_blocks": True, "has_history": True,
                  "cm_has_error": False, "p1_verified": True}
    assert sm._sync_semantic_ok(strict_pass) is True, "strict 全满足应 True"
    strict_fail_cm = {**strict_pass, "cm_has_error": True}
    assert sm._sync_semantic_ok(strict_fail_cm) is False, "strict：cm_has_error 应 False"
    strict_fail_p1 = {**strict_pass, "p1_verified": False}
    assert sm._sync_semantic_ok(strict_fail_p1) is False, "strict：p1 未核验应 False"
    print("_sync_semantic_ok strict/非strict 分支：OK")


def test_deep_merge() -> None:
    base = {"a": {"x": 1, "y": 2}, "b": 5, "c": {"deep": {"k": 1}}, "s": 9}
    patch = {"a": {"y": 99, "z": 3}, "b": 7, "c": {"deep": {"k": 2, "m": 3}}, "s": {"now": "dict"}}
    out = sm.deep_merge(base, patch)
    assert out["a"] == {"x": 1, "y": 99, "z": 3}, out["a"]      # 嵌套递归合并
    assert out["b"] == 7, "标量覆盖"
    assert out["c"] == {"deep": {"k": 2, "m": 3}}, out["c"]     # 多层递归
    assert out["s"] == {"now": "dict"}, "标量被 dict 覆盖"
    assert base["a"] == {"x": 1, "y": 2}, "不应改动入参 base"
    print("deep_merge 嵌套递归 + 标量覆盖 + 不改入参：OK")


if __name__ == "__main__":
    test_gate_green_is_none()
    test_gate_failed_at_priority_chain()
    test_gate_cli_returncode()
    test_sync_all_freshness()
    test_sync_semantic_ok_branches()
    test_deep_merge()
    print("ALL PASS")
