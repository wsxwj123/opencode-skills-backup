#!/usr/bin/env python3
"""citation_guard.py 门禁聚合逻辑回归测试 — 自包含、纯 assert、standalone 可跑。

citation_guard_core 的 J4/J5/J7/A4 单项已被 test_format_contract 覆盖；本文件补
从未被测的**聚合器** run_integrity_gates 的裁决逻辑（哪些拦、哪些只 warn）与其
两个 helper：
  _extract_cited_numbers   正文 [n]/[a,b-c]/en-dash/分号 展开
  _entry_citation_number   多键回退取引用号
  run_integrity_gates:
    - 干净 → exit_code 0
    - J4 不完整（缺字段）→ fail-closed exit 2
    - A4 断裂（orphan 引用未列 / zombie 列而未引）→ fail-closed exit 2
    - J5 高自引 / J7 低时效 单独出现 → 仅 warn，exit 仍 0（不误拦既有工程）

Run: python3 test_citation_guard_gates.py   (rc=0 = 全过)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import citation_guard as G


def _complete_entry(num, year=2024, authors=None):
    return {
        "title": f"Paper {num}", "authors": authors or ["Xu A"],
        "journal": "Nat", "year": year, "volume": "1", "pages": "1-9",
        "doi": f"10.1/{num}", "citation_number": num,
    }


def test_extract_cited_numbers():
    got = G._extract_cited_numbers("a [1] b [3-5] c [7; 9] d [2,4]")
    assert got == {1, 3, 4, 5, 7, 9, 2, 4}, got
    # en-dash 区间
    assert G._extract_cited_numbers("see [10–12]") == {10, 11, 12}
    assert G._extract_cited_numbers("no brackets") == set()


def test_entry_citation_number():
    assert G._entry_citation_number({"citation_number": 5}) == 5
    assert G._entry_citation_number({"ref_number": "12"}) == 12, "字符串数字应转 int"
    assert G._entry_citation_number({"global_id": 3, "id": 9}) == 3, "按键优先级取 global_id"
    assert G._entry_citation_number({"nothing": 1}) is None, "无已知键→None"


def test_gates_clean_passes():
    entries = [_complete_entry(1), _complete_entry(2)]
    r = G.run_integrity_gates(entries, drafts_dir=None,
                              manuscript_authors=[], current_year=2026)
    assert r["exit_code"] == 0 and r["ok"] is True, r


def test_gates_j4_incomplete_blocks():
    # 缺 title/authors/journal 等 → J4 incomplete → fail-closed
    bad = [{"doi": "10.1/x", "citation_number": 1}]
    r = G.run_integrity_gates(bad, drafts_dir=None,
                              manuscript_authors=[], current_year=2026)
    assert r["exit_code"] == 2, f"J4 不完整必须拦: {r['j4_completeness']}"
    assert r["j4_completeness"]["incomplete"], "应记录 incomplete 条目"


def test_gates_a4_broken_blocks():
    with tempfile.TemporaryDirectory() as td:
        drafts = Path(td)
        # 正文引用 [1] 和 [3]；但 index 只列 1、2 →
        #   orphan: 3（引用但未列）；zombie: 2（列但未引）→ A4 fail
        (drafts / "body.md").write_text("uses [1] and [3]\n", encoding="utf-8")
        entries = [_complete_entry(1), _complete_entry(2)]
        r = G.run_integrity_gates(entries, drafts_dir=drafts,
                                  manuscript_authors=[], current_year=2026)
        assert r["exit_code"] == 2, f"A4 断裂必须拦: {r['a4_bidirectional']}"
        assert r["a4_bidirectional"]["status"] == "fail"
        assert 3 in r["a4_bidirectional"]["orphans"], r["a4_bidirectional"]
        assert 2 in r["a4_bidirectional"]["zombies"], r["a4_bidirectional"]

        # 完美配对 → A4 ok，exit 0
        (drafts / "body.md").write_text("uses [1] and [2]\n", encoding="utf-8")
        r2 = G.run_integrity_gates(entries, drafts_dir=drafts,
                                   manuscript_authors=[], current_year=2026)
        assert r2["exit_code"] == 0 and r2["a4_bidirectional"]["status"] == "ok", r2


def test_gates_j5_j7_advisory_never_block():
    # 高自引（3/3 都是本文作者）+ 全部老文献（低时效），但条目本身完整、无 A4 →
    # J5/J7 只 warn，exit 必须仍为 0（不能因软门拦既有工程）。
    authors = ["Xu A"]
    entries = [_complete_entry(i, year=2005, authors=["Xu A"]) for i in (1, 2, 3)]
    r = G.run_integrity_gates(entries, drafts_dir=None,
                              manuscript_authors=authors, current_year=2026)
    assert r["exit_code"] == 0, f"J5/J7 是 warn 级，绝不能改 exit_code: {r}"
    assert r["j5_self_citation"]["strength"] == "warn"
    assert r["j7_recency"]["strength"] == "warn"
    # 高自引确实被标记为 warn（证明不是因为没检测到才没拦）
    assert r["j5_self_citation"]["status"] == "warn", r["j5_self_citation"]


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
