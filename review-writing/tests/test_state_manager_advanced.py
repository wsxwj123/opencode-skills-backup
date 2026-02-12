import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import state_manager  # noqa: E402


class StateManagerAdvancedTests(unittest.TestCase):
    def test_update_merge_literature_keeps_history_and_upserts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                Path("data/literature_index.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "title": "A", "doi": "10.1/a", "note": "old"},
                            {"global_id": 2, "title": "B"},
                        ]
                    ),
                    encoding="utf-8",
                )
                payload_path = Path("payload.json")
                payload_path.write_text(
                    json.dumps(
                        {
                            "literature_index": [
                                {"global_id": 1, "title": "A2", "doi": "10.1/a"},
                                {"title": "C", "doi": "10.1/c"},
                            ]
                        }
                    ),
                    encoding="utf-8",
                )

                state_manager.update_state(str(payload_path), merge=True)

                out = json.loads(Path("data/literature_index.json").read_text(encoding="utf-8"))
                self.assertEqual(len(out), 3)
                by_id = {x["global_id"]: x for x in out}
                self.assertEqual(by_id[1]["title"], "A2")
                self.assertEqual(by_id[2]["title"], "B")
                self.assertIn(3, by_id)
            finally:
                os.chdir(cwd)

    def test_load_minimal_includes_section_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                os.makedirs("drafts", exist_ok=True)
                Path("data/literature_index.json").write_text(
                    json.dumps([{"global_id": 1, "related_sections": ["intro"], "title": "A"}]),
                    encoding="utf-8",
                )
                Path("data/synthesis_matrix.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "section_id": "intro"},
                            {"global_id": 1, "section_id": "methods"},
                        ]
                    ),
                    encoding="utf-8",
                )
                Path("progress.json").write_text(json.dumps({"current_stage": "drafting"}), encoding="utf-8")
                Path("drafts/01_intro.md").write_text("intro draft", encoding="utf-8")

                buf = io.StringIO()
                with redirect_stdout(buf):
                    state_manager.load_state(section="intro", minimal=True)
                data = json.loads(buf.getvalue())

                self.assertEqual(sorted(data.keys()), ["literature_index", "progress", "section_draft", "synthesis_matrix"])
                self.assertEqual(data["section_draft"]["file"], "drafts/01_intro.md")
                self.assertEqual(data["section_draft"]["content"], "intro draft")
                self.assertEqual(data["synthesis_matrix"], [{"global_id": 1, "section_id": "intro"}])
            finally:
                os.chdir(cwd)

    def test_update_merge_matrix_keeps_same_global_id_for_multiple_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                Path("data/synthesis_matrix.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "section_id": "intro", "key_finding": "A"},
                            {"global_id": 1, "section_id": "methods", "key_finding": "B"},
                        ]
                    ),
                    encoding="utf-8",
                )
                payload_path = Path("payload.json")
                payload_path.write_text(
                    json.dumps(
                        {
                            "synthesis_matrix": [
                                {"global_id": 1, "section_id": "intro", "limitation": "L1"},
                            ]
                        }
                    ),
                    encoding="utf-8",
                )

                state_manager.update_state(str(payload_path), merge=True)
                out = json.loads(Path("data/synthesis_matrix.json").read_text(encoding="utf-8"))
                self.assertEqual(len(out), 2)
                by_section = {r["section_id"]: r for r in out}
                self.assertEqual(by_section["intro"]["limitation"], "L1")
                self.assertEqual(by_section["methods"]["key_finding"], "B")
            finally:
                os.chdir(cwd)

    def test_load_minimal_matches_chinese_section_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                os.makedirs("drafts", exist_ok=True)
                Path("data/literature_index.json").write_text(
                    json.dumps([{"global_id": 1, "related_sections": ["结果讨论"], "title": "A"}]),
                    encoding="utf-8",
                )
                Path("data/synthesis_matrix.json").write_text(
                    json.dumps([{"global_id": 1, "section_id": "结果讨论"}]),
                    encoding="utf-8",
                )
                Path("drafts/03_结果讨论.md").write_text("中文章节草稿", encoding="utf-8")

                buf = io.StringIO()
                with redirect_stdout(buf):
                    state_manager.load_state(section="结果讨论", minimal=True)
                data = json.loads(buf.getvalue())
                self.assertEqual(data["section_draft"]["file"], "drafts/03_结果讨论.md")
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
