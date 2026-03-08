import json
import unittest

from helpers import TempProject, create_docx, run_script


class AtomizeManuscriptTests(unittest.TestCase):
    def setUp(self):
        self.project = TempProject()
        self.root = self.project.root
        self.project_root = self.root / "run"
        self.project_root.mkdir()

    def tearDown(self):
        self.project.cleanup()

    def test_manuscript_and_si_are_split_into_sections(self):
        manuscript = create_docx(
            self.root / "manuscript.docx",
            [
                ("heading1", "Introduction"),
                ("paragraph", "Paragraph one in introduction."),
                ("heading1", "Results"),
                ("paragraph", "Results paragraph with Figure 1."),
                ("paragraph", "Figure 1. Example caption."),
            ],
        )
        si = create_docx(
            self.root / "si.docx",
            [
                ("heading1", "Supplementary Methods"),
                ("paragraph", "Supplementary paragraph."),
            ],
        )
        result = run_script(
            "atomize_manuscript.py",
            [
                "--manuscript",
                str(manuscript),
                "--si",
                str(si),
                "--project-root",
                str(self.project_root),
            ],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        m_index = json.loads((self.project_root / "manuscript_section_index.json").read_text(encoding="utf-8"))
        s_index = json.loads((self.project_root / "si_section_index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(m_index["sections"]), 2)
        self.assertEqual(len(s_index["sections"]), 1)
        section_file = self.project_root / m_index["sections"][0]["file"]
        self.assertTrue(section_file.exists())
        self.assertIn("Introduction", section_file.read_text(encoding="utf-8"))
