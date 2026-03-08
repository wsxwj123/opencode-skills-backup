import json
import tempfile
import unittest
from pathlib import Path

from helpers import run_script


class FinalConsistencyReportTests(unittest.TestCase):
    def test_report_lists_each_blocking_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            (project_root / "units").mkdir(parents=True)
            (project_root / "project_state.json").write_text(
                json.dumps({"delivery_status": "author_confirmation_required"}),
                encoding="utf-8",
            )
            (project_root / "units" / "001.json").write_text(
                json.dumps(
                    {
                        "comment_id": "R1-Major-01",
                        "severity": "major",
                        "status": "needs_author_confirmation",
                        "target_document": "manuscript",
                        "author_confirmation_reason": "当前材料未提供新增实验或结果。",
                        "evidence_sources": [{"provider_family": "user-provided", "source": "manuscript_sections/01.md"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = run_script(
                "final_consistency_report.py",
                ["--project-root", str(project_root)],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            report = (project_root / "final_consistency_report.md").read_text(encoding="utf-8")
            self.assertIn("## Blocking Reasons", report)
            self.assertIn("R1-Major-01", report)
            self.assertIn("缺实验/结果", report)
            self.assertIn("当前材料未提供新增实验或结果。", report)

    def test_report_includes_reference_coverage_summary_when_audit_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            (project_root / "units").mkdir(parents=True)
            (project_root / "project_state.json").write_text(
                json.dumps({"delivery_status": "author_confirmation_required"}),
                encoding="utf-8",
            )
            (project_root / "data").mkdir(parents=True)
            (project_root / "data" / "reference_coverage_audit.json").write_text(
                json.dumps(
                    {
                        "ok": False,
                        "citation_style": "numeric",
                        "reference_entries": 0,
                        "cited_numbers": [1, 2, 3],
                        "missing_reference_numbers": [1, 2, 3],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = run_script(
                "final_consistency_report.py",
                ["--project-root", str(project_root)],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            report = (project_root / "final_consistency_report.md").read_text(encoding="utf-8")
            self.assertIn("## Reference Coverage", report)
            self.assertIn("reference_coverage_ok", report)
            self.assertIn("missing_reference_numbers", report)
            self.assertIn("1, 2, 3", report)

    def test_report_includes_reference_search_governance_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            (project_root / "units").mkdir(parents=True)
            (project_root / "project_state.json").write_text(
                json.dumps({"delivery_status": "author_confirmation_required"}),
                encoding="utf-8",
            )
            (project_root / "data").mkdir(parents=True)
            (project_root / "data" / "reference_coverage_audit.json").write_text(
                json.dumps(
                    {
                        "ok": False,
                        "citation_style": "numeric",
                        "reference_entries": 0,
                        "cited_numbers": [1],
                        "missing_reference_numbers": [1],
                        "reference_search_required": True,
                        "reference_search_decision": "approved",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (project_root / "reference_search_manifest.json").write_text(
                json.dumps({"workflow": "review-writing", "reference_search_decision": "approved"}),
                encoding="utf-8",
            )
            (project_root / "reference_search_strategy.json").write_text(
                json.dumps({"workflow": "review-writing"}),
                encoding="utf-8",
            )
            (project_root / "reference_search_status.json").write_text(
                json.dumps({"steps": {"citation_guard_passed": False}}),
                encoding="utf-8",
            )
            (project_root / "reference_search_rounds.json").write_text(
                json.dumps({"workflow": "review-writing", "rounds": [{"round": 1, "queries": ["q1"]}]}),
                encoding="utf-8",
            )
            result = run_script(
                "final_consistency_report.py",
                ["--project-root", str(project_root)],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            report = (project_root / "final_consistency_report.md").read_text(encoding="utf-8")
            self.assertIn("reference_search_workflow", report)
            self.assertIn("review-writing", report)
            self.assertIn("reference_search_guard_passed", report)
            self.assertIn("reference_search_rounds", report)


if __name__ == "__main__":
    unittest.main()
