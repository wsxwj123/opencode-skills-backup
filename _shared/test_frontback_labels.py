#!/usr/bin/env python3
"""§10 前后置标签检测的直连单测（补 acceptance 未覆盖的边界）。

acceptance/test_atomize_frontback.py 走 CLI 黑盒；这里直连 detect_labels/_norm_label，
钉死归一化、前置门、后置位置门、front 只取首个 / back 只取最早一个、防误判边界。
本文件 test_*.py，被 .gitignore 排除、不进 vendored 分发。run: python3 test_frontback_labels.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_headings import detect_labels, _norm_label, _match_label, \
    FRONT_ABSTRACT_LABELS, BACK_MATTER_LABELS  # noqa: E402


def _mk(text):
    """把多行文本按 markdown extract 语义造 (text, real_headings)：'# X' 行为 level1 真标题。"""
    headings = []
    pos = 0
    out = []
    for line in text.split("\n"):
        if line.startswith("# "):
            h = line[2:].strip()
            headings.append({"text": h, "level": 1, "char_offset": pos,
                             "is_caption": False, "confidence": "high"})
            out.append(h)
            pos += len(h) + 1
        else:
            out.append(line)
            pos += len(line) + 1
    return "\n".join(out), headings


def kinds(text):
    t, hd = _mk(text)
    return [(l["kind"], t[l["char_offset"]:l["char_offset"] + len(l["text"])])
            for l in detect_labels(t, hd)]


def conf_of(text, kind):
    """返回该 kind 标签的 confidence（无则 None）。R1/R2 契约判据用。"""
    t, hd = _mk(text)
    for l in detect_labels(t, hd):
        if l["kind"] == kind:
            return l["confidence"]
    return None


class TestNorm(unittest.TestCase):
    def test_fullwidth_and_colon_stripped(self):
        self.assertEqual(_norm_label("摘 要"), "摘要")       # 半角空格去掉
        self.assertEqual(_norm_label("致　谢"), "致谢")       # 全角空格去掉
        self.assertEqual(_norm_label("摘要："), "摘要")       # 全角尾冒号去掉
        self.assertEqual(_norm_label("Abstract:"), "abstract")  # 半角冒号+小写

    def test_lead_number_stripped_in_match(self):
        self.assertTrue(_match_label(_norm_label("一、致谢"), BACK_MATTER_LABELS))
        self.assertTrue(_match_label(_norm_label("5. Acknowledgements"), BACK_MATTER_LABELS))
        self.assertTrue(_match_label(_norm_label("摘要"), FRONT_ABSTRACT_LABELS))

    def test_english_multiword_label(self):
        # 去空白后 "Data Availability Statement" → "dataavailabilitystatement"，须仍命中
        self.assertTrue(_match_label(_norm_label("Data Availability Statement"),
                                     BACK_MATTER_LABELS))


class TestGates(unittest.TestCase):
    def test_front_first_only_and_before_body(self):
        # 中英两份摘要 → 只取最靠前一个 front_abstract
        ks = kinds("摘要\n本文摘要。\n# 1 引言\n正文\n# 参考文献\nrefs")
        self.assertEqual([k for k, _ in ks if k == "front_abstract"], ["front_abstract"])

    def test_back_position_gate_blocks_body_funding(self):
        # "基金" 词在正文行（长行、非独立短行）+ 位置在正文中部 → 绝不成后置切点
        ks = kinds("# 1 引言\n本研究受国家自然科学基金资助（编号81234567）继续说明。\n# 2 方法\n方法")
        self.assertEqual([k for k, _ in ks if k == "back_matter"], [])

    def test_back_earliest_only_after_last_body_heading(self):
        # 参考文献(真标题)之后有 致谢 + 基金 两个后置标签 → 只切最早一个
        ks = kinds("# 1 引言\n正文\n# 参考文献\nrefs\n致谢\n谢词\n基金\n基金说明")
        back = [v for k, v in ks if k == "back_matter"]
        self.assertEqual(len(back), 1)
        self.assertIn("致谢", back[0])

    def test_short_line_funding_before_refs_not_cut(self):
        # 独立短行 "基金" 但位置在参考文献之前（正文段）→ 位置门挡掉
        ks = kinds("# 1 引言\n基金\n某段正文\n# 参考文献\nrefs")
        self.assertEqual([k for k, _ in ks if k == "back_matter"], [])

    def test_no_labels_no_cuts(self):
        self.assertEqual(kinds("# 1 引言\n正文\n# 2 方法\n方法"), [])


class TestR1R2Confidence(unittest.TestCase):
    """§11 后置门加硬：confidence 决定是否成切点（消费方判据=非图注且 confidence!='low'）。"""

    def test_r1_back_matter_with_references_is_high(self):
        # 有参考文献锚点在前 → back_matter high（进 cut_points）
        self.assertEqual(
            conf_of("# 1 引言\n正文\n# 参考文献\nrefs\n致谢\n谢词", "back_matter"), "high")

    def test_r1_back_matter_without_references_is_low(self):
        # 末标题后独立短行"资助"、但全篇无参考文献锚点 → low（不进 cut_points）
        self.assertEqual(
            conf_of("# 1 引言\n正文\n# 2 结论\n结论\n资助\n资助说明", "back_matter"), "low")

    def test_r2_front_abstract_with_following_body_heading_is_high(self):
        # 摘要之后有正文标题 → front_abstract high
        self.assertEqual(
            conf_of("摘要\n摘要正文\n# 1 引言\n正文", "front_abstract"), "high")

    def test_r2_front_abstract_references_counts_as_body_heading(self):
        # 摘要之后只有"参考文献"这一真标题也算"其后有正文标题" → high
        self.assertEqual(
            conf_of("摘要\n摘要正文\n# 参考文献\nrefs", "front_abstract"), "high")

    def test_r2_lonely_front_abstract_without_following_heading_is_low(self):
        # 仅摘要标签 + 纯散文、其后无任何正文标题 → low（不翻路由为有标题路）
        self.assertEqual(
            conf_of("摘要\n本文纯散文无任何编号标题\n后续仍是散文", "front_abstract"), "low")

    def test_r2_headless_trailing_backmatter_not_emitted(self):
        # 无编号标题的纯散文 + 末尾"致谢"：无末正文标题（body_offs 空）→ 位置门挡掉，
        # 根本不产 back_matter（保守不切）。
        self.assertEqual(kinds("纯散文一段\n又一段散文\n致谢\n谢词"), [])


if __name__ == "__main__":
    unittest.main()
