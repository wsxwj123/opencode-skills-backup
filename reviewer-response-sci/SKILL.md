---
name: reviewer-response-sci
description: Use when generating a complete SCI reviewer-response package from manuscript, supplementary material, and review comments, especially when a user needs a one-shot hierarchical HTML deliverable with an email summary and per-comment detailed response pages.
---

# Reviewer Response SCI

## Scope
Default mode is **one-shot full package with atomic storage**.

Given these materials:
- manuscript (`.docx`)
- supplementary information (`.docx`, optional)
- review comments (`.docx`)

Generate:
1. Atomic JSON pages (one JSON per comment + one email JSON).
2. Atomic manuscript units (`manuscript_units/`).
3. Atomic SI units (`si_units/`, if SI provided).
2. One final hierarchical HTML.

## Required Inputs
- `comments_docx_path` (required)
- `manuscript_docx_path` (required)
- `si_docx_path` (optional)
- `project_root` (required)
- `output_html_path` (required)

## Save Path Confirmation (Mandatory)
Before running the pipeline, first ask the user where output files should be saved.

Default behavior if user does not specify a custom location:
1. Use the current project directory.
2. Create a dedicated subfolder for this run (for example: `projects/<task_name_or_date>/`).
3. Write all artifacts into that subfolder (`units/`, `manuscript_units/`, `si_units/`, `logs/`, final HTML).

## Output Contract (One-Shot)
Return one complete HTML document (single file) with hierarchical TOC and interactive navigation.

TOC hierarchy must be:
1. `回复审稿人的邮件` (top item)
2. `Reviewer #N`
3. `Major` / `Minor`
4. `Comment k` (leaf)
5. Leaf items must use **background color** to indicate severity:
   - major comment: major color background
   - minor comment: minor color background
   - do not rely on symbol markers in TOC to indicate severity
6. TOC must support hierarchical collapse/expand:
   - `Reviewer #N` level can be collapsed/expanded
   - `Major/Minor` level can be collapsed/expanded
   - collapsing one reviewer should allow focusing on another reviewer without visual clutter
7. Two-pane layout must support draggable split:
   - left TOC pane and right content pane must be separated by a draggable divider
   - user can drag to resize TOC width
   - width preference should be persisted locally (e.g., `localStorage`)
   - on mobile/narrow screens, divider should be hidden and layout should fall back to single-column

Each leaf page must include:
1. Reviewer intent block:
   - show original reviewer comment first (English)
   - then show interpretation in Chinese and English
2. Response block (`Response to Reviewer`):
   - Chinese + English stacked dual boxes (top/bottom layout)
   - each box has a `复制` button (button text must be exactly `复制`)
3. Revision candidate block (`可能需要修改的正文/附件内容`):
   - must include original location information:
     - which section/subsection
     - which original sentence/paragraph
   - must include original text (for side-by-side logic, stacked display)
   - must include revised text (English)
   - must include Chinese translation for the revised text
   - each Chinese/English revised text box has a `复制` button
   - if no modification needed, explicitly write `无`
   - must include modification rationale with explicit action tags:
     - 添加
     - 删除
     - 修改
     and explain reason for each action
4. Chinese modification notes with `🔴 Core` and `🟡 Support`
5. Evidence area supporting text, image, and table
   - image handling rule:
     - if no image revision required, do not render image placeholder block
     - if image revision is required, render an explicit image placeholder block first

## Atomic JSON Contract
Project layout:
- `project_root/project_state.json`
- `project_root/index.json` (hierarchical TOC source)
- `project_root/units/000_email.json`
- `project_root/units/*.json` (one file per comment)
- `project_root/manuscript_units/*.json` (one paragraph per unit)
- `project_root/si_units/*.json` (one paragraph per unit)

Each unit follows `references/atomic-unit-schema.json`.

## Rules
- Do not fabricate experiments, statistics, or references.
- If evidence is missing, explicitly mark `Not provided by user`.
- Keep tone professional and non-defensive.
- Keep one-page-per-comment structure.
- All copy buttons in the UI must use Chinese label `复制`.
- Frontend must be intentionally designed (not default/plain style), with clear hierarchy, strong readability, and responsive layout.
- Quality gates must fail when:
  - `revised_excerpt_en` is placeholder/empty (unless explicitly running with a relaxed gate mode)
  - `revised_excerpt_en` is identical to `original_excerpt_en`
  - unit status indicates `needs_manual_revision`

## One-Shot Workflow
1. Parse all reviewer comments from `comments_docx_path`.
2. Atomize manuscript and SI into paragraph-level units.
3. Build comment atomic units in `project_root/units/` and attach anchor-based links to manuscript/SI units.
4. Build hierarchical index in `project_root/index.json`.
5. Render single HTML with left hierarchical TOC + right content pane.
6. Run hard gate checks and HTML checks before delivery.
7. Run final consistency report.
8. Write checkpoint + transaction logs to `project_root/logs/`.
9. Sync unit state map to `project_root/logs/unit_state.json`.
10. Write reproducibility snapshot to `project_root/logs/version_snapshot.json` (hashes for key scripts + outputs).

## Re-Render Workflow
After manual editing of any unit JSON:
1. Keep `index.json` unchanged unless hierarchy changes.
2. Rebuild HTML only using `scripts/render_from_atomic_json.py`.
3. Sync state using `scripts/state_manager.py sync`.

## Scripts
- One-shot enforced pipeline: `scripts/run_pipeline.py`
  - Debug/preview mode: add `--allow-placeholder` to relax strict placeholder gate temporarily.
- Preflight checker: `scripts/preflight.py`
- One-shot generator: `scripts/build_full_package.py`
- Re-render from atomic JSON: `scripts/render_from_atomic_json.py`
- Unit state manager: `scripts/state_manager.py`
- Hard gate checker: `scripts/strict_gate.py`
- Consistency checker: `scripts/consistency_check.py`
- Final consistency report: `scripts/final_consistency_report.py`
- HTML validator: `scripts/html_format_check.py`
- Risk phrase scan: `scripts/risk_check.py`

## References
- Atomic schema: `references/atomic-unit-schema.json`
- Atomic workflow: `references/atomic-workflow.md`
- HTML full template: `references/html-template-full.html`
- Output contract: `references/output-template.md`
- Decision rules and sentence patterns: `references/decision-rules.md`
- HTML filling notes: `references/html-fill-guide.md`
