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

    def test_review_report_html_critique_lists_are_split_into_major_and_minor_units(self):
        html = self.root / "report.html"
        html.write_text(
            """
            <html><body>
            <section class="critique-section">
              <h2>七、必须解决的核心问题</h2>
              <ul class="critique-list">
                <li>
                  <div class="critique-title">【问题1】参考文献系统已经失效</div>
                  <div class="critique-content"><strong>问题描述:</strong> References section is empty.</div>
                  <span class="evidence-anchor"><strong>证据锚点:</strong> References section.</span>
                  <div class="root-cause"><strong>根源质询:</strong> Citation management failed.</div>
                  <div class="response-strategy"><strong>作者应对方案:</strong> Rebuild references.</div>
                </li>
              </ul>
            </section>
            <section class="critique-section">
              <h2>八、其他改进建议</h2>
              <ul class="critique-list">
                <li>
                  <div class="critique-title">【建议1】统一 EV 与 exosome 的术语边界</div>
                  <div class="critique-content"><strong>问题描述:</strong> Terms are mixed.</div>
                </li>
              </ul>
            </section>
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
        self.assertEqual(len(units), 2)
        first = json.loads(units[0].read_text(encoding="utf-8"))
        second = json.loads(units[1].read_text(encoding="utf-8"))
        self.assertEqual(first["severity"], "major")
        self.assertEqual(second["severity"], "minor")
        self.assertIn("参考文献系统已经失效", first["reviewer_comment_en"])
        self.assertIn("统一 EV 与 exosome 的术语边界", second["reviewer_comment_en"])
        self.assertEqual(first["reviewer_comment_lang"], "zh")
        self.assertIn("References section is empty", first["problem_description"])
        self.assertIn("References section", first["evidence_anchor"])
        self.assertIn("Citation management failed", first["root_cause"])
        self.assertIn("Rebuild references", first["author_strategy"])

    def test_docx_multiline_comment_is_kept_in_one_unit(self):
        comments = create_docx(
            self.root / "comments.docx",
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the mechanism statement."),
                ("paragraph", "Please also explain whether the claim is limited to the current dataset."),
                ("paragraph", "2. Please expand the limitation discussion."),
            ],
        )
        result = run_script(
            "atomize_comments.py",
            ["--comments", str(comments), "--project-root", str(self.project_root)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        units = sorted((self.project_root / "units").glob("*.json"))
        self.assertEqual(len(units), 2)
        first = json.loads(units[0].read_text(encoding="utf-8"))
        self.assertIn("Please clarify the mechanism statement.", first["reviewer_comment_en"])
        self.assertIn("limited to the current dataset", first["reviewer_comment_en"])

    def test_docx_comment_prefix_format_is_supported(self):
        comments = create_docx(
            self.root / "comments.docx",
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "Comment 1: Please clarify the mechanism statement."),
                ("paragraph", "Additional context for the first comment."),
                ("paragraph", "Comment 2: Add a citation for the background statement."),
            ],
        )
        result = run_script(
            "atomize_comments.py",
            ["--comments", str(comments), "--project-root", str(self.project_root)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        units = sorted((self.project_root / "units").glob("*.json"))
        self.assertEqual(len(units), 2)
        first = json.loads(units[0].read_text(encoding="utf-8"))
        second = json.loads(units[1].read_text(encoding="utf-8"))
        self.assertIn("Additional context for the first comment.", first["reviewer_comment_en"])
        self.assertIn("Add a citation", second["reviewer_comment_en"])
