import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path('/Users/wsxwj/Desktop/opencode file/reviewer-response-sci/scripts/state_manager.py')


class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'units').mkdir(parents=True, exist_ok=True)
        unit = {
            'unit_id': 'u-001',
            'section': 'major',
            'reviewer': 'Reviewer #1',
            'comment_number': '1',
            'title': 't'
        }
        (self.root / 'units' / '001.json').write_text(json.dumps(unit), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_set_show(self):
        subprocess.run(['python3', str(SCRIPT), 'init', '--project-root', str(self.root)], check=True)
        subprocess.run(['python3', str(SCRIPT), 'set', '--project-root', str(self.root), '--unit-id', 'u-001', '--state', 'checked'], check=True)
        out = subprocess.check_output(['python3', str(SCRIPT), 'show', '--project-root', str(self.root), '--unit-id', 'u-001'], text=True)
        data = json.loads(out)
        self.assertEqual(data['u-001']['state'], 'checked')


if __name__ == '__main__':
    unittest.main()
