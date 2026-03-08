import json
import unittest

from helpers import TempProject, run_script


class StrictGateTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.project_root = self.root / "run"
        (self.project_root / "units").mkdir(parents=True)
        (self.project_root / "manuscript_sections").mkdir(parents=True)
        (self.project_root / "comment_records").mkdir(parents=True)

    def tearDown(self):
        self.project.cleanup()

    def _write_valid_base(self):
        unit = {
            "comment_id": "R1-Major-01",
            "reviewer": "Reviewer #1",
            "severity": "major",
            "reviewer_comment_en": "Please clarify the mechanism statement.",
            "reviewer_comment_zh_literal": "请澄清机制表述。",
            "intent_zh": "审稿人要求收紧表述边界。",
            "response_en": "We revised the sentence to limit the claim to the present dataset.",
            "response_zh": "我们已修订该句，将结论限定在当前数据范围内。",
            "original_excerpt_en": "Quercetin showed a protective effect in TAC-treated cells.",
            "revised_excerpt_en": "In the present dataset, Quercetin showed a protective effect in TAC-treated cells.",
            "revised_excerpt_zh": "在当前数据范围内，槲皮素在TAC处理细胞中表现出保护作用。",
            "modification_actions": [{"action": "修改", "reason": "收紧结论边界。"}],
            "notes_core_zh": ["已按评论修改正文。"],
            "notes_support_zh": ["已保留证据来源。"],
            "evidence_sources": [{"provider_family": "user-provided", "source": "manuscript_sections/01-results.md"}],
            "target_document": "manuscript",
            "status": "completed",
            "author_confirmation_reason": "",
            "atomic_location": {
                "manuscript_section_id": "manuscript-001",
                "si_section_id": "",
                "section_file": "manuscript_sections/01-results.md",
                "section_heading": "Results",
                "paragraph_index": 1,
                "matched_sentence": "Quercetin showed a protective effect in TAC-treated cells.",
                "matched_sentence_index": 0,
            },
        }
        (self.project_root / "units" / "001_R1-Major-01.json").write_text(json.dumps(unit), encoding="utf-8")
        (self.project_root / "comment_records" / "R1-Major-01.md").write_text("# R1-Major-01\n", encoding="utf-8")
        (self.project_root / "response_to_reviewers.md").write_text(
            "\n".join(
                [
                    "# 回复审稿人的邮件",
                    "",
                    "# Reviewer #1",
                    "",
                    "## Major",
                    "",
                    "### Comment 1",
                    "",
                    "Please clarify the mechanism statement.",
                    "",
                    "#### 2) Response to Reviewer（中英对照）",
                    "",
                    "We revised the sentence to limit the claim to the present dataset.",
                    "",
                    "In the present dataset, Quercetin showed a protective effect in TAC-treated cells.",
                    "",
                    "#### 5) Evidence Attachments",
                    "",
                    "**Text**",
                    "- user-provided: manuscript_sections/01-results.md",
                    "",
                    "**Image**",
                    "- Not provided by user",
                    "",
                    "**Table**",
                    "- Not provided by user",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (self.project_root / "response_to_reviewers.docx").write_bytes(b"fake")
        (self.project_root / "revised.docx").write_bytes(b"fake")
        (self.project_root / "revised.md").write_text("# Results\n\nIn the present dataset, Quercetin showed a protective effect in TAC-treated cells.\n", encoding="utf-8")
        (self.project_root / "manuscript_edit_plan.md").write_text(
            "\n".join(
                [
                    "# manuscript_edit_plan",
                    "",
                    "| comment_id | 目标文档 | 段落索引 | 待替换片段 | 替换后文本 | 动作类型 |",
                    "|---|---|---|---|---|---|",
                    "| R1-Major-01 | manuscript | 1 | Quercetin showed a protective effect in TAC-treated cells. | In the present dataset, Quercetin showed a protective effect in TAC-treated cells. | 修改 |",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (self.project_root / "manuscript_section_index.json").write_text(
            json.dumps(
                {
                    "sections": [
                        {
                            "section_id": "manuscript-001",
                            "heading": "Results",
                            "file": "manuscript_sections/01-results.md",
                            "paragraphs": [
                                {
                                    "paragraph_index": 1,
                                    "text": "Quercetin showed a protective effect in TAC-treated cells.",
                                    "current_text": "In the present dataset, Quercetin showed a protective effect in TAC-treated cells.",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (self.project_root / "manuscript_sections" / "01-results.md").write_text(
            "# Results\n\nIn the present dataset, Quercetin showed a protective effect in TAC-treated cells.\n",
            encoding="utf-8",
        )
        (self.project_root / "project_state.json").write_text(
            json.dumps(
                {
                    "delivery_status": "ready_to_submit",
                    "counts": {"comment_units": 1},
                    "outputs": {
                        "output_md": str((self.project_root / "revised.md").resolve()),
                        "output_docx": str((self.project_root / "revised.docx").resolve()),
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_gate_rejects_placeholders(self):
        self._write_valid_base()
        unit_path = self.project_root / "units" / "001_R1-Major-01.json"
        unit = json.loads(unit_path.read_text(encoding="utf-8"))
        unit["response_en"] = "AI_FILL_REQUIRED"
        unit["response_zh"] = "待AI"
        unit_path.write_text(json.dumps(unit), encoding="utf-8")
        result = run_script("strict_gate.py", ["--project-root", str(self.project_root)], cwd=self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("placeholder", result.stdout + result.stderr)

    def test_gate_rejects_missing_response_comment_mapping(self):
        self._write_valid_base()
        (self.project_root / "response_to_reviewers.md").write_text("# 回复审稿人的邮件\n", encoding="utf-8")
        result = run_script("strict_gate.py", ["--project-root", str(self.project_root)], cwd=self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing comment mapping", result.stdout + result.stderr)

    def test_gate_rejects_completed_unit_when_manuscript_and_plan_do_not_match(self):
        self._write_valid_base()
        (self.project_root / "manuscript_sections" / "01-results.md").write_text(
            "# Results\n\nQuercetin showed a protective effect in TAC-treated cells.\n",
            encoding="utf-8",
        )
        (self.project_root / "manuscript_edit_plan.md").write_text("# manuscript_edit_plan\n", encoding="utf-8")
        result = run_script("strict_gate.py", ["--project-root", str(self.project_root)], cwd=self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("completed excerpt not found in manuscript section", result.stdout + result.stderr)
        self.assertIn("edit plan missing comment_id", result.stdout + result.stderr)

    def test_gate_requires_literature_index_and_matrix_for_completed_citation_unit(self):
        self._write_valid_base()
        unit_path = self.project_root / "units" / "001_R1-Major-01.json"
        unit = json.loads(unit_path.read_text(encoding="utf-8"))
        unit["editorial_intent"] = "citation"
        unit["evidence_sources"] = [{"provider_family": "paper-search", "source": "PMID:123456"}]
        unit_path.write_text(json.dumps(unit), encoding="utf-8")
        (self.project_root / "reference_sync_report.json").write_text(
            json.dumps({"covered_comment_ids": ["R1-Major-01"], "references_added": 1}),
            encoding="utf-8",
        )
        result = run_script("strict_gate.py", ["--project-root", str(self.project_root)], cwd=self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("literature_index", result.stdout + result.stderr)
