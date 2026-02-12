import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = "/Users/wsxwj/.codex/skills/article-writing/scripts/state_manager.py"


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
        (self.root / "manuscripts" / "04_Results_3.1_Test.md").write_text("Cite [1].\n", encoding="utf-8")

        for _ in range(4):
            p = run_cmd([
                "sync-literature", "--apply", "--strict-references", "--backup-keep", "2"
            ], cwd=self.root)
            self.assertEqual(p.returncode, 0)

        bdir = self.root / "backups" / "literature_sync"
        dirs = [x for x in bdir.glob("lit_sync_*") if x.is_dir()]
        self.assertLessEqual(len(dirs), 2)


if __name__ == "__main__":
    unittest.main()
