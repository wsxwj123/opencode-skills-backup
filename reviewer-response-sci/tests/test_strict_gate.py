import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path('/Users/wsxwj/Desktop/opencode file/reviewer-response-sci/scripts/strict_gate.py')


class TestStrictGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'units').mkdir(parents=True, exist_ok=True)
        (self.root / 'manuscript_units').mkdir(parents=True, exist_ok=True)
        (self.root / 'si_units').mkdir(parents=True, exist_ok=True)

        m = {'unit_id': 'm-0001'}
        (self.root / 'manuscript_units' / '0001.json').write_text(json.dumps(m), encoding='utf-8')

        email = {
            'unit_id': 'u-000-email', 'order': 0, 'reviewer': 'all', 'section': 'email', 'comment_number': '0', 'title': 'mail',
            'source': {}, 'links': {'anchors': [], 'manuscript_unit_ids': [], 'si_unit_ids': []},
            'content': {'reviewer_comment_zh': '', 'reviewer_comment_en': '', 'response_en': '', 'revised_excerpt_en': '', 'notes_core_zh': [], 'notes_support_zh': [], 'evidence': {'text': [], 'images': [], 'table': {'columns': [], 'rows': []}}},
            'status': {'response_state': 'final', 'excerpt_state': 'missing', 'notes_state': 'final'}
        }
        u1 = {
            'unit_id': 'u-001', 'order': 1, 'reviewer': 'Reviewer #1', 'section': 'major', 'comment_number': '1', 'title': 't',
            'source': {}, 'links': {'anchors': ['Figure 1'], 'manuscript_unit_ids': ['m-0001'], 'si_unit_ids': []},
            'content': {'reviewer_comment_zh': 'a', 'reviewer_comment_en': 'b', 'response_en': 'c', 'revised_excerpt_en': 'd', 'notes_core_zh': ['e'], 'notes_support_zh': ['f'], 'evidence': {'text': ['x'], 'images': [{'src':'','alt':'','caption':''}], 'table': {'columns': ['c1'], 'rows': [['r1']]}}},
            'status': {'response_state': 'draft', 'excerpt_state': 'draft', 'notes_state': 'draft'}
        }
        (self.root / 'units' / '000_email.json').write_text(json.dumps(email), encoding='utf-8')
        (self.root / 'units' / '001.json').write_text(json.dumps(u1), encoding='utf-8')

        index = {'toc': {'reviewers': [{'sections': [{'items': [{'unit_id': 'u-001'}]}]}]}}
        (self.root / 'index.json').write_text(json.dumps(index), encoding='utf-8')
        state = {'counts': {'total_units': 2}}
        (self.root / 'project_state.json').write_text(json.dumps(state), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_pass(self):
        subprocess.run(['python3', str(SCRIPT), '--project-root', str(self.root), '--require-links'], check=True)


if __name__ == '__main__':
    unittest.main()
