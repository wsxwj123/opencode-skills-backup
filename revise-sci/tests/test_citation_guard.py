import json
import tempfile
import unittest
from pathlib import Path

from helpers import run_script


class CitationGuardTests(unittest.TestCase):
    def test_citation_guard_accepts_double_verified_paper_search_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            project_root.mkdir()
            raw = project_root / "paper_search_results.json"
            raw.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "comment_id": "R1-Major-01",
                                "confirmed": True,
                                "formatted_citation_text": "(Smith et al., 2023)",
                                "citations": [
                                    {
                                        "title": "Quercetin in cardiovascular models",
                                        "pmid": "123456",
                                        "source_provider": "paper-search",
                                        "source_id": "PMID:123456",
                                        "pubmed_title": "Quercetin in cardiovascular models",
                                        "authors": ["Smith J", "Lee K"],
                                        "journal": "Cardiovasc Res",
                                        "year": 2023,
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = run_script(
                "citation_guard.py",
                [
                    "--paper-search-results",
                    str(raw),
                    "--project-root",
                    str(project_root),
                    "--offline",
                ],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            validated = json.loads((project_root / "paper_search_validated.json").read_text(encoding="utf-8"))
            self.assertTrue(validated["results"][0]["guard_verified"])
            self.assertIn("Quercetin in cardiovascular models", validated["results"][0]["citations"][0]["reference_entry"])

    def test_citation_guard_rejects_entry_without_secondary_verification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            project_root.mkdir()
            raw = project_root / "paper_search_results.json"
            raw.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "comment_id": "R1-Major-01",
                                "confirmed": True,
                                "formatted_citation_text": "(Smith et al., 2023)",
                                "citations": [
                                    {
                                        "title": "Quercetin in cardiovascular models",
                                        "pmid": "123456",
                                        "source_provider": "paper-search",
                                        "source_id": "PMID:123456",
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = run_script(
                "citation_guard.py",
                [
                    "--paper-search-results",
                    str(raw),
                    "--project-root",
                    str(project_root),
                    "--offline",
                ],
                cwd=root,
            )
            self.assertNotEqual(result.returncode, 0)
            report = json.loads((project_root / "paper_search_guard_report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["summary"]["all_rows_guard_verified"])


if __name__ == "__main__":
    unittest.main()
