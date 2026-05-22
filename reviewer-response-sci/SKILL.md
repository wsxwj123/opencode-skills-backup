---
name: reviewer-response-sci
description: 用于 SCI 审稿意见逐条回复的全流程技能，适用于期刊大修/小修阶段，输入论文正文与审稿意见，输出含双栏 HTML 导航、中英文对照、修改定位的完整回复包。当用户提到「审稿意见回复」「回复审稿人」「回复reviewer」「修回」「修稿」「Response to Reviewer」「revise and resubmit」「R&R」「reviewer comments」时优先调用。注意与 reviewer-simulator（模拟写审稿意见）区分：本技能是针对已收到的审稿意见撰写回复。
---

# Reviewer Response SCI

## Scope
Default mode is **one-shot full package with atomic storage**.

## Required Inputs
| 参数 | 必需 | 说明 |
|------|------|------|
| `comments_docx_path` | ✅ | 审稿意见文件 |
| `manuscript_docx_path` | ✅ | 论文正文 |
| `si_docx_path` | 可选 | 补充材料 |
| `project_root` | ✅ | 输出根目录 |
| `output_html_path` | ✅ | 最终 HTML 路径 |

**Outputs（one-shot 产物）：**
1. Atomic JSON pages — `units/` 目录（每条意见一个 JSON + 邮件 JSON）
2. Atomic manuscript units — `manuscript_units/`
3. Atomic SI units — `si_units/`（有SI时）
4. One final hierarchical HTML（主交付物，见 Output Contract）

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
   - **Figure Prompt Block（图片修改需求时自动生成提示词）：**
     When a reviewer requires figure revision or addition, generate a structured Figure Prompt immediately after the image placeholder block:

     ```
     [FIGURE PROMPT — Response to Reviewer #N, Comment K]
     REVISION TYPE: New figure | Replace existing Figure X | Add panel to Figure X | Revise color/style only
     REVIEWER REQUEST SUMMARY: <one sentence distilling what the reviewer asked for>
     TYPE: Data plot | Schematic | Mechanistic pathway | Statistical | Workflow
     SUBJECT: <specific scientific content required by reviewer>
     STYLE: BioRender风格, 科研绘图, 最高分辨率, white background (#FFFFFF), publication-quality, consistent with manuscript's existing figure style [默认BioRender风格；如需其他风格（如Cell-style flat icon / Nature手绘风），在启动时告知]
     COLOR SCHEME: (match manuscript's existing palette; default: Primary #2E86AB | Secondary #A23B72 | Accent #F18F01 | colorblind-safe)
     ELEMENTS:
       - <Element 1>: <exact requirement from reviewer comment>
       - <Element 2>: <additional components needed>
     LAYOUT: <Single panel | Multi-panel, specifying new panel position relative to existing figure>
     TYPOGRAPHY: Match existing manuscript figures (Arial/Helvetica, 8-10pt, English labels)
     STATISTICAL REQUIREMENTS: <if new statistical analysis required: chart type, error bars: SEM/SD, significance markers>
     KEY MESSAGE: <what this revised figure must now demonstrate to satisfy the reviewer>
     AVOID: Changes that contradict existing data; adding elements not supported by the underlying experiment
     ```

     Rules:
     - Generate Figure Prompt ONLY when reviewer explicitly requests a figure change (not for text-only responses)
     - If reviewer requests a new experiment's figure: mark as `[NEW EXPERIMENT REQUIRED]` and note `Not provided by user` in evidence area
     - If revision is cosmetic only (color, font, layout): mark as `[STYLE REVISION ONLY]` and skip ELEMENTS block
     - Store all figure prompts in the corresponding comment unit JSON under `content.figure_prompt`

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
- If a reviewer comment requires adding references, literature retrieval follows topic-dependent routing: ① determine field — life science/medicine → PubMed CLI first (`esearch`/`efetch`, `~/edirect/`, `< /dev/null`, proxy `http://127.0.0.1:7897`); CS/AI/engineering → paper-search MCP first (`mcp__paper-search-mcp__search_arxiv` etc.) ② fallback to the other when primary yields no results. Auto-install PubMed CLI if `~/edirect/esearch` missing: `sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"`.
- **严禁** 使用 `tavily`、`websearch` 或 `openalex`（pyalex）进行文献检索。
- **Serial Search (MANDATORY):** Execute all retrieval calls sequentially (PubMed CLI and paper-search MCP alike). Never parallelize search requests. Enforce ≥1s interval between consecutive calls.
- Do not create ad-hoc fixer scripts (e.g., `fix_gate_errors.py`, temporary patch scripts) during normal runs.
- When gate checks fail, directly edit the failing `project_root/units/*.json` fields and re-run checks.
- Keep one-page-per-comment structure.
- All copy buttons in the UI must use Chinese label `复制`.
- Frontend must be intentionally designed (not default/plain style), with clear hierarchy, strong readability, and responsive layout.
- Quality gates must fail when:
  - `revised_excerpt_en` is placeholder/empty (unless explicitly running with a relaxed gate mode)
  - `revised_excerpt_en` is identical to `original_excerpt_en`
  - unit status indicates `needs_manual_revision`
- If `comments_docx` fails to parse (corrupt file, encoding error), abort immediately and report the exact error; do not proceed to atomization.
- If a reviewer comment cannot be matched to any manuscript paragraph (location confidence below threshold), set `atomic_location.confidence = "low"` and mark the unit `needs_manual_revision`; do not fabricate a location.
- Gate fix loop must not exceed **3 iterations**; if gate still fails after 3 direct JSON edits, halt and report remaining failures to the user with a list of unresolved unit IDs.

## One-Shot Workflow
1. Parse all reviewer comments from `comments_docx_path`.
2. If any comment needs additional citations, run retrieval via topic-dependent routing (life science → PubMed CLI first; CS/AI → paper-search MCP first; fallback to the other when primary yields no results). See Rules section for full routing spec.
3. Atomize manuscript and SI into section-level units (heading + body + corresponding figure captions).
3.5. **[User Checkpoint]** Print a summary table:
   - Total section-level units extracted (manuscript count / SI count)
   - Any sections that failed to split or produced empty units
   Ask the user: "Atomization complete. Proceed to build comment units? (yes / abort)"
   Do not continue to step 4 until user confirms.
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

   **Step 7 Mini-Gate（填写完成后，进入Step 8前执行）：**
   - 抽取前3个comment unit，检查以下字段是否已填（非占位符）：
     - `content.chinese_translation`（非 `待AI` / `AI_FILL_REQUIRED`）
     - `content.response_zh`（非空、非占位符）
     - `content.revised_excerpt_en`（非空、非与 `original_excerpt_en` 相同）
   - 如发现任何占位符或空值，**停止并列出未填字段**，等待修复后再继续
   - 抽查通过后方可进入Step 8渲染

8. Render single HTML with left hierarchical TOC + right content pane from updated atomic JSON.
9. Run hard gate checks and HTML checks before delivery.
   - final delivery must pass `final_content_gate.py`（**内容完整性门禁**，检查回复内容是否填写完整，与其他技能的 `citation_guard.py` 职责不同——后者做文献溯源，本技能做回复内容质量检查）:
     - if any `待AI` / `AI_FILL_REQUIRED` placeholder remains, gate fails
     - `--allow-placeholder` is only for skeleton/prewrite stage, not final delivery
   - if gate fails, fix the listed units by direct JSON edits; do not generate extra fixer scripts
10. Run final consistency report.
11. Write checkpoint + transaction logs to `project_root/logs/`.
12. Sync unit state map to `project_root/logs/unit_state.json`.
13. Write reproducibility snapshot to `project_root/logs/version_snapshot.json` (hashes for key scripts + outputs).

## Re-Render Workflow
After manual editing of any unit JSON:
1. Keep `index.json` unchanged unless hierarchy changes.
2. Rebuild HTML only using `scripts/render_from_atomic_json.py`.
   - If render fails (JSON parse error / missing required field): fix the offending `units/*.json` directly, then re-run. Do not regenerate from scratch.
   - If render fails (script not found / import error): check `scripts/` directory exists and dependencies are installed; fall back to `scripts/run_pipeline.py --allow-placeholder` as last resort.
3. Sync state using `scripts/state_manager.py sync`.
   - If sync fails: run `scripts/state_manager.py status` to identify out-of-sync units; fix manually, then retry sync.

## Scripts
- One-shot enforced pipeline: `scripts/run_pipeline.py`
  - Debug/preview mode: add `--allow-placeholder` to relax strict placeholder gate temporarily.
- Preflight checker: `scripts/preflight.py`
- One-shot generator: `scripts/build_full_package.py`
- Re-render from atomic JSON: `scripts/render_from_atomic_json.py`
- Unit state manager: `scripts/state_manager.py`
- Hard gate checker: `scripts/strict_gate.py`
- Final content gate: `scripts/final_content_gate.py` — 检查回复内容占位符与修改文本是否填写完整（非文献溯源）
- Consistency checker: `scripts/consistency_check.py`
- Final consistency report: `scripts/final_consistency_report.py`
- HTML validator: `scripts/html_format_check.py`
- Risk phrase scan: `scripts/risk_check.py`

## References
按需加载，不要全部预加载：
- Atomic schema: `references/atomic-unit-schema.json` — 单元 JSON 结构定义（原子化构建时参考）
- Atomic workflow: `references/atomic-workflow.md` — 原子化流程详细说明（首次使用或遇到异常时）
- HTML full template: `references/html-template-full.html` — 完整 HTML 渲染模板（渲染步骤时）
- Output contract: `references/output-template.md` — 输出规范（核对交付物结构时）
- Decision rules and sentence patterns: `references/decision-rules.md` — 回复措辞决策规则（撰写英文回复时）
- HTML filling notes: `references/html-fill-guide.md` — HTML 填写注意事项（渲染异常时）
