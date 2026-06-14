---
name: reviewer-response-sci
description: 用于 SCI 审稿意见逐条回复的全流程技能，适用于期刊大修/小修阶段，输入论文正文与审稿意见，生成完整的逐条回复包。当用户提到「审稿意见回复」「回复审稿人」「回复reviewer」「response letter」「回复信」「rebuttal」「逐条回复」「修回」「修稿」「Response to Reviewer」「revise and resubmit」「R&R」「reviewer comments」时优先调用。注意与 reviewer-simulator（模拟写审稿意见）区分：本技能是针对已收到的审稿意见撰写回复。
---

# Reviewer Response SCI

## Scope
Default mode is **one-shot full package with atomic storage**. Two secondary modes also exist: **Re-Render**（手改 unit JSON 后单独重渲，见 Re-Render Workflow）和 **skeleton/prewrite 预览**（出占位符草稿，命令见 Scripts 段）。

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
**主交付物 = 单文件分层 HTML**（左侧层级 TOC + 右侧内容，单页可见）。**全部 UI 由 `scripts/build_full_package.py` 的 `render_html()` 生成**——TOC 层级、严重度背景色、折叠/展开、可拖拽分割线、`复制` 按钮、`localStorage` 持久化、各 box 布局均已硬编码，**AI 无需手工实现 HTML**。完整 UI 验收对照细则见 `references/output-template.md`。

AI 真正要产出的是每条 comment unit 的**内容字段**（脚本只写占位符，AI 填真值）：
- 审稿人意图：原始意见(EN) + 中文直译（直译不意译）+ 中文意图理解（摘要，非粘贴英文原文）。直译/中文回应必须由当前模型直接产出，脚本不自动出译文、只留占位符。
- Response：中文回复 + 对应英文（非逐字翻译）。
- 修改候选：revised EN 段落（聚焦匹配句周围片段）+ 中文译文；无修改写 `无`；定位字段（unit_id/路径/段落与句子 index）随 unit 写入。
- 修改说明：动作列表（添加/删除/修改+原因）+ `🔴 Core`/`🟡 Support` 汇总。
- 证据/图片：**Figure Prompt Block** — 审稿人明确要求改/新增图片时，按 `references/figure-prompt-template.md` 生成结构化提示词，存入对应 comment unit JSON 的 `content.figure_prompt`。

## Atomic JSON Contract
Project layout:
- `project_root/project_state.json`
- `project_root/index.json` (hierarchical TOC source)
- `project_root/citation_registry.json` (new references added during response; see Step 2)
- `project_root/manuscript_edit_plan.md` (ordered revision plan; see Step 5)
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
- Prefer short sentences for clear, natural rhythm; avoid long complex sentences by default, but do not split mechanically.
- If a reviewer comment requires adding references, literature retrieval follows topic-dependent routing: ① determine field — life science/medicine → PubMed CLI first (`esearch`/`efetch`, `~/edirect/`, `< /dev/null`, proxy `http://127.0.0.1:7897`); CS/AI/engineering → paper-search MCP first (`mcp__paper-search-mcp__search_arxiv` etc.) ② fallback to the other when primary yields no results. Auto-install PubMed CLI if `~/edirect/esearch` missing: `sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"`.
- **严禁** 使用 `tavily`、`websearch` 或 `openalex`（pyalex）进行文献检索。
- **Serial Search (MANDATORY):** Execute all retrieval calls sequentially (PubMed CLI and paper-search MCP alike). Never parallelize search requests. Enforce ≥1s interval between consecutive calls.
- Do not create ad-hoc fixer scripts (e.g., `fix_gate_errors.py`, temporary patch scripts) during normal runs.
- When gate checks fail, directly edit the failing `project_root/units/*.json` fields and re-run checks.
- Keep one-page-per-comment structure.
- All copy buttons in the UI must use Chinese label `复制`.
- Frontend design specifications:
  - Color palette: primary `#0F4C81` (deep blue), core marker `#B42318` (red), support marker `#B54708` (amber), background `#F4F7FB`, panel `#FFFFFF`, border `#D9E2EC`
  - Typography: `"Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif`; body 14px/1.6; headings bold; code/path `monospace`
  - Card spacing: `padding: 14px 16px`, `border-radius: 10px`, `margin-bottom: 12px`
  - Responsive breakpoint: ≤980px switch to single-column, sidebar becomes top nav
- Quality gates must fail when:
  - `revised_excerpt_en` is placeholder/empty (unless explicitly running with a relaxed gate mode)
  - `revised_excerpt_en` is identical to `original_excerpt_en`
  - unit status indicates `needs_manual_revision`
- If `comments_docx` fails to parse (corrupt file, encoding error), abort immediately and report the exact error; do not proceed to atomization.
- If a reviewer comment cannot be matched to any manuscript paragraph (location confidence below threshold), set `atomic_location.confidence = "low"` and mark the unit `needs_manual_revision`; do not fabricate a location.
- Gate fix loop must not exceed **3 iterations**; if gate still fails after 3 direct JSON edits, halt and report remaining failures to the user with a list of unresolved unit IDs.
- **AI Style Control:** English responses must avoid AI-typical phrasing patterns:
  - Hedging overuse: "it is important to note that", "it should be noted that", "notably", "importantly"
  - Empty appreciation: "we greatly appreciate your insightful comments", "this is an excellent suggestion"
  - Filler phrases: "in order to", "we would like to point out that", "as the reviewer rightly noted"
  - Structural repetition: ≥3 responses must not open with the same template sentence
  - `risk_check.py` scans for these patterns automatically; WARN-level issues should be fixed before delivery
- **Track Changes Awareness:**
  - This skill generates the **response document** (point-by-point reply); it does **not** produce a track-changes version of the manuscript
  - Track changes (Word `.docx` with revisions marked) must be done **manually** by the user using the `manuscript_edit_plan.md` as a guide
  - `revised_excerpt_en` in each unit shows the proposed new text; the user applies these edits to the manuscript with Track Changes enabled
  - If the user asks for a tracked-changes manuscript, explain this limitation and recommend using `manuscript_edit_plan.md` for efficient manual editing

### Domain Edge Cases
- **Reviewer recommends acceptance without comments** ("I have no major/minor concerns"): create a single email-only response acknowledging the reviewer; do not generate an empty Major/Minor section.
- **Two reviewers give contradictory suggestions** (e.g., R1 says "remove Section 3" vs R2 says "expand Section 3"): flag the conflict explicitly in both units' `notes_core_zh`; in the English response, acknowledge the divergence and state which direction is adopted with evidence-based justification. Add a `[CONFLICTING ADVICE]` marker in `manuscript_edit_plan.md`.
- **Reviewer writes comments in a non-English language**: translate the original comment into English first (store in `reviewer_comment_en`), then produce the Chinese translation from the original language (not from the English translation). Note the original language in a `source_language` annotation in the unit JSON.
- **Manuscript lacks standard section headings** (e.g., Letter/Communication format): atomize by paragraph breaks instead of headings; set `unit_type=paragraph_block` for manuscript units; use paragraph index as the primary location anchor.
- **Same paragraph targeted by 5+ comments**: in `manuscript_edit_plan.md`, merge all into one block sorted by reviewer priority (Editor > R1 > R2 > R3). If modifications conflict within the same paragraph, flag `[INTRA-PARAGRAPH CONFLICT]` and present alternative revision options for user decision.

## One-Shot Workflow

**执行模型（先读这段）：** 本流程是**两段式自动化 + AI 填空**，不是线性手工 13 步。
- `scripts/build_full_package.py`（pipeline 内部自动调用）一次性完成 Step 3/4/5/6/8 的机械部分：atomize 论文/SI 段落、在 `units/*.json` 写好**占位符**骨架（`【待AI...】` / `[AI_FILL_REQUIRED]`）、生成 `index.json`、并由 `render_html()` 渲出完整 HTML。**不要手工 atomize，也不要手写 index.json。**
- AI 的核心工作只有两件：①**Step 7** 把 `units/*.json` 里的占位符字段填成真实内容；②gate 失败时按报告**直接改对应 `units/*.json` 再重跑**。
- 两种调用时机，二选一：
  1. **分步**：先 `build_full_package.py --allow-placeholder` 出骨架 → AI 填 `units/*.json` → 再 `run_pipeline.py`（不带 `--allow-placeholder`）跑全部 gate；
  2. **串起**：一条 `run_pipeline.py` 走完 build→gate（首轮占位符会被门禁拦下，按报告填 units 后重跑）。
- 下列编号步骤是**逻辑顺序说明**，多数由脚本代劳；User Checkpoint 之间 AI 需停下确认。

1. Parse all reviewer comments from `comments_docx_path`.
1.5. **[User Checkpoint]** Print parsed comment summary table:
   - Reviewer count
   - Per-reviewer breakdown: Major / Minor / General comment counts
   - Full list: reviewer × section × comment index × first 20 words of each comment
   Ask the user: "Comment parsing complete. Does this match the reviewer letter? (yes / abort / correct:N)"
   Do not continue to step 1.7 until user confirms.

1.7. **[Strategy Planning]** Build a rebuttal strategy table before writing any responses:
   | Reviewer | # | Section | Strategy | Rationale | Data Needed |
   |----------|---|---------|----------|-----------|-------------|
   | R1 | 1 | Major | Accept | Valid concern, easy fix | None |
   | R1 | 2 | Major | Partial | Agree on X, push back on Y | New ref for Y |
   | R2 | 1 | Minor | Push back | Misunderstanding, cite existing evidence | None |

   Strategy options:
   - **Accept**: fully agree, will revise as requested
   - **Partial**: agree on some points, provide evidence/rationale for others
   - **Push back**: respectfully disagree with evidence-based justification
   - **Acknowledge**: thank reviewer for the suggestion, explain why not adopted (e.g., scope, data limitation)

   Rules:
   - Every comment must have a strategy assignment before proceeding
   - `Push back` requires at least one concrete evidence item (existing data, published precedent, or methodological rationale)
   - If strategy requires new literature, flag in `Data Needed` column for Step 2
   - Print the strategy table and ask user: "Strategy plan ready. Approve? (yes / adjust:R1.2 → Accept / abort)"
   - Do not proceed to Step 2 until user confirms

2. If any comment needs additional citations (identified in Step 1.7 `Data Needed`), run retrieval per the Rules section's topic-dependent routing spec.
   - After retrieval, build `citation_registry.json` in `project_root/`:
     ```json
     {
       "original_ref_count": 42,
       "entries": [
         {
           "ref_number": 43,
           "title": "...",
           "doi": "10.xxxx/...",
           "pmid": "12345678",
           "authors": "First A, Second B",
           "year": 2023,
           "journal": "...",
           "source_provider": "pubmed-cli",
           "source_id": "esearch:query_string",
           "added_for_units": ["003_R1_major_01"],
           "retrieved_at": "2024-..."
         }
       ]
     }
     ```
   - `original_ref_count`: total references in the original manuscript (count from References section)
   - New reference numbers must start from `original_ref_count + 1`, sequential, no gaps
   - Each entry must record `source_provider` (e.g., `pubmed-cli`, `paper-search-mcp`) for traceability
3. Atomize manuscript and SI into section-level units (heading + body + corresponding figure captions).
3.5. **[User Checkpoint]** Print a summary table:
   - Total section-level units extracted (manuscript count / SI count)
   - Any sections that failed to split or produced empty units
   Ask the user: "Atomization complete. Proceed to build comment units? (yes / abort)"
   Do not continue to step 4 until user confirms.
4. Build comment atomic units in `project_root/units/` and attach anchor-based links to manuscript/SI units.
   Also build email page JSON at `project_root/units/000_email.json` with the following content:
   - `subject`: `Response to Reviewers — [Manuscript Title]`
   - `opening`: thank the editor; state that a point-by-point response and revised manuscript are attached
   - `change_summary`: one bullet per reviewer, ≤2 sentences per bullet, summarizing major revisions made
   - `closing`: restate willingness to provide further revisions if needed
   - Tone: professional, concise, non-defensive; English only; no Chinese in email body
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
7. Fill all AI-required fields in each comment unit JSON. Execute in sub-steps:

   **改坏可回滚：** 每次大改 `units/*.json` 前先 `python3 scripts/state_manager.py snapshot --project-root <root>` 建还原点；改坏用 `python3 scripts/state_manager.py rollback --project-root <root>`（默认还原最近一次快照）。快照存于 `logs/snapshots/units_<时间戳>/`。


   **7a. 排序与分批：**
   - 按 reviewer 分组，每组内先 major 后 minor 后 general
   - 如 comment 总数 ≤15，一次性处理；>15 条时分批（每批 ≤10 条），每批完成后写盘再继续下一批
   - 每条 comment unit 需填写以下 8 组字段（参照 `references/atomic-unit-schema.json`）：

   **7b. 逐条填写（每条 comment unit）：**
   1. `content.reviewer_comment_zh`：直译审稿意见（中文，不改写不概括）
   2. `content.reviewer_intent_zh`：理解审稿人真实意图（中文摘要，≤3 句）
   3. `content.response_en`：英文回复（遵循 `references/decision-rules.md` 的基调选择和句式规范；短句优先见 Rules）
   4. `content.response_zh`：中文回复（与英文回复对应，非逐字翻译，需自然通顺）
   5. `content.revised_excerpt_en`：修改后的英文正文段落（如无需修改写 `无`）
   6. `content.revised_excerpt_zh`：修改后的中文翻译（如无需修改写 `无`）
   7. `content.modification_actions`：修改动作列表（每条含 `action_type` + `target` + `reason`）
   8. `content.notes_core_zh` + `content.notes_support_zh`：核心🔴和辅助🟡修改说明

   **7c. 质量标准：**
   - 英文回复：≥3 句、≤300 词；必须包含致谢 + 具体行动描述
   - 中文回复：与英文回复信息等价，但措辞独立，不是机械翻译
   - revised_excerpt：必须与 original_excerpt_en 有实质差异（不能只改标点）
   - 禁止虚构实验、统计、引用（遵循 Rules 中的红线）

   **Step 7 Mini-Gate（填写完成后，进入 Step 8 前执行）：**
   - 抽取前 3 个 comment unit，检查以下字段是否已填（非占位符）：
     - `content.reviewer_comment_zh`（非 `待AI` / `AI_FILL_REQUIRED`）
     - `content.response_zh`（非空、非占位符）
     - `content.revised_excerpt_en`（非空、非与 `original_excerpt_en` 相同）
   - 如发现任何占位符或空值，**停止并列出未填字段**，等待修复后再继续
   - 抽查通过后方可进入 Step 7.5

   7.5. **[User Checkpoint — Quality Review]** 展示回复质量摘要供用户审查：
   - 打印表格：每条 comment 的 unit_id | reviewer | section | response_en 前 50 字 | revised_excerpt 状态（有修改/无/needs_manual）
   - 标记需人工关注的条目：`needs_manual_revision` 的 unit、`confidence=low` 的定位、revised_excerpt_en 为 `无` 但 comment 明确要求改文的
   - 问用户："Response content ready for rendering. Review OK? (yes / fix:unit_id / abort)"
   - 用户可指定修改特定 unit，修改后重新展示该 unit 摘要
   - 确认后方可进入 Step 8

8. Render single HTML with left hierarchical TOC + right content pane from updated atomic JSON.
9. Run hard gate checks, citation checks, and HTML checks before delivery.
   - **判读：** pipeline 退出码 `0` = 全部 gate 通过；非零时 stdout 会打印 `PIPELINE: FAIL (step=..., code=...)` 及失败 step 和涉及的 unit。按失败信息直接改对应 `units/*.json`（≤3 次上限，见 Rules）后重跑 `run_pipeline.py`。
   - These are executed automatically and serially by `scripts/run_pipeline.py` in this order: `strict_gate.py`（硬门禁）→ `final_content_gate.py` → `consistency_check.py` → `final_consistency_report.py` → `html_format_check.py` → `risk_check.py` → `citation_guard.py` → `citation_ref_tracker.py`. Do not run them manually one-by-one during normal runs.
   - final delivery must pass `final_content_gate.py`（**内容完整性门禁**）:
     - if any `待AI` / `AI_FILL_REQUIRED` placeholder remains, gate fails
     - `--allow-placeholder` is only for skeleton/prewrite stage, not final delivery
   - `citation_guard.py` validates new references in `citation_registry.json`（DOI/PMID 真实性、撤稿检测）
   - `citation_ref_tracker.py` checks citation number consistency across all units（未定义引用、编号间隙）
   - `risk_check.py` scans for fabrication patterns + AI style issues
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
3. Sync state using `scripts/state_manager.py sync --project-root .`.
   - If sync fails: run `scripts/state_manager.py show --project-root .` to identify out-of-sync units; fix manually, then retry sync.
4. Run `scripts/final_content_gate.py` and `scripts/html_format_check.py` on the newly rendered HTML.
   - Gate checks are mandatory even for single-unit edits.
   - If gate fails, fix the offending `units/*.json` directly and re-run from step 2. Do not skip.

## Scripts
**入口：** `scripts/run_pipeline.py` —— 一站式串行执行 preflight → build → 全部 gate → consistency report → html gate。5 个必需参数：`--comments` / `--manuscript` / `--si`（可选）/ `--project-root` / `--output-html`。

最小可执行示例（占位符首轮预览，加 `--allow-placeholder` 放宽内容门禁出骨架；正式交付去掉该 flag）：
```bash
python3 scripts/run_pipeline.py \
  --comments /path/to/reviewer_comments.docx \
  --manuscript /path/to/manuscript.docx \
  --si /path/to/supplementary.docx \
  --project-root /path/to/project_root \
  --output-html /path/to/project_root/reviewer_response.html \
  --allow-placeholder
```
无 SI 时省略 `--si`。AI 填完 `units/*.json` 后，去掉 `--allow-placeholder` 重跑同一命令即为正式交付。

各 gate 由 pipeline 自动调用，正常运行无需手动单独跑（详见 Step 9）：
- `strict_gate.py`（硬门禁）/ `final_content_gate.py`（内容完整性，检查占位符与修改文本是否填齐，非文献溯源）/ `consistency_check.py` / `final_consistency_report.py` / `html_format_check.py`
- `risk_check.py`：检测虚构实验/统计、过度承诺、AI 式套话、跨 unit 结构重复
- `citation_guard.py`：验证 `citation_registry.json` 新增引用真实性（DOI/PMID/撤稿检测）；`--offline` 跳过在线验证
- `citation_ref_tracker.py`：交叉验证 `[N]` 引用编号一致性（未定义引用、编号间隙）

Re-Render 单独脚本：`render_from_atomic_json.py`（重渲）、`state_manager.py`（状态同步 `sync`/`show`/`set`/`init`；改 units 前后用 `snapshot`/`rollback` 建还原点与回滚）。

## References
按需加载，不要全部预加载：
- Atomic schema: `references/atomic-unit-schema.json` — 单元 JSON 结构定义（原子化构建时参考）
- Atomic workflow: `references/atomic-workflow.md` — 原子化流程详细说明（首次使用或遇到异常时）
- HTML structural skeleton: `references/html-template-full.html` — 主交付物布局骨架（grid + sidebar + content 结构）；实际渲染由 `scripts/build_full_package.py` 的 `render_html()` 生成完整 UI（含折叠/展开、拖拽分割线、复制按钮、severity 背景色、localStorage 持久化）
- Single-comment fill template: `references/html-template.html` — 单条 comment 的占位符填充骨架，仅配合 `html-fill-guide.md` 手工填单页时使用；与上面的整包骨架 `html-template-full.html` 不同
- Output contract: `references/output-template.md` — 输出规范（核对交付物结构时）
- Decision rules and sentence patterns: `references/decision-rules.md` — 回复措辞决策规则（撰写英文回复时）
- HTML filling notes: `references/html-fill-guide.md` — `html-template.html` 占位符填写注意事项（手工填单页或渲染异常时）
- Figure prompt template: `references/figure-prompt-template.md` — 图片修改/新增时的结构化提示词模板（Output Contract 第3块图片需求时）
- Consistency rules: `references/consistency-rules.json` — `consistency_check.py` 默认加载的一致性规则集（无需手动引用，gate 自动读取）
