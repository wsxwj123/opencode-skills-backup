---
name: article-writing
description: >
This Skill is a structured manuscript collaboration system specifically engineered for researchers drafting high-impact SCI Articles. It shares the same atomic file management, citation verification, and state consistency infrastructure as the general SCI writing skill, while keeping article-oriented defaults for drug-delivery and biomedical manuscripts.
---


# Article Writing Skill (v2.16.4)

## Purpose
This skill is for long-form academic manuscript writing with strict state consistency.
Primary goals:
- no memory loss across turns
- no token explosion during context loading
- stable citation/index consistency after each writing turn
- article-oriented defaults with configurable field profiles

## Research Field Configuration System (v2.16.4)

This version uses the same configurable research field system as `general-sci-writing`, but defaults to the biomedical-domain `drug_delivery` profile for article-focused workflows. The default path is optimized for drug delivery manuscripts, including nanocarriers, engineered bacteria, exosomes, viral vectors, and related translational topics. Other field profiles remain available for switching during initialization.

### Available Fields

| Field ID | Name | Description |
|----------|------|-------------|
| `biomedical_pharma` | Biomedical & Pharmaceutical Research | 医药总配置，覆盖材料、药理、机制、临床等广义医药研究 |
| `default` | General Academic |适用于大多数学科 |
| `drug_delivery` | Drug Delivery System | 默认配置，适用于纳米载体、细菌递送、外泌体、病毒载体等 |
| `clinical_pharmacy_llm` | Clinical Pharmacy & LLM | 临床药学、AI交叉 |
| `computer_science` | Computer Science | 机器学习、系统等 |
| `quantitative_pharmacology` | Quantitative Pharmacology | PK/PD建模等 |

### Using Configuration Manager

```bash
# List all available fields
python scripts/config_manager.py list

# Load the default article profile
python scripts/config_manager.py load drug_delivery

# Validate a configuration
python scripts/config_manager.py validate drug_delivery

# Create a custom configuration
python scripts/config_manager.py create my_field "My Research Field"
```

### Custom Configuration

Users can add custom configurations in:
1. Project directory's `configs/` subdirectory
2. User directory `~/.article-writing/configs/`

Custom configurations have higher priority than built-in ones.

## Canonical Workflow (Required)
Use `write-cycle` as the only entry point.

Initialization rule:
- During `/init`, ask for the project save path and whether to keep the default biomedical-domain `drug_delivery` profile or switch to another field profile in the same message.
- If the user does not request a switch, initialize with `drug_delivery`.

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

## Citation Integrity Defaults
- `citation_guard.py` now enforces provider family allowlist: only `paper-search` and restricted `tavily` are accepted.
- `tavily` is only allowed for no-identifier reverse verification or abstract recovery fallback; Tavily entries carrying DOI/PMID are rejected.
- Any bidirectional verification failure (`title_mismatch`, DOI/PMID mismatch, id mismatch) forces `verified=false` and routes the entry to `manual_review_queue.json`.
- Entries without `source_provider` / `source_id`, or with `needs_manual_review=true`, must not be cited in manuscript text or emitted into the final references list.
- If `citation_guard.py` exits non-zero or report `ok=false`, writing must stop until `manual_review_queue.json` is resolved.

## Runtime Files and Why They Exist
- `.state/write_gate.json`: hard-gate state (prewrite/complete guard)
- `.state/lit_sync_preview.json`: latest dry-run preview payload
- `.state/reports/lit_sync_*.json`: persisted dry-run/apply/error reports
- `.state/load_cache.json`: incremental load cache to reduce repeated payload size

These are runtime artifacts, not manuscript content.

## Tests
Regression tests live in:
- `tests/test_state_manager.py`
- `tests/test_citation_guard.py`

Run:
```bash
python3 -m py_compile scripts/citation_guard.py scripts/state_manager.py
python3 -m unittest discover -s tests -p 'test_*.py' -q
```

## Directory Intent
- `scripts/`: executable workflow logic
- `templates/`: initialization/reference templates
- `configs/`: research field configurations
- `tests/`: regression coverage for state manager
- `manuscripts/` (in project workspace, not skill root): actual section drafts

## Version
- Current: `2.16.4`
