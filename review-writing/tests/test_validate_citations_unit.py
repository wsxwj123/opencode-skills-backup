import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
