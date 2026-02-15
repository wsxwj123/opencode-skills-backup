import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TagLiteratureSectionsTests(unittest.TestCase):
    def test_supports_storyline_json_and_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "storyline.json").write_text(
                json.dumps({"sections": [{"section_id": "Introduction"}, {"section_id": "Methods"}]}),
                encoding="utf-8",
            )
            (root / "data" / "literature_index.json").write_text(
                json.dumps(
                    [
                        {
                            "global_id": 1,
                            "doi": "10.1000/a",
                            "title": "An introduction to test systems",
                            "abstract": "overview and intro",
                        },
                        {
                            "global_id": 2,
                            "title": "Methods for test systems",
                            "abstract": "method details",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (root / "data" / "section_overrides.json").write_text(
                json.dumps(
                    {
                        "by_doi": {
                            "10.1000/a": {
                                "set": ["Methods"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            script = "/Users/wsxwj/.codex/skills/review-writing/scripts/tag_literature_sections.py"
            subprocess.run(
                [
                    "python3",
                    script,
                    "--storyline",
                    str(root / "storyline.json"),
                    "--index",
                    str(root / "data" / "literature_index.json"),
                    "--overrides",
                    str(root / "data" / "section_overrides.json"),
                ],
                check=True,
            )

            payload = json.loads((root / "data" / "literature_index.json").read_text(encoding="utf-8"))
            by_id = {x["global_id"]: x for x in payload}
            self.assertEqual(by_id[1]["related_sections"], ["Methods"])
            self.assertIn("Methods", by_id[2].get("related_sections", []))


if __name__ == "__main__":
    unittest.main()
