import json
import unittest
import zipfile

from helpers import TempProject, create_docx, run_script


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.attachments = self.root / "attachments"
        self.attachments.mkdir()
        (self.attachments / "table_s1.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    def tearDown(self):
        self.project.cleanup()

    def _run_pipeline(self, comments_rows, manuscript_rows):
        comments = create_docx(self.root / "comments.docx", comments_rows)
        manuscript = create_docx(self.root / "manuscript.docx", manuscript_rows)
        project_root = self.root / "run"
        result = run_script(
            "run_pipeline.py",
            [
                "--comments",
                str(comments),
                "--manuscript",
                str(manuscript),
                "--attachments-dir",
                str(self.attachments),
                "--project-root",
                str(project_root),
                "--output-md",
                str(project_root / "revised_manuscript.md"),
                "--output-docx",
                str(project_root / "revised_manuscript.docx"),
            ],
            cwd=self.root,
        )
        return project_root, result

    def test_pipeline_generates_submit_ready_outputs(self):
        project_root, result = self._run_pipeline(
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the protective effect statement in the Results section."),
            ],
            [
                ("heading1", "Results"),
                ("paragraph", "Quercetin showed a protective effect in TAC-treated cells."),
                ("heading1", "Discussion"),
                ("paragraph", "These findings support the proposed mechanism."),
            ],
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        response_md = (project_root / "response_to_reviewers.md").read_text(encoding="utf-8")
        self.assertIn("# 回复审稿人的邮件", response_md)
        self.assertIn("### Comment 1", response_md)
        self.assertIn("#### 2) Response to Reviewer（中英对照）", response_md)
        self.assertIn("#### 5) Evidence Attachments", response_md)
        self.assertTrue((project_root / "response_to_reviewers.docx").exists())
        self.assertTrue((project_root / "revised_manuscript.md").exists())
        self.assertTrue((project_root / "revised_manuscript.docx").exists())
        report = (project_root / "final_consistency_report.md").read_text(encoding="utf-8")
        self.assertIn("ready_to_submit", report)
        with zipfile.ZipFile(project_root / "response_to_reviewers.docx") as zf:
            document_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        self.assertIn('w:type="page"', document_xml)

    def test_pipeline_marks_author_confirmation_when_evidence_is_missing(self):
        project_root, result = self._run_pipeline(
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please add additional experiments and references to support the mechanism."),
            ],
            [
                ("heading1", "Results"),
                ("paragraph", "Quercetin showed a protective effect in TAC-treated cells."),
            ],
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        report = (project_root / "final_consistency_report.md").read_text(encoding="utf-8")
        self.assertIn("author_confirmation_required", report)
        self.assertIn("needs_author_confirmation", report)
        state = json.loads((project_root / "project_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["delivery_status"], "author_confirmation_required")
