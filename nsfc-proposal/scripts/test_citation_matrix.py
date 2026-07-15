#!/usr/bin/env python3
"""回归测试：citation_validator.py 的 matrix_check 三方一致 + reorder_entries_by_p1。

自包含、纯 assert、纯内存构造（不联网、不碰文件），不改被测脚本。
覆盖：
  matrix_check —— 三方（P1 正文角标 / index used_in_sections含P1 / REF 角标）一致 → ok=True,
                  three_way_match=True, order_match=True；造 orphan → orphan_citations 非空 ok=False；
                  首现顺序错 → order_match=False。
  reorder_entries_by_p1 —— 按 P1 首现顺序重排 + 重编 1..N，未引用条目保留排末尾；
                           断言重排前后条目总数不变。
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import citation_validator as cv  # noqa: E402


def _index(refs: list[int]) -> dict:
    return {"metadata": {}, "entries": [
        {"ref_number": n, "title": f"P{n}", "used_in_sections": ["P1_立项依据"]} for n in refs
    ]}


def test_matrix_three_way_match() -> None:
    p1 = "引用[1]，随后[2]，再[3]。"
    ref = "[1] a\n[2] b\n[3] c\n"
    idx = _index([1, 2, 3])
    m = cv.matrix_check(p1, idx, ref)
    assert m["ok"] is True, m
    assert m["three_way_match"] is True, m
    assert m["order_match"] is True, m
    assert m["orphan_citations"] == [] and m["orphan_entries"] == [], m
    assert m["p1_count"] == 3 and m["index_count"] == 3 and m["ref_count"] == 3, m
    print("matrix_check 三方一致 → ok/three_way/order 全 True：OK")


def test_matrix_orphan_citation() -> None:
    # P1 引用 [1][2][3]，但 index/REF 只有 [1][2] → [3] 是孤儿引用
    p1 = "引用[1]，[2]，[3]。"
    ref = "[1] a\n[2] b\n"
    idx = _index([1, 2])
    m = cv.matrix_check(p1, idx, ref)
    assert m["ok"] is False, "有孤儿引用应 ok=False"
    assert m["orphan_citations"] == [3], m["orphan_citations"]
    assert m["three_way_match"] is False, m
    print("matrix_check 孤儿引用 → orphan_citations 非空, ok=False：OK")


def test_matrix_order_mismatch() -> None:
    # 三方集合相同，但 P1 首现顺序 1,2,3 与 REF 顺序 1,3,2 不一致
    p1 = "引用[1]，[2]，[3]。"
    ref = "[1] a\n[3] c\n[2] b\n"
    idx = _index([1, 2, 3])
    m = cv.matrix_check(p1, idx, ref)
    assert m["order_match"] is False, "顺序不一致应 order_match=False"
    assert m["ok"] is False, "顺序错整体应 ok=False"
    assert m["p1_first_order"] == [1, 2, 3] and m["ref_order"] == [1, 3, 2], m
    print("matrix_check 首现顺序错 → order_match=False：OK")


def test_reorder_by_p1() -> None:
    # index 原始编号 1..4；P1 首现顺序为 3,1（[4] 未引用，[2] 未引用）
    idx = {"metadata": {}, "entries": [
        {"ref_number": 1, "title": "one", "used_in_sections": ["P1_立项依据"]},
        {"ref_number": 2, "title": "two", "used_in_sections": ["P1_立项依据"]},
        {"ref_number": 3, "title": "three", "used_in_sections": ["P1_立项依据"]},
        {"ref_number": 4, "title": "four", "used_in_sections": ["P1_立项依据"]},
    ]}
    before = len(idx["entries"])
    p1 = "先引用[3]，再引用[1]。"
    out = cv.reorder_entries_by_p1(idx, p1)
    entries = out["entries"]
    assert len(entries) == before, f"重排不应增删条目：{before}->{len(entries)}"
    # 首现顺序 3,1 排前并重编为 1,2；未引用 2,4 按原编号升序排末尾重编 3,4
    titles = [e["title"] for e in entries]
    assert titles == ["three", "one", "two", "four"], titles
    assert [e["ref_number"] for e in entries] == [1, 2, 3, 4], "应重编 1..N"
    print("reorder_entries_by_p1 首现重排+重编+未引用末尾+总数不变：OK")


if __name__ == "__main__":
    test_matrix_three_way_match()
    test_matrix_orphan_citation()
    test_matrix_order_mismatch()
    test_reorder_by_p1()
    print("ALL PASS")
