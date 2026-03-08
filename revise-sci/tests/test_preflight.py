import json
import unittest
from pathlib import Path

from helpers import TempProject, create_docx, run_script


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.comments = create_docx(
            self.root / "comments.docx",
            [("paragraph", "Reviewer #1"), ("paragraph", "Major"), ("paragraph", "1. Please clarify the mechanism.")],
        )
        self.manuscript = create_docx(
            self.root / "manuscript.docx",
            [("heading1", "Introduction"), ("paragraph", "This is the introduction.")],
        )
        self.attachments = self.root / "attachments"
        self.attachments.mkdir()
        (self.attachments / "figure1.png").write_bytes(b"fake-image")
        self.project_root = self.root / "run"

    def tearDown(self):
        self.project.cleanup()

    def test_preflight_writes_report_and_manifest(self):
        result = run_script(
            "preflight.py",
            [
                "--comments",
                str(self.comments),
                "--manuscript",
                str(self.manuscript),
                "--attachments-dir",
                str(self.attachments),
                "--project-root",
                str(self.project_root),
                "--output-md",
                str(self.project_root / "revised.md"),
                "--output-docx",
                str(self.project_root / "revised.docx"),
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        report = (self.project_root / "precheck_report.md").read_text(encoding="utf-8")
        self.assertIn("预检报告", report)
        self.assertIn("si_docx_path", report)
        self.assertIn("reference_search_decision", report)
        self.assertIn("opencode_driver_command", report)
        state = json.loads((self.project_root / "project_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["inputs"]["reference_search_decision"], "ask")
        manifest = json.loads((self.project_root / "attachments_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["count"], 1)
        self.assertEqual(manifest["files"][0]["name"], "figure1.png")

    def test_preflight_rejects_invalid_paper_search_json(self):
        bad_json = self.root / "paper_search_results.json"
        bad_json.write_text("{not-json", encoding="utf-8")
        result = run_script(
            "preflight.py",
            [
                "--comments",
                str(self.comments),
                "--manuscript",
                str(self.manuscript),
                "--attachments-dir",
                str(self.attachments),
                "--project-root",
                str(self.project_root),
                "--output-md",
                str(self.project_root / "revised.md"),
                "--output-docx",
                str(self.project_root / "revised.docx"),
                "--paper-search-results",
                str(bad_json),
            ],
            cwd=self.root,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("paper_search_results_path must be valid json", result.stdout + result.stderr)

    def test_preflight_requires_explicit_approved_decision_for_paper_search_results(self):
        good_json = self.root / "paper_search_results.json"
        good_json.write_text(json.dumps({"results": []}), encoding="utf-8")
        result = run_script(
            "preflight.py",
            [
                "--comments",
                str(self.comments),
                "--manuscript",
                str(self.manuscript),
                "--attachments-dir",
                str(self.attachments),
                "--project-root",
                str(self.project_root),
                "--output-md",
                str(self.project_root / "revised.md"),
                "--output-docx",
                str(self.project_root / "revised.docx"),
                "--paper-search-results",
                str(good_json),
            ],
            cwd=self.root,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--reference-search-decision approved", result.stdout + result.stderr)
