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

    def test_reindex_by_section_reorders_and_remaps_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                Path("storyline.md").write_text(
                    "# Outline\n\n## Intro\n## Methods\n",
                    encoding="utf-8",
                )
                Path("data/literature_index.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "title": "M1", "related_sections": ["Methods"]},
                            {"global_id": 2, "title": "I1", "related_sections": ["Intro"]},
                            {"global_id": 3, "title": "U1"},
                        ]
                    ),
                    encoding="utf-8",
                )
                Path("data/synthesis_matrix.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "section_id": "Methods"},
                            {"global_id": 2, "section_id": "Intro"},
                            {"global_id": 3, "section_id": "unassigned"},
                        ]
                    ),
                    encoding="utf-8",
                )

                state_manager.reindex_literature_by_section(
                    storyline_path="storyline.md",
                    index_path="data/literature_index.json",
                    matrix_path="data/synthesis_matrix.json",
                )

                idx = json.loads(Path("data/literature_index.json").read_text(encoding="utf-8"))
                self.assertEqual([x["title"] for x in idx], ["I1", "M1", "U1"])
                self.assertEqual([x["global_id"] for x in idx], [1, 2, 3])

                matrix = json.loads(Path("data/synthesis_matrix.json").read_text(encoding="utf-8"))
                by_section = {r["section_id"]: r["global_id"] for r in matrix}
                self.assertEqual(by_section["Intro"], 1)
                self.assertEqual(by_section["Methods"], 2)
            finally:
                os.chdir(cwd)

    def test_reindex_by_section_remaps_draft_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                os.makedirs("drafts", exist_ok=True)
                Path("storyline.md").write_text("# Outline\n\n## Intro\n## Methods\n", encoding="utf-8")
                Path("data/literature_index.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "title": "M1", "related_sections": ["Methods"]},
                            {"global_id": 2, "title": "I1", "related_sections": ["Intro"]},
                        ]
                    ),
                    encoding="utf-8",
                )
                Path("data/synthesis_matrix.json").write_text(
                    json.dumps([{"global_id": 1, "section_id": "Methods"}, {"global_id": 2, "section_id": "Intro"}]),
                    encoding="utf-8",
                )
                Path("drafts/01_intro.md").write_text("Intro uses [2]. Methods later [1].", encoding="utf-8")

                state_manager.reindex_literature_by_section(
                    storyline_path="storyline.md",
                    index_path="data/literature_index.json",
                    matrix_path="data/synthesis_matrix.json",
                )

                text = Path("drafts/01_intro.md").read_text(encoding="utf-8")
                self.assertEqual(text, "Intro uses [1]. Methods later [2].")
            finally:
                os.chdir(cwd)

    def test_reindex_by_section_dedup_uses_matrix_order_and_rewrites_ranges(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                os.makedirs("drafts", exist_ok=True)
                Path("storyline.json").write_text(
                    json.dumps({"sections": [{"section_id": "Intro"}, {"section_id": "Methods"}]}),
                    encoding="utf-8",
                )
                Path("data/literature_index.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 1, "title": "Dup A", "doi": "10.1/dup", "related_sections": ["Methods"]},
                            {"global_id": 2, "title": "Unique B", "doi": "10.1/b", "related_sections": ["Intro"]},
                            {"global_id": 3, "title": "Dup A newer", "doi": "10.1/dup", "related_sections": ["Intro"]},
                        ]
                    ),
                    encoding="utf-8",
                )
                Path("data/literature_matrix.json").write_text(
                    json.dumps(
                        [
                            {"global_id": 3, "section_id": "Intro"},
                            {"global_id": 2, "section_id": "Intro"},
                            {"global_id": 1, "section_id": "Methods"},
                        ]
                    ),
                    encoding="utf-8",
                )
                Path("drafts/01_intro.md").write_text("Citations [3-2,1].", encoding="utf-8")

                state_manager.reindex_literature_by_section(
                    storyline_path="storyline.json",
                    index_path="data/literature_index.json",
                    matrix_path="data/literature_matrix.json",
                    sync_apply=True,
                )

                idx = json.loads(Path("data/literature_index.json").read_text(encoding="utf-8"))
                self.assertEqual(len(idx), 2)
                self.assertEqual([x["global_id"] for x in idx], [1, 2])
                self.assertEqual(idx[0]["doi"], "10.1/dup")
                self.assertEqual(idx[1]["doi"], "10.1/b")

                matrix = json.loads(Path("data/literature_matrix.json").read_text(encoding="utf-8"))
                self.assertEqual([x["global_id"] for x in matrix], [1, 2, 1])

                text = Path("drafts/01_intro.md").read_text(encoding="utf-8")
                self.assertEqual(text, "Citations [1-2].")
            finally:
                os.chdir(cwd)

    def test_reindex_sync_apply_blocks_when_matrix_has_unknown_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                Path("storyline.md").write_text("# Outline\n\n## Intro\n", encoding="utf-8")
                index_path = Path("data/literature_index.json")
                original_index = [{"global_id": 1, "title": "A", "related_sections": ["Intro"]}]
                index_path.write_text(json.dumps(original_index), encoding="utf-8")
                Path("data/synthesis_matrix.json").write_text(
                    json.dumps([{"global_id": 99, "section_id": "Intro"}]),
                    encoding="utf-8",
                )

                with self.assertRaises(SystemExit) as cm:
                    state_manager.reindex_literature_by_section(
                        storyline_path="storyline.md",
                        index_path="data/literature_index.json",
                        matrix_path="data/synthesis_matrix.json",
                        sync_apply=True,
                    )
                self.assertEqual(cm.exception.code, 2)

                idx_after = json.loads(index_path.read_text(encoding="utf-8"))
                self.assertEqual(idx_after, original_index)
            finally:
                os.chdir(cwd)

    def test_reindex_migrates_legacy_matrix_to_canonical_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                os.makedirs("data", exist_ok=True)
                Path("storyline.md").write_text("# Outline\n\n## Intro\n", encoding="utf-8")
                Path("data/literature_index.json").write_text(
                    json.dumps([{"global_id": 1, "title": "A", "related_sections": ["Intro"]}]),
                    encoding="utf-8",
                )
                Path("data/literature_matrix.json").write_text(
                    json.dumps([{"global_id": 1, "section_id": "Intro"}]),
                    encoding="utf-8",
                )

                state_manager.reindex_literature_by_section(
                    storyline_path="storyline.md",
                    index_path="data/literature_index.json",
                    matrix_path=None,
                    sync_apply=True,
                )

                self.assertTrue(Path("data/synthesis_matrix.json").exists())
                matrix = json.loads(Path("data/synthesis_matrix.json").read_text(encoding="utf-8"))
                self.assertEqual(matrix, [{"global_id": 1, "section_id": "Intro"}])
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
