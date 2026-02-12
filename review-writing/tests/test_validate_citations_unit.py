import sys
import unittest
from pathlib import Path
from urllib import error
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import validate_citations  # noqa: E402


class ValidateCitationsUnitTests(unittest.TestCase):
    def test_filter_entries_by_used_ids(self):
        entries = [
            {"global_id": 1, "title": "A"},
            {"global_id": 2, "title": "B"},
            {"global_id": 3, "title": "C"},
        ]
        used_ids = {"1", "3"}
        out = validate_citations.filter_entries_by_used_ids(entries, used_ids)
        self.assertEqual([x["global_id"] for x in out], [1, 3])

    def test_check_with_retry_eventually_passes(self):
        calls = {"n": 0}

        def flaky(_identifier, timeout=8):
            calls["n"] += 1
            if calls["n"] < 2:
                raise error.URLError("temporary failure")
            return True, "ok"

        ok, reason, attempts = validate_citations._check_with_retry(
            "10.1000/test",
            flaky,
            timeout=1,
            retries=2,
            backoff=0.0,
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")
        self.assertEqual(attempts, 2)

    def test_check_with_retry_stops_on_non_transient(self):
        def non_transient(_identifier, timeout=8):
            return False, "DOI mismatch"

        with patch.object(validate_citations.time, "sleep", return_value=None):
            ok, reason, attempts = validate_citations._check_with_retry(
                "10.1000/test",
                non_transient,
                timeout=1,
                retries=3,
                backoff=0.0,
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "DOI mismatch")
        self.assertEqual(attempts, 1)


if __name__ == "__main__":
    unittest.main()
