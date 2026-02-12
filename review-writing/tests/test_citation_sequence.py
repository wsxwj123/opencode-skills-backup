import subprocess
import tempfile
import unittest
from pathlib import Path


class CitationSequenceTests(unittest.TestCase):
    def test_detects_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "drafts").mkdir()
            (root / "drafts" / "a.md").write_text("Text [1] [3].", encoding="utf-8")

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/check_global_citation_sequence.py"
            res = subprocess.run(
                ["python3", script, "--drafts-dir", str(root / "drafts")],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 2)
            self.assertIn("missing", res.stdout.lower())


if __name__ == "__main__":
    unittest.main()
