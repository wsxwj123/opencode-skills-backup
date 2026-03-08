import json
import unittest

from helpers import TempProject, create_docx, run_script


class AtomizeCommentsTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.project_root = self.root / "run"
        self.project_root.mkdir()

    def tearDown(self):
        self.project.cleanup()

    def test_docx_comments_are_split_into_units(self):
        comments = create_docx(
            self.root / "comments.docx",
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the mechanism."),
                ("paragraph", "2. Please expand the limitation discussion."),
                ("paragraph", "Minor"),
                ("paragraph", "1. Correct the typo in Figure 1 legend."),
                ("paragraph", "Reviewer #2"),
                ("paragraph", "Major"),
                ("paragraph", "1. Add a citation for the background statement."),
            ],
        )
        result = run_script(
            "atomize_comments.py",
            ["--comments", str(comments), "--project-root", str(self.project_root)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        units = sorted((self.project_root / "units").glob("*.json"))
        self.assertEqual(len(units), 4)
        first = json.loads(units[0].read_text(encoding="utf-8"))
        self.assertEqual(first["comment_id"], "R1-Major-01")
        self.assertEqual(first["reviewer"], "Reviewer #1")
        self.assertEqual(first["severity"], "major")

    def test_atomic_html_preserves_comment_ids(self):
        html = self.root / "comments.html"
        html.write_text(
            """
            <html><body>
            <div class="comment-unit" data-comment-id="R1-Major-09" data-reviewer="Reviewer #1" data-severity="major">
              <p class="comment-text">Please correct Figure 2 legend.</p>
            </div>
            </body></html>
            """,
            encoding="utf-8",
        )
        result = run_script(
            "atomize_comments.py",
            ["--comments", str(html), "--project-root", str(self.project_root)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        units = sorted((self.project_root / "units").glob("*.json"))
        self.assertEqual(len(units), 1)
        payload = json.loads(units[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["comment_id"], "R1-Major-09")
        self.assertEqual(payload["reviewer_comment_en"], "Please correct Figure 2 legend.")
