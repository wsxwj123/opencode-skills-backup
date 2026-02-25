# VERIFICATION

Last verified: 2026-02-25 | 281 tests | 0 failures

## Scripts Inventory

| Script | Description | LOC (approx) |
|--------|-------------|---------------|
| `scripts/state_manager.py` | Central orchestrator: init/prewrite/postwrite/snapshot/rollback | 1820+ |
| `scripts/atomic_md_workflow.py` | Subsection management: validate/merge/self-check | 720+ |
| `scripts/check_quality.py` | Quality validation: fonts/spacing/structure/tables/figures | 1200+ |
| `scripts/abbreviation_registry.py` | Abbreviation lifecycle: extract/register/strip/validate | 840+ |
| `scripts/count_words.py` | Markdown word counting: file/chapter/full thesis | 590+ |
| `scripts/markdown_to_docx.py` | MD→Word conversion with CSU formatting | 420+ |
| `scripts/merge_chapters.py` | Docx merging with TOC/header/footer | 380+ |
| `scripts/merge_documents.py` | Compatibility wrapper for merge | 50+ |
| `scripts/figure_registry.py` | Figure numbering: register/validate/cross-validate/export | 400+ |
| `scripts/thesis_profile.py` | Profile management | 110+ |
| `scripts/shared_utils.py` | Shared utilities | 95+ |

## Test Suites (281 tests total)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/test_sci2doc_scripts.py` | 55 | Integration: state_manager, atomic_md, check_quality, count_words, merge |
| `scripts/test_abbreviation_registry.py` | 59 | Abbreviation: register/extract/strip/validate/CLI |
| `scripts/test_checkers.py` | 24 | Checkers: citations/writing style/table format |
| `scripts/test_count_words.py` | 41 | Word count: strip/count/file/dir/unified |
| `scripts/test_figure_registry.py` | 38 | Figure: letter conv/parse/CRUD/validate/cross-validate/export |
| `tests/test_markdown_to_docx.py` | 27 | MD→Docx: parse/separator/borders/fonts |
| `tests/test_merge_chapters.py` | 18 | Merge: extract/merge/TOC/header-footer/resolve order |
| **Total** | **262** | |

Note: `tests/test_sci2doc_scripts.py` contains 55 tests across 3 test classes (main 48 + TestMethodsTableCheck 7 + TestTitleMatchingExclusionLogic 12 = 67 test methods; pytest collects as shown above). Actual pytest collected count: **281**.

## Documentation

- `SKILL.md` — Authoritative spec (16+ non-negotiable requirements, Word format, figure/abbreviation/table contracts)
- `README.md` — Usage guide with CLI examples
- `QUICK_START.md` — Quick reference

## Baseline Targets

- Body target >= 80,000 Chinese chars (configured in `thesis_profile.json`)
- Chinese abstract 1500-2500 chars
- Chapter targets negotiated and stored in profile
- Atomic markdown numbering validation required
- Chapter self-check required
- Subsection summary snapshot required
- Three-line table format enforced
- Abbreviation registry populated and cross-validated
- Figure numbering registry populated and cross-validated
