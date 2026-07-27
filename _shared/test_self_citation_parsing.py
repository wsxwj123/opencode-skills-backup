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
    # "Smith, John Jr., PhD" 是一个人。后缀不再贡献缩写（旧实现把 PhD 的 p 当
    # 名字缩写混进 key），姓氏由逗号定为 smith。
    assert _keys(["Smith, John Jr., PhD"]) == [("smith", frozenset({"j"}))]


def test_normal_multi_element_list_unchanged():
    assert _keys(["Smith J", "Doe A"]) == [
        ("smith", frozenset({"j"})),
        ("doe", frozenset({"a"})),
    ]
    assert _surnames(["Smith, J", "Doe, A"]) == ["smith", "doe"]


def test_last_first_alternating_pairs():
    # 切分产出 Last, First 对；姓氏归属见 test_name_key.py（逗号前是姓）。
    assert C._split_names("Smith, John, Doe, Jane") == ["Smith, John", "Doe, Jane"]
    assert _surnames("Smith, John, Doe, Jane") == ["smith", "doe"]


# --- 名的成分不得被当成新作者 -------------------------------------------------

def test_hyphenated_given_name_is_one_person():
    # "Wang, Xue-Meng" = 姓 Wang + 名 Xue-Meng。旧实现按 [a-z]+ 取词，"Xue-Meng"
    # 出两个 token 被判成新作者，真实数据里 BibTeX 的 "Last, First-First and ..."
    # 整串几乎每个作者都被切碎。
    assert C._split_names("Wang, Xue-Meng") == ["Wang, Xue-Meng"]
    assert _surnames(["Wang, Xue-Meng"]) == ["wang"]
    s = "Fu, Zhuang-Jiong and Chen, Qi-Wen and Han, Zi-Yi"
    assert C._split_names(s) == ["Fu, Zhuang-Jiong", "Chen, Qi-Wen", "Han, Zi-Yi"]
    assert _surnames(s) == ["fu", "chen", "han"]
    assert C._split_names("Wang, Xue-Meng, Li, Ming-Hua") == \
        ["Wang, Xue-Meng", "Li, Ming-Hua"]


def test_given_name_with_middle_initials_is_one_person():
    # "Silva, Caio C G" 同理：一个名 + 自带的中间名缩写，不是两个人。
    assert C._split_names("Silva, Caio C G") == ["Silva, Caio C G"]
    assert _keys(["Silva, Caio C G"]) == [("silva", frozenset({"c", "g"}))]
    assert C._split_names("Smith, John A") == ["Smith, John A"]


# --- 🔴 防过并：该拆的必须还拆得开 --------------------------------------------

def test_must_still_split_distinct_authors():
    # 缩写在前 = 自然序的新作者（"B.F. Sabath"），绝不能并进上一个人
    assert C._split_names("Nasim, B.F. Sabath") == ["Nasim", "B.F. Sabath"]
    assert C._split_names("Nasim, F., B.F. Sabath, and G.A. Eapen") == \
        ["Nasim, F.", "B.F. Sabath", "G.A. Eapen"]
    # 上一个人已带名/缩写 → 后面的整名是新作者
    assert C._split_names("Zhang WX, Li Y") == ["Zhang WX", "Li Y"]
    assert C._split_names("Smith J, Doe A") == ["Smith J", "Doe A"]
    assert C._split_names("Chen, Ying-Chi and Li, Yi-Ting") == \
        ["Chen, Ying-Chi", "Li, Yi-Ting"]
    # 连字符姓氏打头也照拆
    assert C._split_names("Laberty-Robert, Christel and Sanchez, J") == \
        ["Laberty-Robert, Christel", "Sanchez, J"]


def test_over_merge_would_show_up_as_a_missing_author():
    # 过并的直接后果：第二个人查不到自引。这里逐个人都必须命中。
    entries = [{"authors": ["Fu, Zhuang-Jiong and Chen, Qi-Wen and Han, Zi-Yi"]}]
    for who in ("Fu ZJ", "Chen QW", "Han ZY"):
        assert C.check_self_citation(entries, [who])["count"] == 1, who
    # 不相干的人仍不命中
    assert C.check_self_citation(entries, ["Zhuang J"])["count"] == 0


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
