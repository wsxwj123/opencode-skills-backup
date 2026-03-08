import json
import os
import sys
import unittest

from helpers import TempProject, create_fake_opencode, create_fake_paper_search_runner, run_script


class ExecuteReferenceSearchTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.project_root = self.root / "project"
        self.project_root.mkdir()
        (self.project_root / "reference_search_manifest.json").write_text(
            json.dumps(
                {
                    "workflow": "review-writing",
                    "allowed_provider_families": ["paper-search"],
                }
            ),
            encoding="utf-8",
        )
        (self.project_root / "reference_search_strategy.json").write_text(
            json.dumps(
                {
                    "workflow": "review-writing",
                    "provider_policy": {"primary": ["paper-search"]},
                    "mandatory_guard_command": "python scripts/citation_guard.py --paper-search-results <project_root/paper_search_results.json> --project-root <project_root> --live",
                }
            ),
            encoding="utf-8",
        )
        (self.project_root / "reference_search_rounds.json").write_text(
            json.dumps(
                {
                    "workflow": "review-writing",
                    "rounds": [
                        {"round": 1, "provider_family": "paper-search", "queries": ["topic review 2024"]},
                        {"round": 2, "provider_family": "paper-search", "queries": ["section heading query"]},
                        {"round": 3, "provider_family": "paper-search", "queries": ["critical refresh query"]},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (self.project_root / "reference_search_status.json").write_text(
            json.dumps({"steps": {"search_round_plan_generated": True, "paper_search_batch_imported": False}}),
            encoding="utf-8",
        )

    def tearDown(self):
        self.project.cleanup()

    def test_execute_reference_search_requires_runner_when_not_configured(self):
        result = run_script(
            "execute_reference_search.py",
            ["--project-root", str(self.project_root), "--disable-opencode-driver"],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        request = (self.project_root / "reference_search_execution_request.md").read_text(encoding="utf-8")
        self.assertIn("paper-search runner", request)
        execution = json.loads((self.project_root / "reference_search_execution.json").read_text(encoding="utf-8"))
        self.assertFalse(execution["ok"])
        self.assertFalse(execution["runner_available"])

    def test_execute_reference_search_runs_local_runner_and_writes_results(self):
        payload = json.dumps(
            {
                "results": [
                    {
                        "comment_id": "R1-Major-01",
                        "confirmed": True,
                        "formatted_citation_text": "(Smith et al., 2023)",
                        "target_section_heading": "Introduction",
                        "target_paragraph_index": 1,
                        "citations": [
                            {
                                "source_provider": "paper-search",
                                "source_id": "PMID:123456",
                                "pmid": "123456",
                                "title": "Quercetin in cardiovascular models",
                            }
                        ],
                    }
                ]
            }
        )
        runner = create_fake_paper_search_runner(self.root / "fake_runner.py", payload)
        result = run_script(
            "execute_reference_search.py",
            [
                "--project-root",
                str(self.project_root),
                "--paper-search-runner",
                f"{sys.executable} {runner}",
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        output_rows = json.loads((self.project_root / "paper_search_results.json").read_text(encoding="utf-8"))
        self.assertEqual(output_rows["results"][0]["comment_id"], "R1-Major-01")
        execution = json.loads((self.project_root / "reference_search_execution.json").read_text(encoding="utf-8"))
        self.assertTrue(execution["ok"])
        status = json.loads((self.project_root / "reference_search_status.json").read_text(encoding="utf-8"))
        self.assertTrue(status["steps"]["paper_search_batch_imported"])

    def test_execute_reference_search_uses_opencode_driver_when_runner_missing(self):
        payload = json.dumps(
            {
                "results": [
                    {
                        "comment_id": "R1-Major-01",
                        "confirmed": True,
                        "formatted_citation_text": "(Smith et al., 2023)",
                        "target_section_heading": "Introduction",
                        "target_paragraph_index": 1,
                        "citations": [
                            {
                                "source_provider": "paper-search",
                                "source_id": "PMID:123456",
                                "pmid": "123456",
                                "title": "Quercetin in cardiovascular models",
                            }
                        ],
                    }
                ]
            }
        )
        fake_opencode = create_fake_opencode(self.root / "opencode", payload)
        env = dict(os.environ)
        env["PATH"] = f"{self.root}:{env.get('PATH', '')}"
        result = run_script(
            "execute_reference_search.py",
            ["--project-root", str(self.project_root)],
            cwd=self.root,
            env=env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        execution = json.loads((self.project_root / "reference_search_execution.json").read_text(encoding="utf-8"))
        self.assertEqual(execution["driver_mode"], "opencode-driver")
        self.assertTrue((self.project_root / "reference_search_opencode_prompt.md").exists())
        self.assertEqual(fake_opencode.exists(), True)


if __name__ == "__main__":
    unittest.main()
