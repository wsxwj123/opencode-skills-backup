import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import citation_guard  # noqa: E402


NOW = datetime(2026, 3, 7, tzinfo=timezone.utc)


def build_entry(**overrides):
    entry = {
        "title": "Nanoparticle delivery for liver cancer",
        "doi": "10.1000/test",
        "pmid": "",
        "source_provider": "paper-search",
        "source_id": "PMID:123456",
    }
    entry.update(overrides)
    return entry


class CitationGuardTests(unittest.TestCase):
    def test_main_report_exposes_provider_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_path = root / "literature_index.json"
            report_path = root / "citation_guard_report.json"
            manual_path = root / "manual_review_queue.json"
            log_path = root / "verification_run_log.json"
            index_path.write_text("[]", encoding="utf-8")

            argv = [
                "citation_guard.py",
                "--index",
                str(index_path),
                "--report",
                str(report_path),
                "--manual-review",
                str(manual_path),
                "--log",
                str(log_path),
                "--offline",
            ]

            with patch.object(sys, "argv", argv):
                exit_code = citation_guard.main()

            self.assertEqual(exit_code, 2)
            payload = citation_guard.load_json(report_path, {})
            self.assertTrue(payload["report"]["provider_policy"]["tavily_only_for_no_identifier"])

    def test_rejects_non_allowed_provider_family(self):
        entry = build_entry(source_provider="custom-search", source_id="custom:1")
        with patch.object(
            citation_guard,
            "_fetch_crossref_by_doi",
            return_value={"title": entry["title"], "doi": entry["doi"], "pmid": None, "retracted": False},
        ):
            checked = citation_guard.validate_entry(
                entry,
                online_check=True,
                mcp_index={},
                require_mcp=False,
                mcp_ttl_days=30,
                now_utc=NOW,
            )

        self.assertFalse(checked["verified"])
        self.assertIn("source_provider_not_allowed", checked["verification_details"]["failure_reasons"])

    def test_rejects_tavily_entries_with_identifier(self):
        entry = build_entry(source_provider="tavily-search", source_id="tv:1")
        with patch.object(
            citation_guard,
            "_fetch_crossref_by_doi",
            return_value={"title": entry["title"], "doi": entry["doi"], "pmid": None, "retracted": False},
        ):
            checked = citation_guard.validate_entry(
                entry,
                online_check=True,
                mcp_index={},
                require_mcp=False,
                mcp_ttl_days=30,
                now_utc=NOW,
            )

        self.assertFalse(checked["verified"])
        self.assertIn("tavily_not_for_identifier_entries", checked["verification_details"]["failure_reasons"])

    def test_tavily_without_identifier_requires_manual_review(self):
        entry = build_entry(
            doi="",
            pmid="",
            source_provider="tavily-search",
            source_id="tv:2",
            tavily_title="Nanoparticle delivery for liver cancer",
        )
        checked = citation_guard.validate_entry(
            entry,
            online_check=False,
            mcp_index={},
            require_mcp=False,
            mcp_ttl_days=30,
            now_utc=NOW,
        )

        self.assertFalse(checked["verified"])
        self.assertTrue(checked["needs_manual_review"])
        self.assertTrue(checked["verification_details"]["sources"]["tavily_no_identifier"])

    def test_bidirectional_failure_forces_manual_confirmation(self):
        entry = build_entry(pmid="123456")
        with patch.object(
            citation_guard,
            "_fetch_crossref_by_doi",
            return_value={"title": entry["title"], "doi": entry["doi"], "pmid": None, "retracted": False},
        ), patch.object(
            citation_guard,
            "_fetch_pubmed_by_pmid",
            return_value={"title": entry["title"], "doi": "10.1000/other", "pmid": entry["pmid"], "retracted": False},
        ):
            checked = citation_guard.validate_entry(
                entry,
                online_check=True,
                mcp_index={},
                require_mcp=False,
                mcp_ttl_days=30,
                now_utc=NOW,
            )

        self.assertFalse(checked["verified"])
        self.assertTrue(checked["needs_manual_review"])
        self.assertTrue(checked["verification_details"]["bidirectional_verification_failed"])
        self.assertIn(
            "manual_confirmation_required_bidirectional_failure",
            checked["verification_details"]["failure_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
