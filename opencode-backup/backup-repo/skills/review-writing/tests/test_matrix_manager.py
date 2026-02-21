import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class MatrixManagerTests(unittest.TestCase):
    def test_bootstrap_and_focus_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "data" / "literature_index.json").write_text(
                json.dumps(
                    [
                        {
                            "global_id": 1,
                            "title": "Transformer for imaging",
                            "related_sections": ["methods", "results"],
                            "year": 2023,
                            "journal": "J1",
                        },
                        {
                            "global_id": 2,
                            "title": "Baseline cohort",
                            "related_sections": ["methods"],
                            "year": 2022,
                            "journal": "J2",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/matrix_manager.py"
            subprocess.run(
                [
                    "python3",
                    script,
                    "bootstrap",
                    "--index",
                    str(root / "data" / "literature_index.json"),
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--round",
                    "1",
                ],
                check=True,
            )

            matrix = json.loads((root / "data" / "synthesis_matrix.json").read_text(encoding="utf-8"))
            keys = {(r["global_id"], r["section_id"]) for r in matrix}
            self.assertEqual(keys, {(1, "methods"), (1, "results"), (2, "methods")})

            res = subprocess.run(
                [
                    "python3",
                    script,
                    "focus",
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--section",
                    "methods",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn('"section": "methods"', res.stdout)

    def test_bind_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "data" / "synthesis_matrix.json").write_text(
                json.dumps(
                    [
                        {
                            "global_id": 1,
                            "section_id": "results",
                            "title": "Radiomics predicts response",
                            "abstract": "Radiomics and transformer models improve outcomes.",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (root / "data" / "claims_results.json").write_text(
                json.dumps(
                    [
                        {
                            "claim_id": "C1",
                            "text": "Transformer improves outcome prediction",
                            "keywords": ["transformer", "outcomes"],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/matrix_manager.py"
            subprocess.run(
                [
                    "python3",
                    script,
                    "bind-claims",
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--section",
                    "results",
                    "--claims",
                    str(root / "data" / "claims_results.json"),
                ],
                check=True,
            )

            matrix = json.loads((root / "data" / "synthesis_matrix.json").read_text(encoding="utf-8"))
            self.assertEqual(matrix[0]["claim_id"], "C1")
            self.assertEqual(matrix[0]["evidence_round"], 2)

    def test_bind_claims_requires_min_hits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "data" / "synthesis_matrix.json").write_text(
                json.dumps(
                    [
                        {
                            "global_id": 1,
                            "section_id": "results",
                            "title": "Only one keyword match",
                            "abstract": "contains transformer but not the second marker",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (root / "data" / "claims_results.json").write_text(
                json.dumps(
                    [
                        {
                            "claim_id": "C1",
                            "text": "Transformer improves outcome prediction",
                            "keywords": ["transformer", "outcomes"],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/matrix_manager.py"
            subprocess.run(
                [
                    "python3",
                    script,
                    "bind-claims",
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--section",
                    "results",
                    "--claims",
                    str(root / "data" / "claims_results.json"),
                ],
                check=True,
            )

            matrix = json.loads((root / "data" / "synthesis_matrix.json").read_text(encoding="utf-8"))
            self.assertIsNone(matrix[0].get("claim_id"))

    def test_bind_claims_can_use_semantic_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "data" / "synthesis_matrix.json").write_text(
                json.dumps(
                    [
                        {
                            "global_id": 1,
                            "section_id": "results",
                            "title": "Transformer model improves outcome prediction",
                            "abstract": "Outcome prediction improves with transformer architectures.",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (root / "data" / "claims_results.json").write_text(
                json.dumps(
                    [
                        {
                            "claim_id": "C9",
                            "text": "Transformer architecture improves outcome prediction",
                            "keywords": ["nonexistent", "keywords"],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/matrix_manager.py"
            subprocess.run(
                [
                    "python3",
                    script,
                    "bind-claims",
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--section",
                    "results",
                    "--claims",
                    str(root / "data" / "claims_results.json"),
                    "--min-hits",
                    "3",
                    "--semantic-threshold",
                    "0.2",
                ],
                check=True,
            )

            matrix = json.loads((root / "data" / "synthesis_matrix.json").read_text(encoding="utf-8"))
            self.assertEqual(matrix[0]["claim_id"], "C9")
            self.assertGreaterEqual(matrix[0].get("semantic_score", 0.0), 0.2)

    def test_bind_claims_fail_on_no_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "data" / "synthesis_matrix.json").write_text(
                json.dumps(
                    [
                        {
                            "global_id": 1,
                            "section_id": "results",
                            "title": "No overlap title",
                            "abstract": "irrelevant abstract",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (root / "data" / "claims_results.json").write_text(
                json.dumps(
                    [
                        {
                            "claim_id": "C404",
                            "text": "Unrelated claim",
                            "keywords": ["x", "y"],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/matrix_manager.py"
            res = subprocess.run(
                [
                    "python3",
                    script,
                    "bind-claims",
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--section",
                    "results",
                    "--claims",
                    str(root / "data" / "claims_results.json"),
                    "--min-hits",
                    "2",
                    "--semantic-threshold",
                    "0.95",
                    "--fail-on-no-update",
                ],
                check=False,
            )
            self.assertEqual(res.returncode, 2)

    def test_bootstrap_reads_legacy_matrix_and_writes_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "data" / "literature_index.json").write_text(
                json.dumps([{"global_id": 1, "title": "A", "related_sections": ["intro"]}]),
                encoding="utf-8",
            )
            (root / "data" / "literature_matrix.json").write_text(
                json.dumps([{"global_id": 9, "section_id": "legacy"}]),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/matrix_manager.py"
            subprocess.run(
                [
                    "python3",
                    script,
                    "bootstrap",
                    "--index",
                    str(root / "data" / "literature_index.json"),
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--round",
                    "1",
                ],
                check=True,
            )

            self.assertTrue((root / "data" / "synthesis_matrix.json").exists())
            matrix = json.loads((root / "data" / "synthesis_matrix.json").read_text(encoding="utf-8"))
            keys = {(r.get("global_id"), r.get("section_id")) for r in matrix}
            self.assertIn((9, "legacy"), keys)
            self.assertIn((1, "intro"), keys)


if __name__ == "__main__":
    unittest.main()
