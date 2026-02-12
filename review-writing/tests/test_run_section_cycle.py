import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import run_section_cycle  # noqa: E402


class RunSectionCycleTests(unittest.TestCase):
    def test_round1_bootstrap_is_global_and_summary_payload_flag(self):
        calls = []

        def fake_run(cmd):
            calls.append(cmd)

        def fake_exists(path):
            # payload exists before update; update deletes later but summary should keep initial state
            return str(path).endswith("state_update_payload.json")

        argv = [
            "run_section_cycle.py",
            "intro",
            "--round",
            "1",
            "--skip-live",
        ]

        with patch.object(run_section_cycle, "run", side_effect=fake_run), patch.object(
            run_section_cycle.os.path, "exists", side_effect=fake_exists
        ), patch.object(run_section_cycle, "_save_json", return_value=None), patch.object(sys, "argv", argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                run_section_cycle.main()
            out = buf.getvalue()

        bootstrap_cmd = [c for c in calls if c[:3] == ["python3", "scripts/matrix_manager.py", "bootstrap"]][0]
        self.assertNotIn("--section", bootstrap_cmd)

        summary_line = out.split("Cycle Summary:")[-1].strip()
        summary = json.loads(summary_line)
        self.assertTrue(summary["payload_used"])

    def test_live_validation_command_uses_live_used_only(self):
        calls = []

        def fake_run(cmd):
            calls.append(cmd)

        def fake_exists(path):
            s = str(path)
            return s.endswith("strategy.json")

        argv = [
            "run_section_cycle.py",
            "intro",
            "--round",
            "2",
            "--claims",
            "claims.json",
            "--search-strategy",
            "strategy.json",
        ]
        with patch.object(run_section_cycle, "run", side_effect=fake_run), patch.object(
            run_section_cycle.os.path, "exists", side_effect=fake_exists
        ), patch.object(run_section_cycle, "_load_gates", return_value={"round1_complete": True, "sections": {}}), patch.object(
            run_section_cycle, "_save_json", return_value=None
        ), patch.object(run_section_cycle, "_sha256_file", return_value="abc"), patch.object(
            run_section_cycle, "_load_strategy_payload", return_value={"queries": ["q1"]}
        ), patch.object(sys, "argv", argv):
            run_section_cycle.main()

        validate_cmd = [c for c in calls if c[:3] == ["python3", "scripts/validate_citations.py", "--fail-on-orphan"]][0]
        self.assertIn("--live-used-only", validate_cmd)

        bind_cmd = [c for c in calls if c[:3] == ["python3", "scripts/matrix_manager.py", "bind-claims"]][0]
        self.assertIn("--fail-on-no-update", bind_cmd)

        audit_cmd = [c for c in calls if c[:3] == ["python3", "scripts/matrix_manager.py", "audit"]][0]
        self.assertIn("--fail-on-gap", audit_cmd)

    def test_round2_blocked_when_round1_not_completed(self):
        argv = [
            "run_section_cycle.py",
            "intro",
            "--round",
            "2",
            "--claims",
            "claims.json",
            "--search-strategy",
            "strategy.json",
        ]
        with patch.object(run_section_cycle.os.path, "exists", return_value=True), patch.object(
            run_section_cycle, "_load_gates", return_value={"round1_complete": False, "sections": {}}
        ), patch.object(run_section_cycle, "_save_json", return_value=None), patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as cm:
                run_section_cycle.main()
            self.assertEqual(cm.exception.code, 2)

    def test_round2_requires_claims(self):
        argv = ["run_section_cycle.py", "intro", "--round", "2"]
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as cm:
                run_section_cycle.main()
            self.assertEqual(cm.exception.code, 2)

    def test_round2_requires_search_strategy(self):
        argv = ["run_section_cycle.py", "intro", "--round", "2", "--claims", "claims.json"]
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as cm:
                run_section_cycle.main()
            self.assertEqual(cm.exception.code, 2)

    def test_records_search_manifest_on_round2(self):
        calls = []

        def fake_run(cmd):
            calls.append(cmd)

        saved = {}

        def fake_save(path, payload):
            if str(path).endswith("search_manifest.json"):
                saved["manifest"] = payload

        def fake_exists(path):
            s = str(path)
            return s.endswith("strategy.json")

        argv = [
            "run_section_cycle.py",
            "intro",
            "--round",
            "2",
            "--claims",
            "claims.json",
            "--search-strategy",
            "strategy.json",
            "--skip-live",
        ]
        with patch.object(run_section_cycle, "run", side_effect=fake_run), patch.object(
            run_section_cycle.os.path, "exists", side_effect=fake_exists
        ), patch.object(run_section_cycle, "_load_gates", return_value={"round1_complete": True, "sections": {}}), patch.object(
            run_section_cycle, "_save_json", side_effect=fake_save
        ), patch.object(run_section_cycle, "_load_json", return_value=[]), patch.object(
            run_section_cycle, "_sha256_file", return_value="abc"
        ), patch.object(run_section_cycle, "_load_strategy_payload", return_value={"queries": ["q1"]}), patch.object(
            sys, "argv", argv
        ):
            run_section_cycle.main()

        self.assertIn("manifest", saved)
        self.assertEqual(saved["manifest"][-1]["strategy_file"], "strategy.json")
        self.assertEqual(saved["manifest"][-1]["round"], 2)

    def test_resume_ignores_old_checkpoint_version(self):
        with patch.object(
            run_section_cycle, "_load_json",
            return_value={
                "workflow_version": run_section_cycle.WORKFLOW_VERSION - 1,
                "status": "failed",
                "section": "intro",
                "round": 2,
                "completed_steps": ["load_state"],
            },
        ):
            steps, msg = run_section_cycle._load_resume_steps("intro", 2, resume=True)
        self.assertEqual(steps, set())
        self.assertIn("workflow_version", msg)

    def test_prune_log_files_keeps_latest(self):
        import os
        import tempfile
        import time

        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("logs/snapshots", exist_ok=True)
                for i in range(5):
                    p = Path("logs/snapshots") / f"state_snapshot_{i}.json"
                    p.write_text("{}", encoding="utf-8")
                    time.sleep(0.01)
                for i in range(4):
                    p = Path("logs") / f"cycle_checkpoint_s{i}.json"
                    p.write_text("{}", encoding="utf-8")
                    time.sleep(0.01)

                out = run_section_cycle._prune_log_files(keep_snapshots=2, keep_checkpoints=1)
                self.assertEqual(out["snapshots"], 3)
                self.assertEqual(out["checkpoints"], 3)
            finally:
                os.chdir(cwd)

    def test_writes_checkpoint_on_failure(self):
        calls = []
        checkpoint_payloads = []

        def fake_run(cmd):
            calls.append(cmd)
            if cmd[:3] == ["python3", "scripts/matrix_manager.py", "audit"]:
                raise RuntimeError("boom")

        def fake_save(path, payload):
            checkpoint_payloads.append(payload)

        argv = ["run_section_cycle.py", "intro", "--round", "1", "--skip-live"]
        with patch.object(run_section_cycle, "run", side_effect=fake_run), patch.object(
            run_section_cycle.os.path, "exists", return_value=False
        ), patch.object(run_section_cycle, "_load_gates", return_value={"round1_complete": True, "sections": {}}), patch.object(
            run_section_cycle, "_save_json", side_effect=fake_save
        ), patch.object(sys, "argv", argv):
            with self.assertRaises(RuntimeError):
                run_section_cycle.main()

        self.assertTrue(any(p.get("status") == "failed" for p in checkpoint_payloads))


if __name__ == "__main__":
    unittest.main()
