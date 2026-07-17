#!/usr/bin/env python3
# 白盒测试：reference_renderer.citation_sort_key 提升为模块级后可导入 + 行为与旧闭包等价。
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reference_renderer as rr


def _old_sort_key(e):
    """旧的 render_all 内嵌闭包逻辑，逐字复制用于等价性对拍。"""
    m = re.search(r"\d+", str(e.get("id", "")))
    return int(m.group()) if m else float("inf")


class TestCitationSortKey(unittest.TestCase):
    def test_importable_module_level(self):
        self.assertTrue(callable(rr.citation_sort_key))

    def test_equivalent_to_old_closure(self):
        cases = [
            {"id": "ref001"}, {"id": "ref012"}, {"id": "ref2"},
            {"id": "new:smith2023"}, {"id": ""}, {}, {"id": "abc"},
            {"id": "ref100"}, {"id": "10.1/x"},
        ]
        for c in cases:
            self.assertEqual(rr.citation_sort_key(c), _old_sort_key(c), c)

    def test_numeric_ascending_order(self):
        entries = [{"id": "ref012"}, {"id": "ref001"}, {"id": "ref002"}]
        ordered = sorted(entries, key=rr.citation_sort_key)
        self.assertEqual([e["id"] for e in ordered], ["ref001", "ref002", "ref012"])

    def test_render_all_still_sorts_by_id(self):
        entries = [
            {"id": "ref002", "authors": ["B"], "year": 2021, "title": "T2"},
            {"id": "ref001", "authors": ["A"], "year": 2020, "title": "T1"},
        ]
        out = rr.render_all(entries)
        self.assertLess(out.index("T1"), out.index("T2"), "ref001 应排在 ref002 之前")


if __name__ == "__main__":
    unittest.main()
