# Article Writing Skill (v2.15.2)

## Purpose
This skill is for long-form academic manuscript writing with strict state consistency.
Primary goals:
- no memory loss across turns
- no token explosion during context loading
- stable citation/index consistency after each writing turn

## Canonical Workflow (Required)
Use `write-cycle` as the only entry point.

1. Pre-write load (strict by default):
```bash
python scripts/state_manager.py write-cycle --section results_3.1 --token-budget 6000 --tail-lines 80
```

2. If continuing an existing section draft:
```bash
python scripts/state_manager.py write-cycle --section results_3.1 --include-draft --token-budget 6000 --tail-lines 80
```

3. Finalize this turn:
```bash
python scripts/state_manager.py write-cycle --section results_3.1 --finalize --sync-literature --sync-apply --strict-references --summary "..."
```

4. Word count (default excludes References):
```bash
python scripts/state_manager.py word-count
python scripts/state_manager.py word-count --section results_3.1
```

5. Stats and rollback:
```bash
python scripts/state_manager.py stats
python scripts/state_manager.py rollback --target snapshot
python scripts/state_manager.py rollback --target literature_sync
```

6. Merge and export references:
```bash
python scripts/merge_manuscript.py --manuscript-dir manuscripts
python scripts/merge_manuscript.py --manuscript-dir manuscripts --skip-docx
python scripts/export_bibtex.py --index-file literature_index.json --output-file references.bib
```

## Safety Defaults
- `write-cycle` uses strict preflight by default.
- literature apply is blocked if `dedup_conflicts` exists.
- apply only proceeds if you explicitly pass `--allow-conflicts`.
- md rewrite is default; docx rewrite is opt-in with `--rewrite-docx`.

## Runtime Files and Why They Exist
- `.state/write_gate.json`: hard-gate state (prewrite/complete guard)
- `.state/lit_sync_preview.json`: latest dry-run preview payload
- `.state/reports/lit_sync_*.json`: persisted dry-run/apply/error reports
- `.state/load_cache.json`: incremental load cache to reduce repeated payload size

These are runtime artifacts, not manuscript content.

## Tests
Regression tests live in:
- `tests/test_state_manager.py`

Run:
```bash
python3 -m unittest discover -s tests -p 'test_*.py' -q
```

## Directory Intent
- `scripts/`: executable workflow logic
- `templates/`: initialization/reference templates
- `tests/`: regression coverage for state manager
- `manuscripts/` (in project workspace, not skill root): actual section drafts

## Version
- Current: `2.15.2`
