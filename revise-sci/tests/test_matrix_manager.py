import json
import unittest

from helpers import TempProject, run_script


class MatrixManagerTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.index_path = self.root / "literature_index.json"
        self.matrix_path = self.root / "synthesis_matrix.json"
        self.report_path = self.root / "synthesis_matrix_audit.json"

    def tearDown(self):
        self.project.cleanup()

    def test_bootstrap_and_audit_generate_review_writing_style_matrix(self):
        self.index_path.write_text(
            json.dumps(
                [
                    {
                        "global_id": 1,
                        "related_sections": ["manuscript-001", "manuscript-002"],
                        "claim_ids": ["R1-Major-01"],
                        "source_tier": "revision-citation",
                        "study_type": "review",
                        "year": 2023,
                        "journal": "Cardiovasc Res",
                        "title": "Quercetin in cardiovascular models",
                        "abstract": "Background summary.",
                        "key_finding": "Supports the background claim.",
                        "limitation": "Model-specific evidence.",
                        "comment_ids": ["R1-Major-01"],
                        "reference_entry": "Smith J. Quercetin in cardiovascular models. Cardiovasc Res. 2023.",
                    }
                ]
            ),
            encoding="utf-8",
        )

        bootstrap = run_script(
            "matrix_manager.py",
            [
                "bootstrap",
                "--index",
                str(self.index_path),
                "--matrix",
                str(self.matrix_path),
                "--round",
                "2",
            ],
            cwd=self.root,
        )
        self.assertEqual(bootstrap.returncode, 0, msg=bootstrap.stdout + bootstrap.stderr)

        matrix = json.loads(self.matrix_path.read_text(encoding="utf-8"))
        self.assertEqual(len(matrix), 2)
        self.assertEqual({row["section_id"] for row in matrix}, {"manuscript-001", "manuscript-002"})
        self.assertTrue(all(row["claim_id"] == "R1-Major-01" for row in matrix))

        audit = run_script(
            "matrix_manager.py",
            [
                "audit",
                "--matrix",
                str(self.matrix_path),
                "--report",
                str(self.report_path),
                "--fail-on-gap",
            ],
            cwd=self.root,
        )
        self.assertEqual(audit.returncode, 0, msg=audit.stdout + audit.stderr)
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["missing_claim"], 0)
        self.assertEqual(report["missing_key_fields"], 0)
        self.assertEqual(report["round_distribution"]["2"], 2)

