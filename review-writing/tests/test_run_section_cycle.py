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

        argv = ["run_section_cycle.py", "intro", "--round", "2", "--claims", "claims.json"]
        with patch.object(run_section_cycle, "run", side_effect=fake_run), patch.object(
            run_section_cycle.os.path, "exists", return_value=False
        ), patch.object(run_section_cycle, "_load_gates", return_value={"round1_complete": True, "sections": {}}), patch.object(
            run_section_cycle, "_save_json", return_value=None
        ), patch.object(sys, "argv", argv):
            run_section_cycle.main()

        validate_cmd = [c for c in calls if c[:3] == ["python3", "scripts/validate_citations.py", "--fail-on-orphan"]][0]
        self.assertIn("--live-used-only", validate_cmd)

    def test_round2_blocked_when_round1_not_completed(self):
        argv = ["run_section_cycle.py", "intro", "--round", "2", "--claims", "claims.json"]
        with patch.object(run_section_cycle.os.path, "exists", return_value=False), patch.object(
            run_section_cycle, "_load_gates", return_value={"round1_complete": False, "sections": {}}
        ), patch.object(run_section_cycle, "_save_json", return_value=None), patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as cm:
                run_section_cycle.main()
            self.assertEqual(cm.exception.code, 2)

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
