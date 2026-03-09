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

    def test_reviewer_response_sci_html_is_ingested_as_seeded_units(self):
        html = self.root / "reviewer_response.html"
        html.write_text(
            """
            <html><body>
            <section id="page-u-001" class="page">
              <h2>Reviewer #1 | MAJOR | Comment 1</h2>
              <div class="card">
                <h3>1) 审稿人意图理解 / Reviewer Intent</h3>
                <div class="stack-box"><h4>原始审稿意见（English）</h4><p>Please clarify the mechanism statement.</p></div>
                <div class="stack-box"><h4>应如何理解（中文）</h4><p>审稿人要求澄清机制表述。</p></div>
              </div>
              <div class="card">
                <h3>2) Response to Reviewer（中英对照）</h3>
                <div class="stack-box"><h4>English Response</h4><p>We clarified the mechanism statement in the revised manuscript.</p></div>
                <div class="stack-box"><h4>中文对照</h4><p>我们已在修订稿中澄清相关机制表述。</p></div>
              </div>
              <div class="card">
                <h3>3) 可能需要修改的正文/附件内容（中英对照）</h3>
                <div class="stack-box"><h4>定位信息（原文位置）</h4><p>Section: 2.1 Introduction | Paragraph index: 5</p></div>
                <div class="stack-box"><h4>Original Text (English, 对照)</h4><p>The mechanism remains unclear in the current text.</p></div>
                <div class="stack-box"><h4>Revised Text (English)</h4><p>In the present dataset, the mechanism statement is limited to the current observation.</p></div>
                <div class="stack-box"><h4>修改后中文对照</h4><p>我们已将机制表述限定在当前观察范围内。</p></div>
              </div>
              <div class="card">
                <h3>5) Evidence Attachments</h3>
                <p><strong>Anchors:</strong> Section 2.1</p>
              </div>
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
        self.assertEqual(len(units), 1)
        payload = json.loads(units[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["comment_input_mode"], "reviewer-response-sci-html")
        self.assertEqual(payload["response_seed_en"], "We clarified the mechanism statement in the revised manuscript.")
        self.assertEqual(payload["response_seed_zh"], "我们已在修订稿中澄清相关机制表述。")
        self.assertEqual(payload["original_excerpt_seed_en"], "The mechanism remains unclear in the current text.")
        self.assertEqual(payload["revised_excerpt_seed_en"], "In the present dataset, the mechanism statement is limited to the current observation.")
        self.assertEqual(payload["revision_location_seed"], "Section: 2.1 Introduction | Paragraph index: 5")
