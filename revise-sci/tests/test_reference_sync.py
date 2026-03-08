import json
import unittest

from helpers import TempProject, run_script


class ReferenceSyncTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.project_root = self.root / "run"
        (self.project_root / "units").mkdir(parents=True)
        (self.project_root / "data").mkdir(parents=True)

    def tearDown(self):
        self.project.cleanup()

    def test_reference_sync_uses_canonical_literature_index(self):
        unit = {
            "comment_id": "R1-Major-01",
            "status": "completed",
            "editorial_intent": "citation",
        }
        (self.project_root / "units" / "001.json").write_text(json.dumps(unit), encoding="utf-8")
        (self.project_root / "paper_search_validated.json").write_text(json.dumps({"results": []}), encoding="utf-8")
        (self.project_root / "data" / "literature_index.json").write_text(
            json.dumps(
                [
                    {
                        "global_id": 1,
                        "comment_ids": ["R1-Major-01"],
                        "reference_entry": "Smith J, Lee K. Quercetin in cardiovascular models. Cardiovasc Res. 2023. DOI: 10.1000/xyz123.",
                    }
                ]
            ),
            encoding="utf-8",
        )
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text("# Introduction\n\nBackground text.\n", encoding="utf-8")

        result = run_script(
            "reference_sync.py",
            ["--project-root", str(self.project_root), "--output-md", str(output_md)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        merged = output_md.read_text(encoding="utf-8")
        self.assertIn("## References", merged)
        self.assertIn("Quercetin in cardiovascular models", merged)
        report = json.loads((self.project_root / "reference_sync_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["covered_comment_ids"], ["R1-Major-01"])

