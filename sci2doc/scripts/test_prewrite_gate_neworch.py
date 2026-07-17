#!/usr/bin/env python3
# 白盒测试：prewrite_gate §4.1-A 新增的 new_refs 并表核验 helpers（残留新键映射判定）。
# 只测新增逻辑，既有闸门检查由 acceptance/testkit 覆盖。
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prewrite_gate as pg


class TestNewOrchHelpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wb_gate_")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def test_load_newref_map_missing_is_empty(self):
        self.assertEqual(pg._load_newref_map(self.tmp), {})

    def test_load_newref_map_reads_file(self):
        with open(os.path.join(self.tmp, ".newref_map.json"), "w") as f:
            json.dump({"new:x": "ref002"}, f)
        self.assertEqual(pg._load_newref_map(self.tmp), {"new:x": "ref002"})

    def test_prev_section_md_files_matches_both_namings(self):
        cdir = os.path.join(self.tmp, "atomic_md", "第2章")
        os.makedirs(cdir)
        open(os.path.join(cdir, "2.1.md"), "w").close()
        open(os.path.join(cdir, "2.2_标题.md"), "w").close()
        open(os.path.join(cdir, "2.3.md"), "w").close()
        self.assertEqual([os.path.basename(f) for f in pg.prev_section_md_files(self.tmp, "2", 1)],
                         ["2.1.md"])
        self.assertEqual([os.path.basename(f) for f in pg.prev_section_md_files(self.tmp, "2", 2)],
                         ["2.2_标题.md"])

    def test_residual_new_key_regex(self):
        self.assertEqual(pg.NEW_KEY_RE.findall("正文 [@new:pending] 和 [@ref001] 与 [@new:foo-bar]。"),
                         ["new:pending", "new:foo-bar"])


if __name__ == "__main__":
    unittest.main()
