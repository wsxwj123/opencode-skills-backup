import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = str(SKILL_ROOT / "scripts" / "state_manager.py")
MERGE_SCRIPT = str(SKILL_ROOT / "scripts" / "merge_manuscript.py")
EXPORT_BIB_SCRIPT = str(SKILL_ROOT / "scripts" / "export_bibtex.py")


def run_cmd(args, cwd):
    p = subprocess.run(
        ["python3", SCRIPT] + args,
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    return p


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class StateManagerTests(unittest.TestCase):
    def write_matrix(self, refs):
        write_json(self.root / "literature_matrix.json", {"sections": {"results_3.1": refs}})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manuscripts").mkdir(parents=True, exist_ok=True)
        (self.root / "section_memory").mkdir(parents=True, exist_ok=True)

        write_json(self.root / "project_config.json", {"project_name": "t", "target_journal": "nature"})
        write_json(self.root / "storyline.json", {"sections": [{"id": "results_3.1", "title": "x"}]})
        write_json(self.root / "writing_progress.json", {"status": "draft"})
        (self.root / "context_memory.md").write_text("init\n", encoding="utf-8")
        write_json(self.root / "literature_index.json", [])
        write_json(self.root / "figures_database.json", [])
        write_json(self.root / "reviewer_concerns.json", {})
        write_json(self.root / "version_history.json", [])
        write_json(self.root / "si_database.json", [])
        self.write_matrix([])
        (self.root / "section_memory" / "results_3.1.md").write_text("mem\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_gate_requires_write_cycle_origin(self):
        p1 = run_cmd(["preflight", "--section", "results_3.1"], cwd=self.root)
        self.assertEqual(p1.returncode, 0)
        p2 = run_cmd([
            "load", "--section", "results_3.1", "--with-global-history", "--compact",
            "--token-budget", "6000", "--tail-lines", "80"
        ], cwd=self.root)
        self.assertEqual(p2.returncode, 0)
        p3 = run_cmd(["gate-check", "--section", "results_3.1", "--phase", "prewrite"], cwd=self.root)
        self.assertNotEqual(p3.returncode, 0)
        self.assertIn("requires write-cycle origin", p3.stdout)

        p4 = run_cmd(["write-cycle", "--section", "results_3.1"], cwd=self.root)
        self.assertEqual(p4.returncode, 0)

    def test_strict_rebuild_renumbers_ranges_and_tables(self):
        write_json(self.root / "literature_index.json", [
            {"title": "A", "doi": "10.1/x"},
            {"title": "B", "doi": "10.1/y"},
            {"title": "A duplicate", "doi": "10.1/x"},
            {"title": "C", "doi": "10.1/z"},
        ])
        self.write_matrix([1, 2, 3, 4])
        (self.root / "manuscripts" / "04_Results_3.1_Test.md").write_text(
            "# Results\n"
            "Main text [1-4].\n\n"
            "| Item | Ref |\n"
            "|---|---|\n"
            "| A | [3] |\n"
            "| C | [4] |\n\n"
            "# References\n"
            "1. Old A.\n"
            "2. Old B.\n"
            "3. Old Dup A.\n"
            "4. Old C.\n",
            encoding="utf-8",
        )

        p = run_cmd([
            "sync-literature", "--apply", "--strict-references", "--reference-style", "vancouver"
        ], cwd=self.root)
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertTrue(out.get("applied"))

        md = (self.root / "manuscripts" / "04_Results_3.1_Test.md").read_text(encoding="utf-8")
        self.assertIn("Main text [1-3].", md)
        self.assertIn("| A | [1] |", md)
        self.assertIn("| C | [3] |", md)
        self.assertIn("# References", md)
        self.assertIn("1. A.", md)
        self.assertIn("2. B.", md)
        self.assertIn("3. C.", md)

    def test_rollback_on_validation_failure(self):
        write_json(self.root / "literature_index.json", [
            {"title": "A", "doi": "10.1/x"},
            {"title": "B", "doi": "10.1/y"},
        ])
        self.write_matrix([1, 2])
        bad_md = self.root / "manuscripts" / "04_Results_3.1_Bad.md"
        bad_md.write_text("Text with broken cite [9].\n", encoding="utf-8")
        before_index = (self.root / "literature_index.json").read_text(encoding="utf-8")

        p = run_cmd(["sync-literature", "--apply", "--strict-references"], cwd=self.root)
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertIn("error", out)
        self.assertTrue(out.get("rolled_back"))

        after_index = (self.root / "literature_index.json").read_text(encoding="utf-8")
        self.assertEqual(before_index, after_index)
        self.assertIn("[9]", bad_md.read_text(encoding="utf-8"))

    def test_backup_retention_keep_latest_n(self):
        write_json(self.root / "literature_index.json", [
            {"title": "A", "doi": "10.1/x"},
            {"title": "A dup", "doi": "10.1/x"},
        ])
        self.write_matrix([1, 2])
        (self.root / "manuscripts" / "04_Results_3.1_Test.md").write_text("Cite [1].\n", encoding="utf-8")

        for _ in range(4):
            p = run_cmd([
                "sync-literature", "--apply", "--strict-references", "--backup-keep", "2"
            ], cwd=self.root)
            self.assertEqual(p.returncode, 0)

        bdir = self.root / "backups" / "literature_sync"
        dirs = [x for x in bdir.glob("lit_sync_*") if x.is_dir()]
        self.assertLessEqual(len(dirs), 2)

    def test_nature_reference_style_rebuild(self):
        write_json(self.root / "literature_index.json", [
            {
                "authors": "Zhang Y, Li X",
                "title": "Nanoparticle delivery",
                "journal": "Nat Nanotechnol",
                "year": "2024",
                "volume": "19",
                "pages": "100-110",
                "doi": "10.1/abc"
            }
        ])
        self.write_matrix([1])
        mdp = self.root / "manuscripts" / "04_Results_3.1_Style.md"
        mdp.write_text("# References\n1. Old.\n", encoding="utf-8")

        p = run_cmd([
            "sync-literature", "--apply", "--strict-references", "--reference-style", "nature"
        ], cwd=self.root)
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertTrue(out.get("applied"))

        md = mdp.read_text(encoding="utf-8")
        self.assertIn("Nat Nanotechnol 19, 100-110 (2024)", md)

    def test_conflicts_block_apply_unless_allowed(self):
        write_json(self.root / "literature_index.json", [
            {"title": "Targeted nanoparticle delivery for liver cancer"},
            {"title": "Targeted nanoparticle delivery for liver cancers"},
        ])
        self.write_matrix([1, 2])

        blocked = run_cmd([
            "sync-literature", "--apply",
            "--similarity-threshold", "0.999",
            "--conflict-threshold", "0.5"
        ], cwd=self.root)
        self.assertEqual(blocked.returncode, 0)
        b = json.loads(blocked.stdout)
        self.assertIn("error", b)
        self.assertIn("Dedup conflicts detected", b["error"])

        allowed = run_cmd([
            "sync-literature", "--apply",
            "--similarity-threshold", "0.999",
            "--conflict-threshold", "0.5",
            "--allow-conflicts"
        ], cwd=self.root)
        self.assertEqual(allowed.returncode, 0)
        a = json.loads(allowed.stdout)
        self.assertTrue(a.get("applied"))

    def test_load_cache_invalidation_after_source_change(self):
        write_json(self.root / "storyline.json", {"sections": [{"id": "results_3.1", "title": "old"}]})

        p1 = run_cmd([
            "write-cycle", "--section", "results_3.1"
        ], cwd=self.root)
        self.assertEqual(p1.returncode, 0)

        out1 = run_cmd([
            "load", "--section", "results_3.1", "--with-global-history", "--compact"
        ], cwd=self.root)
        data1 = json.loads(out1.stdout)
        self.assertIn("old", json.dumps(data1.get("storyline_section", {}), ensure_ascii=False))

        write_json(self.root / "storyline.json", {"sections": [{"id": "results_3.1", "title": "new"}]})
        out2 = run_cmd([
            "load", "--section", "results_3.1", "--with-global-history", "--compact"
        ], cwd=self.root)
        data2 = json.loads(out2.stdout)
        self.assertIn("new", json.dumps(data2.get("storyline_section", {}), ensure_ascii=False))

    def test_write_cycle_default_is_strict(self):
        os.remove(self.root / "reviewer_concerns.json")
        strict_default = run_cmd([
            "write-cycle", "--section", "results_3.1"
        ], cwd=self.root)
        self.assertNotEqual(strict_default.returncode, 0)

        lenient = run_cmd([
            "write-cycle", "--section", "results_3.1", "--preflight-lenient"
        ], cwd=self.root)
        self.assertEqual(lenient.returncode, 0)

    def test_set_field_persists_active_configuration(self):
        p = run_cmd(["set-field", "--field", "computer_science"], cwd=self.root)
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("field_id"), "computer_science")

        project_config = json.loads((self.root / "project_config.json").read_text(encoding="utf-8"))
        self.assertEqual(project_config.get("field_config"), "computer_science")

        active_field = json.loads((self.root / "active_field_config.json").read_text(encoding="utf-8"))
        self.assertEqual(active_field.get("field_id"), "computer_science")

        reviewer_concerns = json.loads((self.root / "reviewer_concerns.json").read_text(encoding="utf-8"))
        self.assertIsInstance(reviewer_concerns, dict)

    def test_word_count_excludes_references_by_default(self):
        md = self.root / "manuscripts" / "04_Results_3.1_Word.md"
        md.write_text(
            "# Results\nalpha beta gamma\n\n# References\n1. should not count\n",
            encoding="utf-8",
        )
        p = run_cmd(["word-count"], cwd=self.root)
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertTrue(out.get("exclude_references"))
        self.assertEqual(out.get("total"), 5)

    def test_stats_and_snapshot_rollback(self):
        before = (self.root / "context_memory.md").read_text(encoding="utf-8")
        snap = run_cmd(["snapshot"], cwd=self.root)
        self.assertEqual(snap.returncode, 0)
        (self.root / "context_memory.md").write_text("changed\n", encoding="utf-8")

        rb = run_cmd(["rollback", "--target", "snapshot"], cwd=self.root)
        self.assertEqual(rb.returncode, 0)
        rb_out = json.loads(rb.stdout)
        self.assertTrue(rb_out.get("restored"))
        self.assertEqual((self.root / "context_memory.md").read_text(encoding="utf-8"), before)

        st = run_cmd(["stats"], cwd=self.root)
        self.assertEqual(st.returncode, 0)
        st_out = json.loads(st.stdout)
        self.assertIn("word_count", st_out)
        self.assertIn("backups", st_out)
        self.assertGreaterEqual(st_out["backups"].get("snapshot_count", 0), 1)

    def test_merge_and_export_scripts_cli(self):
        a = self.root / "manuscripts" / "04_Results_3.1_A.md"
        b = self.root / "manuscripts" / "05_Discussion_5.1_B.md"
        a.write_text("# A\nText [1].\n", encoding="utf-8")
        b.write_text("# B\nText [2].\n", encoding="utf-8")

        p_merge = subprocess.run(
            [
                "python3", MERGE_SCRIPT,
                "--manuscript-dir", "manuscripts",
                "--skip-docx",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
        )
        self.assertEqual(p_merge.returncode, 0, msg=p_merge.stdout + p_merge.stderr)
        merge_out = json.loads(p_merge.stdout)
        self.assertTrue(merge_out.get("ok"))
        self.assertEqual(merge_out.get("files_merged_count"), 2)

        write_json(self.root / "literature_index.json", {"references": [
            {"ref_id": "r1", "title": "T1", "journal": "J", "year": "2024"},
            {"ref_id": "r2", "title": "T2", "journal": "J", "year": "2025"},
        ]})
        p_bib = subprocess.run(
            [
                "python3", EXPORT_BIB_SCRIPT,
                "--index-file", "literature_index.json",
                "--output-file", "references.bib",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
        )
        self.assertEqual(p_bib.returncode, 0, msg=p_bib.stdout + p_bib.stderr)
        bib_out = json.loads(p_bib.stdout)
        self.assertTrue(bib_out.get("ok"))
        self.assertEqual(bib_out.get("references_exported_count"), 2)
        self.assertTrue((self.root / "references.bib").exists())

    def test_merge_precheck_blocks_out_of_range_citations(self):
        write_json(self.root / "literature_index.json", [
            {"ref_id": "r1", "title": "T1", "journal": "J", "year": "2024"},
        ])
        bad = self.root / "manuscripts" / "04_Results_3.1_BadMerge.md"
        bad.write_text("# A\nText [2].\n", encoding="utf-8")

        p_merge = subprocess.run(
            [
                "python3", MERGE_SCRIPT,
                "--manuscript-dir", "manuscripts",
                "--skip-docx",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(p_merge.returncode, 0, msg=p_merge.stdout + p_merge.stderr)
        out = json.loads(p_merge.stdout)
        self.assertEqual(out.get("error"), "merge_precheck_failed")
        self.assertIn("out of range", json.dumps(out.get("precheck", {}), ensure_ascii=False))

    def test_matrix_reindex_gate_blocks_apply_when_missing(self):
        write_json(self.root / "literature_index.json", [
            {"title": "A", "doi": "10.1/x"},
            {"title": "B", "doi": "10.1/y"},
        ])
        os.remove(self.root / "literature_matrix.json")
        p = run_cmd(["sync-literature", "--apply", "--strict-references"], cwd=self.root)
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertIn("error", out)
        self.assertEqual(out.get("error"), "schema_validation_failed")
        self.assertIn("matrix", json.dumps(out.get("schema", {}), ensure_ascii=False).lower())

    def test_matrix_reindex_gate_blocks_unknown_section_ids(self):
        write_json(self.root / "storyline.json", {"sections": [{"id": "results_3.1", "title": "x"}]})
        write_json(self.root / "literature_index.json", [
            {"title": "A", "doi": "10.1/x"},
        ])
        write_json(self.root / "literature_matrix.json", {"sections": {"results": [1]}})
        p = run_cmd(["sync-literature", "--apply", "--strict-references"], cwd=self.root)
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertIn("error", out)
        self.assertEqual(out.get("error"), "schema_validation_failed")
        self.assertIn("unknown section ids", json.dumps(out.get("schema", {}), ensure_ascii=False).lower())


if __name__ == "__main__":
    unittest.main()
