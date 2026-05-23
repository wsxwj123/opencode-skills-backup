---
name: sci2doc
description: 用于将SCI论文材料转化为中文博士学位论文草稿，执行严格的章节结构、原子化Markdown工作流、门禁检查和版本回滚。当用户提到博士论文、学位论文、毕业论文、学位论文写作、SCI转论文、SCI转博士论文、把文章写成论文、doctoral thesis、dissertation 时优先调用。
---

# Sci2Doc

## Overview

This skill converts SCI paper materials (PDF/Word plus user context) into a Chinese doctoral thesis draft.

This skill is process-first, not one-shot generation.

The workflow is built around:
- `state_manager.py` for anti-forgetfulness, token budgeting, gate checks, snapshot/rollback
- `atomic_md_workflow.py` for atomic subsection markdown files, numbering validation, merge, self-check, section-level snapshot

## 快速流程索引 (Quick Workflow Index)

执行前必看——全流程 7 步顺序如下，详细说明见各节。

| 步骤 | 操作 | 阻断条件 | 详见 |
|------|------|----------|------|
| **0. 材料确认** | 确认源材料可访问、用户提供论文题目/章数/院校 | 材料缺失 → 停止 | `### 0) Material Input Gate` |
| **1. 样式选择** | 询问 CSU默认 or 自定义；写入 `thesis_profile.json` | 自定义信息不完整 → `pending_template` | `## Style Selection Gate` |
| **2. 初始化项目** | `state_manager.py init`；验证 profile；协商章节字数目标 | profile 缺字段 → 不允许生成 docx | `### 1) Initialize Project` |
| **3. 文献检索** | 学科路由（生命科学→PubMed CLI / CS/AI→paper-search MCP）；运行 citation_guard | guard `ok=false` → 停止写作 | `## Citation Zero-Hallucination Gate` |
| **4. 预写门禁** | `write-cycle --chapter N` 加载跨章记忆 | 每章每节必做，不可跳过 | `### 2) Prewrite Gate` |
| **5. 原子化写作** | 每节一个 `.md`；写完验证编号+实验映射；更新 `chapter_index.json`；原始图不可用时生成 Figure Prompt | 编号断裂 → 修复后才能继续 | `### 3) Atomic Subsection Writing` |
| **6. 快照与质量门** | 节后快照；章后 self-check；humanizer 去 AI 化 | self-check 失败 → 修复 | `### 4) / ### 5) / ### 6)` |
| **7. 合并导出** | merge → gate-check → generate Word | format acceptance 未通过 → 不交付 | `### 7) / ### 8) / ### 9)` |

---

## Style Selection Gate (Mandatory)

> **执行顺序：** 本 Gate 在 `### 0) Material Input Gate` 完成后执行（先确认材料，再选样式）。如无源材料，停在 Step 0，不进入 Style Selection。

Before any project initialization or drafting, the AI **must** present exactly two style options and require the user to choose one:

1. `默认设置` — use the built-in Central South University (中南大学) doctoral thesis style.
2. `自定义样式` — user must provide the target university plus detailed Word formatting requirements and/or reference template materials.

Rules:
- The choice must be written to local state via `thesis_profile.json > format_profile`.
- `project_state.json > progress.status` must mirror the operational state.
- If the user chooses custom style but the template information is incomplete, the project may still be initialized, but it **must** be marked as `pending_template`.
- `custom` can become `ready` only after the AI writes structured layout fields into local state, at minimum:
  - `format_profile.page_margins_cm.top|bottom|left|right`
  - `format_profile.header_distance_cm`
  - `format_profile.footer_distance_cm`
  - `format_profile.university_name`
  - `format_profile.degree_type`
- For requirement-driven customization, AI should prefer writing structured rules into `format_profile.style_profile` when the user provides explicit font/size/spacing/table/front-matter requirements instead of a `.docx/.dotx` file.
- `pending_template` projects may continue collecting requirements and drafting source markdown, but **must not** generate `.docx` or run final format acceptance.
- Do not silently inherit CSU layout numbers when switching a project from `default_csu` to `custom`. Missing structured custom layout fields mean `pending_template`, not `ready`.
- Built-in automated Word formatting defaults to CSU only for `default_csu`. For `custom ready`, scripts must read local structured fields instead of hardcoded CSU constants.
- Custom template evidence files should be stored under `04_图表文件/` or referenced by absolute path in `format_profile.source_template_files`.
- `state_manager.py init` and `state_manager.py profile` must automatically render managed front matter files into:
  - `atomic_md/封面.md`
  - `atomic_md/题名页.md`
  - `atomic_md/独创性声明与授权书.md`
  - `atomic_md/中文摘要.md`
  - `atomic_md/英文摘要.md`
  - `atomic_md/目录.md`
  - `atomic_md/缩略语表.md`
  - `02_分章节文档/封面.docx`
  - `02_分章节文档/题名页.docx`
  - `02_分章节文档/独创性声明与授权书.docx`
  - `02_分章节文档/中文摘要.docx`
  - `02_分章节文档/英文摘要.docx`
  - `02_分章节文档/目录.docx`
  - `02_分章节文档/缩略语表.docx`
- If a front matter markdown file has been manually rewritten and no longer carries the managed marker, scripts must not silently overwrite it.
- If `format_profile.status == pending_template`, managed front matter markdown may still be refreshed, but managed `.docx` front matter must be skipped.

## Non-Negotiable Requirements

1. Body text target is **at least 80,000 Chinese characters**.
2. Chapter-level target allocation is **not hardcoded** and must be negotiated with the user for each project.
3. Chinese abstract must be **1500-2500 characters**.
4. Main structure is fixed:
- independent Introduction chapter
- multiple research chapters
- independent final Conclusion/Outlook chapter
- total chapters >= 5
5. References are unified at the end of the full thesis.
6. Review article content is handled separately by the user and is out of this skill's body target scope.
7. For research chapters, Results & Discussion must map to Methods experiment-by-experiment.
8. One experiment must map to at least one standalone figure or table.
9. Atomic markdown is mandatory:
- one subsection per `.md`
- continuous numbering
- merge to chapter/full `.md` before Word conversion
10. Chapter completion requires immediate self-check.
11. Each subsection summary completion requires immediate snapshot.
12. Humanization is required before finalizing chapter text; use humanizer-zh principles to reduce mechanical AI style.
13. Do not invent experimental data.
13.1 Do not invent references; citation hallucination is forbidden.
14. Literature retrieval follows topic-dependent routing (MANDATORY):
    - Life science / medicine / clinical / biochemistry / pharmacology → **PubMed CLI first** (`esearch`/`efetch`/`einfo`, `~/edirect/`, requires `< /dev/null`, proxy `http://127.0.0.1:7897`). Auto-install if missing: `sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"`.
    - CS / AI / engineering / physics / interdisciplinary → **paper-search MCP first** (`mcp__paper-search-mcp__search_arxiv` etc.).
    - Fallback to the other source when primary yields no results. All calls serial ≥1s (see rule 15 below).
    - **Forbidden:** `tavily`, `websearch`, `openalex` (pyalex).
15. Abbreviation consistency is mandatory:
    - First occurrence of any abbreviation must expand as: `中文全称（English Full Name, ABBR）`
    - All subsequent occurrences use bare abbreviation only, no re-expansion.
    - Use `abbreviation_registry.py` to register, track, and auto-strip redundant expansions.
    - A formal abbreviation table page (three-line format, alphabetically sorted) must be generated in front matter.
16. Three-line table format is mandatory for all tables:
    - Top border: 1.5pt solid
    - Header-body separator: 0.5pt solid
    - Bottom border: 1.5pt solid
    - No vertical lines, no other horizontal lines
    - Use Markdown `| col1 | col2 |` syntax in atomic `.md` files; `markdown_to_docx.py` auto-converts to Word three-line tables.
    - Table captions use five-point KaiTi (楷体五号, 10.5pt), centered above the table.
17. Writing style constraints are mandatory:
    - No em dashes (——). Use commas, periods, or restructure the sentence instead.
    - Statements only, no rhetorical or direct questions in body text. Every sentence must be declarative.
    - Result descriptions must be objective, fair, and neutral. No subjective adjectives (e.g. 令人惊讶的、显著优于、远超预期). State data and let readers judge.
    - Result discussions must be correct, precise, and provide extended analysis (e.g. compare with prior work, explain mechanisms, note limitations).
    - Language must be plain and accessible. Avoid overly formal/literary phrasing, archaic words, and jargon without explanation.
    - No metaphors of any kind (e.g. 如同、好比、仿佛、犹如、像...一样、...的桥梁、...的基石).
    - No parallelism/排比 constructions (e.g. repeating sentence patterns for rhetorical effect).
    - Use `check_quality.py` `check_writing_style()` to auto-detect violations.
18. Formatting alignment rules are mandatory:
    - Body text (正文) must use justified alignment (两端对齐, `WD_ALIGN_PARAGRAPH.JUSTIFY`), not left-aligned.
    - All three-line table cell text must be center-aligned (居中).
    - All figure placeholders must be center-aligned with no first-line indent.
19. Bold marker handling in body text:
    - `**text**` and `__text__` Markdown bold markers must be stripped during Word conversion; body text should not contain bold formatting.
    - Single `*` used for statistical significance (e.g. `*p<0.05`, `*P<0.01`) must be preserved as-is.
    - `strip_bold_markers()` in `markdown_to_docx.py` handles this automatically.

## Citation Zero-Hallucination Gate (Mandatory)

Before writing any chapter section and before final full-thesis merge, run:

`python3 scripts/citation_guard.py --index "${save_path}/literature_index.json" --mcp-cache "${save_path}/mcp_literature_cache.json" --mcp-ttl-days 30 --manual-review "${save_path}/manual_review_queue.json" --log "${save_path}/verification_run_log.json" --report "${save_path}/citation_guard_report.json"`

Rules:
- Immediately after each retrieval/import batch updates `literature_index.json`, run the guard once before any drafting.
- If guard exits non-zero or report `ok=false`, stop writing and resolve the queue first.
- When bidirectional verification fails (`title_mismatch`|`doi_invalid_or_unresolved`|`pmid_invalid_or_unresolved`|`id_mismatch`), set `verified=false` immediately and route entry to `manual_review_queue` for manual confirmation before正文引用.
- Unverified references must not be cited in chapter markdown.
- Every cited entry must carry traceability fields (`source_provider` + `source_id`) and DOI/PMID whenever available.

**`literature_index.json` 必需字段 schema（每条文献一个 JSON 对象，存入顶层数组）：**

```json
[
  {
    "id": "ref001",
    "title": "文章完整标题（从检索结果复制，勿手写）",
    "authors": ["Author A", "Author B"],
    "year": 2023,
    "journal": "Journal Name",
    "doi": "10.xxxx/xxxxx",
    "pmid": "12345678",
    "source_provider": "pubmed-cli",
    "source_id": "12345678",
    "chapter": 2,
    "verified": false
  }
]
```

字段规则：`source_provider` 只允许 `"pubmed-cli"` 或 `"paper-search"`；`doi`/`pmid` 至少填一个；`verified` 初始为 `false`，citation_guard 通过后由脚本置 `true`；`chapter` 为该文献首次引用的章节号；未知字段填空字符串，**严禁填写推测值**。

- Source provider policy is strict:
  - Allowed: `pubmed-cli` (life science primary, esearch/efetch/einfo，~/edirect/，需 < /dev/null，代理 http://127.0.0.1:7897), `paper-search` (CS/AI primary / fallback / preprints: arXiv/bioRxiv).
  - Forbidden: `websearch`, `openalex-cli` (pyalex), `tavily` provider entries.
  - **严禁** 使用 `tavily`、`websearch` 或 `openalex`（pyalex）查文献，无论有无 DOI/PMID.
  - **Serial Search (MANDATORY):** Execute all retrieval calls sequentially (PubMed CLI and paper-search MCP alike). Never parallelize search requests. Enforce ≥1s interval between consecutive calls.
  - **Citation Type by Context (MANDATORY):**
    - Background / field overview → Reviews or Systematic Reviews preferred.
    - Specific mechanistic/experimental claims → Original Articles (mandatory primary evidence; do NOT substitute a Review as the sole support for a specific experimental claim).
    - Clinical efficacy/safety claims → Clinical Trials (same priority as Original Articles for clinical evidence).
    - Emerging/cutting-edge claims → Preprints (only when no peer-reviewed equivalent exists; label as [Preprint] in citation list).
- This guard does not change existing chapter writing workflow; it only validates reference correctness.
- For final delivery strict mode, run with `--require-mcp`.

## Single Source of Truth

The thesis target profile is stored in:
- `thesis_profile.json`

The style choice and formatting gate are also stored there:
- `format_profile.mode`: `default_csu` | `custom`
- `format_profile.status`: `ready` | `pending_template`
- `format_profile.source_template_files`
- `format_profile.requirements_summary`
- `format_profile.missing_requirements`
- `format_profile.allow_docx_generation`
- `format_profile.page_margins_cm`
- `format_profile.header_distance_cm`
- `format_profile.footer_distance_cm`
- `format_profile.header_left_text`
- `format_profile.graduate_school_name`
- `format_profile.declaration_authorization_school_name`
- `format_profile.school_code`
- `format_profile.style_profile`
- `format_profile.page_numbering`

Default profile is created by `state_manager.py init` and can be updated with:
- `state_manager.py profile`

Preferred structured update entrypoints:
- `state_manager.py profile --format-profile-json '{...}'`
- `state_manager.py profile --project-info-json '{...}'`

Structured payload rules:
- `--format-profile-json` and `--project-info-json` must decode to JSON objects only.
- Scripts must reject unknown top-level keys or wrong field types instead of silently ignoring them.
- `format_profile.page_numbering` is the canonical location for page-number orchestration:
  - `front_matter.format|start`
  - `body.format|start`
  - `back_matter.format|start`
- Allowed page number formats are:
  - `decimal`
  - `lowerRoman`
  - `upperRoman`
  - `lowerLetter`
  - `upperLetter`
- Requirement-only customization should be mapped into structured fields first:
  - page layout -> `page_margins_cm`, `header_distance_cm`, `footer_distance_cm`
  - body/heading/table/abstract rules -> `style_profile`
  - page numbering switch points -> `page_numbering`
- If the user only gives narrative formatting rules and those rules are still insufficient to fill the required structured fields, keep the project in `pending_template`.

`project_info_json` should be used for front matter content such as:
- `classification`
- `udc`
- `abstract_zh`
- `keywords_zh`
- `abstract_en`
- `keywords_en`

`project_state.json` mirrors the actionable runtime status. When custom requirements are incomplete, `progress.status` must be `pending_template`.

All scripts should follow this profile to avoid rule conflicts and to prevent accidental export under the wrong school format.

## Project Directory Structure

After `init`, the project root contains exactly these directories and files. **Do NOT create any directories outside this list.**

```
${save_path}/
├── atomic_md/              # 原子化 markdown（唯一写作源）
│   ├── 第1章/
│   │   ├── 1.1_引言.md
│   │   └── ...
│   ├── 第2章/
│   └── 缩略词表.md
├── 02_分章节文档/           # 单章 docx 输出（merge --to-docx）
├── 02_分章节文档_md/        # 单章 md 合并中间产物
├── 03_合并文档/             # 全文 docx 输出（merge-full --to-docx）
├── 03_合并文档_md/          # 全文 md 合并中间产物
├── 04_图表文件/             # 图表描述文件 + 自定义格式模板证据文件（AI/用户手动放置）
├── .state/                 # gate-check 状态
├── backups/                # 快照备份（自动创建）
├── snapshots/              # section-snapshot（自动创建）
├── project_state.json      # 项目状态
├── thesis_profile.json     # 论文配置
├── context_memory.md       # 运行时上下文记忆
├── chapter_index.json      # 章节结构索引
├── literature_index.json   # 文献引用索引
├── figures_index.json      # 图表引用索引
├── figure_map.json         # SCI图号→论文图号映射（自动生成）
├── history_log.json        # 操作历史
└── abbreviation_registry.json  # 缩写注册表（自动生成）
```

### Anti-Drift Rule (Mandatory)

AI **must not** create directories outside the above list. Specifically:
- ❌ `01_文献分析/` — removed, never used by any script
- ❌ `05_参考文献/` — removed, never used by any script
- ❌ `chapter_memory/` — removed, never used by any script
- ❌ `chapters/` — not a project directory
- ❌ `output/` — not a project directory; use `02_分章节文档/` for chapter docx
- ❌ `front_matter/` — not a project directory; front matter goes in `atomic_md/`

If the AI needs to store any new artifact, it must go into one of the existing directories above. Creating ad-hoc directories is a workflow violation.

## Prewrite Memory Loading (Critical)

When `write-cycle` runs, `load_state` automatically loads:

1. `project_state.json` — project metadata, progress, and **outline** (大纲)
2. `chapter_index.json` — chapter structure with section titles (filtered to current chapter)
3. `literature_index.json` — references (filtered to current chapter)
4. `figures_index.json` — figures/tables (filtered to current chapter)
5. `context_memory.md` — timestamped operation summaries
6. `history_log.json` — recent operation events
7. **`chapter_section_digests`** — lightweight digests extracted from existing `atomic_md/第N章/*.md` files

Item 7 is the cross-section consistency mechanism. It does NOT load full markdown content (that would blow the token budget). Instead, it extracts only:
- Headings (section structure)
- Table captions (表 X-X：...)
- Key experimental facts (grouping, reagents, concentrations, methods — max 10 per section, 80 chars each)
- Character count (progress tracking)

This gives the AI enough context to avoid contradicting earlier subsections (e.g. wrong experimental design, wrong reagent lists) without consuming significant tokens.

### AI Responsibility: Update chapter_index.json

After writing each subsection, the AI **must** update `chapter_index.json` with key facts from that section. This is the primary structured memory that persists across sessions. The digest mechanism is a safety net, not a replacement.

Example entry:
```json
{
  "chapter": "2",
  "section": "2.1",
  "title": "实验材料与试剂",
  "key_facts": ["PMG浓度梯度: 0, 5, 10, 20 μg/mL", "细胞系: HepG2, LO2", "Western blot检测蛋白表达"],
  "tables": ["表 2-1：主要试剂及来源", "表 2-2：主要仪器设备"]
}
```

**Rule**: Never skip `write-cycle` before writing a new subsection. It is the only mechanism that loads cross-section memory.

## Required Workflow

### 0) Material Input Gate (Mandatory)

Before initializing any project, verify:
- Source materials (PDF/Word SCI papers + supplementary figures) are accessible at a known local path.
- User has provided: thesis topic, research chapter count estimate, target university (or explicit consent to use CSU default).

If source materials are missing or inaccessible, **stop and request them**. Do not proceed to Step 1.

**SCI 论文内容提取（必做）：** 确认材料可访问后，在进入 Step 1 前，必须将 SCI 论文内容提取为可读文本：

- **PDF 格式** → 使用 `/pdf` skill（`pdf-viewer:view-pdf`）逐页阅读，或在用户本地运行：
  ```bash
  # 使用 pdfminer 提取（无需联网）
  python3 -c "import pdfminer.high_level; print(pdfminer.high_level.extract_text('paper.pdf'))" > paper_text.txt
  ```
  若 pdfminer 未安装：`pip3 install pdfminer.six`
- **Word 格式** → 使用 `/docx` skill 或直接 Read 工具读取文件内容
- **网络来源（DOI 可访问）** → 使用 `/fetch-everything` skill 抓取全文

提取完成后，AI 应先通读全文摘要（Abstract）、结果（Results）、方法（Methods）三节，形成对实验内容的基本理解，再进入 Step 1。

### 1) Initialize Project

First choose one style path.

Default CSU style:

```bash
python3 scripts/state_manager.py --project-root "${save_path}" init \
  --title "论文中文题目" --author "作者姓名" --major "学科" \
  --format-mode default_csu
```

Custom style with incomplete requirements allowed:

```bash
python3 scripts/state_manager.py --project-root "${save_path}" init \
  --title "论文中文题目" --author "作者姓名" --major "学科" \
  --format-mode custom --university-name "目标院校" --degree-type "博士学位论文" \
  --template-source "${save_path}/04_图表文件/格式规范.pdf" \
  --missing-requirement "页边距规范" --missing-requirement "页眉页脚规范"
```

If custom style is still incomplete, the project must stay in `pending_template`.

Then verify profile:

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile --show
```

If front matter needs to be regenerated manually:

```bash
python3 scripts/state_manager.py --project-root "${save_path}" render-front-matter
```

If needed, update negotiated targets:

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile \
  --body-target 80000 --abstract-min 1500 --abstract-max 2500 \
  --references-min 80 --min-chapters 5 \
  --chapter-target 1:12000 --chapter-target 2:17000
```

When custom requirements are supplemented later, update the local profile first:

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile \
  --format-mode custom --university-name "目标院校" --degree-type "博士学位论文" \
  --template-source "${save_path}/04_图表文件/格式规范.pdf" \
  --format-requirement "A4，上下 2.54cm，左右 3.17cm，页眉 1.5cm，页脚 1.75cm" \
  --top-margin-cm 2.54 --bottom-margin-cm 2.54 \
  --left-margin-cm 3.17 --right-margin-cm 3.17 \
  --header-distance-cm 1.5 --footer-distance-cm 1.75 \
  --graduate-school-name "目标院校研究生院" \
  --declaration-school-name "目标院校"
```

If the user only gives a template path or prose notes but no structured layout numbers, keep the project in `pending_template`.

Initialization and profile updates must auto-refresh managed front matter files. User-edited front matter files without the managed marker must be left untouched.
When the user provides detailed requirements in chat, AI should convert them into structured JSON and write them through `--format-profile-json` / `--project-info-json` instead of leaving them only in prose memory.

### 2) Prewrite Gate (Mandatory)

```bash
python3 scripts/state_manager.py --project-root "${save_path}" \
  write-cycle --chapter 2 --token-budget 6000 --tail-lines 80 --json-summary
```

### 3) Atomic Subsection Writing

Store subsection files under:
- `${save_path}/atomic_md/第{chapter}章/`

Filename pattern:
- `{section_number}_{section_title}.md`
- Example: `2.1_研究对象.md`

**Table reminder**: Any subsection presenting structured data (reagents, instruments, grouping, statistical results, etc.) **must** include a Markdown pipe table. See [Table Contract](#table-contract) for syntax. Do NOT describe tabular data in prose — use a table.

Validate numbering:

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  validate --chapter 2
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  validate --chapter 2 --enforce-research-structure
```

Validate experiment mapping and one-experiment-one-figure/table:

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  validate-experiment-map --chapter 2
```

**Post-write (Mandatory after each subsection):**

```bash
# Extract + register + strip redundant abbreviation expansions
python3 scripts/abbreviation_registry.py --project-root "${save_path}" \
  process --file "${md_file}" --chapter 2 --section 2.1 --in-place
```

After running the above: update `chapter_index.json` with key facts from this section (AI responsibility), then proceed to Step 4 (Snapshot).

### 4) Subsection Summary Snapshot

After finishing each subsection summary:

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  section-snapshot --chapter 2 --section 2.1
```

### 5) Merge Chapter Markdown and Convert

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  merge --chapter 2 --to-docx
```

Hard gate:
- If `format_profile.status == pending_template`, `markdown_to_docx.py` must reject `.docx` generation.
- Do not bypass this by manually calling the converter.

### 6) Chapter Self-Check (Immediate)

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  self-check --target "${save_path}/02_分章节文档/第2章_自动合并.docx"
```

Notes:
- If `format_profile.status == pending_template`, `check_quality.py` must reject format acceptance and instruct the user to补齐模板要求 first.
- If `chapter_targets` is configured, chapter self-check uses that chapter target first.
- Chapter self-check does not enforce full-thesis references minimum; references minimum is enforced in full-thesis check.

### 7) Finalize Chapter State

```bash
python3 scripts/state_manager.py --project-root "${save_path}" \
  write-cycle --chapter 2 --finalize --summary "第2章完成并通过自检" --snapshot
```

### 8) Merge Full Markdown and Full Word

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" merge-full --to-docx
```

Rule:
- `merge-full` must include root-level front matter markdown files from `atomic_md/` before正文合并内容。

Optional high-fidelity chapter docx merge:

```bash
python3 scripts/merge_chapters.py \
  --project-root "${save_path}" \
  --input-dir "${save_path}/02_分章节文档" \
  --output "${save_path}/03_合并文档/完整博士论文.docx" \
  --require-high-fidelity
```

Compatibility rule:
- `merge_documents.py` must prefer materialized front matter docx files in `02_分章节文档/` and include `封面`、`题名页`、`独创性声明与授权书` by default when present.

### 9) Full Thesis Checks

```bash
# 字数统计（支持 .md / atomic_md 目录，自动检测路径类型）
python3 scripts/state_manager.py --project-root "${save_path}" word-count
# 或直接指定路径：
python3 scripts/count_words.py "${save_path}/atomic_md"
python3 scripts/count_words.py "${save_path}/atomic_md/第2章/2.1_引言.md"

python3 scripts/check_quality.py "${save_path}/03_合并文档/完整博士论文.docx" \
  --output json --enforce-full-structure
```

### 10) Rollback if Needed

```bash
python3 scripts/state_manager.py --project-root "${save_path}" rollback --target snapshot
python3 scripts/state_manager.py --project-root "${save_path}" rollback --target snapshot --strict-mirror
```

## Chapter Structure Contract

For each research chapter (Chapter 2 to Chapter N-1), keep this order:

1. 引言
2. 材料与方法
3. 结果与讨论
4. 实验结论
5. 小结

Rules:
- Results & Discussion is coupled with each method experiment.
- Do not place all results first and discuss later in a separate bulk section.
- **材料与方法 must contain tables** for at least: 实验试剂与耗材, 实验仪器与设备, 实验分组设计. Use Markdown pipe syntax (`| col | col |`). Never describe these as prose paragraphs.
- **结果与讨论 must contain tables** when presenting quantitative/statistical data (e.g. 各组指标比较). Use Markdown pipe syntax.
- Marker convention in subsection markdown:
- `[实验] EXP-2-1` in methods
- `[对应实验] EXP-2-1` in results/discussion
- `[图] 图2-1` or `[表] 表2-1` linked to current experiment

## Outline Contract

The thesis outline must include:

- Cover/title page
- Originality and authorization statements
- Chinese abstract + keywords
- English abstract + keywords
- Table of contents (+ figure/table lists if needed)
- Symbol/abbreviation list (if needed)
- Chapter 1 Introduction
- Multiple research chapters (>= 3 research chapters recommended for total >= 5 chapters)
- Final conclusion/outlook chapter
- References at end
- Acknowledgements
- Achievements during doctoral period (papers/patents/awards)

## Abbreviation Contract

Rules:
- Before writing any new section, query the abbreviation registry to check which abbreviations are already known.
- When introducing a new abbreviation for the first time, use the full pattern: `中文全称（English Full Name, ABBR）`
- After the first occurrence is registered, all subsequent uses must be the bare abbreviation only.
- After AI generates a section markdown, run `abbreviation_registry.py process` to extract, register, and strip redundant expansions before saving.
- The abbreviation table page is auto-generated from the registry during full-thesis Word conversion.

CLI quick reference:

```bash
# Query before writing
python3 scripts/abbreviation_registry.py --project-root "${save_path}" list

# Process after writing a section (extract + register + strip)
python3 scripts/abbreviation_registry.py --project-root "${save_path}" \
  process --file "${md_file}" --chapter 2 --section 2.1 --in-place

# Generate abbreviation table markdown
python3 scripts/abbreviation_registry.py --project-root "${save_path}" table

# Validate cross-references (registry entries vs actual markdown files)
python3 scripts/abbreviation_registry.py --project-root "${save_path}" validate
```

## Humanization Contract

Before finalizing each chapter:

1. Run technical self-check (word count + quality):
   ```bash
   python3 scripts/atomic_md_workflow.py --project-root "${save_path}" self-check --target "${save_path}/02_分章节文档/第N章_自动合并.docx"
   ```
2. Invoke the `/humanizer-zh` skill on the chapter's merged markdown. The skill rewrites the text in-place; confirm the output before saving. If `/humanizer-zh` is unavailable, manually apply the following checklist to every paragraph:
   - [ ] **无模板化过渡句**：删除"综上所述"、"值得注意的是"、"由此可见"等空洞衔接词
   - [ ] **无重复排比**：连续出现≥3个句式相同的句子→合并或改写
   - [ ] **无空洞宏观主张**：每段必须有具体数据或实验结果支撑，不允许纯观点段落
   - [ ] **证据先于结论**：数据/观测在前，解释/结论在后；不允许倒置
   - [ ] **无破折号（——）**：改用逗号、句号或拆句
   - [ ] **无修辞疑问/反问**：所有句子必须陈述句
   - [ ] **无比喻/排比**：删除"如同"、"犹如"、"是…的桥梁"等表达
3. Re-run self-check to confirm no regressions (特别检查 writing_style 类问题归零)
4. Finalize snapshot + gate completion

## Table Contract

All data tables in the thesis must use three-line (三线表) format.

### Markdown Syntax in Atomic `.md` Files

Write tables using standard Markdown pipe syntax:

```markdown
表 2-1：主要实验试剂

| 试剂名称 | 规格 | 生产厂家 |
|---|---|---|
| 胎牛血清 | 500 mL | Gibco |
| DMEM培养基 | 高糖型 | HyClone |
```

Rules:
- Caption line (`表 X-X：标题`) must appear directly above the table.
- Separator row (`|---|---|---|`) is required between header and data rows.
- No empty rows between caption and table header.
- `markdown_to_docx.py` automatically converts this to a Word three-line table with correct borders.

### Applicable Sections

Three-line tables are mandatory in (but not limited to):
- 实验试剂与耗材 — columns: 试剂名称, 规格/货号, 生产厂家
- 实验仪器与设备 — columns: 仪器名称, 型号, 生产厂家
- 实验分组设计 — columns: 组别, 处理方式, 样本数
- 数据统计结果 — columns vary by experiment
- Any section presenting structured data

**Writing rule**: If a subsection contains 3+ items sharing the same attributes (name+spec+source, group+treatment+n, etc.), it MUST be written as a Markdown pipe table, never as a prose list or paragraph.

### Quality Check

```bash
python3 scripts/check_quality.py "${save_path}/03_合并文档/完整博士论文.docx" \
  --output json --enforce-full-structure
```

The quality checker validates: no vertical lines, correct border weights (1.5pt top/bottom, 0.5pt header line).

## Word Format Specification (CSU Standard)

完整字体、字号、页边距、页眉页脚、三线表边框等参数详见 `references/word-format-spec.md`（中南大学博士学位论文标准，由 `markdown_to_docx.py` 硬编码实现，`check_quality.py` 强制校验）。

## Figure Numbering Contract

All figures must be tracked via `figure_map.json` to maintain consistent numbering between SCI source papers and the Chinese thesis.

### Numbering Rule

Chinese figure IDs follow the pattern `图{chapter}-{seq}`:
- `图1-1`, `图2-3`, `图5-6`
- Chapter number = thesis chapter (not the SCI paper figure number)
- Sequence number = order within that chapter (1-based, continuous)

### SCI Source Mapping

SCI subfigure letters map to numbers: A→1, B→2, ..., F→6, ..., Z→26.

Priority rule: **chapter-based numbering takes precedence**. If a figure from SCI "Figure 6A" is placed in Chapter 2 as the 3rd figure, it becomes `图2-3` (not `图6-1`).

### Marker Convention in Atomic `.md` Files

```markdown
[图] 图2-1：PMG对HepG2细胞形态的影响（对应 Figure 1A）
```

### Workflow

1. **During writing**: Use `[图] 图N-M` markers in subsection `.md` files.
2. **Register mapping**: Run `figure_registry.py register` for each figure.
3. **Validate**: Run `figure_registry.py validate` to check continuity.
4. **Cross-validate**: Run `figure_registry.py cross-validate` to verify all markers match the registry.

### CLI Quick Reference

```bash
# Register a figure mapping
python3 scripts/figure_registry.py --project-root "${save_path}" register \
  --chapter 2 --seq 1 --source "Figure 1A" --title "PMG对HepG2细胞形态的影响"

# List all mappings (or filter by chapter)
python3 scripts/figure_registry.py --project-root "${save_path}" list --chapter 2

# Delete a mapping
python3 scripts/figure_registry.py --project-root "${save_path}" unregister --cn-id "图2-1"

# Validate continuity and uniqueness
python3 scripts/figure_registry.py --project-root "${save_path}" validate

# Cross-validate with atomic_md markers
python3 scripts/figure_registry.py --project-root "${save_path}" cross-validate --chapter 2

# Export mapping table
python3 scripts/figure_registry.py --project-root "${save_path}" export --format markdown
```

## Figure Prompt Generation（图注之外，同步生成AI绘图提示词）

For each figure referenced in the converted document where the original figure is unavailable or needs redrawing, generate a Figure Prompt block:

```
[FIGURE PROMPT — Figure N: <caption title>]
TYPE: Data plot | Schematic | Mechanistic pathway | Workflow | Statistical | Structural | Microscopy description
SUBJECT: <exact scientific content from the original paper, one sentence>
STYLE: BioRender风格, 科研示意图, 最高分辨率, white background (#FFFFFF), publication-quality [默认BioRender风格；如需其他风格（如Cell-style flat icon / Nature手绘风 / 简约线条风），在启动时告知]
COLOR SCHEME: Primary #2E86AB | Secondary #A23B72 | Accent #F18F01 | Neutral #4A4A4A | colorblind-safe
ELEMENTS:
  - <Element 1>: <derived from figure caption or manuscript description>
  - <Element 2>: <arrows, labels, key components>
LAYOUT: <inferred from caption: single/multi-panel> | <aspect ratio: 4:3 default>
TYPOGRAPHY: Arial/Helvetica, 8-10pt, English labels, panel letters bold top-left
DATA REPRESENTATION (if applicable): <chart type | axes labels from caption>
SCALE/LEGEND: <from original caption if stated | N/A>
KEY MESSAGE: <derived from the Results section paragraph that references this figure>
AVOID: 3D effects, gradients, clip art, decorative elements, photo-realistic rendering
SOURCE NOTE: Reconstructed from: <original paper DOI or figure caption text>
```

Generation rules:
- Only generate a Figure Prompt if the original figure is not available in the source PDF or needs reconstruction
- Derive all element descriptions from the figure caption + surrounding Results text — do NOT fabricate experimental data
- If microscopy/imaging data: describe as "Representative [modality] image showing [structure], [magnification] if stated, scale bar [X]μm if stated" — do NOT attempt to recreate actual experimental images
- Store all generated prompts in `${save_path}/figure_prompts.md`
- Mark each prompt with `[RECONSTRUCTED]` tag to distinguish from original figures

## Common Mistakes

1. Mistake: Hardcoding chapter targets without user negotiation.
- Fix: update `thesis_profile.json` via `state_manager.py profile`.

2. Mistake: Keeping conflicting old thresholds in docs/scripts.
- Fix: profile-driven targets only.

3. Mistake: Writing one chapter in a single large markdown file.
- Fix: atomic subsection files + validate numbering.

4. Mistake: Skipping self-check and snapshot.
- Fix: run `self-check` and `section-snapshot` as hard gates.

5. Mistake: Overly mechanical AI text in final chapter.
- Fix: run humanizer pass before finalize.

## Acceptance Checklist

- [ ] Body target >= 80,000 (configured and checked)
- [ ] Chapter targets negotiated and stored in profile
- [ ] Chinese abstract 1500-2500
- [ ] Structure meets intro + research + conclusion with >= 5 chapters
- [ ] References unified at end
- [ ] Atomic markdown workflow used and numbering validated
- [ ] Chapter self-check run immediately after chapter merge
- [ ] Subsection summary snapshots created
- [ ] Humanization pass completed before finalize
- [ ] Snapshot/rollback available and tested
- [ ] All tables use three-line format (1.5pt top/bottom, 0.5pt header, no vertical lines)
- [ ] Abbreviation registry populated and cross-reference validation passed
- [ ] No redundant abbreviation expansions in non-first-occurrence chapters
- [ ] Abbreviation table page generated in front matter
- [ ] Figure numbering registry populated and validated
- [ ] Figure cross-validation passed (all `[图]` markers registered)
- [ ] Body text uses justified alignment (两端对齐)
- [ ] All table cells center-aligned; figure placeholders centered with no indent
- [ ] Bold markers stripped from body text; significance markers (*p<0.05) preserved
- [ ] Page header: 宋体五号, left "中南大学博士学位论文", right chapter name, 1.5cm from top
- [ ] Page footer: TNR 小五号 centered page number, 1.75cm from bottom
- [ ] Chinese abstract: 三号黑体居中标题, 四号宋体正文, 关键词全角分号
- [ ] English abstract: 三号TNR居中标题, 四号TNR正文, keywords semicolon-separated
- [ ] Table of contents: 三号黑体居中标题, 章名小四黑体, 节名小四宋体, 1.5倍行距
- [ ] Table caption spacing: 段前12pt/段后0; Figure caption spacing: 段前0/段后12pt
- [ ] Three-line table header separator: 0.5pt (sz=4)
