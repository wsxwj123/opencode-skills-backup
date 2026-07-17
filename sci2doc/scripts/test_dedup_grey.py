#!/usr/bin/env python3
# test_dedup_grey.py —— 去重灰区交人工三档 + 复查队列落盘幂等（INTERFACE §9 自验收）
#
# 覆盖锁定考卷(stdout 契约)之外的落盘面：
#   - 三档：DOI/PMID 精确→自动合并；标识符冲突→作新条目不标疑似；仅标题命中→标疑似不合并
#   - data/dedup_review_queue.json 结构 {generated_at,count,entries} + (key,suspected_same_as) 幂等
#
# 直接子进程跑脚本，自建最小夹具，不依赖 testkit 的 orch_testlib。

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "citation_renumber.py")


def run(root, ret_path):
    return subprocess.run([sys.executable, SCRIPT, "merge-refs", "--root", root,
                           "--return", ret_path],
                          capture_output=True, text=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="grey_")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def write_index(self, entries):
        with open(os.path.join(self.tmp, "literature_index.json"), "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False)

    def merge(self, new_refs, section_id="2.1"):
        p = os.path.join(self.tmp, ".write_return_%s.json" % section_id)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"section_id": section_id, "new_refs": new_refs}, f, ensure_ascii=False)
        r = run(self.tmp, p)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def queue(self):
        p = os.path.join(self.tmp, "data", "dedup_review_queue.json")
        return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None


class TestThreeTiers(Base):
    def test_tier1_doi_exact_auto_merge(self):
        self.write_index([{"id": "ref001", "doi": "10.1/A", "pmid": None, "title": "X"}])
        j = self.merge([{"key": "new:a", "title": "diff title", "doi": "10.1/A", "pmid": ""}])
        self.assertEqual((j["deduped"], j["merged"]), (1, 0))
        self.assertEqual(j["suspected_duplicates"], [])
        self.assertIsNone(self.queue(), "有把握合并不落队列")

    def test_tier1_pmid_exact_auto_merge(self):
        self.write_index([{"id": "ref001", "doi": None, "pmid": "555", "title": "X"}])
        j = self.merge([{"key": "new:a", "title": "diff", "doi": "", "pmid": "555"}])
        self.assertEqual((j["deduped"], j["merged"]), (1, 0))
        self.assertEqual(j["suspected_duplicates"], [])

    def test_tier2_conflict_new_entry_no_flag(self):
        # 同标题、DOI 明确不同 → 有把握不同篇 → 作新条目、不标疑似（第1轮守卫）
        self.write_index([{"id": "ref001", "doi": "10.1/A", "pmid": None, "title": "Same T"}])
        j = self.merge([{"key": "new:a", "title": "Same T", "doi": "10.9/B", "pmid": ""}])
        self.assertEqual((j["deduped"], j["merged"]), (0, 1))
        self.assertEqual(j["suspected_duplicates"], [])
        self.assertIsNone(self.queue())

    def test_tier3_title_only_flagged_not_merged(self):
        # 库中仅 PMID，新引用仅 DOI，标题相同 → 无共享强标识符 → 灰区标疑似、不合并
        self.write_index([{"id": "refX", "doi": None, "pmid": "999", "title": "Shared T"}])
        j = self.merge([{"key": "new:a", "title": "Shared T", "doi": "10.5/A", "pmid": ""}])
        self.assertEqual((j["deduped"], j["merged"]), (0, 1))
        sd = j["suspected_duplicates"]
        self.assertEqual(len(sd), 1)
        self.assertEqual(sd[0]["key"], "new:a")
        self.assertEqual(sd[0]["suspected_same_as"], "refX")
        self.assertIn("reason", sd[0])
        q = self.queue()
        self.assertEqual(q["count"], 1)
        self.assertIn("generated_at", q)
        self.assertEqual(q["entries"][0]["suspected_same_as"], "refX")


class TestQueueIdempotent(Base):
    def test_same_pair_not_double_stacked(self):
        self.write_index([{"id": "refX", "doi": None, "pmid": "999", "title": "Shared T"}])
        refs = [{"key": "new:a", "title": "Shared T", "doi": "10.5/A", "pmid": ""}]
        self.merge(refs)
        # 重跑：new:a 这次 DOI 10.5/A 已入库→tier1 自动合并，不再新增疑似；队列仍只 1 条
        self.merge(refs)
        q = self.queue()
        self.assertEqual(q["count"], 1, "同 (key,suspected_same_as) 不重复堆积")

    def test_distinct_pairs_accumulate(self):
        self.write_index([{"id": "refX", "doi": None, "pmid": "999", "title": "T1"},
                          {"id": "refY", "doi": None, "pmid": "888", "title": "T2"}])
        self.merge([{"key": "new:a", "title": "T1", "doi": "10.5/A", "pmid": ""}], section_id="2.1")
        self.merge([{"key": "new:b", "title": "T2", "doi": "10.6/B", "pmid": ""}], section_id="2.2")
        q = self.queue()
        self.assertEqual(q["count"], 2)
        keys = {(e["key"], e["suspected_same_as"]) for e in q["entries"]}
        self.assertEqual(keys, {("new:a", "refX"), ("new:b", "refY")})


if __name__ == "__main__":
    unittest.main()
