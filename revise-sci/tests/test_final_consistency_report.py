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


if __name__ == "__main__":
    unittest.main()
