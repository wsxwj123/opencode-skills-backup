---
name: reviewer-response-sci
description: 使用于 SCI 审稿意见回复（回复审稿人、审稿意见逐条回复、Response to Reviewer）。当用户提到“审稿意见回复/回复审稿人/SCI审稿回复”时优先调用。Supports one-shot hierarchical HTML deliverable with atomic manuscript/SI linking.
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
4. One final hierarchical HTML.

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
   - show original reviewer comment (English)
   - show Chinese translation of reviewer comment (direct/literal translation, not paraphrased rewriting)
   - translation implementation rule:
     - translation must be produced directly by the current model (AI direct translation), not by local machine-translation dependencies
     - script must not output final Chinese translation automatically; script only keeps AI-to-fill placeholders before final rendering
   - show Chinese understanding of reviewer intent
   - do not include English interpretation in this block
   - Chinese fields must be written in Chinese summary form; do not directly paste English comment text as the Chinese understanding
2. Response block (`Response to Reviewer`):
   - Chinese response first, then corresponding English translation (top/bottom layout)
   - each box has a `复制` button (button text must be exactly `复制`)
3. Revision candidate block (`可能需要修改的正文/附件内容`):
   - must include one **Quick Location** block (human-facing):
     - section/subsection
     - paragraph index (manuscript/SI)
     - one Word-search key sentence
   - do **not** show a separate verbose `定位信息` block if Quick Location already exists
   - must include atomic-document location fields:
     - `manuscript_unit_id` / `si_unit_id`
     - atomic json relative path (e.g., `manuscript_units/0007.json`)
     - paragraph index and matched sentence index/text
   - atomic-document location must be collapsed by default (`details/summary`) as debug information
   - must include original text as a **focused paragraph snippet** around the matched sentence (not full long section)
   - `Original Text` should be collapsed by default (`details/summary`)
   - must include revised text (English) that corresponds to the focused original paragraph
   - must include Chinese translation for the revised text
   - each Chinese/English revised text box has a `复制` button
   - if no modification needed, explicitly write `无`
   - do not render a separate `Tracked Edit` block
   - do not render a standalone `修改说明` card inside Section 3
4. Chinese modification notes block (`修改说明（中文）`) must be a single merged card:
   - subsection A: detailed action list (`添加/删除/修改` + reason for each action)
   - subsection B: summary list with `🔴 Core` and `🟡 Support`
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
- `project_root/manuscript_units/*.json` (one section-level block per unit: heading + corresponding body text + corresponding figure captions when present)
- `project_root/si_units/*.json` (one section-level block per unit: heading + corresponding body text + corresponding figure captions when present)

Each unit follows `references/atomic-unit-schema.json`.
Each comment unit should carry `content.atomic_location` and must be renderable in HTML section 3.
Source atomic units (`manuscript_units` / `si_units`) must include:
- section-level units (`unit_type=section_block`, optionally `preamble_block`)
- section text and corresponding figure captions in the same section-level unit when available
- force split back-matter sections into independent units: `Author Contributions`, `Acknowledgements`, `Conflicts of Interest`, `References` (supports numbered headings like `6. AUTHOR CONTRIBUTIONS` and inline heading patterns)
- if no figure exists, figure-caption units can be absent
- optional image attachment extraction is allowed but not mandatory; section text + corresponding figure caption text is mandatory

## Rules
- Do not fabricate experiments, statistics, or references.
- If evidence is missing, explicitly mark `Not provided by user`.
- Keep tone professional and non-defensive.
- English reviewer responses must be fluent and natural, with low AI-style phrasing.
- Prefer short sentences; avoid long and complex sentences by default.
- Short-sentence preference means clear and natural rhythm, not mechanical sentence splitting.
- If a reviewer comment requires adding references, literature retrieval must use `paper-search` MCP with PubMed only.
- Do not use any non-PubMed search tool for citation retrieval in this skill.
- Keep one-page-per-comment structure.
- All copy buttons in the UI must use Chinese label `复制`.
- Frontend must be intentionally designed (not default/plain style), with clear hierarchy, strong readability, and responsive layout.
- Quality gates must fail when:
  - `revised_excerpt_en` is placeholder/empty (unless explicitly running with a relaxed gate mode)
  - `revised_excerpt_en` is identical to `original_excerpt_en`
  - unit status indicates `needs_manual_revision`

## One-Shot Workflow
1. Parse all reviewer comments from `comments_docx_path`.
2. If any comment needs additional citations, run PubMed retrieval via `paper-search` MCP only.
3. Atomize manuscript and SI into section-level units (heading + body + corresponding figure captions).
4. Build comment atomic units in `project_root/units/` and attach anchor-based links to manuscript/SI units.
5. Build `manuscript_edit_plan.md` in `project_root/` **before** final delivery.
   - The plan must be sorted by manuscript original order (ascending `manuscript_paragraph_index`).
   - Each row must include:
     - `comment_unit_id` / reviewer and major-minor info
     - target document (`manuscript` / `SI` / both)
     - section heading
     - paragraph index
     - one Word-search key sentence (`Word Find key sentence`)
     - exact to-be-replaced snippet (if available)
     - revised text to insert (EN, and ZH if provided)
     - action type (`添加` / `删除` / `修改`)
   - When multiple comments map to the same paragraph, merge into one ordered block with sub-items.
   - If a comment is global (language polishing, full-figure consistency), put it in a separate `Global edits` section and explicitly mark as non-localized.
6. Build hierarchical index in `project_root/index.json`.
7. Let model fill all Chinese translation/Chinese response fields in atomic JSON units.
   - model must also fill:
     - reviewer intent understanding
     - English response to reviewer
     - revised excerpt (EN + ZH)
     - core/support modification notes
     - modification action reasons
8. Render single HTML with left hierarchical TOC + right content pane from updated atomic JSON.
9. Run hard gate checks and HTML checks before delivery.
   - final delivery must pass `final_content_gate.py`:
     - if any `待AI` / `AI_FILL_REQUIRED` placeholder remains, gate fails
     - `--allow-placeholder` is only for skeleton/prewrite stage, not final delivery
10. Run final consistency report.
11. Write checkpoint + transaction logs to `project_root/logs/`.
12. Sync unit state map to `project_root/logs/unit_state.json`.
13. Write reproducibility snapshot to `project_root/logs/version_snapshot.json` (hashes for key scripts + outputs).

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
- Final content gate: `scripts/final_content_gate.py`
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
