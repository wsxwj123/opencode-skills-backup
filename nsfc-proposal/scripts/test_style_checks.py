#!/usr/bin/env python3
"""回归测试：humanizer_zh.py 节奏/列表豁免 + diagnosis_engine.py 评级阈值/修复动作。

自包含、纯 assert、纯内存构造，不改被测脚本。
覆盖：
  humanizer_zh.rhythm_check —— 句长过均给 flat_rhythm 告警；错落文本不报。
  humanizer_zh.scan_text    —— allow_lists=True 豁免列表行；=False 同文本报 bullet_list（正反对照）。
  diagnosis_engine 评级阈值 —— _grade_from_ratio / _grade_from_issue_count / _score_to_grade 边界。
  diagnosis_engine._build_fix_actions —— 含 D 维报告产修复动作；全 A/无 C-D → 单条"维持当前质量"。
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import humanizer_zh as hz          # noqa: E402
import diagnosis_engine as de      # noqa: E402


def test_rhythm_flat_vs_varied() -> None:
    # 连续 3 句长度差 <5 字 → flat_rhythm
    flat = hz.rhythm_check("研究方法好。数据分析强。结果显著多。")
    assert flat["count"] >= 1, f"均匀句长应报 flat: {flat}"
    assert any(i["type"] == "flat_rhythm" for i in flat["issues"]), flat["issues"]

    # 长短错落 → 不报硬节奏问题
    varied = hz.rhythm_check(
        "简短。这是一个中等长度的句子描述内容细节。"
        "这里是一个明显更长的句子它包含了大量的额外说明文字用于打破节奏的均匀性从而避免单调问题的出现。"
    )
    assert varied["count"] == 0, f"错落文本不应报: {varied}"
    print("rhythm_check 句长过均报/错落不报：OK")


def test_scan_allow_lists() -> None:
    text = "- 列表项一\n- 列表项二"
    with_allow = hz.scan_text(text, allow_lists=True)
    assert with_allow["count"] == 0, f"allow_lists=True 应豁免列表: {with_allow}"

    without = hz.scan_text(text, allow_lists=False)
    codes = [i["code"] for i in without["issues"]]
    assert codes.count("bullet_list") == 2, f"allow_lists=False 应报 bullet_list: {codes}"
    print("scan_text 列表豁免 True/False 正反对照：OK")


def test_grade_thresholds() -> None:
    # _grade_from_ratio 边界：>=0.95 A / >=0.8 B / >=0.6 C / else D
    assert (de._grade_from_ratio(0.95), de._grade_from_ratio(0.94)) == ("A", "B")
    assert (de._grade_from_ratio(0.8), de._grade_from_ratio(0.79)) == ("B", "C")
    assert (de._grade_from_ratio(0.6), de._grade_from_ratio(0.59)) == ("C", "D")

    # _grade_from_issue_count：0 A / <=2 B / <=5 C / else D
    assert (de._grade_from_issue_count(0), de._grade_from_issue_count(2)) == ("A", "B")
    assert (de._grade_from_issue_count(3), de._grade_from_issue_count(5)) == ("C", "C")
    assert de._grade_from_issue_count(6) == "D"

    # _score_to_grade：>=3.8 A / >=3.0 B+ / >=2.0 C / else D
    assert (de._score_to_grade(3.8), de._score_to_grade(3.79)) == ("A", "B+")
    assert (de._score_to_grade(3.0), de._score_to_grade(2.99)) == ("B+", "C")
    assert (de._score_to_grade(2.0), de._score_to_grade(1.99)) == ("C", "D")
    print("diagnosis 评级阈值边界 ratio/issue_count/score_to_grade：OK")


def test_build_fix_actions() -> None:
    # 全 A + 一致性全过 + 矩阵 ok → 单条"维持当前质量"
    all_a = {
        "dimensions": {"D-03": {"name": "研究方案", "grade": "A"}},
        "consistency_validation": {"V-01": {"pass": True}},
        "citation_matrix": {"ok": True},
    }
    acts = de._build_fix_actions(all_a)
    assert len(acts) == 1 and acts[0]["title"] == "维持当前质量", acts

    # 含 D/C 维 → 产出对应修复动作（非"维持当前质量"）
    with_d = {
        "dimensions": {"D-01": {"name": "立项依据", "grade": "D"},
                       "D-07": {"name": "写作风格", "grade": "C"}},
        "consistency_validation": {},
        "citation_matrix": {"ok": True},
    }
    acts = de._build_fix_actions(with_d)
    titles = [a["title"] for a in acts]
    assert "维持当前质量" not in titles, "含D维不应输出维持动作"
    assert len(acts) >= 2, f"D-01+D-07 应各产一动作: {titles}"
    for a in acts:
        assert {"title", "location", "action", "acceptance"} <= set(a), f"动作字段不全: {a}"
    print("_build_fix_actions 含D产动作 / 全A维持：OK")


if __name__ == "__main__":
    test_rhythm_flat_vs_varied()
    test_scan_allow_lists()
    test_grade_thresholds()
    test_build_fix_actions()
    print("ALL PASS")
