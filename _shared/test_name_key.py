#!/usr/bin/env python3
"""J5 自引检查的**姓氏识别**回归测试（_name_key）。

背景：_name_key 旧实现用"最长 token 当姓氏"这个启发式判姓，实测误判：
  "Doe, Jane"  → 姓判成 jane（逗号前才是姓）
  "Pan-Pan Lu" → 姓判成 pan（连字符名被拆成两个 token，比姓 Lu 长）
后果：这类作者与 Vancouver 形态（"Doe J" / "Lu PP"）互相匹配不上，自引率被低估。

新判据（按序，可解释）：
  1. 有逗号 → 逗号前是姓（"Doe, Jane" / "van der Pol, E."）；
  2. 无逗号 → **最后一个"非首字母缩写"token 是姓**——Vancouver 形态把缩写放在
     末尾（"Doe J" / "Smith JA" / "De Vos M"），自然序把姓放在末尾
     （"Jane Doe" / "Pan-Pan Lu"），两者由此统一；
  3. 连字符/撇号在 token 内部连写不拆（"Pan-Pan" 是一个名，不是两个）；
  4. 后缀（Jr./PhD…）先剔除；中文名整串当姓、无缩写。

跑法：python3 _shared/test_name_key.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import citation_guard_core as C  # noqa: E402


def _sur(name):
    k = C._name_key(name)
    return k[0] if k else None


def _match(a, b):
    ka, kb = C._name_key(a), C._name_key(b)
    return bool(ka and kb and C._names_match(ka, kb))


# --- 复现：修前必失败 ---------------------------------------------------------

def test_repro_last_comma_first_surname():
    # 旧实现取最长 token → "jane"。姓是逗号前的 Doe。
    assert _sur("Doe, Jane") == "doe", C._name_key("Doe, Jane")


def test_repro_hyphenated_given_name():
    # 旧实现把 "Pan-Pan" 拆成两个 token 并取最长 → "pan"。姓是 Lu。
    assert _sur("Pan-Pan Lu") == "lu", C._name_key("Pan-Pan Lu")


def test_repro_cross_format_now_matches():
    # 姓判错的直接后果：同一个人的两种写法匹配不上。
    assert _match("Doe, Jane", "Doe J")
    assert _match("Pan-Pan Lu", "Lu PP")
    assert _match("Quancai Li", "Li Q")      # 真实索引里最常见的拼音自然序


# --- 各形态正例 ---------------------------------------------------------------

def test_last_comma_first():
    assert C._name_key("Doe, Jane") == ("doe", frozenset({"j"}))
    assert C._name_key("Smith, John") == ("smith", frozenset({"j"}))
    assert C._name_key("Whitsett, J.A.") == ("whitsett", frozenset({"j", "a"}))


def test_first_last():
    assert C._name_key("Jane Doe") == ("doe", frozenset({"j"}))
    assert C._name_key("Mary Ellen Sanders") == ("sanders", frozenset({"m", "e"}))


def test_hyphenated_given_keeps_one_token():
    assert C._name_key("Pan-Pan Lu") == ("lu", frozenset({"p"}))
    assert C._name_key("Xiao-Ming Wang") == ("wang", frozenset({"x"}))
    # 连字符姓氏两种写法一致
    assert _match("Sanchez-Garcia J", "J. Sanchez-Garcia")


def test_vancouver():
    assert C._name_key("Doe J") == ("doe", frozenset({"j"}))
    assert C._name_key("Smith JA") == ("smith", frozenset({"j"}))
    assert C._name_key("Wei XX") == ("wei", frozenset({"x"}))
    # 带小品词的姓（De Vos / van der Pol）：两种写法都落到同一个末词
    assert _sur("De Vos M") == "vos" and _sur("M. De Vos") == "vos"
    assert _sur("van der Pol, E.") == "pol" and _sur("E. van der Pol") == "pol"


def test_cjk_and_suffixes():
    assert C._name_key("张三") == ("张三", frozenset())
    assert C._name_key("李四") == ("李四", frozenset())
    # 后缀不当名、也不当姓
    assert C._name_key("Doe, John Jr.") == ("doe", frozenset({"j"}))
    assert C._name_key("Smith, John Jr., PhD") == ("smith", frozenset({"j"}))
    assert _sur("John Smith PhD") == "smith"


def test_accents_fold():
    # 同一个人在不同索引里带不带变音符都应同 key（真实数据 3.2% 名字带变音符）
    assert _sur("Chavarría M") == "chavarria" == _sur("Chavarria M")
    assert _match("Le Gouëllec A", "A. Le Gouellec")


def test_degenerate_inputs():
    assert C._name_key("") is None
    assert C._name_key(None) is None
    assert C._name_key("   ,  ") is None
    assert C._name_key("Smith") == ("smith", frozenset())
    assert C._name_key("J A")[0] == "a"          # 全是缩写：退化但不炸


# --- 🔴 防假阳：不同的人绝不能撞成同一个 --------------------------------------

def test_different_people_do_not_match():
    for a, b in [
        ("Wang Wei", "Wang Ming"),      # 名不同
        ("Li X", "Liu X"),              # 姓不同（近似但不同）
        ("Doe, Jane", "Doe, Robert"),   # 同姓不同名
        ("Smith JA", "Smith B"),        # 同姓，缩写不重叠
        ("Jane Doe", "Doe, Robert"),
        ("Pan-Pan Lu", "Lu QM"),
        ("Zhang, W.", "Zhang, Y."),
    ]:
        assert not _match(a, b), f"{a!r} 与 {b!r} 不是同一个人却匹配上了"


def test_hyphen_fragment_is_not_a_wildcard():
    # 拆分层偶尔会把 "Wang, Xue-Meng" 切出孤立的 "Xue-Meng"（真实数据里有）。
    # 它不得退化成"无缩写"key 去通配所有姓 Xue/Meng 的人。
    entries = [{"authors": ["Xue W", "Meng L", "Pan J"]}]
    for frag in ("Xue-Meng", "Pan-Pan"):
        r = C.check_self_citation(entries, [frag])
        assert r["count"] == 0, f"{frag} 误命中: {r}"


def test_self_citation_end_to_end_no_false_positive():
    entries = [{"authors": ["Wang Ming", "Liu X", "Doe, Robert"]},
               {"authors": ["Quancai Li", "Pan-Pan Lu"]}]
    r = C.check_self_citation(entries, ["Wang Wei"])
    assert r["count"] == 0, r
    # 真作者仍命中（两种写法各一条）
    assert C.check_self_citation(entries, ["Li Q"])["count"] == 1
    assert C.check_self_citation(entries, ["Doe RB"])["count"] == 1


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
