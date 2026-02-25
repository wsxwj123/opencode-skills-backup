# VERIFICATION (Archived)

This verification record is archived. Historical thresholds in older versions are superseded.

## Active Verification Scope

Validation should be executed against current scripts and profile-driven rules:

- `scripts/state_manager.py`
- `scripts/atomic_md_workflow.py`
- `scripts/count_words.py`
- `scripts/check_quality.py`
- `scripts/abbreviation_registry.py`
- `scripts/shared_utils.py`

Test suites (177 tests total):

- `tests/test_sci2doc_scripts.py` (55 tests)
- `scripts/test_abbreviation_registry.py` (57 tests)
- `scripts/test_checkers.py` (24 tests)
- `scripts/test_count_words.py` (41 tests)

And current documentation:

- `/Users/wsxwj/.config/opencode/skills/sci2doc/SKILL.md`
- `/Users/wsxwj/.config/opencode/skills/sci2doc/README.md`
- `/Users/wsxwj/.config/opencode/skills/sci2doc/QUICK_START.md`

## Baseline Targets

- Body target >= 80,000 Chinese chars (configured in `thesis_profile.json`)
- Chinese abstract 1500-2500 chars
- Chapter targets negotiated and stored in profile
- Atomic markdown numbering validation required
- Chapter self-check required
- Subsection summary snapshot required
