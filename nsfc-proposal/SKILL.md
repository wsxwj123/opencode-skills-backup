---
name: nsfc-proposal
description: Use when drafting, restructuring, or polishing Chinese NSFC proposals (2026 template), especially when strict section-by-section gating, hypothesis-objective-content-problem consistency, literature verification via paper-search MCP, and anti-AI Chinese academic writing constraints are required.
---

# NSFC Proposal Skill

## Overview
This skill manages end-to-end NSFC proposal writing and polishing under the 2026 structure. It enforces section-level gates, cross-section consistency, literature verification, and restrained academic Chinese style.

Use two modes:
- Write Mode: build from zero in phased gates.
- Polish Mode: import an existing draft, diagnose first, then revise section by section.

## Mode Handshake Gate (Mandatory)
Before any drafting/revision action, the assistant must ask exactly one mode-selection question and wait for the user answer:
- `Write Mode` (from scratch)
- `Polish Mode` (revise existing draft)

Hard rules:
- If mode is not explicitly confirmed, do not run section writing, diagnosis, citation verification, or merge commands.
- First actionable response in this skill must be the mode-selection question when mode is missing.
- If the user already explicitly states `Write Mode` or `Polish Mode` in the opening message, do not ask again; proceed directly with the specified mode.
- After user confirms mode, record it in project state/profile and continue with that mode workflow only.

## Inputs Required
Collect before execution:
- Project basics: title, discipline code, project type, research attribute, duration, budget.
- Existing materials: draft files, prior work, platform/conditions, related projects.
- User constraints: word targets per section, preferred P2 sub-structure, H/O/RC/KSQ mapping count.

## Tooling Rules
Academic literature retrieval must use paper-search MCP tools:
- `paper-search_search_pubmed` (primary)
- `paper-search_search_semantic` (supplement)
- `paper-search_search_google_scholar` (coverage)
- `paper-search_search_biorxiv` / `paper-search_search_medrxiv` (recent preprints)

Runtime name mapping (for environments using MCP namespaced tools):
- `paper-search_search_pubmed` -> `mcp__paper-search__search_pubmed`
- `paper-search_search_semantic` -> `mcp__paper-search__search_semantic`
- `paper-search_search_google_scholar` -> `mcp__paper-search__search_google_scholar`
- `paper-search_search_biorxiv` -> `mcp__paper-search__search_biorxiv`
- `paper-search_search_medrxiv` -> `mcp__paper-search__search_medrxiv`

Do not use generic web search/fetch tools for citation evidence in proposal claims.

## Non-Conflict Canon (Authoritative)
Apply these resolutions when references conflict:
1. No-bullet narrative applies to proposal body sections only; diagnostics/review reports may use structured lists.
2. Interaction extras (reverse questioning, suggested follow-up questions, extended thinking) are optional by context, not mandatory on every response.
3. Merge order is fixed: references at the end of final merged manuscript.
4. V-01 consistency validation must not require nonexistent `mapped_to_h` fields on SQ nodes. Validate by traversing H and KSQ links from SQ references.
5. P2 should not include numbered literature markers; citation numbering is restricted to P1.

## Execution Workflow

### Write Mode
Follow phased gates in order:
1. Phase 0: initialize project profile, section targets, mapping cardinality.
2. Phase 1: write P1 with full citation pipeline and verification.
3. Phase 2: write P2 and enforce strict H/O/RC/KSQ one-to-one mapping.
4. Phase 3: write P3 with feasibility evidence linked to methods.
5. Phase 4: write P4 and compliance declarations.
6. Phase 5: budget narratives and traceability to methods.
7. Phase 6: Chinese/English abstracts generated last from full content.
8. Phase 7: global consistency + review + merge.

At each phase:
- snapshot
- sync required state files
- halt for user confirmation

### Polish Mode
1. Import draft and split into atomic section files by original heading hierarchy.
2. Generate strict review report first (`polish_review_report`).
3. Agree priority with user (rewrite vs polish vs keep).
4. Revise section by section following issue order:
   - academic design/hypothesis
   - consistency
   - writing style
   - format/length
5. Run global consistency repair and full review.
6. Merge final output.

## State and Artifacts
Maintain and sync after each section edit:
- `data/consistency_map.json`
- `data/literature_index.json`
- `context_memory.md`
- `project_state.json`
- `history_log.json`

Any missing sync blocks phase progression.


- Use dual-track verification for citations: provide MCP retrieval cache in `data/mcp_literature_cache.json` and run online validation without `--offline` whenever network is available. Final gate should enforce `--require-mcp`.

## Quality Gates
Block progression when any of the following fails:
- ERROR-level consistency rules.
- Unverified references in P1 citation set.
- Citation-index-reference matrix mismatch.
- Any D-grade in global review dimensions.
- More than 3 C-grade dimensions in global review.
- Page estimate beyond configured hard limit.

Use atomic gate command for final checks:
- `python scripts/state_manager.py --root . gate-check --sections-dir sections --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --mcp-cache data/mcp_literature_cache.json --mcp-ttl-days 30 --require-mcp`

Failure handling playbook:
- `failed_at=sync`: run `sync-all --auto-fix`, then re-run `gate-check`.
- `failed_at=citation`: repair index/cache, re-run `verify-all --require-mcp`, then `gate-check`.
- `failed_at=matrix`: run `matrix-check` and `reorder`, then `gate-check`.
- `failed_at=review`: fix D/C dimensions from review report, then `gate-check`.

## References
Load only what is needed:
- `references/00_设计方案_总览.md`
- `references/01_目录结构与配置.md`
- `references/02_核心机制.md`
- `references/03_写作规范与反AI.md`
- `references/04_文献管理.md`
- `references/05_Write_Mode流程.md`
- `references/06_Polish_Mode流程.md`
- `references/07_自审与评审模块.md`
- `references/08_脚本清单与合并规则.md`
- `references/09_交互规范与回复模板.md`

## Output Contract
Deliverables should include:
- section files under `sections/`
- updated state and data files
- review reports in `data/`
- merged manuscript in `output/` (md/docx if requested)

When reporting to user, state:
- what was changed
- which gate passed/failed
- what is blocked and exact unblock action

## Script Entry Points
Use scripts under `scripts/` from proposal project root:
- `python scripts/state_manager.py --root . init`
- `python scripts/state_manager.py --root . load --section P1 --minimal`
- `python scripts/state_manager.py --root . write-cycle --section P1 --token-budget 4000`
- `python scripts/state_manager.py --root . sync-all --auto-fix`
- `python scripts/state_manager.py --root . gate-check --sections-dir sections --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --mcp-cache data/mcp_literature_cache.json --mcp-ttl-days 30 --require-mcp`
- `python scripts/consistency_mapper.py --path data/consistency_map.json validate`
- `python scripts/consistency_mapper.py --path data/consistency_map.json validate-one V-01`
- `python scripts/citation_validator.py verify-all --index data/literature_index.json --p1 sections/P1_立项依据.md --mcp-cache data/mcp_literature_cache.json --mcp-ttl-days 30 --require-mcp --manual-review data/manual_review_queue.json --log data/verification_run_log.json`
- `python scripts/citation_validator.py verify-entry --index data/literature_index.json --p1 sections/P1_立项依据.md --ref-number 1 --mcp-cache data/mcp_literature_cache.json --require-mcp`
- `python scripts/citation_validator.py matrix-check --p1 sections/P1_立项依据.md --index data/literature_index.json --ref sections/REF_参考文献.md`
- `python scripts/humanizer_zh.py scan-all sections`
- `python scripts/diagnosis_engine.py full-review --sections-dir sections --consistency data/consistency_map.json --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --output data/diagnosis_report.json`
- `python scripts/diagnosis_engine.py polish-review --sections-dir sections --consistency data/consistency_map.json --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --json-output data/diagnosis_report.json --md-output data/polish_review_report.md`
- `python scripts/section_merger.py validate-order --sections-dir sections`
- `python scripts/section_merger.py merge --sections-dir sections --output output/申请书_合并.md`
- `python scripts/section_merger.py merge --sections-dir sections --only P1_立项依据.md,P2,REF_参考文献.md --output output/阶段稿_合并.md`
- `python scripts/word_counter.py summary sections`

These scripts are production-ready workflow utilities for iterative proposal drafting and polishing.


## Regression Tests
- `python3 -m unittest discover -s tests -p 'test_*.py'`
