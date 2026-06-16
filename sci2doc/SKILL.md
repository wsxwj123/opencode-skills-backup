---
name: sci2doc
description: 用于将SCI论文材料转化为中文博士学位论文草稿，执行严格的章节结构、原子化Markdown工作流、门禁检查和版本回滚。当用户提到博士论文、博士学位论文、毕业论文、SCI转论文、doctoral thesis、dissertation 时优先调用。
---

# Sci2Doc

## Overview

本技能仅适用于博士学位论文（正文 ≥8 万字 / ≥5 章），且需用户提供已成稿的 SCI 论文材料作为转化来源。若场景是硕士/本科论文，或用户没有可访问的 SCI 论文材料，主动退出本技能，不要套用本流程。

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
| **0.5. 研究主线设计** | 产出科学问题→贡献→章节映射表；协商章节字数目标；写入 `outline` | `outline` 为空 → 不得进入 Step 1 | `### 0.5) Research Storyline Design` |
| **1. 样式选择** | 询问 CSU默认 or 自定义；写入 `thesis_profile.json` | 自定义信息不完整 → `pending_template` | `## Style Selection Gate` |
| **2. 初始化项目** | `state_manager.py init`；验证 profile；章节字数已在 Step 0.5 协商 | profile 缺字段 → 不允许生成 docx | `### 1) Initialize Project` |
| **3. 文献检索** | 学科路由（生命科学→PubMed CLI / CS/AI→paper-search MCP）；运行 citation_guard | guard `ok=false` → 停止写作 | `## Citation Zero-Hallucination Gate` |
| **4. 预写门禁** | `write-cycle --chapter N` 加载跨章记忆 | 每章每节必做，不可跳过 | `### 2) Prewrite Gate` |
| **5. 原子化写作** | 每节一个 `.md`；写完验证编号+实验映射；更新 `chapter_index.json`；原始图不可用时生成 Figure Prompt | 编号断裂 → 修复后才能继续 | `### 3) Atomic Subsection Writing` |
| **6. 快照与质量门** | 节后快照；章后 self-check；humanizer 去 AI 化 | self-check 失败 → 修复 | `### 4) / ### 5) / ### 6)` |
| **7. 合并导出** | merge → gate-check → generate Word | format acceptance 未通过 → 不交付 | `### 7) / ### 8) / ### 9)` |

---

## Style Selection Gate (Mandatory)

> **执行顺序：** 本 Gate 在 `### 0) Material Input Gate` 完成后执行（先确认材料，再选样式）。如无源材料，停在 Step 0，不进入 Style Selection。

初始化或起草前，AI **必须** 让用户在两种样式中二选一：

1. `默认设置` — 内置中南大学（CSU）博士学位论文格式。
2. `自定义样式` — 用户须提供目标院校 + 详细 Word 格式要求和/或模板证据文件。

🔴 **CHECKPOINT（阻断 init）：** 未与用户明确确认样式前，**不得运行 `state_manager.py init`**。即使用户可能想用默认 CSU，也必须先得到用户对"就用中南大学默认格式"的明确确认，再带样式参数运行 init。**禁止** 因看到 QUICK_START 的 init 示例就直接套用默认 `--format-mode default_csu` 跑 init（该默认会静默落成 CSU 格式且立即放行 docx 导出）。

**硬门禁：** 自定义信息不完整的项目标记为 `pending_template`，可继续整理 markdown，但 **不得生成 `.docx`、不得运行格式验收**。`custom` 仅在写入结构化布局字段后才能转为 `ready`，否则保持 `pending_template`。

**custom→ready 最小必填字段**（缺一即保持 `pending_template`）：`page_margins_cm.top/bottom/left/right`（四个边距）、`header_distance_cm`、`footer_distance_cm`、`university_name`、`degree_type`。

字段完整定义、需求→字段映射、managed front matter 文件清单、managed marker 覆盖规则等细则见 `references/format_profile_schema.md § Style Selection Gate (full rules)`。

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
9. Atomic markdown is mandatory: one subsection per `.md`, continuous numbering, merge before Word conversion.
10. Chapter completion requires immediate self-check.
11. Each subsection summary completion requires immediate snapshot.
12. Humanization is required before finalizing chapter text；细则见 `## Humanization Contract`。
13. Do not invent experimental data.
13.1 Do not invent references; citation hallucination is forbidden.
14. Literature retrieval follows topic-dependent routing (MANDATORY)：细则见 `## Citation Zero-Hallucination Gate`。
15. 缩写一致性强制执行：首次展开格式 `中文全称（English Full Name, ABBR）`，后续裸缩写；用 `abbreviation_registry.py` 管理；需生成前置缩略语表。细则见 `## Abbreviation Contract`。
16. 三线表格式强制：所有数据表使用 Markdown 管道语法，`markdown_to_docx.py` 自动转换；边框参数与题注字体字号见 `references/word-format-spec.md § Three-Line Table Borders`。细则见 `## Table Contract`。
17. 文风约束：见 `## Humanization Contract`（清单集中在那里）；`check_quality.py check_writing_style()` 自动检测，违规必须清零后才能 finalize。
18. 格式对齐规则：正文两端对齐、三线表单元格居中、图占位符居中无首行缩进。完整参数见 `references/word-format-spec.md`。
19. Bold marker 处理：`**text**` / `__text__` 在 Word 转换时由 `strip_bold_markers()` 自动剥除；单 `*` 统计显著性标记（如 `*p<0.05`）保留原样。
20. 已发表 SCI 内容复用合规底线：
    - 正文复用必须**改写**为中文学术表述，不得直接翻译粘贴。
    - 每章首次复用处必须标注来源文献（正文引用 [N] + 声明"本章部分内容已发表于 [N]"）。
    - 复用成果须同时体现在"攻读学位期间取得的成果"清单与"独创性声明"中。
    - 缺标注的已发表内容复用等同未注明引用，触发学位办自我抄袭/重复发表红线。

## Citation Zero-Hallucination Gate (Mandatory)

Before writing any chapter section and before final full-thesis merge, run:

`python3 scripts/citation_guard.py --index "${save_path}/literature_index.json" --mcp-cache "${save_path}/mcp_literature_cache.json" --mcp-ttl-days 30 --manual-review "${save_path}/manual_review_queue.json" --log "${save_path}/verification_run_log.json" --report "${save_path}/citation_guard_report.json"`

Rules:
- Immediately after each retrieval/import batch updates `literature_index.json`, run the guard once before any drafting.
- If guard exits non-zero or report `ok=false`, stop writing and resolve the queue first.
- When bidirectional verification fails (`title_mismatch`|`doi_invalid_or_unresolved`|`pmid_invalid_or_unresolved`|`id_mismatch`), set `verified=false` immediately and route entry to `manual_review_queue` for manual confirmation before正文引用.
- Unverified references must not be cited in chapter markdown.
- Every cited entry must carry traceability fields (`source_provider` + `source_id`) and DOI/PMID whenever available.

**Topic-dependent routing (MANDATORY):**
- Life science / medicine / clinical / biochemistry / pharmacology → **PubMed CLI first** (`esearch`/`efetch`/`einfo`, `~/edirect/`, requires `< /dev/null`, proxy `http://127.0.0.1:7897`). Auto-install if missing: `sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"`.
- CS / AI / engineering / physics / interdisciplinary → **paper-search MCP first** (`mcp__paper-search-mcp__search_arxiv` etc.).
- Fallback to the other source when primary yields no results.

`literature_index.json` 必需字段 schema 见 `references/format_profile_schema.md § literature_index.json schema`。

- Source provider policy is strict:
  - Allowed: `pubmed-cli` (life science primary), `paper-search` (CS/AI primary / fallback / preprints).
  - Forbidden: `websearch`, `openalex-cli` (pyalex), `tavily`。`citation_guard.py` 以 `source_provider_not_allowed` 拒绝这些来源。
  - 无 DOI/PMID 的条目不予放行，进入 `manual_review_queue` 人工核实。
  - **Serial Search (MANDATORY):** Execute all retrieval calls sequentially. Never parallelize. Enforce ≥1s interval between consecutive calls.
  - **Citation Type by Context (MANDATORY):**
    - Background / field overview → Reviews or Systematic Reviews preferred.
    - Specific mechanistic/experimental claims → Original Articles (do NOT substitute a Review as the sole support).
    - Clinical efficacy/safety claims → Clinical Trials.
    - Emerging/cutting-edge claims → Preprints (label as [Preprint]; only when no peer-reviewed equivalent exists).
- This guard does not change existing chapter writing workflow; it only validates reference correctness.
- For final delivery strict mode, run with `--require-mcp`.

## Single Source of Truth

论文目标配置存于 `thesis_profile.json`；样式选择与格式门禁存于其 `format_profile`；运行时状态镜像在 `project_state.json`。自定义要求不完整时 `progress.status` 必须为 `pending_template`（导出硬门禁见 `## Style Selection Gate`）。

`format_profile` 完整字段清单、结构化更新入口（`--format-profile-json` / `--project-info-json`）、页码格式枚举、需求→字段映射规则、`project_info` 字段，均见 `references/format_profile_schema.md § Single Source of Truth`。

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
├── backups/                # 快照备份 / section-snapshot（自动创建）
├── project_state.json      # 项目状态
├── thesis_profile.json     # 论文配置
├── context_memory.md       # 运行时上下文记忆
├── chapter_index.json      # 章节结构索引
├── literature_index.json   # 文献引用索引
├── figures_index.json      # 图表引用索引
├── figure_map.json         # SCI图号→论文图号映射（自动生成）
├── history_log.json        # 操作历史
├── abbreviation_registry.json  # 缩写注册表（自动生成）
├── mcp_literature_cache.json   # MCP 文献检索缓存（citation_guard 自动生成）
├── citation_guard_report.json  # citation_guard 运行报告（自动生成）
├── manual_review_queue.json    # 待人工核验引用队列（citation_guard 自动生成）
├── verification_run_log.json   # citation_guard 运行日志（自动生成）
└── references_rendered.md      # GB/T 7714 著录渲染输出（reference_renderer 自动生成）
```

### Anti-Drift Rule (Mandatory)

AI **must only** create or write files into the directories listed above. Any artifact that does not fit an existing directory is a workflow violation. Do not create directories outside this list.

## Prewrite Memory Loading (Critical)

When `write-cycle` runs, `load_state` automatically loads:

1. `project_state.json` — project metadata, progress, and **outline**（含研究主线 `scientific_question` + 各章 `core_argument`，是写作一致性的锚点）
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

提取完成后，AI 应先通读全文摘要（Abstract）、结果（Results）、方法（Methods）三节，形成对实验内容的基本理解，再进入 Step 0.5。

**SCI 自身参考文献导出（初始种子）：** 在通读的同时，同步扫描源 SCI 论文的 References 部分，将其中每条参考文献按 `literature_index.json` schema 格式整理为初始种子条目，`source_provider` 填 `"sci-source-seed"`，`verified` 填 `false`，写入项目的 `literature_index.json`（若文件已存在则 merge 而非覆盖）。这些种子作为 Step 3 文献检索的**待核验候选清单**（已带 DOI/PMID，省去重新构造检索式、确定检索目标的成本），而非可直接引用的来源。注意：`sci-source-seed` 不在 `citation_guard.py` 的合法 provider 白名单（`pubmed-cli` / `paper-search`）内——种子条目必须在 Step 3 以其 DOI/PMID 为目标经 `pubmed-cli` 或 `paper-search` 正式检索核验，核验通过后将 `source_provider` 更新为实际核验来源并置 `verified=true`，方可引用；未核验的种子不得进入正文。

> 以下各步只列命令名 + 关键参数 + 门禁条件。**完整可复制 CLI（含所有 flag、占位符）见 `QUICK_START.md`。**

### 0.5) Research Storyline Design (Mandatory)

> **执行时机：** Step 0（材料确认 + 内容提取）完成后、Style Selection Gate 前执行。

通读 SCI 论文材料的 Abstract / Introduction / Results / Discussion 后，AI **必须**与用户共同确定"研究主线"并产出下表，写入 `project_state.json` 的 `outline` 字段（每章一条记录）再进入 Step 1。

**强制产出：科学问题 → 贡献映射表**

| 字段 | 说明 |
|------|------|
| `scientific_question` | 全论文核心科学问题（一句话，来自材料，不得自造） |
| `chapters[]` | 每章：章号、章名、对应 SCI 论文/图组、本章核心论点、承载主要内容（300字以内） |
| `contribution_map` | 各 SCI 来源 → 对应章节（避免章节撞题） |

**写入格式（project_state.json `outline` 数组，每条一章）：**
```json
{
  "chapter": 2,
  "title": "XX对XX的影响",
  "sci_source": "Paper A, Figure 1-3",
  "core_argument": "XX通过XX机制发挥XX作用",
  "estimated_content": "材料方法+结果讨论，主实验3个，预计图表各3"
}
```

🔴 **门禁（阻断 Step 1）：** `outline` 数组为空时不得进入 Style Selection Gate。`outline` 必须包含：`scientific_question`（顶层字段）+ 所有研究章条目（含 `sci_source` 和 `core_argument`）。

**章节字数协商在此阶段完成（不在 init 后）：** 基于各章实际承载内容（实验数量/图表数量/方法复杂度），与用户协商每章字数目标，写入 profile 的 `chapter_targets`，再执行 Step 1 init。

### 1) Initialize Project

- `state_manager.py init`：先二选一样式。`--format-mode default_csu` 或 `--format-mode custom`（+ `--university-name` / `--degree-type` / `--template-source` / `--missing-requirement`）。
- `state_manager.py profile --show` 验证；`render-front-matter` 手动重渲前置页；`profile --body-target/--abstract-min/--chapter-target ...` 写入已协商好的各章字数目标（应在 Step 0.5 中已与用户确定）。
- 自定义结构化布局字段不全 → 保持 `pending_template`（最小必填字段见 `## Style Selection Gate`）。
- init / profile 必须自动刷新 managed front matter；无 managed marker 的用户改写文件不得覆盖。用户在聊天里给的详细要求应转成 JSON 经 `--format-profile-json` / `--project-info-json` 写入，而非仅留在 prose memory。

### 2) Prewrite Gate (Mandatory)

- `state_manager.py write-cycle --chapter N --token-budget 6000 --tail-lines 80 --json-summary`。每章每节必跑，加载跨章记忆。

### 3) Atomic Subsection Writing

- 文件存于 `${save_path}/atomic_md/第{chapter}章/`，命名 `{section_number}_{section_title}.md`（如 `2.1_研究对象.md`）。
- **Table reminder**：呈现结构化数据（试剂/仪器/分组/统计）的小节 **必须** 用 Markdown 管道表，见 [Table Contract](#table-contract)，不得用散文描述。
- 校验：`atomic_md_workflow.py validate --chapter N`（加 `--enforce-research-structure`）+ `validate-experiment-map --chapter N`。**门禁：** 编号断裂 → 修复后才能继续。
- Post-write 必做：`abbreviation_registry.py process --file ... --in-place`，然后更新 `chapter_index.json` key_facts（AI 责任），再进 Step 4。

### 4) Subsection Summary Snapshot

- `atomic_md_workflow.py section-snapshot --chapter N --section X.Y`。每节小结完成即快照。

#### 🔴 每节收口自检清单（Definition of Done · 节级）

**硬规则：以下各项未逐一确认通过，不得向用户声明"该节完成"。**

**🔴 进入下一节前置闸口**：上一节 `delegate_review verify` 必须 exit 0（含结构完整性项 S6），否则不得开始下一节——写完即检，不过不进。

**🔴 委托盲检（不得主 agent 自评）**：你刚写完本节，自评会失真地默认通过、且易漏项。落盘前必须把 DoD 清单**委托给独立上下文的子代理盲检**，自己不直接打勾：
1. 生成任务包：`python scripts/delegate_review.py pack --checklist references/dod_checklist.json --gate section-dod --files <本节文件>`
2. **派一个独立子代理**（Claude Code 用 `academic-blind-reviewer`；其他平台派通用子代理），把任务包原样给它、**不要给它本节的写作上下文**，要求按任务包返回 JSON 数组。
3. 校验返回：`python scripts/delegate_review.py verify --checklist references/dod_checklist.json --gate section-dod --return <子代理返回.json>`；退出码非 0（任一缺项/fail/无证据）= **fail-closed**，据子代理证据修复后重跑，**未过不得声明完成**。
- **降级路径**（当前环境无法派子代理时）：主 agent 切换"审稿人视角"、清空对本节的写作记忆，逐项独立重核——绝不因"自己刚写完"默认通过；仍跑 `verify` 把关。

下列清单与 `references/dod_checklist.json` gate=`section-dod` 逐项对应（改清单先改 JSON），供人工对照；能脚本核的项子代理会先跑脚本：

通用项（全技能共享）：
- [ ] **G1** 编号连续：引文 `[n]` 与参考列表一一对应，无孤儿编号、无缺号（脚本：`atomic_md_workflow.py validate --chapter N`）
- [ ] **G2** 新增引用已过 citation_guard（`citation_guard.py` 报告 `ok=true`）
- [ ] **G3** 符合研究主线：本节内容不跑题、不与 `outline.core_argument` 矛盾
- [ ] **G4** 占位符清零：文中无 `CITE_PENDING` / `DATA_PENDING` / `【待AI】` / `【待翻译】` 等未填占位符
- [ ] **G5** 去 AI 通过：`check_quality.py` 的 `check_writing_style()` 零违规（含中文句长 ≤50 字、AI 禁词、破折号/scare quotes/解释性冒号）
- [ ] **G6** 字数达标：本节字数贡献符合 `chapter_targets` 分配比例（估算）

sci2doc 特有项：
- [ ] **S1** 实验-方法映射标记完整：`[实验] EXP-N-M` 与 `[对应实验] EXP-N-M` 成对出现，无悬空
- [ ] **S2** 一实验 ≥ 一图表：每个 `[实验] EXP-N-M` 对应至少一个 `[图] 图N-X` 或 `[表] 表N-X`
- [ ] **S3** 三线表格式：本节所有数据表使用 Markdown 管道语法，无散文替代（脚本：`check_quality.py` 三线表类别）
- [ ] **S4** 缩略语首展：本节新引入缩略语均已按 `中文全称（English Full Name, ABBR）` 格式首展，已过 `abbreviation_registry.py process`
- [ ] **S5** 自我抄袭标注：本节复用已发表 SCI 内容处已标注来源文献 `[N]` 及声明（见 Non-Negotiable 第 20 条）

### 5) Merge Chapter Markdown and Convert

- `atomic_md_workflow.py merge --chapter N --to-docx`。
- **硬门禁：** `format_profile.status == pending_template` 时 `markdown_to_docx.py` 拒绝生成 `.docx`，不得手动绕过转换器。

### 6) Chapter Self-Check (Immediate)

- `atomic_md_workflow.py self-check --target ".../02_分章节文档/第N章_自动合并.docx"`。
- 章节自检按 `chapter_targets` 判断，不卡全文参考文献下限（在全文总检卡）。`pending_template` 时 `check_quality.py` 同样拒绝格式验收（同 Style Gate 导出门禁）。

#### 🔴 每章收口自检清单（Definition of Done · 章级）

**硬规则：以下各项未逐一确认通过，不得向用户声明"该章完成"，不得进入 Step 7。**

**🔴 进入下一章前置闸口**：上一章 `delegate_review verify` 必须 exit 0（含章结构完整性项 S8），否则不得开始下一章——写完即检，不过不进。

**🔴 委托盲检（不得主 agent 自评）**：章级闸口同样必须委托独立子代理盲检，不得主 agent 自评：
1. 生成任务包：`python scripts/delegate_review.py pack --checklist references/dod_checklist.json --gate chapter-dod --files <章节合并文件>`
2. **派一个独立子代理**（Claude Code 用 `academic-blind-reviewer`；其他平台派通用子代理），把任务包原样给它、**不要给它本章的写作上下文**，要求按任务包返回 JSON 数组。
3. 校验返回：`python scripts/delegate_review.py verify --checklist references/dod_checklist.json --gate chapter-dod --return <子代理返回.json>`；退出码非 0（任一缺项/fail/无证据）= **fail-closed**，据子代理证据修复后重跑，**未通过不得进入 Step 7**。
- **降级路径**（当前环境无法派子代理时）：主 agent 切换"审稿人视角"、清空对本章的写作记忆，逐项独立重核——绝不因"自己刚写完"默认通过；仍跑 `verify` 把关。

下列清单与 `references/dod_checklist.json` gate=`chapter-dod` 逐项对应（改清单先改 JSON），供人工对照；能脚本核的项子代理会先跑脚本：

通用项（全技能共享）：
- [ ] **G1** 全章引文编号连续，无孤儿、无缺号（脚本：`atomic_md_workflow.py validate --chapter N`）
- [ ] **G2** 本章所有引用已过 citation_guard（`citation_guard.py` 报告 `ok=true`）
- [ ] **G3** 全章内容符合 `outline` 本章 `core_argument`，无跑题
- [ ] **G4** 全章占位符清零（`CITE_PENDING` / `DATA_PENDING` / `【待AI】` 全部归零）
- [ ] **G5** 去 AI 通过：`check_quality.py check_writing_style()` 零违规（含中文句长、AI 禁词、三项标点规范）
- [ ] **G6** 本章字数达标：`count_words.py` 输出 ≥ `chapter_targets[N]`

sci2doc 特有项：
- [ ] **S1** 全章实验-方法映射完整：`atomic_md_workflow.py validate-experiment-map --chapter N` 通过
- [ ] **S2** 全章每个实验 ≥ 一图表（`figure_registry.py validate` 通过）
- [ ] **S3** 全章所有三线表格式校验通过（`check_quality.py` 三线表类别零 error）
- [ ] **S4** 缩略语注册表已更新，本章无重复首展、无遗漏（`abbreviation_registry.py validate` 通过）
- [ ] **S5** GB/T 7714 著录格式：本章新引文已过 `reference_renderer.py validate_all`，零偏差
- [ ] **S6** 自我抄袭标注完整：本章所有复用 SCI 来源处均有 `[N]` 引用 + 声明
- [ ] **S7** 章后 self-check 已跑（`atomic_md_workflow.py self-check` 输出 ok=true），无 error 级问题

### 7) Finalize Chapter State

- `state_manager.py write-cycle --chapter N --finalize --summary "..." --snapshot`。

### 8) Merge Full Markdown and Full Word

- `atomic_md_workflow.py merge-full --to-docx`。**规则：** 必须先纳入 `atomic_md/` 根级前置页 markdown，再合并正文。
- 可选高保真合并：`merge_chapters.py --input-dir .../02_分章节文档 --output .../03_合并文档/完整博士论文.docx --require-high-fidelity`。
- 兼容规则：`merge_documents.py` 优先用 `02_分章节文档/` 中已物化的前置页 docx，默认纳入 `封面`、`题名页`、`独创性声明与授权书`。

### 9) Full Thesis Checks

- 字数：`state_manager.py word-count` 或 `count_words.py <路径>`（支持 .md / atomic_md 目录）。
- 全文质检：`check_quality.py ".../完整博士论文.docx" --output json --enforce-full-structure`。

### 10) Rollback if Needed

- `state_manager.py rollback --target snapshot`（加 `--strict-mirror` 严格镜像）。

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
- **缩略语表**（Abbreviation List）：首次出现展开的英文缩略语，三线表，字母升序，auto-generated from `abbreviation_registry.py table`
- **符号表**（Symbol/Notation Table，理工科含大量数学/物理变量时必设，其他可选）：变量符号、含义、单位，三线表；见 `references/symbol_table_template.md`
- Chapter 1 Introduction
- Multiple research chapters (>= 3 research chapters recommended for total >= 5 chapters)
- Final conclusion/outlook chapter
- References at end
- Acknowledgements
- Achievements during doctoral period (papers/patents/awards)
  - 作为转化来源的已发表 SCI 论文必须全部列入此清单；正文中复用这些成果之处须与本清单及独创性声明保持一致（见 Non-Negotiable 第 20 条）。

## Abbreviation Contract

Rules:
- Before writing any new section, query the abbreviation registry to check which abbreviations are already known.
- When introducing a new abbreviation for the first time, use the full pattern: `中文全称（English Full Name, ABBR）`
- After the first occurrence is registered, all subsequent uses must be the bare abbreviation only.
- After AI generates a section markdown, run `abbreviation_registry.py process` to extract, register, and strip redundant expansions before saving.
- The abbreviation table page is auto-generated from the registry during full-thesis Word conversion.

命令：`abbreviation_registry.py list`（写前查询）/ `process --file ... --in-place`（写后注册+去重展开）/ `table`（生成缩略语表 md）/ `validate`（交叉引用校验）。完整 CLI 见 `QUICK_START.md`。

## Humanization Contract

Before finalizing each chapter:

1. Run technical self-check（命令见 `QUICK_START.md` § 7）。
2. Invoke the `/humanizer-zh` skill on the chapter's merged markdown. The skill rewrites the text in-place; confirm the output before saving. If `/humanizer-zh` is unavailable, manually apply the following checklist to every paragraph:

   **中文正文规则（博论核心，脚本可检测项见括号）：**
   - [ ] **中文单句 ≤50 字**（含嵌套从句计中文字符；`check_quality.py` 检测 `cn_sentence_too_long`）
   - [ ] **从句嵌套 ≤2 层**：禁止"当A使B导致C从而D"类四层套叠结构
   - [ ] **短句（≤15字）与长句（30-50字）交替**：禁连续 3 句字数差异 <5 字（`check_quality.py` 检测 `cn_sentence_monotone`）
   - [ ] **中文 AI 禁词清零**：`check_quality.py` 的 `去AI-禁词` 类别零违规（覆盖：至关重要/深入探讨/蓬勃发展/革命性的/综上所述/值得注意的是/不仅…而且/大量研究表明 等）
   - [ ] **无模板化过渡句**：删除"由此可见"、"在此基础上"等空洞衔接词
   - [ ] **无重复排比**：连续出现≥3个句式相同的句子→合并或改写
   - [ ] **无空洞宏观主张**：每段必须有具体数据或实验结果支撑，不允许纯观点段落
   - [ ] **证据先于结论**：数据/观测在前，解释/结论在后；不允许倒置
   - [ ] **无破折号（——）**：改用逗号、句号或拆句（注意：连字符 `-` 不在此限）
   - [ ] **无修辞疑问/反问**：所有句子必须陈述句
   - [ ] **无比喻/排比**：删除"如同"、"犹如"、"是…的桥梁"等表达
   - [ ] **无 scare quotes（恐惧引号）**：禁用双引号/引号包裹自造词或普通短语以暗示"新概念"或"特别含义"（保留合法场景：术语首次定义、原文引用、已固化术语）。检测规则：引号内为 2-10 字且非术语首次展开模式
   - [ ] **无解释性冒号（装饰句式）**：禁用"概念：解释"装饰结构（如"本研究的核心：探索..."）。合法冒号场景：比例（1:2）、列表引导（以下三点：）、标题/图表标签（表2-1：...）、数值（10:00）

   **英文摘要规则（Abstract 专用）：**
   - [ ] **英文单句 ≤30 词**：每句不超过 30 个英文单词
   - [ ] **禁 -ing 悬垂从句**：禁用 `, reflecting/ensuring/highlighting/demonstrating/suggesting...` 悬垂分词（改为独立句）

3. Re-run self-check to confirm no regressions（特别确认 `writing_style` 类 + `去AI-禁词` 类 + `句长规范` 类问题归零）
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

边框参数（pt 值）与题注字体字号见 `references/word-format-spec.md § Three-Line Table Borders`；格式由 `check_quality.py` 强制校验（无竖线，顶/底线 1.5pt，表头线 0.5pt）。

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

命令：`figure_registry.py register`（注册映射）/ `list`（列出/筛章）/ `unregister`（删除）/ `validate`（连续性）/ `cross-validate --chapter N`（与 atomic_md 交叉验证）/ `export --format markdown`（导出映射表）。完整 CLI 见 `QUICK_START.md`。

## Figure Prompt Generation（图注之外，同步生成AI绘图提示词）

原图在源 PDF 中不可用或需重绘时，按 `references/figure_prompt_template.md` 为每张图生成 Figure Prompt 块，存入 `${save_path}/figure_prompts.md` 并标 `[RECONSTRUCTED]`。所有元素描述须来自图注与 Results 文本，**不得编造实验数据**。

**配图代码生成（opt-in，默认关）**：与上述 Figure Prompt 并列的另一可选项，默认不生成配图（基础实验用户自行作图）。仅当用户**明确要求**"生成配图/画图代码"（如生信、统计图场景）时启用。启用后：① 调用本地 matplotlib/seaborn skill 生成**可运行代码**（产出代码非图片）；② 遵循学术规范：按数据选图型（bar/boxplot/line/scatter+回归/**forest plot**/**funnel plot**（meta 分析用）/heatmap/network/concept map），APA 7.0 caption，色盲安全配色（viridis/cividis/Tol），300 DPI，轴标签带单位，**禁 3D 图与饼图**；③ 生成后由用户运行得图。

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

格式类参数（字体/字号/边框/对齐/页眉页脚/摘要/目录间距等）由脚本硬编码并强制校验，**不在此复述**，以 `check_quality.py` 各类别通过为准。本清单只保留需人工确认的项：

- [ ] `check_quality.py --enforce-full-structure` 各类别（三线表 / 引用格式 / 标点 / 缩略语 / 字体字号 / 页眉页脚 / **参考文献著录格式**）全部通过
- [ ] Body target >= 80,000 且各章字数已与用户协商并写入 profile
- [ ] 结构满足：引言 + 研究章 + 结论，总章数 >= 5；参考文献统一在全文末尾
- [ ] 原子化工作流：编号校验通过、章节自检已跑、小节快照已建、快照/回滚可用
- [ ] Humanization pass 已完成（humanizer-zh 或人工清单）
- [ ] 缩略语注册表与图号注册表已填充并交叉校验通过
- [ ] **查重预检（人工）：** 提交知网/万方查重前，基于 Non-Negotiable 第 20 条中已标注的复用来源，人工列出"高风险复用段落清单"（每条含：所在章节、原 SCI 来源 [N]、改写状态 confirmed/pending），确认全部为中文改写且有引用标注，再提交查重。

> **🔴 硬规则（全局）：每节收口自检清单（G1-G6 + S1-S5）与每章收口自检清单（G1-G6 + S1-S7）未逐项确认通过，不得向用户声明"该节/该章完成"。** 能脚本核的项必须跑脚本取证据（`ok=true` / 零 error）；人工项逐条打 ✅ 后方可放行。此规则优先于任何上下文压力或用户催促。
