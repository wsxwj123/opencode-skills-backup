#!/usr/bin/env python3
"""Regression guard: state_manager 的文献/矩阵合并去重、PRISMA 不变量、以及
state.json 的三个保字段写操作（set_phase / complete_section / check_pending）。

风险点：
  _merge_literature —— 增量导入文献时按 doi>pmid>title 身份去重。若去重错误会
    静默丢论文或重复计数；必须保证"同一篇合并、新论文分配连续 global_id、绝不丢"。
  _merge_matrix    —— 按 (global_id, section_id) 合并综合矩阵行，无号行全保留。
  _validate_prisma_invariants —— PRISMA 流数守恒（dedup≤ident≤...；excl=screen-incl）。
    这是投稿包 PRISMA 图的数据正确性根基，双向断言"该报违规就报、健康就静默"。
  set_phase / complete_section —— 必须只动指定键、保留其余（防止改 phase 时抹掉
    completed_sections / zotero_root_key 等）；complete_section 幂等且不双列。
  check_pending —— Phase 4 入口门，有 pending 必须 exit1 拦截、清空放行。

全部纯函数或以显式 state_path 写临时文件，独立可跑。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import state_manager as sm


def _ids(rows):
    return [r.get("global_id") for r in rows]


def test_merge_literature_dedup_by_identity_and_assign_ids():
    existing = [{"global_id": 1, "doi": "10.1/x", "title": "A"}]
    incoming = [
        {"doi": "10.1/X", "title": "A duplicate", "year": 2020},  # 同 doi(大小写归一)→合并进 gid1
        {"pmid": "999", "title": "B"},                            # 新论文 → 分配 gid2
    ]
    merged = sm._merge_literature(existing, incoming)
    assert _ids(merged) == [1, 2], f"应合并同 doi、给新论文连续号: {_ids(merged)}"
    gid1 = next(r for r in merged if r["global_id"] == 1)
    assert gid1.get("year") == 2020, "重复项字段应 update 进已存在条目"
    assert len(merged) == 2, "去重后不该丢或多"


def test_merge_literature_never_drops_untitled_no_identity():
    # 无 doi/pmid/title → 无身份，不能与他人合并，必须各自分配号并全保留
    existing = []
    incoming = [{"note": "x"}, {"note": "y"}]
    merged = sm._merge_literature(existing, incoming)
    assert len(merged) == 2 and _ids(merged) == [1, 2], merged


def test_merge_literature_preexisting_gid_kept():
    existing = [{"global_id": 5, "pmid": "111", "title": "E"}]
    incoming = [{"global_id": 5, "pmid": "111", "title": "E2"}]  # 同 gid → 合并覆盖
    merged = sm._merge_literature(existing, incoming)
    assert len(merged) == 1 and merged[0]["title"] == "E2", merged


def test_merge_matrix_by_gid_section_and_noid_kept():
    existing = [{"global_id": 1, "section_id": "2.1", "note": "old"}]
    incoming = [
        {"global_id": 1, "section_id": "2.1", "note": "new"},  # 同键合并
        {"global_id": 1, "section_id": "2.2", "note": "other"},  # 不同 section → 新行
        {"section_id": "2.3"},  # 无 gid → 保留在尾部
    ]
    merged = sm._merge_matrix(existing, incoming)
    assert len(merged) == 3, merged
    keyed = {(r.get("global_id"), r.get("section_id")): r for r in merged}
    assert keyed[(1, "2.1")]["note"] == "new", "同 (gid,section) 应 update"
    assert (1, "2.2") in keyed and (None, "2.3") in keyed


def test_prisma_invariants_ok_and_violations():
    # 健康：identified≥dedup≥screen≥incl，excl=screen-incl
    assert sm._validate_prisma_invariants(
        {"identified": 100, "deduplicated": 80, "screened": 80,
         "included": 10, "excluded": 70}) == []
    # dedup>ident 违规
    v = sm._validate_prisma_invariants({"identified": 50, "deduplicated": 80})
    assert any("deduplicated" in x for x in v), v
    # excl != screen-incl 违规
    v = sm._validate_prisma_invariants(
        {"screened": 80, "included": 10, "excluded": 60})
    assert any("excluded" in x for x in v), v
    # included>screened 违规
    v = sm._validate_prisma_invariants({"screened": 5, "included": 9, "excluded": 0})
    assert any("included" in x for x in v), v


def test_set_phase_preserves_other_keys():
    with tempfile.TemporaryDirectory() as d:
        sp = str(Path(d) / "state.json")
        Path(sp).write_text(json.dumps(
            {"phase": 1, "mode": "write", "completed_sections": ["1.1"],
             "zotero_root_key": "ABC"}), encoding="utf-8")
        sm.set_phase(3, state_path=sp)
        st = json.loads(Path(sp).read_text(encoding="utf-8"))
        assert st["phase"] == 3, st
        # 其余键一字未动
        assert st["mode"] == "write" and st["completed_sections"] == ["1.1"] \
            and st["zotero_root_key"] == "ABC", st


def test_complete_section_idempotent_and_no_double_list():
    with tempfile.TemporaryDirectory() as d:
        sp = str(Path(d) / "state.json")
        Path(sp).write_text(json.dumps(
            {"completed_sections": ["1.1"],
             "pending_sections": {"bucket": ["1.2"]}}), encoding="utf-8")
        sm.complete_section("1.2", state_path=sp)
        sm.complete_section("1.1", state_path=sp)  # 重复 → no-op
        st = json.loads(Path(sp).read_text(encoding="utf-8"))
        assert st["completed_sections"] == ["1.1", "1.2"], st
        # 完成后必须从 pending 移除，绝不同时出现在两个列表
        assert "1.2" not in st["pending_sections"]["bucket"], st


def test_check_pending_blocks_then_passes():
    with tempfile.TemporaryDirectory() as d:
        sp = str(Path(d) / "state.json")
        # 有 pending → 抛 SystemExit(1)
        Path(sp).write_text(json.dumps(
            {"pending_sections": {"bucket": ["1.3"]}}), encoding="utf-8")
        raised = None
        try:
            sm.check_pending(state_path=sp)
        except SystemExit as e:
            raised = e.code
        assert raised == 1, f"有 pending 必须拦截 exit1, got {raised}"
        # 清空 → 放行(不抛)
        Path(sp).write_text(json.dumps(
            {"pending_sections": {"bucket": []}}), encoding="utf-8")
        sm.check_pending(state_path=sp)  # 不抛即通过


if __name__ == "__main__":
    test_merge_literature_dedup_by_identity_and_assign_ids()
    test_merge_literature_never_drops_untitled_no_identity()
    test_merge_literature_preexisting_gid_kept()
    test_merge_matrix_by_gid_section_and_noid_kept()
    test_prisma_invariants_ok_and_violations()
    test_set_phase_preserves_other_keys()
    test_complete_section_idempotent_and_no_double_list()
    test_check_pending_blocks_then_passes()
    print("OK: state_manager 合并去重 + PRISMA 不变量 + 保字段写 + Phase4 pending 门")
