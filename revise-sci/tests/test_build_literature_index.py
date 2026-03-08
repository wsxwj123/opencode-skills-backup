import json
import unittest

from helpers import TempProject, run_script


class BuildLiteratureIndexTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.project_root = self.root / "run"
        (self.project_root / "units").mkdir(parents=True)

    def tearDown(self):
        self.project.cleanup()

    def test_build_deduplicates_verified_citations_into_canonical_index(self):
        unit_a = {
            "comment_id": "R1-Major-01",
            "reviewer_comment_en": "Add a citation for the background statement.",
            "target_document": "manuscript",
            "atomic_location": {
                "manuscript_section_id": "manuscript-001",
                "section_heading": "Introduction",
                "paragraph_index": 1,
            },
        }
        unit_b = {
            "comment_id": "R2-Minor-02",
            "reviewer_comment_en": "Please cite prior cardiovascular model studies.",
            "target_document": "manuscript",
            "atomic_location": {
                "manuscript_section_id": "manuscript-004",
                "section_heading": "Discussion",
                "paragraph_index": 2,
            },
        }
        (self.project_root / "units" / "001.json").write_text(json.dumps(unit_a), encoding="utf-8")
        (self.project_root / "units" / "002.json").write_text(json.dumps(unit_b), encoding="utf-8")
        (self.project_root / "paper_search_validated.json").write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "comment_id": "R1-Major-01",
                            "confirmed": True,
                            "guard_verified": True,
                            "formatted_citation_text": "(Smith et al., 2023)",
                            "target_section_heading": "Introduction",
                            "target_paragraph_index": 1,
                            "citations": [
                                {
                                    "guard_verified": True,
                                    "doi": "10.1000/xyz123",
                                    "title": "Quercetin in cardiovascular models",
                                    "authors": ["Smith J", "Lee K"],
                                    "journal": "Cardiovasc Res",
                                    "year": 2023,
                                    "reference_entry": "Smith J, Lee K. Quercetin in cardiovascular models. Cardiovasc Res. 2023. DOI: 10.1000/xyz123.",
                                    "key_finding": "Supports the background claim.",
                                    "limitation": "Model-specific evidence.",
                                }
                            ],
                        },
                        {
                            "comment_id": "R2-Minor-02",
                            "confirmed": True,
                            "guard_verified": True,
                            "formatted_citation_text": "(Smith et al., 2023)",
                            "target_section_heading": "Discussion",
                            "target_paragraph_index": 2,
                            "citations": [
                                {
                                    "guard_verified": True,
                                    "doi": "10.1000/xyz123",
                                    "title": "Quercetin in cardiovascular models",
                                    "authors": ["Smith J", "Lee K"],
                                    "journal": "Cardiovasc Res",
                                    "year": 2023,
                                    "reference_entry": "Smith J, Lee K. Quercetin in cardiovascular models. Cardiovasc Res. 2023. DOI: 10.1000/xyz123.",
                                    "key_finding": "Supports the background claim.",
                                    "limitation": "Model-specific evidence.",
                                }
                            ],
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = run_script("build_literature_index.py", ["--project-root", str(self.project_root)], cwd=self.root)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        literature = json.loads((self.project_root / "data" / "literature_index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(literature), 1)
        entry = literature[0]
        self.assertEqual(entry["global_id"], 1)
        self.assertEqual(entry["doi"], "10.1000/xyz123")
        self.assertCountEqual(entry["comment_ids"], ["R1-Major-01", "R2-Minor-02"])
        self.assertCountEqual(entry["claim_ids"], ["R1-Major-01", "R2-Minor-02"])
        self.assertCountEqual(entry["related_sections"], ["manuscript-001", "manuscript-004"])

        claims = json.loads((self.project_root / "data" / "revision_claims.json").read_text(encoding="utf-8"))
        self.assertEqual(len(claims), 2)
        self.assertEqual({claim["global_id"] for claim in claims}, {1})

