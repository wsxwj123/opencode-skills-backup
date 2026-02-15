import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class PreflightReviewProjectTests(unittest.TestCase):
    def _make_min_project(self, root):
        for d in ("drafts", "data", "logs", "figures"):
            (root / d).mkdir()
        (root / "storyline.md").write_text("# Outline\n\n## Intro\n", encoding="utf-8")
        (root / "data" / "literature_index.json").write_text("[]", encoding="utf-8")
        (root / "data" / "synthesis_matrix.json").write_text("[]", encoding="utf-8")

    def test_preflight_passes_for_minimal_valid_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_min_project(root)
            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/preflight_review_project.py"
            res = subprocess.run(
                ["python3", script, "--project-root", str(root), "--fail-on-error"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0)
            payload = json.loads(res.stdout)
            self.assertEqual(payload["summary"]["error_count"], 0)

    def test_preflight_fails_on_split_brain_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_min_project(root)
            (root / "data" / "literature_matrix.json").write_text('[{"global_id":1}]', encoding="utf-8")
            (root / "data" / "synthesis_matrix.json").write_text('[{"global_id":2}]', encoding="utf-8")

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/preflight_review_project.py"
            res = subprocess.run(
                ["python3", script, "--project-root", str(root), "--fail-on-error"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 2)
            self.assertIn("matrix_split_brain", res.stdout)


if __name__ == "__main__":
    unittest.main()
