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
        (self.project_root / "response_to_reviewers.md").write_text("# x\n", encoding="utf-8")
        (self.project_root / "response_to_reviewers.docx").write_bytes(b"fake")
        (self.project_root / "revised.docx").write_bytes(b"fake")
        (self.project_root / "revised.md").write_text("# y\n", encoding="utf-8")
        (self.project_root / "manuscript_edit_plan.md").write_text("plan\n", encoding="utf-8")
        (self.project_root / "index.json").write_text(json.dumps({"toc": {"reviewers": []}}), encoding="utf-8")
        (self.project_root / "project_state.json").write_text(
            json.dumps({"delivery_status": "ready_to_submit", "counts": {"comment_units": 1}}),
            encoding="utf-8",
        )

    def tearDown(self):
        self.project.cleanup()

    def test_gate_rejects_placeholders(self):
        unit = {
            "comment_id": "R1-Major-01",
            "severity": "major",
            "response_en": "AI_FILL_REQUIRED",
            "response_zh": "待AI",
            "notes_core_zh": ["ok"],
            "notes_support_zh": ["ok"],
            "evidence_sources": [{"provider_family": "paper-search", "source": "PMID:1"}],
            "status": "completed",
        }
        (self.project_root / "units" / "001.json").write_text(json.dumps(unit), encoding="utf-8")
        result = run_script("strict_gate.py", ["--project-root", str(self.project_root)], cwd=self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("placeholder", result.stdout + result.stderr)
