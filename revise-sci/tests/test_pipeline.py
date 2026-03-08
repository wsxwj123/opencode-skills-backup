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
        self.assertTrue((project_root / "data" / "reference_registry.json").exists())
        self.assertTrue((project_root / "data" / "reference_coverage_audit.json").exists())
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
        unit = json.loads(next((project_root / "units").glob("*.json")).read_text(encoding="utf-8"))
        self.assertNotRegex(unit["response_en"], r"[\u4e00-\u9fff]")

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

    def test_pipeline_resume_keeps_existing_units_when_inputs_are_unchanged(self):
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

    def test_pipeline_resume_fails_when_comments_file_changes(self):
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
        project_root = self.root / "resume_changed_run"
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
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("resume inputs changed", second.stdout + second.stderr)

    def test_pipeline_resume_fails_when_skill_signature_changes(self):
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
        project_root = self.root / "resume_version_changed_run"
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
        state_path = project_root / "project_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["skill_signature"] = "old-signature"
        state_path.write_text(json.dumps(state), encoding="utf-8")
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
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("resume skill version changed", second.stdout + second.stderr)

    def test_pipeline_force_rebuild_recreates_outputs_when_inputs_change(self):
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
        project_root = self.root / "force_rebuild_run"
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
                "--force-rebuild",
            ],
            cwd=self.root,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        self.assertEqual(len(list((project_root / "units").glob("*.json"))), 2)

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
                            "target_section_heading": "Introduction",
                            "target_paragraph_index": 1,
                            "citations": [
                                {
                                    "source": "PMID:123456",
                                    "source_provider": "paper-search",
                                    "source_id": "PMID:123456",
                                    "pmid": "123456",
                                    "title": "Quercetin in cardiovascular models",
                                    "pubmed_title": "Quercetin in cardiovascular models",
                                    "authors": ["Smith J", "Lee K"],
                                    "journal": "Cardiovasc Res",
                                    "year": 2023,
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
        literature_index = json.loads((project_root / "data" / "literature_index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(literature_index), 1)
        self.assertEqual(literature_index[0]["comment_ids"], ["R1-Major-01"])
        self.assertEqual(literature_index[0]["claim_ids"], ["R1-Major-01"])
        synthesis_matrix = json.loads((project_root / "data" / "synthesis_matrix.json").read_text(encoding="utf-8"))
        self.assertEqual(len(synthesis_matrix), 1)
        self.assertEqual(synthesis_matrix[0]["claim_id"], "R1-Major-01")
        self.assertEqual(synthesis_matrix[0]["global_id"], 1)
        synthesis_audit = json.loads((project_root / "data" / "synthesis_matrix_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(synthesis_audit["missing_claim"], 0)
        revised_md = (project_root / "revised_manuscript.md").read_text(encoding="utf-8")
        self.assertIn("## References", revised_md)
        self.assertIn("Quercetin in cardiovascular models", revised_md)

    def test_pipeline_live_citation_verify_sets_guard_report_to_online_mode(self):
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
        project_root = self.root / "paper_search_live_verify_run"
        project_root.mkdir()
        (project_root / "paper_search_results.json").write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "comment_id": "R1-Major-01",
                            "confirmed": True,
                            "formatted_citation_text": "(Smith et al., 2023)",
                            "target_section_heading": "Introduction",
                            "target_paragraph_index": 1,
                            "citations": [
                                {
                                    "source": "PMID:123456",
                                    "source_provider": "paper-search",
                                    "source_id": "PMID:123456",
                                    "pmid": "123456",
                                    "title": "Quercetin in cardiovascular models",
                                    "pubmed_title": "Quercetin in cardiovascular models",
                                    "authors": ["Smith J", "Lee K"],
                                    "journal": "Cardiovasc Res",
                                    "year": 2023,
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
                "--live-citation-verify",
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        guard = json.loads((project_root / "paper_search_guard_report.json").read_text(encoding="utf-8"))
        self.assertTrue(guard["summary"]["online_check"])

    def test_pipeline_requires_anchor_for_auto_completed_citation_comment(self):
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
        project_root = self.root / "paper_search_no_anchor_run"
        project_root.mkdir()
        (project_root / "paper_search_results.json").write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "comment_id": "R1-Major-01",
                            "confirmed": True,
                            "formatted_citation_text": "(Smith et al., 2023)",
                            "citations": [{"source": "PMID:123456"}],
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
        self.assertEqual(unit["status"], "needs_author_confirmation")

    def test_pipeline_requires_double_verified_paper_search_results_for_citation_completion(self):
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
        project_root = self.root / "paper_search_not_double_verified_run"
        project_root.mkdir()
        (project_root / "paper_search_results.json").write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "comment_id": "R1-Major-01",
                            "confirmed": True,
                            "formatted_citation_text": "(Smith et al., 2023)",
                            "target_section_heading": "Introduction",
                            "target_paragraph_index": 1,
                            "citations": [
                                {
                                    "source_provider": "paper-search",
                                    "source_id": "PMID:123456",
                                    "pmid": "123456",
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
        self.assertEqual(unit["status"], "needs_author_confirmation")
        self.assertIn("双重验证", unit["author_confirmation_reason"])

    def test_pipeline_uses_structured_evidence_anchor_for_location(self):
        comments_html = self.root / "report.html"
        comments_html.write_text(
            """
            <html><body>
            <section class="critique-section">
              <h2>七、必须解决的核心问题</h2>
              <ul class="critique-list">
                <li>
                  <div class="critique-title">【问题1】重建 1.1 小节逻辑</div>
                  <div class="critique-content"><strong>问题描述:</strong> The 1.1 section needs restructuring.</div>
                  <span class="evidence-anchor"><strong>证据锚点:</strong> 1.1 节。</span>
                  <div class="response-strategy"><strong>作者应对方案:</strong> Rewrite section 1.1.</div>
                </li>
              </ul>
            </section>
            </body></html>
            """,
            encoding="utf-8",
        )
        manuscript = create_docx(
            self.root / "anchored_manuscript.docx",
            [
                ("paragraph", "Introduction"),
                ("paragraph", "Front paragraph."),
                ("paragraph", "1. Current Status of Pulmonary Disease Research"),
                ("paragraph", "Section 1 paragraph."),
                ("paragraph", "1.1 Pathophysiological Features and the Targeting Gap"),
                ("paragraph", "Section 1.1 paragraph."),
                ("paragraph", "2. Engineering Strategies"),
                ("paragraph", "Section 2 paragraph."),
            ],
        )
        project_root = self.root / "anchor_run"
        result = run_script(
            "run_pipeline.py",
            [
                "--comments",
                str(comments_html),
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
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        unit = json.loads(next((project_root / "units").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(unit["atomic_location"]["section_heading"], "1.1 Pathophysiological Features and the Targeting Gap")

    def test_pipeline_fails_when_numeric_citations_have_no_matching_reference_entries(self):
        comments = create_docx(
            self.root / "comments.docx",
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the protective effect statement in the Results section."),
            ],
        )
        manuscript = create_docx(
            self.root / "manuscript_missing_refs.docx",
            [
                ("heading1", "Introduction"),
                ("paragraph", "Background statement [1,2]."),
                ("heading1", "Results"),
                ("paragraph", "Quercetin showed a protective effect in TAC-treated cells."),
                ("paragraph", "References"),
            ],
        )
        project_root = self.root / "missing_refs_run"
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
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference coverage", result.stdout + result.stderr)

    def test_pipeline_imports_external_reference_source_when_docx_references_are_missing(self):
        comments = create_docx(
            self.root / "comments.docx",
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the protective effect statement in the Results section."),
            ],
        )
        manuscript = create_docx(
            self.root / "manuscript_seeded_refs.docx",
            [
                ("heading1", "Introduction"),
                ("paragraph", "Background statement [1,2]."),
                ("heading1", "Results"),
                ("paragraph", "Quercetin showed a protective effect in TAC-treated cells."),
                ("paragraph", "References"),
            ],
        )
        project_root = self.root / "seeded_refs_run"
        project_root.mkdir()
        seed = project_root / "reference_seed.json"
        seed.write_text(
            json.dumps(
                {
                    "entries": [
                        {"id": "ext-001", "title": "Study A", "doi": "10.1000/a"},
                        {"id": "ext-002", "title": "Study B", "pmid": "123456"},
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
                "--references-source",
                str(seed),
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        audit = json.loads((project_root / "data" / "reference_coverage_audit.json").read_text(encoding="utf-8"))
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["reference_source"], str(seed.resolve()))

    def test_pipeline_autodiscovers_same_title_sibling_docx_when_references_are_missing(self):
        comments = create_docx(
            self.root / "comments.docx",
            [
                ("paragraph", "Reviewer #1"),
                ("paragraph", "Major"),
                ("paragraph", "1. Please clarify the protective effect statement in the Results section."),
            ],
        )
        manuscript = create_docx(
            self.root / "Manuscript .docx",
            [
                ("paragraph", "Advancement of Extracellular Vesicles Applications in Pulmonary Diseases"),
                ("heading1", "Introduction"),
                ("paragraph", "Background statement [1,2,3]."),
                ("heading1", "References"),
            ],
        )
        sibling = create_docx(
            self.root / "Manuscript (1).docx",
            [
                ("paragraph", "Advancement of Extracellular Vesicles Applications in Pulmonary Diseases"),
                ("heading1", "References"),
                ("paragraph", "1. Legacy Study A. 2023."),
                ("paragraph", "2. Legacy Study B. 2024."),
                ("paragraph", "3. Legacy Study C. 2025."),
            ],
        )
        project_root = self.root / "autodiscovered_refs_run"
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
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        audit = json.loads((project_root / "data" / "reference_coverage_audit.json").read_text(encoding="utf-8"))
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["reference_source"], str(sibling.resolve()))
