#!/usr/bin/env python3
"""J5 自引检查的作者串解析回归测试。

背景：真实 literature_index 里 authors 常把整串作者塞进单个 list 元素
（['Nasim, F., B.F. Sabath, and G.A. Eapen']，本机实测约 26% 条目是这形态）。
修复前 _split_author_field 对 list 原样返回，整串只产出一个 name key
（最长 token "sabath"），第一作者 Nasim 匹配不上 → 自引率被系统性低估。

跑法：python3 _shared/test_self_citation_parsing.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import citation_guard_core as C  # noqa: E402


def _keys(value):
    return C._entry_author_keys({"authors": value})


def _surnames(value):
    return [k[0] for k in _keys(value)]


# --- 复现：整串单元素 list ---------------------------------------------------

def test_blob_in_single_list_slot_yields_every_author():
    blob = ["Nasim, F., B.F. Sabath, and G.A. Eapen"]
    assert _surnames(blob) == ["nasim", "sabath", "eapen"], _keys(blob)


def test_blob_first_author_now_matches_manuscript_author():
    entries = [{"authors": ["Nasim, F., B.F. Sabath, and G.A. Eapen"]}]
    for who in ("Nasim F", "Sabath BF", "Eapen GA"):
        r = C.check_self_citation(entries, [who])
        assert r["count"] == 1, f"{who} 应命中自引: {r}"


def test_non_author_still_does_not_match():
    entries = [{"authors": ["Nasim, F., B.F. Sabath, and G.A. Eapen"]}]
    r = C.check_self_citation(entries, ["Wang L"])
    assert r["count"] == 0, r


def test_plain_string_blob_also_split():
    # 字符串分支旧实现只切 and/;/&，不切逗号，同样漏掉 Nasim。
    s = "Nasim, F., B.F. Sabath, and G.A. Eapen"
    assert _surnames(s) == ["nasim", "sabath", "eapen"], _keys(s)


# --- 边界：不许误伤 -----------------------------------------------------------

def test_single_author_with_comma_stays_one_person():
    assert _keys(["Zhang, W."]) == [("zhang", frozenset({"w"}))]
    assert _keys(["Kim, D.H., et al."]) == [("kim", frozenset({"d", "h"}))]


def test_suffixes_do_not_split_a_name():
    # "Smith, John Jr., PhD" 是一个人，且 key 与修复前逐字相同。
    assert _keys(["Smith, John Jr., PhD"]) == [("smith", frozenset({"j", "p"}))]


def test_normal_multi_element_list_unchanged():
    assert _keys(["Smith J", "Doe A"]) == [
        ("smith", frozenset({"j"})),
        ("doe", frozenset({"a"})),
    ]
    assert _surnames(["Smith, J", "Doe, A"]) == ["smith", "doe"]


def test_last_first_alternating_pairs():
    # 只断言切分；姓氏归属由 _name_key 的"最长 token"策略决定（本轮不动它，
    # 'Doe, Jane' 会被判成姓 jane），那是另一个已知限制。
    assert C._split_names("Smith, John, Doe, Jane") == ["Smith, John", "Doe, Jane"]


def test_cjk_and_degenerate_inputs():
    assert _keys(["张三"]) == [("张三", frozenset())]
    assert _keys([]) == []
    assert _keys(["", "   "]) == []
    assert _keys(None) == []
    assert _keys(123) == []


def test_et_al_is_not_an_author():
    assert _surnames(["Fujita, Y., et al."]) == ["fujita"]
    assert _surnames("Wang L, et al.") == ["wang"]


# --- J5 契约：advisory，且分母/状态语义不变 ------------------------------------

def test_skipped_semantics_unchanged():
    assert C.check_self_citation([{"authors": ["A B"]}], [])["status"] == "skipped"
    assert C.check_self_citation([{"title": "x"}], ["A B"])["status"] == "skipped"


def test_warn_threshold_unchanged():
    entries = [{"authors": ["Xu, A."]} for _ in range(3)]
    r = C.check_self_citation(entries, ["Xu A"])
    assert r["status"] == "warn" and r["self_ratio"] == 1.0, r
    assert set(r) == {"status", "self_ratio", "count", "total_with_authors",
                      "threshold"}, r


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # 修复前 _split_names 不存在，也要报 FAIL 而非中断
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
