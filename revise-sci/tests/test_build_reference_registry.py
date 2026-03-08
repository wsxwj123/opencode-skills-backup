import json
import unittest

from helpers import TempProject, run_script


class BuildReferenceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.project_root = self.root / "run"
        (self.project_root / "data").mkdir(parents=True)

    def tearDown(self):
        self.project.cleanup()

    def test_builds_reference_registry_and_numeric_coverage_audit(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Background statement [1,2-3].",
                    "",
                    "## References",
                    "",
                    "1. Smith J. Study A. 2023.",
                    "2. Lee K. Study B. 2024.",
                    "3. Wang M. Study C. 2025.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = run_script(
            "build_reference_registry.py",
            ["--project-root", str(self.project_root), "--output-md", str(output_md)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        registry = json.loads((self.project_root / "data" / "reference_registry.json").read_text(encoding="utf-8"))
        audit = json.loads((self.project_root / "data" / "reference_coverage_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(len(registry), 3)
        self.assertEqual([entry["reference_number"] for entry in registry], [1, 2, 3])
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["citation_style"], "numeric")
        self.assertEqual(audit["cited_numbers"], [1, 2, 3])

    def test_reports_missing_reference_numbers_when_body_citations_exceed_registry(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Background statement [1,4].",
                    "",
                    "## References",
                    "",
                    "1. Smith J. Study A. 2023.",
                    "2. Lee K. Study B. 2024.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = run_script(
            "build_reference_registry.py",
            ["--project-root", str(self.project_root), "--output-md", str(output_md)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        audit = json.loads((self.project_root / "data" / "reference_coverage_audit.json").read_text(encoding="utf-8"))
        self.assertFalse(audit["ok"])
        self.assertEqual(audit["missing_reference_numbers"], [4])

    def test_imports_review_writing_style_reference_seed_when_manuscript_has_no_references(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Background statement [1-2].",
                    "",
                    "## References",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        seed = self.project_root / "seed.json"
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
            "build_reference_registry.py",
            [
                "--project-root",
                str(self.project_root),
                "--output-md",
                str(output_md),
                "--references-source",
                str(seed),
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        registry = json.loads((self.project_root / "data" / "reference_registry.json").read_text(encoding="utf-8"))
        audit = json.loads((self.project_root / "data" / "reference_coverage_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(len(registry), 2)
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["reference_source"], str(seed.resolve()))

    def test_merges_missing_numeric_reference_numbers_from_external_seed(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Background statement [1-4].",
                    "",
                    "## References",
                    "",
                    "1. Smith J. Study A. 2023.",
                    "3. Wang M. Study C. 2025.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        seed = self.project_root / "seed.json"
        seed.write_text(
            json.dumps(
                {
                    "entries": [
                        {"reference_number": 1, "reference_entry": "1. Smith J. Study A. 2023."},
                        {"reference_number": 2, "reference_entry": "2. Lee K. Study B. 2024."},
                        {"reference_number": 3, "reference_entry": "3. Wang M. Study C. 2025."},
                        {"reference_number": 4, "reference_entry": "4. Zhao T. Study D. 2026."},
                    ]
                }
            ),
            encoding="utf-8",
        )
        result = run_script(
            "build_reference_registry.py",
            [
                "--project-root",
                str(self.project_root),
                "--output-md",
                str(output_md),
                "--references-source",
                str(seed),
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        audit = json.loads((self.project_root / "data" / "reference_coverage_audit.json").read_text(encoding="utf-8"))
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["missing_reference_numbers"], [])
        rebuilt_md = output_md.read_text(encoding="utf-8")
        self.assertIn("2. Lee K. Study B. 2024.", rebuilt_md)
        self.assertIn("4. Zhao T. Study D. 2026.", rebuilt_md)

    def test_reports_missing_author_year_citations(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "As reported by Smith et al. (2023) and (Lee, 2024), EVs shape pulmonary signaling.",
                    "",
                    "## References",
                    "",
                    "1. Smith J. Study A. 2023.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = run_script(
            "build_reference_registry.py",
            ["--project-root", str(self.project_root), "--output-md", str(output_md)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        audit = json.loads((self.project_root / "data" / "reference_coverage_audit.json").read_text(encoding="utf-8"))
        self.assertFalse(audit["ok"])
        self.assertEqual(audit["citation_style"], "author-year")
        self.assertIn("lee|2024", audit["missing_author_year_citations"])

    def test_imports_ris_reference_seed(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Background statement [1-2].",
                    "",
                    "## References",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        seed = self.project_root / "references.ris"
        seed.write_text(
            "\n".join(
                [
                    "TY  - JOUR",
                    "AU  - Smith, John",
                    "TI  - Study A",
                    "JO  - Journal A",
                    "PY  - 2023",
                    "DO  - 10.1000/a",
                    "ER  -",
                    "TY  - JOUR",
                    "AU  - Lee, Kelly",
                    "TI  - Study B",
                    "JO  - Journal B",
                    "PY  - 2024",
                    "ER  -",
                ]
            ),
            encoding="utf-8",
        )
        result = run_script(
            "build_reference_registry.py",
            [
                "--project-root",
                str(self.project_root),
                "--output-md",
                str(output_md),
                "--references-source",
                str(seed),
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        registry = json.loads((self.project_root / "data" / "reference_registry.json").read_text(encoding="utf-8"))
        self.assertEqual(len(registry), 2)
        self.assertIn("Study A", registry[0]["raw_text"])

    def test_writes_reference_recovery_request_when_missing_citations_remain(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Background statement [1,5].",
                    "",
                    "## References",
                    "",
                    "1. Smith J. Study A. 2023.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = run_script(
            "build_reference_registry.py",
            ["--project-root", str(self.project_root), "--output-md", str(output_md)],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        request = (self.project_root / "reference_recovery_request.md").read_text(encoding="utf-8")
        self.assertIn("5", request)
        self.assertIn(".docx/.bib/.ris/.json/.md/.txt", request)
        self.assertIn("是否允许按 review-writing 规则启动新文献检索并补全文末参考文献", request)
        self.assertIn("paper-search", request)
        self.assertIn("citation_guard.py", request)
        self.assertIn("synthesis_matrix.json", request)

    def test_writes_reference_search_manifest_when_search_is_approved(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Background statement [1,5].",
                    "",
                    "## References",
                    "",
                    "1. Smith J. Study A. 2023.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (self.project_root / "project_state.json").write_text(
            json.dumps({"inputs": {"reference_search_decision": "approved"}}),
            encoding="utf-8",
        )
        result = run_script(
            "build_reference_registry.py",
            [
                "--project-root",
                str(self.project_root),
                "--output-md",
                str(output_md),
                "--reference-search-decision",
                "approved",
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        manifest = json.loads((self.project_root / "reference_search_manifest.json").read_text(encoding="utf-8"))
        strategy = json.loads((self.project_root / "reference_search_strategy.json").read_text(encoding="utf-8"))
        status = json.loads((self.project_root / "reference_search_status.json").read_text(encoding="utf-8"))
        rounds = json.loads((self.project_root / "reference_search_rounds.json").read_text(encoding="utf-8"))
        task = (self.project_root / "reference_search_task.md").read_text(encoding="utf-8")
        self.assertEqual(manifest["workflow"], "review-writing")
        self.assertEqual(manifest["reference_search_decision"], "approved")
        self.assertEqual(manifest["allowed_provider_families"], ["paper-search"])
        self.assertTrue(manifest["verification_policy"]["dual_verification_required"])
        self.assertFalse(manifest["verification_policy"]["allow_unverified"])
        self.assertEqual(strategy["workflow"], "review-writing")
        self.assertEqual(strategy["provider_policy"]["primary"], ["paper-search"])
        self.assertIn("websearch", strategy["provider_policy"]["forbidden"])
        self.assertIn("citation_guard.py", strategy["mandatory_guard_command"])
        self.assertEqual(len(strategy["round_model"]), 3)
        self.assertEqual(status["reference_search_decision"], "approved")
        self.assertFalse(status["steps"]["paper_search_batch_imported"])
        self.assertTrue(status["steps"]["search_round_plan_generated"])
        self.assertFalse(status["steps"]["validated_batch_present"])
        self.assertEqual(rounds["workflow"], "review-writing")
        self.assertEqual(len(rounds["rounds"]), 3)
        self.assertTrue(any(batch["queries"] for batch in rounds["rounds"] if batch["round"] == 1))
        self.assertIn("citation_guard.py", task)
        self.assertIn("paper-search", task)
        self.assertIn("build_literature_index.py", task)

    def test_generates_search_governance_artifacts_for_approved_supplement_path(self):
        output_md = self.project_root / "revised_manuscript.md"
        output_md.write_text(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Background statement [1].",
                    "",
                    "## References",
                    "",
                    "1. Smith J. Study A. 2023.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (self.project_root / "project_state.json").write_text(
            json.dumps({"inputs": {"reference_search_decision": "approved"}}),
            encoding="utf-8",
        )
        (self.project_root / "paper_search_results.json").write_text(json.dumps({"results": []}), encoding="utf-8")
        result = run_script(
            "build_reference_registry.py",
            [
                "--project-root",
                str(self.project_root),
                "--output-md",
                str(output_md),
                "--reference-search-decision",
                "approved",
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertTrue((self.project_root / "reference_search_manifest.json").exists())
        self.assertTrue((self.project_root / "reference_search_strategy.json").exists())
        self.assertTrue((self.project_root / "reference_search_status.json").exists())
        self.assertTrue((self.project_root / "reference_search_rounds.json").exists())
