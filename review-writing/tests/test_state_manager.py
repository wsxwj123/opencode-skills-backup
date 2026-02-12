import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import state_manager  # noqa: E402


class StateManagerTests(unittest.TestCase):
    def test_minimal_without_section_is_blocked_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "progress.json").write_text("{}", encoding="utf-8")
            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/state_manager.py"
            res = subprocess.run(
                ["python3", script, "load", "--minimal"],
                cwd=str(root),
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 2)
            self.assertIn("--section", res.stdout)

    def test_minimal_without_section_can_be_explicitly_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "progress.json").write_text("{}", encoding="utf-8")
            (root / "data" / "literature_index.json").write_text("[]", encoding="utf-8")
            (root / "data" / "synthesis_matrix.json").write_text("[]", encoding="utf-8")
            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/state_manager.py"
            res = subprocess.run(
                ["python3", script, "load", "--minimal", "--allow-unscoped-minimal"],
                cwd=str(root),
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0)

    def test_update_assigns_id_when_global_id_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                Path("data/literature_index.json").write_text(
                    json.dumps([{"global_id": 5, "title": "Existing"}], ensure_ascii=False),
                    encoding="utf-8",
                )
                payload = [
                    {"global_id": None, "title": "New Paper"},
                    {"title": "Another New Paper"},
                ]
                payload_path = Path("payload.json")
                payload_path.write_text(json.dumps({"literature_index": payload}), encoding="utf-8")

                state_manager.update_state(str(payload_path))

                data = json.loads(Path("data/literature_index.json").read_text(encoding="utf-8"))
                ids = sorted(item["global_id"] for item in data)
                self.assertEqual(ids, [5, 6, 7])
            finally:
                os.chdir(cwd)

    def test_load_section_strict_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                Path("data/literature_index.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "related_sections": ["intro"], "title": "A"},
                            {"global_id": 2, "related_sections": ["methods"], "title": "B"},
                        ]
                    ),
                    encoding="utf-8",
                )
                Path("data/synthesis_matrix.json").write_text(
                    json.dumps([{"global_id": 1}, {"global_id": 2}]),
                    encoding="utf-8",
                )

                buf = io.StringIO()
                with redirect_stdout(buf):
                    state_manager.load_state(section="results", fallback_recent=False)
                out = json.loads(buf.getvalue())

                self.assertEqual(out["literature_index"], [])
                self.assertEqual(out["synthesis_matrix"], [])
            finally:
                os.chdir(cwd)

    def test_load_section_uses_normalized_section_matching(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                Path("data/literature_index.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "related_sections": ["Results 3.1"], "title": "A"},
                        ]
                    ),
                    encoding="utf-8",
                )
                Path("data/synthesis_matrix.json").write_text(
                    json.dumps([{"global_id": 1, "section_id": "results_3-1"}]),
                    encoding="utf-8",
                )

                buf = io.StringIO()
                with redirect_stdout(buf):
                    state_manager.load_state(section="results_3.1", fallback_recent=False)
                out = json.loads(buf.getvalue())

                self.assertEqual(len(out["literature_index"]), 1)
                self.assertEqual(len(out["synthesis_matrix"]), 1)
            finally:
                os.chdir(cwd)

    def test_snapshot_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("logs", exist_ok=True)
                Path("project_info.md").write_text("# Demo", encoding="utf-8")

                out_path = Path("logs") / "snapshots" / "manual_snapshot.json"
                state_manager.snapshot_state(str(out_path))

                self.assertTrue(out_path.exists())
                payload = json.loads(out_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["project_info"], "# Demo")
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
