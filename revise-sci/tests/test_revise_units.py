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


if __name__ == "__main__":
    unittest.main()
