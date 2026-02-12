import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class FinalConsistencyCheckTests(unittest.TestCase):
    def test_fails_on_missing_section_and_claim_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "drafts").mkdir()
            (root / "data").mkdir()
            (root / "storyline.md").write_text(
                "# Outline\n\n## Introduction\n## Methods\n",
                encoding="utf-8",
            )
            (root / "drafts" / "01_introduction.md").write_text("Text [1].", encoding="utf-8")
            (root / "data" / "literature_index.json").write_text(
                json.dumps([{"global_id": 1, "title": "A"}]),
                encoding="utf-8",
            )
            (root / "data" / "synthesis_matrix.json").write_text(
                json.dumps([{"global_id": 1, "section_id": "Introduction", "claim_id": None}]),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/final_consistency_check.py"
            res = subprocess.run(
                [
                    "python3",
                    script,
                    "--storyline",
                    str(root / "storyline.md"),
                    "--drafts-dir",
                    str(root / "drafts"),
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--index",
                    str(root / "data" / "literature_index.json"),
                    "--fail-on-gap",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 2)

    def test_passes_when_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "drafts").mkdir()
            (root / "data").mkdir()
            (root / "storyline.md").write_text(
                "# Outline\n\n## Introduction\n",
                encoding="utf-8",
            )
            (root / "drafts" / "01_introduction.md").write_text("Text [1].", encoding="utf-8")
            (root / "data" / "literature_index.json").write_text(
                json.dumps([{"global_id": 1, "title": "A"}]),
                encoding="utf-8",
            )
            (root / "data" / "synthesis_matrix.json").write_text(
                json.dumps(
                    [
                        {
                            "global_id": 1,
                            "section_id": "Introduction",
                            "claim_id": "C1",
                            "updated_in_round3": True,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/final_consistency_check.py"
            res = subprocess.run(
                [
                    "python3",
                    script,
                    "--storyline",
                    str(root / "storyline.md"),
                    "--drafts-dir",
                    str(root / "drafts"),
                    "--matrix",
                    str(root / "data" / "synthesis_matrix.json"),
                    "--index",
                    str(root / "data" / "literature_index.json"),
                    "--fail-on-gap",
                    "--min-round3-ratio",
                    "0.5",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
