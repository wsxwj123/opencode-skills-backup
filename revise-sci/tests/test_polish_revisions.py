import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location("polish_revisions", SCRIPTS_DIR / "polish_revisions.py")
polish_revisions = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(polish_revisions)


class PolishRevisionsTests(unittest.TestCase):
    def test_build_polish_prompt_contains_anti_ai_constraints(self):
        unit = {
            "comment_id": "R1-Major-01",
            "editorial_intent": "clarify",
            "revision_plan": {
                "scope": "sentence_replace",
                "original_fragment": "They showed a protective effect in TAC-treated cells.",
                "raw_fragment": "In the present dataset, They showed a protective effect in TAC-treated cells.",
                "paragraph_before": "They showed a protective effect in TAC-treated cells.",
            },
            "atomic_location": {"section_heading": "Results", "paragraph_index": 7},
            "author_confirmation_reason": "",
        }
        prompt = polish_revisions.build_polish_prompt(Path("/tmp/revise-sci"), Path("/tmp/revise-sci/out.json"), [unit])
        self.assertIn("Do not rewrite untouched source text", prompt)
        self.assertIn("article-writing, review-writing, and humanizer-zh", prompt)
        self.assertIn("not only... but also", prompt)
        self.assertIn("OUTPUT_JSON_PATH=", prompt)

    def test_apply_polished_fragment_preserves_unmodified_sentences(self):
        plan = {
            "scope": "sentence_replace",
            "target_sentence_index": 1,
            "paragraph_before": "Sentence one. Raw changed sentence. Sentence three.",
        }
        polished = polish_revisions.apply_polished_fragment(plan, "Polished changed sentence.")
        self.assertEqual(polished, "Sentence one. Polished changed sentence. Sentence three.")

    def test_local_polish_removes_banned_ai_markers(self):
        cleaned = polish_revisions.polish_changed_text_locally("Moreover, this serves as a pivotal role in the realm of pulmonary repair.")
        self.assertNotIn("Moreover", cleaned)
        self.assertNotIn("serves as", cleaned)
        self.assertNotIn("pivotal role", cleaned)

    def test_run_polish_driver_short_circuits_when_no_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            driver_mode, payload, execution = polish_revisions.run_polish_driver(Path(tmpdir), [], "", "")
        self.assertEqual(driver_mode, "not-required")
        self.assertEqual(payload, {"results": []})
        self.assertEqual(execution["driver_mode"], "not-required")


if __name__ == "__main__":
    unittest.main()
