---
name: revise-sci
description: Use when revising a scientific manuscript from reviewer comments, manuscript docx files, SI, and attachments, especially when the user needs a point-by-point Response to Reviewers plus a revised manuscript in markdown and Word.
---

# Revise-Sci

## Overview
Use this skill to convert reviewer comments, the original manuscript, SI, and attachments into two formal deliverables: a revised manuscript and a structured `Response to Reviewers`, both in Markdown and Word.

The workflow is script-gated. Do not skip steps. Do not fabricate experiments, data, statistics, or references.
The comment parser supports both atomic `comment-unit` HTML and reviewer-simulator style report HTML with critique lists.
The manuscript atomizer also recognizes numbered section headings such as `1`, `1.1`, and `2.3.4` even when the source Word paragraph style is not a formal heading style.

## Required Inputs
- `comments_path`
- `manuscript_docx_path`
- `project_root`
- `output_md_path`
- `output_docx_path`

Optional but supported:
- `si_docx_path`
- `attachments_dir_path`
- `reference_docx_path`
- `paper_search_results_path`
- `references_source_path`

## Output Contract
Always produce:
- `response_to_reviewers.md`
- `response_to_reviewers.docx`
- revised manuscript markdown at `output_md_path`
- revised manuscript Word at `output_docx_path`
- `precheck_report.md`
- `issue_matrix.md`
- `manuscript_edit_plan.md`
- `final_consistency_report.md`
- `data/literature_index.json`
- `data/revision_claims.json`
- `data/synthesis_matrix.json`
- `data/synthesis_matrix_audit.json`
- `data/reference_registry.json`
- `data/reference_coverage_audit.json`

## Pipeline
Run the scripts in this exact order:

```bash
python scripts/preflight.py ...
python scripts/atomize_comments.py ...
python scripts/atomize_manuscript.py ...
python scripts/build_issue_matrix.py ...
python scripts/citation_guard.py ...   # if paper_search_results_path is provided
python scripts/revise_units.py ...
python scripts/build_literature_index.py ...
python scripts/matrix_manager.py bootstrap ...
python scripts/matrix_manager.py audit ...
python scripts/merge_manuscript.py ...
python scripts/reference_sync.py ...
python scripts/build_reference_registry.py ...
python scripts/export_docx.py ...
python scripts/final_consistency_report.py ...
python scripts/strict_gate.py ...
```

Or use the single entrypoint:

```bash
python scripts/run_pipeline.py --comments <comments_path> --manuscript <manuscript_docx_path> --project-root <project_root> --output-md <output_md_path> --output-docx <output_docx_path> [--paper-search-results <paper_search_results_path>] [--resume] [--resume-from <step>] [--force-rebuild]
```

## Response Format
`response_to_reviewers` must use this hierarchy:
- `# 回复审稿人的邮件`
- `# Reviewer #N`
- `## Major / Minor`
- `### Comment k`

Each comment must contain:
1. `审稿意见与中文理解`
2. `Response to Reviewer（中英对照）`
3. `可能需要修改的正文/附件内容（中英对照）`
4. `修改说明（中文）`
5. `Evidence Attachments`

## Rules
- Missing information must be written as `Not provided by user` or `需作者确认`.
- If a reviewer asks for new literature, only `paper-search` is allowed as the external provider family.
- `paper_search_results_path` may be used to ingest confirmed paper-search results into citation-oriented comment handling.
- `paper_search_results_path` is not trusted directly. It must first pass `citation_guard.py`, which performs dual verification using provider trace + identifier/title consistency evidence before the citations are allowed to auto-complete a comment.
- `build_literature_index.py` must convert validated citation support into review-writing style canonical artifacts: `data/literature_index.json` and `data/revision_claims.json`.
- `matrix_manager.py` must derive `data/synthesis_matrix.json` from the canonical literature index and emit `data/synthesis_matrix_audit.json` before delivery.
- `build_reference_registry.py` must extract the final manuscript reference list into canonical `data/reference_registry.json` and audit body-to-reference coverage into `data/reference_coverage_audit.json`.
- `build_reference_registry.py` may import a fallback reference seed from `references_source_path` when the manuscript reference list is empty or absent.
- If a manuscript already has a partial numeric `References` section, `build_reference_registry.py` should try to merge missing numbered entries from the detected legacy reference source instead of failing immediately.
- If unresolved reference gaps still remain after registry rebuild, `build_reference_registry.py` must emit `reference_recovery_request.md` so the author knows exactly which source formats to provide next.
- If no original or legacy reference source is available, the workflow must first ask the user whether to start a new literature-search-and-fill cycle; default state is `reference_search_decision=ask`, not silent auto-search.
- If the user approves new reference search, the search-and-fill path must follow the `review-writing` discipline: `paper-search` retrieval only, immediate `citation_guard.py` after each import batch, update canonical `data/literature_index.json`, then refresh `data/synthesis_matrix.json` / `data/synthesis_matrix_audit.json` before any new references can enter the manuscript.
- If `reference_search_decision=approved` and reference gaps still exist, the skill must generate `reference_search_manifest.json` and `reference_search_task.md` so the approved search cycle is executable and auditable rather than implicit.
- The approved search cycle should also emit `reference_search_strategy.json` and `reference_search_status.json` so search scope, provider policy, round model, and step status remain explicit and machine-checkable.
- The approved search cycle should also emit `reference_search_rounds.json`, containing concrete query batches for Round 1 / Round 2 / Round 3 under `review-writing` governance.
- The approved search cycle must explicitly declare `workflow=review-writing`, `allowed_provider_families=["paper-search"]`, `forbidden_provider_families` containing `websearch`, and `verification_policy.dual_verification_required=true`.
- The approved search cycle must keep a three-round structure in both `reference_search_manifest.json` and `reference_search_strategy.json`, and must record `citation_guard.py` as the mandatory verification command.
- `build_reference_registry.py` should audit both numeric citations and author-year citations; unresolved gaps in either style must block delivery.
- Confirmed citation support must include an explicit anchor such as `target_section_heading`, `target_paragraph_index`, or `target_text`; otherwise the item stays in `needs_author_confirmation`.
- If current materials are insufficient, keep the item in `needs_author_confirmation` instead of inventing a resolution.
- Treat `completed` as a narrow state: only conservative text-only clarification or limitation edits with reliable paragraph localization may be auto-completed.
- If paragraph localization is ambiguous and multiple candidates score similarly, the item must fall back to `needs_author_confirmation` instead of selecting a paragraph aggressively.
- If a comment contains an explicit structured section hint such as `Section 4.2` or `4.2 节` but that hint cannot be matched to an existing section, the workflow must not fall back to lexical matching and must keep the item in `needs_author_confirmation`.
- For Chinese-source reviewer comments, keep the original Chinese comment as the authoritative source block and render a separate English working summary instead of mislabeled bilingual fields.
- Citation-only comments may be auto-completed only when confirmed `paper-search` results and formatted citation text are explicitly provided.
- Citation-only comments may be auto-completed only when the row is `confirmed`, the citation guard marks it `guard_verified=true`, and the target anchor is explicit.
- After manuscript merge, `reference_sync.py` must append or update the `References/参考文献` section using canonical `data/literature_index.json` and emit `reference_sync_report.json`.
- When `author_confirmation_reason` is rendered into English, the translated reason must remain fully English with no leftover Chinese fragments.
- For substantive requests such as new mechanism explanations, new evidence, new figures, or unresolved section matches, stop at `needs_author_confirmation`.
- `strict_gate.py` must verify comment coverage, response/manuscript/edit-plan consistency, atomic location completeness, provider-family policy, and per-comment evidence blocks before delivery.
- `strict_gate.py` must also verify that every auto-completed citation comment is covered by `reference_sync_report.json`; otherwise delivery fails.
- `strict_gate.py` must also verify that every auto-completed citation comment is present in both `data/literature_index.json` and `data/synthesis_matrix.json`, and that `data/synthesis_matrix_audit.json` reports no unresolved matrix gaps.
- `strict_gate.py` must fail delivery when `data/reference_coverage_audit.json` reports unresolved numeric citation gaps, even if the comment-level workflow itself completed.
- `strict_gate.py` must parse `response_to_reviewers.docx` and verify that comment headings, response-section headings, and evidence-section headings are present for every comment block.
- `strict_gate.py` must also verify that `reference_search_manifest.json`, `reference_search_strategy.json`, and `reference_search_status.json` are internally consistent with actual approved-search artifacts such as `paper_search_validated.json`, `paper_search_guard_report.json`, `data/literature_index.json`, `data/synthesis_matrix_audit.json`, and `reference_sync_report.json`.
- `references_source_path` is optional. If not provided explicitly, the pipeline may auto-detect likely sources such as a same-title sibling manuscript docx with a populated `References` block, `<comments_dir>/data/literature_index.json`, attachment files named like `reference*`/`bibliography*`, or project-local seed files.
- `references_source_path` auto-discovery should also inspect nearby versioned manuscript docx files inside shallow subdirectories of the manuscript folder when they share the same title and contain a usable `References` block.
- `references_source_path` may also be a `.ris` file exported from a reference manager.
- Keep `Evidence Attachments` in every comment block, even when no image or table is available.
- `--resume` skips already-materialized upstream artifacts so a rerun does not silently overwrite previously curated units.
- `--resume` also checks stored input fingerprints; if comments/manuscript/SI/attachments/reference/paper-search inputs changed, the rerun fails fast instead of trusting stale artifacts.
- `--resume` must also fail fast when the stored skill signature differs from the current script tree signature.
- `--resume-from <step>` must clear the selected step and all downstream generated artifacts, then rebuild only from that step onward under the same verified input fingerprint.
- `--force-rebuild` clears generated project artifacts, including `data/` and citation intermediate files, and reruns the pipeline from scratch inside the same `project_root`.
- `--live-citation-verify` enables online title/identifier verification when `paper-search` results are provided; pipeline mode should be recorded in preflight output.
- `final_consistency_report.md` should list each `needs_author_confirmation` item with a blocker type and the exact stored reason.
- `final_consistency_report.md` should also summarize reference coverage status, including detected numeric citations, reference entry count, and missing reference numbers when present.
- `final_consistency_report.md` should also report whether `reference_search_required=true` and the current `reference_search_decision`.
- Word export should render common markdown emphasis and list markers as real Word formatting instead of leaving raw `**...**` and list prefixes in the document body.
- `response_to_reviewers.docx` should include a visible heading hierarchy plus a TOC field, centered header text, and footer page-number field so the exported package is review-ready rather than plain-text only.
- Markdown pipe tables in manuscript or response markdown should be rendered as actual Word tables rather than plain paragraphs.
- Response block labels such as `Text / Image / Table` should be rendered with a dedicated Word paragraph style so exported reviewer-response documents keep a consistent block structure.
- If `reference_search_decision=approved` and `--auto-run-reference-search` is enabled, the pipeline should invoke a local runner hook via `execute_reference_search.py`; this runner must still obey `review-writing` governance and may only emit `paper-search` rows.
- If approved auto-run is requested but no local runner is configured, the pipeline must fail explicitly and write `reference_search_execution_request.md` instead of pretending that search has already been executed.
- The local runner contract must remain machine-checkable: `--rounds-json <path> --output <path> --project-root <path>`, with output saved to `project_root/paper_search_results.json`.
- Approved search auto-execution must rerun `citation_guard.py`, `revise_units.py`, literature-index/matrix steps, `reference_sync.py`, and `build_reference_registry.py` before export and gate.
- If no explicit local runner is provided but `opencode` is available, the workflow may fall back to an internal `opencode run` driver that still writes the same `paper_search_results.json` schema under `review-writing` governance.
- The `opencode` fallback must write a preserved prompt file (`reference_search_opencode_prompt.md`) and an execution report (`reference_search_execution.json`) so the retrieval path remains auditable.
- `strict_gate.py` and `final_consistency_report.md` should surface `reference_search_execution.json` state instead of hiding the actual execution mode.
- Query hints for approved search should come not only from missing reference coverage but also from pending citation-oriented review comments that still point to `paper-search` as a required evidence source.
- Lexical paragraph localization should use structured fields plus low-signal-token filtering and heading-weighted scoring; if the best lexical candidate is still low-confidence, keep the item in `needs_author_confirmation`.
- Reviewer-response Word export should use dedicated body, reviewer-heading, label, and comment-heading styles, with improved spacing and Word-native table header shading, rather than leaving all blocks as generic paragraphs.
- Automatic manuscript rewriting must stay at the changed-fragment level. `revise_units.py` should replace only the targeted sentence, or append only the new limitation sentence, instead of rewriting the entire paragraph.
- A dedicated `polish` stage must run after `revise` and before literature/reference merge. This stage should consume only `revision_plan.raw_fragment`, never untouched original sentences.
- The polishing stage should follow `article-writing`, `review-writing`, and `humanizer-zh` constraints together: direct evidence-bounded wording, no invented claims, no new citations, no banned AI phrases, no decorative transitions, and no paragraph-wide rewrite unless the new content is itself a new paragraph.
- The polishing stage should emit `revision_polish_manifest.json`, `revision_polish_prompt.md`, and `revision_polish_execution.json` so the anti-AI prompt, driver mode, and candidate coverage remain auditable.
- `strict_gate.py` must verify that completed revised fragments with a non-empty `revision_plan.scope` have polish state, a valid `polish_driver_mode`, and no residual banned AI-style markers.
- The polishing prompt should be layered, not flat. It must include: role definition, non-negotiable edit/evidence/citation/length constraints, deep anti-AI rewriting protocol, and a JSON-only output contract.
- `revision_plan` should carry `locked_prefix`, `locked_suffix`, `evidence_boundary_note`, and `citation_strings` so the polishing step can preserve untouched context explicitly rather than infer it.
- The polishing output schema should include `edit_decision`, `meaning_changed`, `scope_respected`, `ai_style_flags_removed`, and `notes`.
- `strict_gate.py` must fail if a polished revision reports `meaning_changed=true`, `scope_respected=false`, or if reconstructed paragraph text no longer preserves the locked prefix/suffix context.
