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
        self.assertNotIn('w:type="page"', document_xml)

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

    def test_pipeline_does_not_auto_complete_substantive_comment_without_explicit_support(self):
        project_root, result = self._run_pipeline(
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please explain why this effect occurs in the current model."),
            ],
            [
                ("heading1", "Results"),
                ("paragraph", "Quercetin showed a protective effect in TAC-treated cells."),
            ],
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        state = json.loads((project_root / "project_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["delivery_status"], "author_confirmation_required")
        unit = json.loads(next((project_root / "units").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(unit["status"], "needs_author_confirmation")
        revised_md = (project_root / "revised_manuscript.md").read_text(encoding="utf-8")
        self.assertNotIn("This paragraph has been revised in response to the reviewer comment.", revised_md)

    def test_pipeline_replaces_generic_clarify_boilerplate_with_scoped_revision(self):
        project_root, result = self._run_pipeline(
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the protective effect statement in the Results section."),
            ],
            [
                ("heading1", "Results"),
                ("paragraph", "Quercetin showed a protective effect in TAC-treated cells."),
            ],
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        revised_md = (project_root / "revised_manuscript.md").read_text(encoding="utf-8")
        self.assertIn("In the present dataset, Quercetin showed a protective effect in TAC-treated cells.", revised_md)
        self.assertNotIn("This sentence has been clarified to align the stated conclusion with the reviewed evidence.", revised_md)

    def test_pipeline_inserts_page_breaks_only_between_comments(self):
        project_root, result = self._run_pipeline(
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the protective effect statement in the Results section."),
                ("paragraph", "2. Please expand the limitation discussion."),
            ],
            [
                ("heading1", "Results"),
                ("paragraph", "Quercetin showed a protective effect in TAC-treated cells."),
                ("heading1", "Discussion"),
                ("paragraph", "These findings support the proposed mechanism."),
            ],
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        with zipfile.ZipFile(project_root / "response_to_reviewers.docx") as zf:
            document_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        self.assertEqual(document_xml.count('w:type="page"'), 1)

    def test_pipeline_resume_keeps_existing_units_and_skips_re_atomizing_comments(self):
        comments = create_docx(
            self.root / "comments.docx",
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the protective effect statement in the Results section."),
            ],
        )
        manuscript = create_docx(
            self.root / "manuscript.docx",
            [
                ("heading1", "Results"),
                ("paragraph", "Quercetin showed a protective effect in TAC-treated cells."),
            ],
        )
        project_root = self.root / "resume_run"
        first = run_script(
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
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        unit_path = next((project_root / "units").glob("*.json"))
        unit = json.loads(unit_path.read_text(encoding="utf-8"))
        unit["resume_marker"] = "keep-me"
        unit_path.write_text(json.dumps(unit), encoding="utf-8")

        create_docx(
            comments,
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the protective effect statement in the Results section."),
                ("paragraph", "2. Add a citation for the background statement."),
            ],
        )
        second = run_script(
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
                "--resume",
            ],
            cwd=self.root,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        unit_paths = sorted((project_root / "units").glob("*.json"))
        self.assertEqual(len(unit_paths), 1)
        resumed = json.loads(unit_paths[0].read_text(encoding="utf-8"))
        self.assertEqual(resumed["resume_marker"], "keep-me")

    def test_pipeline_ingests_confirmed_paper_search_results_for_citation_comment(self):
        comments = create_docx(
            self.root / "comments.docx",
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Add a citation for the background statement."),
            ],
        )
        manuscript = create_docx(
            self.root / "manuscript.docx",
            [
                ("heading1", "Introduction"),
                ("paragraph", "Quercetin has been widely studied in cardiovascular models."),
            ],
        )
        project_root = self.root / "paper_search_run"
        (project_root).mkdir()
        (project_root / "paper_search_results.json").write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "comment_id": "R1-Major-01",
                            "confirmed": True,
                            "formatted_citation_text": "(Smith et al., 2023)",
                            "citations": [
                                {
                                    "source": "PMID:123456",
                                    "title": "Quercetin in cardiovascular models",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
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
                "--paper-search-results",
                str(project_root / "paper_search_results.json"),
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        unit = json.loads(next((project_root / "units").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(unit["status"], "completed")
        self.assertIn("(Smith et al., 2023)", unit["revised_excerpt_en"])
        self.assertIn("PMID:123456", json.dumps(unit["evidence_sources"], ensure_ascii=False))
