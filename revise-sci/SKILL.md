---
name: revise-sci
description: Use when revising a scientific manuscript from reviewer comments, manuscript docx files, SI, and attachments, especially when the user needs a point-by-point Response to Reviewers plus a revised manuscript in markdown and Word.
---

# Revise-Sci

## Overview
Use this skill to convert reviewer comments, the original manuscript, SI, and attachments into two formal deliverables: a revised manuscript and a structured `Response to Reviewers`, both in Markdown and Word.

The workflow is script-gated. Do not skip steps. Do not fabricate experiments, data, statistics, or references.

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

## Pipeline
Run the scripts in this exact order:

```bash
python scripts/preflight.py ...
python scripts/atomize_comments.py ...
python scripts/atomize_manuscript.py ...
python scripts/build_issue_matrix.py ...
python scripts/revise_units.py ...
python scripts/merge_manuscript.py ...
python scripts/export_docx.py ...
python scripts/final_consistency_report.py ...
python scripts/strict_gate.py ...
```

Or use the single entrypoint:

```bash
python scripts/run_pipeline.py --comments <comments_path> --manuscript <manuscript_docx_path> --project-root <project_root> --output-md <output_md_path> --output-docx <output_docx_path>
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
- If current materials are insufficient, keep the item in `needs_author_confirmation` instead of inventing a resolution.
- Keep `Evidence Attachments` in every comment block, even when no image or table is available.
