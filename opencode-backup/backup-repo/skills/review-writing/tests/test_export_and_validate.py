import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class ExportAndValidateTests(unittest.TestCase):
    def test_export_bibtex_clean_exports_only_used_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "drafts").mkdir()
            (root / "data").mkdir()

            (root / "drafts" / "s1.md").write_text("Alpha [1].", encoding="utf-8")
            (root / "data" / "literature_index.json").write_text(
                json.dumps(
                    [
                        {"global_id": 1, "authors": ["A"], "title": "T1", "journal": "J", "year": 2024},
                        {"global_id": 2, "authors": ["B"], "title": "T2", "journal": "J", "year": 2023},
                    ]
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/export_bibtex.py"
            out = root / "references.bib"
            subprocess.run(
                [
                    "python3",
                    script,
                    "--clean",
                    "--input",
                    str(root / "data" / "literature_index.json"),
                    "--drafts-dir",
                    str(root / "drafts"),
                    "--output",
                    str(out),
                ],
                check=True,
            )

            text = out.read_text(encoding="utf-8")
            self.assertIn("@article{ref_1", text)
            self.assertNotIn("@article{ref_2", text)

    def test_validate_citations_local_fail_on_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "drafts").mkdir()
            (root / "data").mkdir()

            (root / "drafts" / "s1.md").write_text("Alpha [99].", encoding="utf-8")
            (root / "data" / "literature_index.json").write_text(
                json.dumps([{"global_id": 1, "title": "Known"}]),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/validate_citations.py"
            res = subprocess.run(
                [
                    "python3",
                    script,
                    "--drafts-dir",
                    str(root / "drafts"),
                    "--index-path",
                    str(root / "data" / "literature_index.json"),
                    "--fail-on-orphan",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(res.returncode, 2)
            self.assertIn("Orphan citations", res.stdout)

    def test_export_bibtex_clean_supports_range_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "drafts").mkdir()
            (root / "data").mkdir()

            (root / "drafts" / "s1.md").write_text("Alpha [1-2].", encoding="utf-8")
            (root / "data" / "literature_index.json").write_text(
                json.dumps(
                    [
                        {"global_id": 1, "authors": ["A"], "title": "T1", "journal": "J", "year": 2024},
                        {"global_id": 2, "authors": ["B"], "title": "T2", "journal": "J", "year": 2023},
                        {"global_id": 3, "authors": ["C"], "title": "T3", "journal": "J", "year": 2022},
                    ]
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/export_bibtex.py"
            out = root / "references.bib"
            subprocess.run(
                [
                    "python3",
                    script,
                    "--clean",
                    "--input",
                    str(root / "data" / "literature_index.json"),
                    "--drafts-dir",
                    str(root / "drafts"),
                    "--output",
                    str(out),
                ],
                check=True,
            )

            text = out.read_text(encoding="utf-8")
            self.assertIn("@article{ref_1", text)
            self.assertIn("@article{ref_2", text)
            self.assertNotIn("@article{ref_3", text)


if __name__ == "__main__":
    unittest.main()
