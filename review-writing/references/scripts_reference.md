# Scripts Reference

All scripts are in `[project]/scripts/` (copied from skill directory during Phase 0 init).

## Script Overview

| Script | Purpose | Mode |
|--------|---------|------|
| `zotero_manager.py` | Zotero Web API: init, add, dedup, get-section, export BibTeX | Zotero |
| `state_manager.py` | Canonical dedup + reindex (Phase 2.5 None Mode only) | None |
| `citation_utils.py` | **Import-only library, no CLI.** Shared citation-token parser (`extract_citation_ids`, `parse_citation_group`) imported by `citation_guard.py`, `validate_citations.py`, `check_global_citation_sequence.py`, `export_bibtex.py`. Never invoke directly — `python3 scripts/citation_utils.py` will run and exit silently. | All |
| `export_bibtex.py` | BibTeX export from literature_index.json | None/EndNote |
| `matrix_manager.py` | Section-claim evidence matrix: bootstrap + focus | None |
| `word_counter.py` | Count words/chars in draft files | All |
| `validate_citations.py` | DOI/PMID online validation | All |
| `citation_guard.py` | Anti-hallucination guard | All |
| `check_global_citation_sequence.py` | Verify global [1..N] citation continuity | All |

## `state_manager.py` commands (None Mode — Phase 2.5 only)

```bash
# Canonical dedup + reindex literature by section order + remap draft citations:
python3 scripts/state_manager.py reindex \
  --storyline outline.md --index data/literature_index.json \
  --matrix data/synthesis_matrix.json
# Note: state.json is managed via inline Python in Phase 0.5/1/3, NOT via this script.
```

## `matrix_manager.py` commands (None Mode)

```bash
# Phase 2 Step 5b — bootstrap matrix after adding papers for a section:
python3 scripts/matrix_manager.py bootstrap \
  --index data/literature_index.json \
  --matrix data/synthesis_matrix.json \
  --section X.X --round 1

# Phase 3 Step 1 — load evidence context before writing a section:
python3 scripts/matrix_manager.py focus \
  --matrix data/synthesis_matrix.json \
  --section X.X
```

## `citation_guard.py` command

```bash
# Phase 2 (per-section, lightweight):
python3 scripts/citation_guard.py \
  --index data/literature_index.json \
  --log data/citation_guard_report.json

# Phase 4 (final delivery, full validation):
python3 scripts/citation_guard.py \
  --index data/literature_index.json \
  --log data/citation_guard_report.json \
  --write-back \
  --manual-review data/manual_review_queue.json
# --write-back   : persists verified:true/false back into literature_index.json
# --manual-review: dumps unverifiable entries to a JSON queue for human review
# --require-mcp  : hard-gate — blocks if any entry lacks MCP evidence (use only for top-tier journals)
# --offline      : skip online checks (fast mode, local index only)
```

## `word_counter.py` command

```bash
python3 scripts/word_counter.py --file drafts/section_01_01.md --language en
# --language cn: counts Chinese characters (CJK), goal 15,000–20,000 chars
# --language en: counts English words (whitespace split), goal 7,000–10,000 words
# Read language setting from outline.md and pass accordingly.
```

## `validate_citations.py` command (Phase 4 — pre-export consistency check)

```bash
python3 scripts/validate_citations.py \
  --drafts-dir drafts \
  --index-path data/literature_index.json \
  --live --live-used-only \
  --fail-on-orphan --retries 2
# --drafts-dir       : directory to scan for [N] citations (default: drafts)
# --index-path       : literature_index.json path (default: data/literature_index.json)
# --live             : enable online DOI/PMID verification (skip in offline mode)
# --live-used-only   : with --live, only validate gids actually cited in drafts
#                       (saves API calls — skip orphan entries)
# --timeout 8        : HTTP timeout per live check (default: 8s)
# --retries 2        : transient-error retry count (default: 2)
# --retry-backoff 0.6: base backoff seconds between retries (default: 0.6)
# --fail-on-orphan   : exit non-zero if any [N] in drafts has no matching index entry
# --fail-on-live     : exit non-zero if any live DOI/PMID check fails
# --fail-on-trace    : exit non-zero if source traceability gaps exist
# Difference from citation_guard.py: validate_citations cross-checks drafts ⟷ index;
# citation_guard validates the index itself (independent of drafts).
```

## `zotero_manager.py` command reference

| Command | Function |
|---------|---------|
| `--status --lib-id X --api-key Y` | Test connection, list libraries and existing collections |
| `--init --title "T" --outline outline.md --lib-id X --api-key Y` | Create root + subcollection tree from outline |
| `--add-batch --section "2.1" --papers tmp/papers_2_1.json --root-key ROOT_KEY --index data/literature_index.json --lib-id X --api-key Y` | Safe upsert (3 branches): ① paper already in Zotero (has zotero_key) → link to section collection only, gid unchanged; ② paper in local index but NOT yet in Zotero (no zotero_key, e.g. Polish Mode import) → create Zotero item using existing gid, back-fill zotero_key; ③ paper not in index at all → create Zotero item + new gid, append to local index. `--root-key` scopes all collection lookups to the current project's root collection, preventing cross-project contamination when multiple reviews share the same Zotero library. |
| `--dedup --scope ROOT_KEY --lib-id X --api-key Y` | **Repair only** — deduplicate within root collection scope; assigns gid:N; do NOT use in normal workflow (--add-batch already deduplicates at write time) |
| `--get-section "2.1" --lib-id X --api-key Y` | Return section paper list (gid, title, authors, year, abstract) |
| `--export-bibtex --output refs.bib --root-key ROOT_KEY --lib-id X --api-key Y` | Generate .bib with citation keys ref_N; `--root-key` scopes export to current project (without it, exports entire library) |
