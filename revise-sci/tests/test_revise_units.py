import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location("revise_units", SCRIPTS_DIR / "revise_units.py")
revise_units = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(revise_units)


class ReviseUnitsTests(unittest.TestCase):
    def test_comment_query_text_aggregates_structured_fields(self):
        unit = {
            "comment_title": "Section 3.2 therapeutic potential needs restructuring",
            "problem_description": "The current organization is difficult to follow.",
            "root_cause": "The logic in therapeutic scenarios is fragmented.",
            "author_strategy": "Reframe the section around clinical scenarios.",
            "reviewer_comment_original": "",
            "reviewer_comment_en": "",
        }
        query = revise_units.comment_query_text(unit)
        self.assertIn("Section 3.2 therapeutic potential", query)
        self.assertIn("clinical scenarios", query)

    def test_translate_reason_to_en_handles_split_paper_search_requirement(self):
        reason = "当前材料未提供已确认的新文献信息；如需补充检索，必须仅使用 paper-search。"
        translated = revise_units.translate_reason_to_en(reason)
        self.assertEqual(
            translated,
            "The current materials do not provide confirmed new references; if additional retrieval is needed, only paper-search may be used.",
        )
        self.assertNotIn("Author confirmation is still required for this item.", translated)

    def test_best_location_reports_ambiguity_when_top_matches_tie(self):
        section_index = {
            "sections": [
                {
                    "section_id": "manuscript-001",
                    "heading": "Introduction",
                    "file": "manuscript_sections/01-introduction.md",
                    "paragraphs": [
                        {"paragraph_index": 1, "text": "Background statement for disease mechanism."},
                        {"paragraph_index": 2, "text": "Background statement for disease mechanism."},
                    ],
                }
            ]
        }
        section, paragraph, score, ambiguous = revise_units.best_location("Please clarify the background statement.", section_index)
        self.assertIsNotNone(section)
        self.assertIsNotNone(paragraph)
        self.assertGreaterEqual(score, 1)
        self.assertTrue(ambiguous)

    def test_best_location_rejects_low_signal_lexical_matches(self):
        section_index = {
            "sections": [
                {
                    "section_id": "manuscript-001",
                    "heading": "Introduction",
                    "file": "manuscript_sections/01-introduction.md",
                    "paragraphs": [
                        {"paragraph_index": 1, "text": "This section introduces the study context."},
                    ],
                }
            ]
        }
        _, _, _, ambiguous = revise_units.best_location("Please improve the current section structure.", section_index)
        self.assertTrue(ambiguous)

    def test_resolve_evidence_anchor_matches_section_number_token(self):
        unit = {"evidence_anchor": "证据锚点: 建议重点修改 3.3.5 节关于 PK/PD 的表述。"}
        section_index = {
            "sections": [
                {
                    "section_id": "manuscript-010",
                    "heading": "3.3.5 Pharmacokinetics (PK) and Pharmacodynamics (PD) of EVs in Pulmonary Delivery",
                    "file": "manuscript_sections/10-pk-pd.md",
                    "paragraphs": [
                        {"paragraph_index": 87, "text": "The in vivo fate of EVs determines pulmonary PK/PD performance."}
                    ],
                }
            ]
        }
        section, paragraph = revise_units.resolve_evidence_anchor(unit, section_index)
        self.assertEqual(section["section_id"], "manuscript-010")
        self.assertEqual(paragraph["paragraph_index"], 87)

    def test_resolve_structured_heading_hint_prefers_section_heading(self):
        unit = {
            "comment_title": "Section 3.2 therapeutic potential needs restructuring",
            "problem_description": "The current organization is difficult to follow.",
            "root_cause": "The logic in section 3.2 Therapeutic Potential is too fragmented.",
            "author_strategy": "Reframe the section around clinical scenarios.",
        }
        section_index = {
            "sections": [
                {
                    "section_id": "manuscript-003",
                    "heading": "2.4 Isolation methods",
                    "file": "manuscript_sections/03-isolation.md",
                    "paragraphs": [{"paragraph_index": 41, "text": "Isolation methods include ultracentrifugation."}],
                },
                {
                    "section_id": "manuscript-007",
                    "heading": "3.2 Therapeutic Potential",
                    "file": "manuscript_sections/07-therapeutic-potential.md",
                    "paragraphs": [{"paragraph_index": 92, "text": "EV-based therapy has shown promise in pulmonary disease models."}],
                },
            ]
        }
        section, paragraph = revise_units.resolve_structured_heading_hint(unit, section_index)
        self.assertEqual(section["section_id"], "manuscript-007")
        self.assertEqual(paragraph["paragraph_index"], 92)

    def test_unresolved_structured_heading_hint_blocks_aggressive_fallback(self):
        unit = {
            "comment_title": "Section 4.2 needs rewriting",
            "problem_description": "The logic in section 4.2 is inconsistent.",
        }
        self.assertTrue(revise_units.has_unresolved_structured_heading_hint(unit))
        self.assertIn("结构化章节提示", revise_units.assess_status(
            "The logic in section 4.2 is inconsistent.",
            {"needs_experiment": False, "needs_citation": False, "needs_figure": False},
            None,
            None,
            -1,
            False,
            None,
            False,
            unresolved_structured_hint=True,
        )[2][0])

    def test_revise_paragraph_clarify_only_replaces_target_sentence(self):
        paragraph = "Extracellular vesicles were isolated by ultracentrifugation. They showed a protective effect in TAC-treated cells. The viability assay was repeated three times."
        plan = revise_units.revise_paragraph(paragraph, "Please clarify the protective effect statement.", "clarify")
        self.assertEqual(plan["scope"], "sentence_replace")
        self.assertEqual(
            plan["paragraph_after_raw"],
            "Extracellular vesicles were isolated by ultracentrifugation. In the present dataset, they showed a protective effect in TAC-treated cells. The viability assay was repeated three times.",
        )
        self.assertEqual(plan["original_fragment"], "They showed a protective effect in TAC-treated cells.")
        self.assertEqual(plan["locked_prefix"], "Extracellular vesicles were isolated by ultracentrifugation.")
        self.assertEqual(plan["locked_suffix"], "The viability assay was repeated three times.")
        self.assertEqual(plan["change_scope"], "sentence")

    def test_revise_paragraph_limitation_appends_new_sentence_only(self):
        paragraph = "Extracellular vesicles were isolated by ultracentrifugation."
        plan = revise_units.revise_paragraph(paragraph, "Please discuss the limitation.", "limitation")
        self.assertEqual(plan["scope"], "sentence_append")
        self.assertEqual(plan["original_fragment"], "")
        self.assertIn("This finding should be interpreted", plan["raw_fragment"])
        self.assertTrue(plan["paragraph_after_raw"].startswith("Extracellular vesicles were isolated by ultracentrifugation."))
        self.assertEqual(plan["locked_prefix"], "Extracellular vesicles were isolated by ultracentrifugation.")
        self.assertEqual(plan["locked_suffix"], "")


if __name__ == "__main__":
    unittest.main()
