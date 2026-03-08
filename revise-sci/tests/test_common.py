import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location("common", SCRIPTS_DIR / "common.py")
common = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(common)


class CommonTests(unittest.TestCase):
    def test_comment_nature_prioritizes_methodology_over_table_anchor_noise(self):
        text = (
            "稿件没有交代检索数据库、关键词、纳入排除标准，也没有说明证据等级差异。"
            "Table 2 未提供系统纳入逻辑。"
        )
        self.assertEqual(common.comment_nature(text), "需要实质性解释、结构重构或方法学澄清")


if __name__ == "__main__":
    unittest.main()
