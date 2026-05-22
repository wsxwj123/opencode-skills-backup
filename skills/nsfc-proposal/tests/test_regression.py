#!/usr/bin/env python3
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import citation_validator  # noqa: E402
import state_manager  # noqa: E402


class CitationRegressionTests(unittest.TestCase):
    def test_normalize_mcp_cache_sets_schema(self) -> None:
        raw = {"entries": [{"doi": "10.1000/xyz123", "title": "A"}]}
        norm = citation_validator._normalize_mcp_cache(raw)
        self.assertEqual(norm["metadata"]["schema_version"], citation_validator.CACHE_SCHEMA_VERSION)
        self.assertEqual(len(norm["entries"]), 1)

    def test_failure_levels_split_hard_soft(self) -> None:
        entry = {
            "ref_number": 1,
            "title": "",
            "doi": "",
            "pmid": "",
            "used_in_sections": ["P1_立项依据"],
            "key_finding": "",
        }
        out = citation_validator.validate_entry(entry, p1_text="", online_check=False, mcp_index={})
        details = out["verification_details"]
        self.assertIn("identifier_missing", details["hard_fail_reasons"])
        self.assertIn("title_missing", details["soft_fail_reasons"])
        self.assertFalse(out["verified"])

    def test_verify_all_sets_mcp_schema_metadata(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        idx = {
            "metadata": {},
            "entries": [
                {
                    "ref_number": 1,
                    "title": "Test Title for Matching",
                    "doi": "10.1000/test-001",
                    "pmid": "12345678",
                    "used_in_sections": ["P1_立项依据"],
                    "key_finding": "关键发现",
                }
            ],
        }
        mcp_index = {
            "doi:10.1000/test-001": {
                "title": "Test Title for Matching",
                "doi": "10.1000/test-001",
                "pmid": "12345678",
                "verified_at": now,
            }
        }
        out, stats, _queue = citation_validator.verify_all(
            idx,
            p1_text="这里引用[1]说明关键发现。",
            online_check=False,
            mcp_index=mcp_index,
            require_mcp=True,
            mcp_schema_version="1.0",
        )
        self.assertEqual(out["metadata"]["mcp_cache_schema_version"], "1.0")
        self.assertIn("hard_fail_entries", stats)
        self.assertIn("soft_fail_entries", stats)

    def test_matrix_check_pass(self) -> None:
        index = {
            "entries": [
                {"ref_number": 1, "used_in_sections": ["P1_立项依据"]},
                {"ref_number": 2, "used_in_sections": ["P1_立项依据"]},
            ]
        }
        m = citation_validator.matrix_check("text [1] and [2]", index, "refs [1]\nrefs [2]")
        self.assertTrue(m["ok"])


class StateManagerRegressionTests(unittest.TestCase):
    def test_sync_semantic_ok_strict(self) -> None:
        semantic = {
            "strict_mode": True,
            "cm_has_error": False,
            "has_context_blocks": True,
            "has_history": True,
            "p1_verified": True,
        }
        self.assertTrue(state_manager._sync_semantic_ok(semantic))


if __name__ == "__main__":
    unittest.main()
