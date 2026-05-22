import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path('/Users/wsxwj/Desktop/opencode file/reviewer-response-sci/scripts/consistency_check.py')


class TestConsistencyCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'units').mkdir(parents=True, exist_ok=True)
        unit = {
            'unit_id': 'u-001',
            'content': {
                'reviewer_comment_zh': '',
                'reviewer_comment_en': '',
                'response_en': 'safe response',
                'revised_excerpt_en': 'MPC-83 is used.',
                'notes_core_zh': ['ok'],
                'notes_support_zh': ['ok']
            }
        }
        (self.root / 'units' / '001.json').write_text(json.dumps(unit), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_pass(self):
        subprocess.run(['python3', str(SCRIPT), '--project-root', str(self.root), '--fail-on-conflict'], check=True)


if __name__ == '__main__':
    unittest.main()
