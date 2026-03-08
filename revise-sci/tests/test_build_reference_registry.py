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
