#!/usr/bin/env python3
# 白盒测试：citation_renumber 内部归一化/去重/翻号逻辑的边界（acceptance 已覆盖 CLI 契约，
# 这里补内部函数级边界：DOI https 前缀归一、标题模糊去重、next_ref_id 递增）。
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import citation_renumber as cr

SCRIPT = os.path.join(HERE, "citation_renumber.py")


class TestNormalizers(unittest.TestCase):
    def test_doi_strips_url_prefix_and_case(self):
        self.assertEqual(cr.norm_doi("https://doi.org/10.1/AbC"), "10.1/abc")
        self.assertEqual(cr.norm_doi("HTTPS://dx.doi.org/10.1/x/"), "10.1/x")
        self.assertEqual(cr.norm_doi(None), "")

    def test_doi_strips_bare_doi_prefix(self):  # E2
        canon = cr.norm_doi("10.1/x")
        self.assertEqual(cr.norm_doi("doi:10.1/X"), canon)
        self.assertEqual(cr.norm_doi("DOI: 10.1/x"), canon)
        self.assertEqual(cr.norm_doi("doi:10.1/x/."), canon)  # 前缀+尾部同时去
        self.assertEqual(cr.norm_doi("10.1234/doi.abc"), "10.1234/doi.abc")  # 中段 doi. 不误删

    def test_pmid_keeps_only_digits(self):  # E1
        self.assertEqual(cr.norm_pmid("PMID: 12345678"), "12345678")
        self.assertEqual(cr.norm_pmid("12345678 "), "12345678")
        self.assertEqual(cr.norm_pmid("12345678"), "12345678")
        self.assertEqual(cr.norm_pmid(12345678), "12345678")  # int 入参
        self.assertEqual(cr.norm_pmid("120345"), "120345")    # 中间的 0 不丢
        self.assertEqual(cr.norm_pmid(None), "")
        self.assertEqual(cr.norm_pmid("pmid:  "), "")         # 无数字→空

    def test_title_removes_punct_and_case(self):
        self.assertEqual(cr.norm_title("A Novel, Method!"), cr.norm_title("a novel method"))

    def test_next_ref_id_increments_max(self):
        self.assertEqual(cr.next_ref_id([{"id": "ref001"}, {"id": "ref010"}]), "ref011")
        self.assertEqual(cr.next_ref_id([]), "ref001")

    def test_find_existing_by_title_when_no_ids(self):
        entries = [{"id": "ref001", "title": "Deep Learning Methods", "doi": None, "pmid": None}]
        hit = cr.find_existing({"title": "deep-learning methods!"}, entries)
        self.assertEqual(hit, "ref001")


class TestMergeTitleDedup(unittest.TestCase):
    """CLI 级：标题模糊命中（DOI/PMID 都缺时的第三级去重）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wb_merge_")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        with open(os.path.join(self.tmp, "literature_index.json"), "w") as f:
            json.dump([{"id": "ref001", "title": "Gene X Regulation", "doi": None, "pmid": "5"}], f)

    def test_title_only_new_ref_dedupes(self):
        ret = os.path.join(self.tmp, ".write_return_2.1.json")
        with open(ret, "w") as f:
            json.dump({"section_id": "2.1", "new_refs": [
                {"key": "new:t", "title": "gene x regulation", "doi": "", "pmid": "5"}]}, f)
        r = subprocess.run([sys.executable, SCRIPT, "merge-refs", "--root", self.tmp,
                            "--return", ret], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        j = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(j["deduped"], 1)
        self.assertEqual(j["mapping"]["new:t"], "ref001")


if __name__ == "__main__":
    unittest.main()
