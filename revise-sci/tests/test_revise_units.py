import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location("revise_units", SCRIPTS_DIR / "revise_units.py")
revise_units = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(revise_units)


class ReviseUnitsTests(unittest.TestCase):
    def test_translate_reason_to_en_handles_split_paper_search_requirement(self):
        reason = "当前材料未提供已确认的新文献信息；如需补充检索，必须仅使用 paper-search。"
        translated = revise_units.translate_reason_to_en(reason)
        self.assertEqual(
            translated,
            "The current materials do not provide confirmed new references; if additional retrieval is needed, only paper-search may be used.",
        )
        self.assertNotIn("Author confirmation is still required for this item.", translated)


if __name__ == "__main__":
    unittest.main()
