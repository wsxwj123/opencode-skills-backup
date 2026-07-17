#!/usr/bin/env python3
# 白盒测试：delegate_write 内部正则/装载器边界（acceptance 已覆盖 CLI 契约 V1-V9）。
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import delegate_write as dw


class TestBareNumRegex(unittest.TestCase):
    def test_matches_bare_numeric_citations(self):
        for s in ["[5]", "[5,6]", "[5-7]", "[ 5 , 6 ]", "[5，6]"]:
            self.assertTrue(dw.BARE_NUM_RE.search(s), s)

    def test_ignores_chinese_markers_and_keys(self):
        for s in ["[数据来源]", "[图]", "[表]", "[实验]", "[@ref001]", "[@new:x]"]:
            self.assertIsNone(dw.BARE_NUM_RE.search(s), s)


class TestSectionRegex(unittest.TestCase):
    def test_accepts_dotted(self):
        for s in ["2", "2.1", "2.1.3", "10.4"]:
            self.assertTrue(dw.SECTION_RE.match(s), s)

    def test_rejects_bad(self):
        for s in ["2.x", "P1", "2.", ".1", "abc"]:
            self.assertIsNone(dw.SECTION_RE.match(s), s)


class TestKeyRegex(unittest.TestCase):
    def test_extracts_keys(self):
        md = "见 [@ref001] 与 [@new:smith2023] 及 [@ref012]。"
        self.assertEqual(dw.KEY_RE.findall(md), ["ref001", "new:smith2023", "ref012"])


if __name__ == "__main__":
    unittest.main()
