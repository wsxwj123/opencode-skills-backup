---
name: sci2doc
version: 2.20.0
description: 用于将SCI论文材料转化为中文博士或硕士学位论文草稿，执行严格的章节结构、原子化Markdown工作流、门禁检查和版本回滚。当用户提到博士论文、硕士论文、学位论文、毕业论文、SCI转论文、doctoral thesis、master thesis、dissertation 时优先调用。
---

# Sci2Doc

## Overview

本技能适用于博士或硕士学位论文，需用户提供已成稿的 SCI 论文材料作为转化来源。若用户没有可访问的 SCI 论文材料，或场景是本科毕业论文，主动退出本技能，不要套用本流程。

This skill converts SCI paper materials (PDF/Word plus user context) into a Chinese doctoral thesis draft.

This skill is process-first, not one-shot generation.

The workflow is built around:
- `state_manager.py` for anti-forgetfulness, token budgeting, gate checks, snapshot/rollback
- `atomic_md_workflow.py` for atomic subsection markdown files, numbering validation, merge, self-check, section-level snapshot

## 接续与决定日志（每次启动本技能先跑）

学位论文往往跨多次会话才写完，用户中途还常插新要求。连续性靠外部状态文件维持，不靠模型记忆：

1. **开局先跑接续报告并打握手**：`env_preflight.py` 会打印 `RESUME_CMD`（绝对路径）。照它跑
   `python <..>/session_journal.py resume --root <project_root>`，把输出贴给用户并确认「从这里接着写」再动笔。
2. **用户每插一条新要求/新决定，立即 log**：`python <..>/session_journal.py log --root <project_root> --note "用户要求：<原话>"`。
   决定写入 `decisions_log.md`（append-only），后续会话必读并遵守。
3. **引文核证命令**：`env_preflight.py` 同时打印 `CITATION_CHECK_CMD`，见 `## Citation Claim Check (承重论点↔引文)`。

## 快速流程索引 (Quick Workflow Index)

全流程 7 步顺序如下，详细说明见各节。

| 步骤 | 操作 | 阻断条件 | 详见 |
|------|------|----------|------|
| **0. 材料确认** | 确认源材料可访问、用户提供论文题目/章数/院校 | 材料缺失 → 停止 | `### 0) Material Input Gate` |
| **0.5. 研究主线设计** | 产出科学问题→贡献→章节映射表；协商章节字数目标；写入 `outline` | `outline` 为空 → 不得进入 Step 1 | `### 0.5) Research Storyline Design` |
| **1. 样式选择** | 询问 内置默认模板 or 自定义；写入 `thesis_profile.json` | 自定义信息不完整 → `pending_template` | `## Style Selection Gate` |
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

1. `默认设置` — 内置默认学位论文模板（通用格式，可自定义为任意院校）。机构字段为占位符（`示例大学`/`[学校代码]`），用户应替换为本校信息。
2. `自定义样式` — 用户须提供目标院校 + 详细 Word 格式要求和/或模板证据文件。

🔴 **CHECKPOINT（阻断 init）：** 未与用户明确确认样式前，**不得运行 `state_manager.py init`**。即使用户可能想用内置默认模板，也必须先得到用户对"就用内置默认模板"的明确确认，再带样式参数运行 init。**禁止** 因看到 QUICK_START 的 init 示例就直接套用默认 `--format-mode default_generic` 跑 init（该默认会静默落成内置模板格式且立即放行 docx 导出）。

**硬门禁：** 自定义信息不完整的项目标记为 `pending_template`，可继续整理 markdown，但 **不得生成 `.docx`、不得运行格式验收**。`custom` 仅在写入结构化布局字段后才能转为 `ready`，否则保持 `pending_template`。

**custom→ready 最小必填字段**（缺一即保持 `pending_template`）：`page_margins_cm.top/bottom/left/right`（四个边距）、`header_distance_cm`、`footer_distance_cm`、`university_name`、`degree_type`。

字段完整定义、需求→字段映射、managed front matter 文件清单、managed marker 覆盖规则等细则见 `references/format_profile_schema.md § Style Selection Gate (full rules)`。

## Non-Negotiable Requirements

1. Body text target depends on degree type: **≥50,000 characters for doctoral**, **≥30,000 for master's** (defaults; confirmed with user at project start and written to profile as `body_target_chars`). 这是**软目标**而非硬门（`check_quality.py` 字数不足为 warning）：可经用户同意上调；不达标只提示、不阻断导出。**真实材料撑不到目标时宁可少写，绝不编数据/灌水凑字**（A③ 已把综述/绪论并入正文计数以减压）。
2. Chapter-level target allocation is **not hardcoded** and must be negotiated with the user for each project.
3. Chinese abstract must be **1500-2500 characters**.
4. Main structure is fixed:
   - independent Introduction chapter
   - multiple research chapters
   - independent final Conclusion/Outlook chapter
   - total chapters >= 5
5. References are unified at the end of the full thesis.
6. Body word count scope: abstract through end of body text (before full-thesis references). **综述/绪论章计入正文字数**——把凑字数压力从研究章分摊出去，缓解逼 AI 靠编数据/扩实验凑字（`check_quality.py` / `count_words.py` 已将 review 章并入 body 计数，另单列 `review_words` 供展示）。仅全文末尾统一参考文献、目录、致谢、附录、成果、声明、缩略语表排除在外；若确有整章须排除，用 `format_profile.exclude_from_body_count`（章标题字符串列表）逐章显式声明。
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
17. 文风约束：见 `## Humanization Contract`（清单集中在那里）；`check_quality.py check_writing_style()` 自动检测。**硬禁清零项**：破折号（——）/scare quotes/解释性冒号三项标点 + AI 禁词，finalize 前必须归零。**软提示项**（不阻断 finalize）：句长/句式节奏（C 降软）。
18. 格式对齐规则：正文两端对齐、三线表单元格居中、图占位符居中无首行缩进。完整参数见 `references/word-format-spec.md`。
19. Bold marker 处理：`**text**` / `__text__` 在 Word 转换时由 `md_runs.inline_md_to_runs()` 解析为真正的粗体 run；单 `*` 统计显著性标记（如 `*p<0.05`）由其内置保护规则保留原样。
20. 已发表 SCI 内容复用合规底线：
    - 正文复用必须**改写**为中文学术表述，不得直接翻译粘贴。
    - 每章首次复用处必须标注来源文献（正文引用 [N] + 声明"本章部分内容已发表于 [N]"）。
    - 复用成果须同时体现在"攻读学位期间取得的成果"清单与"独创性声明"中。
    - 缺标注的已发表内容复用等同未注明引用，触发学位办自我抄袭/重复发表红线。
    - **本技能不做查重，改写 ≠ 降重**：技能只把英文材料改写成中文学术表述并做文风/翻译腔软检测，不计算重复率、不对接知网/万方/Turnitin。是否达标须用户自行送第三方查重系统核验。
    - **逐段"原文-改写"对照表（人工产出）**：凡复用已发表 SCI 内容的段落，须在 `docx/reuse_map.md`（或交付附件）中逐段列出对照表——列：所在章节 / 原文出处 [N] / SCI 原文片段 / 中文改写文本 / 改写状态(confirmed/pending)，供用户自查重复率与送查重。

## Citation Zero-Hallucination Gate (Mandatory)

Before writing any chapter section and before final full-thesis merge, run:

`python3 scripts/citation_guard.py --index "${save_path}/literature_index.json" --mcp-cache "${save_path}/mcp_literature_cache.json" --mcp-ttl-days 30 --write-back --manual-review "${save_path}/manual_review_queue.json" --log "${save_path}/verification_run_log.json" --report "${save_path}/citation_guard_report.json"`

`--write-back` 由脚本把每条 `verified` 与 `verification_details.checked_at` 落回 `literature_index.json`（AI 不手动改 `verified`）。据此下一轮核验对**已 verified 且未过 TTL** 的条目自动短路复用、跳过在线重验；`sci-source-seed` 种子（`verified=false`）与过期/未验条目照常走完整在线核验，撤稿与新鲜度安全不受影响。报告字段 `reused_fresh_verified_count` 记录本轮命中短路的条目数。

Rules:
- Immediately after each retrieval/import batch updates `literature_index.json`, run the guard once before any drafting.
- If guard exits non-zero or report `ok=false`, stop writing and resolve the queue first.
- When bidirectional verification fails (`title_mismatch`|`doi_invalid_or_unresolved`|`pmid_invalid_or_unresolved`|`id_mismatch`), set `verified=false` immediately and route entry to `manual_review_queue` for manual confirmation before正文引用.
- Unverified references must not be cited in chapter markdown.
- Every cited entry must carry traceability fields (`source_provider` + `source_id`) and DOI/PMID whenever available.

**Topic-dependent routing (MANDATORY):**
- Life science / medicine / clinical / biochemistry / pharmacology → **PubMed CLI first** (`esearch`/`efetch`/`einfo`, `~/edirect/`, requires `< /dev/null`, proxy `http://127.0.0.1:<PROXY_PORT>`). Auto-install if missing: `sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"`. **Windows:** edirect 在 Windows PowerShell/CMD 不可用，用 WSL bash，或自动回退 paper-search MCP。
- CS / AI / engineering / physics / interdisciplinary → **paper-search MCP first** (`mcp__paper-search-mcp__search_arxiv` etc.).
- Fallback to the other source when primary yields no results.

> **跨平台命令说明：** 本文档内联的 `python3 scripts/xxx.py` 命令在 Windows 上用 `python` 或 `py` 代替 `python3`。

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

## Citation Claim Check (承重论点↔引文)

`citation_guard.py` 只验引文**真实性**（DOI/PMID/标题对得上）；它不判「这篇引文到底**支不支持**它挂着的那句论点」。写研究章时，对**承重论点句**（机制/因果/关键定量结论）↔ 其引文，必须再过一道**引文核证**：

1. `literature_index.json` 每条可选带 `key_finding`（该文献真实结论一句话）与 `claim`（本文用它支撑的论点）两字段，最小承载核证语义（schema 见 `references/format_profile_schema.md § literature_index.json schema`）。
2. 写某研究章前，对每个「承重论点句 ↔ 引文」建一行证据，落 `claim_evidence.json`（list），字段 `{section, claim_sentence, is_load_bearing, ref_id, retrieved_abstract, verdict∈support/weak/contradict/unknown, evidence_quote, user_confirmed}`。`retrieved_abstract` 用**检索到的真实 abstract**（不看可编的 `key_finding`），取 abstract 走本技能既有文献检索subagent。**已建过证据的可留空以省事**：脚本读写 `ref_evidence_cache.json`，对某条 `ref_id` 已缓存过 abstract 的行自动回填 abstract、AI 不必重新检索；同一 `(ref_id, claim_sentence)` 已判定过的行自动复用上次结论，AI 只需对**新的 (文献, 论点) 组合**做反向验证。
3. 跑共享核证脚本（`env_preflight.py` 打印的 `CITATION_CHECK_CMD`），命令 `python <_shared>/citation_claim_check.py --root <project_root> --evidence <project_root>/claim_evidence.json`。脚本自动读写 `ref_evidence_cache.json`（回填 abstract + 复用同 (文献,论点) 已确认结论），门禁强度不变。
   - 承重句 `verdict∈{contradict,unknown}` 或缺 abstract 或未 `user_confirmed` → **fail-closed（exit 2），硬拦 + 人工逐条确认**后方可下笔。
   - 背景陈述句只在表里批量呈现、不逐条阻断。
4. 纳入节/章 DoD（见 dod_checklist `section-dod`/`chapter-dod` 的 citation_claim_check 项）。

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
├── scripts/                # 技能脚本副本（init 自包含拷入；SKILL 命令 `python3 scripts/xxx.py` 即指向此处）
├── materials/              # 原始材料素材档（material_ingest.py 生成，可选）
│   ├── materials_archive.json  # 素材总索引
│   └── <name>.md           # 每材料一个结构化素材档
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

> **A① 跨章综合例外：** 当前章为**绪论（绪论/引言）或结论（结论/总结/小结/展望）**时，`load_state` 不按当前章过滤，而是**全量加载 chapter_index / literature_index / figures_index + 全部研究章的 section digest/key_facts**（`bundle.synthesis_role` = `intro`/`conclusion`，`scope=cross-chapter-synthesis`）。这样绪论能综述全部研究、结论能跨章综合各研究章的真实数据，避免缝线全露。章类型由 `project_state.json.outline` 里该章标题判定。**引文核证不整批重验**：绪论/结论引用的文献若已在某研究章验过（承重论点↔引文那道核证），`citation_claim_check.py` 经 `ref_evidence_cache.json` 自动复用该 (文献, 论点) 的既有 abstract 与确认结论，AI 不必对全量引文手动重记证据；只有**新出现的 (文献, 论点) 组合**才需反向验证，fail-closed 不放松。
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

**Degree & target confirmation (must ask before anything else):**

AI must ask the user two questions before proceeding:

1. **Degree type**: doctoral (博士) or master's (硕士)?
2. **Body word count target**: defaults are doctoral ≥50,000 / master's ≥30,000; confirm or let user specify a different number.

Record answers into `thesis_profile.json > format_profile.degree_type` and `targets.body_target_chars` during `init` / `profile` step. Do not proceed to material extraction until both are confirmed.

Before initializing any project, also verify:
- Source materials (PDF/Word SCI papers + supplementary figures) are accessible at a known local path.
- User has provided: thesis topic, research chapter count estimate, target university (or explicit consent to use the built-in default template).

If source materials are missing or inaccessible, **stop and request them**. Do not proceed to Step 1.

**[可选] 多格式原始材料落盘：** 若用户除 SCI 论文外还提供了其他原始材料（实验数据 Excel/CSV、组会笔记 md、参考 PDF/Word、结果图片等），在提取 SCI 论文文本前先运行材料落盘脚本，把素材分析写进 `materials/` 目录，供后面按章写作时引用取证：

```bash
python3 scripts/material_ingest.py --dir /path/to/raw_materials --save-path "${save_path}"
# 或指定文件列表：--list file1.xlsx file2.md fig1.png
```

落盘完成后，`materials/materials_archive.json` 为素材总索引，每个材料对应一个 `materials/<name>.md`（含可引用要点、表结构/数值范围、图片待确认标记）。后续写作时，引用数值/结论必须能追溯到对应 entry，不得凭空生成。图片类材料标记 `pending_confirm`，须等用户口述或补充图内容后方可引用。详细规则见 `references/material_ingest_guide.md`。

**SCI 论文内容提取（必做）：** 确认材料可访问后，在进入 Step 1 前，必须将 SCI 论文内容提取为可读文本：

- **PDF 格式** → 使用 `/pdf` skill（`pdf-viewer:view-pdf`）逐页阅读，或在用户本地运行：
  ```bash
  # 使用 pdfminer 提取（无需联网）
  python3 -c "import pdfminer.high_level; print(pdfminer.high_level.extract_text('paper.pdf'))" > paper_text.txt
  ```
  若 pdfminer 未安装：`pip3 install pdfminer.six`
- **Word 格式** → 使用 `/docx` skill 或直接 Read 工具读取文件内容
- **网络来源（DOI 可访问）** → 使用 `/fetch-everything` skill 抓取全文

**[docx/pdf 源稿] 内嵌图抠出（必做于 atomic_md_workflow 之前）：** 支持 docx 与 pdf，运行下面这一步把内嵌图按出现顺序解到 `figures/`，供后续按章节嵌图与 `figure_registry.py` 使用（pdf 需 PyMuPDF，缺失则优雅跳过；其他非 docx/pdf 输入自动 no-op，安全可重复运行）：

```bash
python3 scripts/extract_docx_images.py --manuscript /path/to/source.docx --project-root "${save_path}"
```

产出：`figures/figure_NN.<ext>` + `figures/image_manifest.json`。脚本只搬运二进制，不做 OCR / 图像识别；图片对应到章节图号的映射仍走 `figure_registry.py` 注册流程。

提取完成后，AI 应先通读全文摘要（Abstract）、结果（Results）、方法（Methods）三节，大致读懂做过哪些实验，再进入 Step 0.5。

**SCI 自身参考文献导出（初始种子）：** 在通读的同时，同步扫描源 SCI 论文的 References 部分，将其中每条参考文献按 `literature_index.json` schema 格式整理为初始种子条目，`source_provider` 填 `"sci-source-seed"`，`verified` 填 `false`，写入项目的 `literature_index.json`（若文件已存在则 merge 而非覆盖）。这些种子作为 Step 3 文献检索的**待核验候选清单**（已带 DOI/PMID，省去重新构造检索式、确定检索目标的成本），而非可直接引用的来源。注意：`sci-source-seed` 不在 `citation_guard.py` 的合法 provider 白名单（`pubmed-cli` / `paper-search`）内。种子条目必须在 Step 3 以其 DOI/PMID 为目标经 `pubmed-cli` 或 `paper-search` 正式检索核验，核验通过后将 `source_provider` 更新为实际核验来源并置 `verified=true`，方可引用；未核验的种子不得进入正文。

> 以下各步只列命令名 + 关键参数 + 门禁条件。**完整可复制 CLI（含所有 flag、占位符）见 `QUICK_START.md`。**

---

## 开场监工卡（每次启动本技能必须原样打印给用户）

> 学位类型与源材料确认之后、产出章节结构之前，AI **必须** 把下面这张卡原样打印给用户。这是把 sci2doc 最容易翻车的地方摊到明面上，请用户当监工，别当甩手掌柜。

```
【sci2doc 监工卡 · 请你盯这几件事】
1. 数据不许编：为凑字数（博士≥5万字/硕士≥3万字），AI 最爱把实验数值编圆。
   每写一章，找我要一张"数值→原文哪张图/表"对照表，你随机抽 2-3 个数回原文核对。
2. 一章一章写，别一次甩全文：要求逐章交付。一次性生成整篇会跳过所有逐节质检和盲检，
   看着完整实则没过任何门。你发现我在批量出全文，立刻喊停。
3. 本技能不查重，改写≠降重：复用已发表 SCI 段落时，找我要"逐段原文-改写对照表"
   （章节/原文出处/SCI原文/中文改写/状态），你自己拿去知网/维普送查，别信"已改写"三个字。
4. 引文抽验 DOI：从参考文献里随机挑 3-5 篇，让我给出 DOI/PMID，你上 doi.org 点开验真伪。
5. 章节结构要你亲自签字：下面的"研究主线/章节结构"必须你确认后我才落签字解锁正文，
   我不会替你确认。没签字，正文写入会被门禁物理拦下。
```

> 若开工前置的 `env_preflight.py` 报门禁状态为 `degraded`（当前环境不透传 hook）→ 明确告诉用户"本环境无法强制拦截，上面 5 条全靠你人工盯"。

---

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

> **[章节结构签字·强制门禁落锁]** 用户在对话里明确确认上面的研究主线 / 章节结构映射表后（且**仅在此之后**），运行开局 `env_preflight.py` 打印的那条 `SIGNOFF_CMD`（已含解析好的绝对路径）落盘签字。注意 `env_preflight.py` 在会话开场就运行（即本 Step 0.5 签字之前，见本文件开头第 1 条握手；它文档虽列在 Step 1，实际执行在最前），所以此刻 `SIGNOFF_CMD` 早已拿到，不存在签字时还没拿到命令的次序歧义——即 `python "<.../\_shared/structure_signoff_gate.py>" confirm --root <项目根> --note "<用户确认原话摘录>"`。这一步解锁正文写作：**未落签字，PreToolUse hook 会物理拦截任何对 `atomic_md/*/*.md`（学位论文各章正文）的写入**（这是防跳步的硬门，不是提示词纪律）。这道拦截 hook 由 `env_preflight.py` 开工时经 `_shared/install_gate_hook.py` 自动安装并校验（带备份与回滚），门禁状态 active 即在岗；报 degraded 或 error 时会告警，此时无法物理拦截、只能靠人工盯，需留意。若后续章节结构又改，改完让用户重新确认并重跑本命令覆盖签字。⚠️ 严禁在用户未确认时自行运行 confirm——那等于伪造用户签字。
>
> 注意：本签字闸管的是**章节结构确认**，与 `## Style Selection Gate`（样式/格式确认，阻断 init 与 docx 导出）是**两道独立的门**，各管各的，别混淆或相互替代。

### 1) Initialize Project

- **Env Precheck（软门禁，建项目文件前）**：`python3 scripts/env_preflight.py ${save_path} --cli esearch --py docx`，写 `env_status.json`，末行 `PRECHECK: OK|ASK|BLOCKED`。`BLOCKED`（Python 过低）→ 停并引导升级；`ASK`（缺 git/esearch/python-docx 等可选工具）→ **逐项问用户是否安装**并给指引，用户答"已装/不装"后才继续，后续再遇缺工具同此处理；`OK` → 继续。
- **Git Init（叠加在 snapshot 之上）**：`python3 scripts/git_checkpoint.py init ${save_path}`。git 可用且项目根不在他人仓库内时建 git 检查点，否则静默回退 snapshot。
- `state_manager.py init`：先二选一样式。`--format-mode default_generic` 或 `--format-mode custom`（+ `--university-name` / `--degree-type` / `--template-source` / `--missing-requirement`）。
- `state_manager.py profile --show` 验证；`render-front-matter` 手动重渲前置页；`profile --body-target/--abstract-min/--chapter-target ...` 写入已协商好的各章字数目标（应在 Step 0.5 中已与用户确定）。
- 自定义结构化布局字段不全 → 保持 `pending_template`（最小必填字段见 `## Style Selection Gate`）。
- init / profile 必须自动刷新 managed front matter；无 managed marker 的用户改写文件不得覆盖。用户在聊天里给的详细要求应转成 JSON 经 `--format-profile-json` / `--project-info-json` 写入，而非仅留在 prose memory。

### 2) Prewrite Gate (Mandatory)

- `state_manager.py write-cycle --chapter N --token-budget 6000 --tail-lines 80 --json-summary`。每章每节必跑，加载跨章记忆。

### 3) Atomic Subsection Writing

- **🔴 开写前置闸门 (Mandatory，脚本硬拦截)**：每节开写前必须先跑 `python3 scripts/prewrite_gate.py --section X.Y --root .`（X.Y 为章.节，如 2.1），exit≠0 禁止开写。它统一硬检查：上一节完成（同章编号紧邻上一节 `atomic_md/第N章/{X.Y-1}_*.md` 存在非空）、大纲就位（`project_state.json.outline` 含本章 + `chapter_index.json`）、素材就位（`figures_index.json` 本章有图表/实验映射条目，无则降级 warning）、上一节占位符清零（无 `CITE_PENDING`/`DATA_PENDING`/`【待`）；上一节盲检结果（`.review_pass/<上一节>.json`）缺失即 prewrite_gate 硬拦 exit 1，禁止开写；必须先跑 delegate_review verify --section <上一节> 落盘通过标记。**⑥ 数据溯源硬门**：prewrite_gate 还会对上一节跑 `data_trace_gate`——上一节含实验数值却无有效 `[数据来源] materials/<档>#<字段>` 标记（或标记指向不存在的素材档/字段）即硬拦 exit 1（堵编数据）。
- **盲检逃生口（仅盲检子代理不可用时）**：本环境派不出独立盲检子代理（平台无 academic-blind-reviewer 或子代理反复失败）才可加 `--allow-manual-review "<非空理由>"`，对上一节或上一章章级盲检做显式人工放行。它只放行这两处盲检项，上一节文件/大纲/占位符/data_trace 等其余硬门照常拦。放行会写 `.review_pass/<sec>.json`（`manual:true`+理由+时间戳）并追加 `.review_pass/MANUAL_REVIEW_AUDIT.log` 留痕，绝非静默跳过；理由为空即拒绝放行。用了此逃生口等于承认盲检未做，须请用户亲自复核数据溯源与章节逻辑。
- 文件存于 `${save_path}/atomic_md/第{chapter}章/`，命名 `{section_number}_{section_title}.md`（如 `2.1_研究对象.md`）。
- **Table reminder**：呈现结构化数据（试剂/仪器/分组/统计）的小节 **必须** 用 Markdown 管道表，见 [Table Contract](#table-contract)，不得用散文描述。
- 校验：`atomic_md_workflow.py validate --chapter N`（加 `--enforce-research-structure`）+ `validate-experiment-map --chapter N`。**门禁：** 编号断裂 → 修复后才能继续。
- **⑥ 数据溯源标注（写作时必做，堵编数据）**：凡写入实验数值（浓度/剂量/比率/统计量等），该处必须紧跟标注 `[数据来源] materials/<素材档>#<字段>`，指向真实 `materials/*.md` 素材档里承载该数值的字段。落盘后自查 `python3 scripts/data_trace_gate.py --section X.Y --root .`，exit≠0 必须补标或删除无源数值——**追溯不到 materials 的数值就是编的，不得留在正文**。
- Post-write 必做：`abbreviation_registry.py process --file ... --in-place`，然后更新 `chapter_index.json` key_facts（AI 责任），再进 Step 4。

### 4) Subsection Summary Snapshot

- `atomic_md_workflow.py section-snapshot --chapter N --section X.Y`。每节小结完成即快照。
- **Git Checkpoint**：`python3 scripts/git_checkpoint.py commit ${save_path} "[sci2doc] section X.Y done"`（git 不可用自动 no-op，snapshot 仍兜底）。

#### 🔴 每节收口自检清单（Definition of Done · 节级）

**硬规则：以下各项未逐一确认通过，不得向用户声明"该节完成"。**

**🔴 进入下一节前置闸口**：上一节 `delegate_review verify` 必须 exit 0（含结构完整性项 S6），否则不得开始下一节。写完即检，不过不进。
**🔴 修复 3 次仍不过 → 回滚兜底**：同一节/章据盲检证据修复重跑 3 次仍 fail，停止盲目重写，提示用户回滚到上一检查点（git 可用 `git checkout <sha> -- <文件>`；否则 `state_manager.py rollback --target snapshot`）后重写。

**🔴 委托盲检（不得主 agent 自评）**：落盘前必须把 DoD 清单**委托给独立上下文的subagent盲检**，自己不直接打勾：
1. 生成任务包：`python scripts/delegate_review.py pack --checklist references/dod_checklist.json --gate section-dod --files <本节文件>`
2. **派一个独立subagent**（Claude Code 用 `academic-blind-reviewer`；其他平台派通用subagent），把任务包原样给它、**不要给它本节的写作上下文**，要求按任务包返回 JSON 数组。
3. 校验返回：`python scripts/delegate_review.py verify --checklist references/dod_checklist.json --gate section-dod --return <subagent返回.json> --section <当前节号如3.2> --root <项目根>`；退出码非 0（任一缺项/fail/无证据）= **fail-closed**，据subagent证据修复后重跑，**未过不得声明完成**。verify 通过会落盘 `.review_pass/<当前节号>.json`，下一节 `prewrite_gate.py` 会**硬校验**它（缺失即拒绝开写）。

> ⚠️ 若环境派不出真正独立的subagent，**绝不能同一 AI 自问自答冒充盲检**。告诉用户「本环境盲检不可靠，请你亲自复核数据溯源与章节逻辑」，交回用户。

**🔴 ①DoD停（盲检通过后必须停一次）**：`section-dod` 盲检 exit 0 后，**不得直接开写下一节**。先把该节 DoD **逐项结论**（每项 pass/证据一行）摆给用户，并**HALT 等用户明确说"过，继续下一节"**才动笔。用户未确认前停在此处。

**本节完整 DoD 判据（全部核查项 + 脚本命令）以 `references/dod_checklist.json` gate=`section-dod` 为唯一真源（20 项）**：盲检subagent据此逐项核、能脚本核的先跑脚本，退出码非 0 即 fail-closed。含 G1-G6 通用（编号连续/citation_guard/主线对齐/占位清零/去AI 硬禁三项标点/字数软目标）、S1-S5 sci2doc 特有（实验-方法映射/一实验≥一图表/三线表/缩略语首展/自我抄袭标注）、S-GIT 检查点，及 **S6 结构完整性、S10 数据溯源硬门（含数值却无 `[数据来源]` 标记=编数据嫌疑，fail-closed）、S11 承重引文核证，与 C1 科学事实正确 / I1 论证逻辑闭环 / O3 工作量与原创性 / O4 中英摘要对应 / M3 伦理合规披露 五项盲检质量核**。此处不再内联清单，避免与真源 drift。

### 5) Merge Chapter Markdown and Convert

- `atomic_md_workflow.py merge --chapter N --to-docx`。
- **硬门禁：** `format_profile.status == pending_template` 时 `markdown_to_docx.py` 拒绝生成 `.docx`，不得手动绕过转换器。

### 6) Chapter Self-Check (Immediate)

- `atomic_md_workflow.py self-check --target ".../02_分章节文档/第N章_自动合并.docx"`。
- 章节自检按 `chapter_targets` 判断，不卡全文参考文献下限（在全文总检卡）。`pending_template` 时 `check_quality.py` 同样拒绝格式验收（同 Style Gate 导出门禁）。

#### 🔴 每章收口自检清单（Definition of Done · 章级）

**硬规则：以下各项未逐一确认通过，不得向用户声明"该章完成"，不得进入 Step 7。**

> **[数据溯源·用户必抽验]** 学位论文里每个实验数值/每张图都必须能在原始 SCI 里找到出处。每写完一章，让 AI 给一张"本章数值/结论 → 源自原文哪张图/哪段"对照表，用户抽查几行（`data_trace_gate.py` 已机械校验 `[数据来源]` 标记，⑥）。⚠️ 字数目标已降为**软目标**（A③/C 降软，综述/绪论并入正文减压），就是为了不再逼 AI 靠编数据/扩实验凑字——追溯不到 materials 的数值就是编的。引文同样抽几篇验 DOI。

**🔴 进入下一章前置闸口**：上一章 `delegate_review verify` 必须 exit 0（含章结构完整性项 S8），否则不得开始下一章。写完即检，不过不进。现在 `prewrite_gate.py` 已对这道闸口硬校验，不再只靠提示词纪律：写下一章首节（如第 N 章的 N.1）前，它会读 `.review_pass/第<N-1>章.json`，缺标记或未 passed 即 exit≠0 硬拦。前提是上一章 chapter-dod 盲检已用 `delegate_review.py verify --section 第<N-1>章` 落盘通过标记。第 1 章首节无上一章，放行。

**🔴 委托盲检（不得主 agent 自评）**：章级闸口同样委托独立subagent盲检，不得主 agent 自评：
1. 生成任务包：`python scripts/delegate_review.py pack --checklist references/dod_checklist.json --gate chapter-dod --files <章节合并文件>`
2. **派一个独立subagent**（Claude Code 用 `academic-blind-reviewer`；其他平台派通用subagent），把任务包原样给它、**不要给它本章的写作上下文**，要求按任务包返回 JSON 数组。
3. 校验返回：`python scripts/delegate_review.py verify --checklist references/dod_checklist.json --gate chapter-dod --return <subagent返回.json>`；退出码非 0（任一缺项/fail/无证据）= **fail-closed**，据subagent证据修复后重跑，**未通过不得进入 Step 7**。

**🔴 ①DoD停（盲检通过后必须停一次）**：`chapter-dod` 盲检 exit 0 后，**不得直接开写下一章**。先把本章 DoD **逐项结论**（每项 pass/证据一行，含数据溯源 S10、承重引文核证 S11）摆给用户，并**HALT 等用户明确说"过，继续下一章"**才动笔。用户未确认前停在此处。

**本章完整 DoD 判据（全部核查项 + 脚本命令）以 `references/dod_checklist.json` gate=`chapter-dod` 为唯一真源（19 项）**：盲检subagent据此逐项核、能脚本核的先跑脚本，退出码非 0 即 fail-closed。含 G1-G7 通用（编号/citation_guard/主线/占位/去AI/字数/G7 常识软报告）、S1-S7 sci2doc 特有（实验-方法映射/一实验≥一图表/三线表/缩略语注册/GB7714 著录/自我抄袭/章后 self-check）、S9 字符级排版（`subsup_bare` + `halfwidth_punct_in_cn` + `english_misspelling` 任一命中即 `check_quality.py` 非零退出 hard 阻断）、S-GIT 检查点，及 **S8 全章结构完整性、S10 全章数据溯源硬门（数值均标 `[数据来源]`，fail-closed）、S11 全章承重引文核证**。此处不再内联清单，避免与真源 drift。

### 7) Finalize Chapter State

- `state_manager.py write-cycle --chapter N --finalize --summary "..." --snapshot`。
- **Git Checkpoint（章末）**：`python3 scripts/git_checkpoint.py commit ${save_path} "[sci2doc] chapter N done"`（git 不可用自动 no-op）。

### 8) Merge Full Markdown and Full Word

- `atomic_md_workflow.py merge-full --to-docx`。**规则：** 必须先纳入 `atomic_md/` 根级前置页 markdown，再合并正文。
- 可选高保真合并：`merge_chapters.py --input-dir .../02_分章节文档 --output .../03_合并文档/完整博士论文.docx --require-high-fidelity`。
- 兼容规则：`merge_documents.py` 优先用 `02_分章节文档/` 中已物化的前置页 docx，默认纳入 `封面`、`题名页`、`独创性声明与授权书`。

### 9) Full Thesis Checks

- 字数：`state_manager.py word-count` 或 `count_words.py <路径>`（支持 .md / atomic_md 目录）。
- 全文质检：`check_quality.py ".../完整博士论文.docx" --output json --enforce-full-structure`。
- **参考文献两道门**：全文总量 `references_min_count`（默认 ≥80）为硬门（error，阻断）。另有按章软门（warning，不阻断，阈值在 `thesis_profile` 的 `per_chapter_ref_floor`，硕/博分档，硕地板低于博）：绪论/文献综述章 `[n]` 引用偏少、研究/实验章引用偏少各自提示补充，结论章不设地板。软门只提醒不阻断导出。

### 10) Rollback if Needed

- `state_manager.py rollback --target snapshot`（加 `--strict-mirror` 严格镜像）。

## Chapter Structure Contract

For each research chapter (Chapter 2 to Chapter N-1), keep this order:

1. 引言
2. 材料与方法
3. 结果与讨论
4. 实验结论
5. 小结

**绪论章（第 1 章）写法：跨全部研究章的综述**
- 把各子研究框进**统一科学问题**（`project_state.json.outline.scientific_question`），逐一预告每个研究章要解决的子问题与贡献点（研究章标题须在绪论正文出现，`check_quality.py check_cross_chapter_coherence` 软核）。
- 写绪论时 `write-cycle` 会**跨章加载全部研究章 digest**（A①，`synthesis_role=intro`），据此综述全部研究，不得只写第一个研究。

**结论章（末章）写法：逐章综合各研究结果拉回中心问题**
- 逐个研究章回收其核心发现（研究章标题须在结论正文出现），再综合成回答中心科学问题的整体结论，指出跨研究的一致性/递进关系与整体贡献。
- 写结论时 `write-cycle` **跨章加载全部研究章 digest/key_facts**（A①，`synthesis_role=conclusion`），结论数值/结论必须来自各研究章真实结果，不得凭空生成或与研究章矛盾。

研究章（第 2 章至第 N-1 章）Rules:
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
- When introducing a new abbreviation for the first time, use the full pattern: `中文全称（英文全称，缩写）`，例：`聚焦超声（focused ultrasound，FUS）`。英文全称按期刊惯例书写，**大小写均可**（`focused ultrasound` 与 `Polymerase Chain Reaction` 都合法）；含希腊字母（γ/β/α）须**原样保留**，缩写与全称都不得在希腊字母处截断（写 `IFN-γ` / `TGF-β`，不得残缺为 `IFN-`）。
- 中文全称前**不接动词或介词**：直接以术语起首（写"聚焦超声（…）"，不写"采用/使用/在聚焦超声（…）"），否则动词会被吞进全称，污染缩略语表。
- After the first occurrence is registered, all subsequent uses must be the bare abbreviation only.
- After AI generates a section markdown, run `abbreviation_registry.py process` to extract, register, and strip redundant expansions before saving.
- 缩略语对照表为三列：**英文缩写 / 英文全称 / 中文全称**（auto-generated from registry during full-thesis Word conversion）。

命令：`abbreviation_registry.py list`（写前查询）/ `process --file ... --in-place`（写后注册+去重展开）/ `table`（生成缩略语表 md）/ `validate`（交叉引用校验）。完整 CLI 见 `QUICK_START.md`。

## Humanization Contract

Before finalizing each chapter:

1. Run technical self-check（命令见 `QUICK_START.md` § 7）。
2. Invoke the `/humanizer-zh` skill on the chapter's merged markdown. The skill rewrites the text in-place; confirm the output before saving. If `/humanizer-zh` is unavailable, manually apply the following checklist to every paragraph:

   **中文正文规则（博论核心，脚本可检测项见括号）：**
   > C 降软：句长/句式节奏为**软提示**（`cn_sentence_too_long` 为 warning、`cn_sentence_monotone` 为 info，均不阻断 finalize）；**破折号（——）/scare quotes/解释性冒号三项标点与 AI 禁词仍为硬禁清零**（主干保留）。
   - [ ] **中文单句 ≤50 字**（软提示，尽量拆分；`check_quality.py` 检测 `cn_sentence_too_long`，warning）
   - [ ] **从句嵌套 ≤2 层**：禁止"当A使B导致C从而D"类四层套叠结构（软提示）
   - [ ] **短句（≤15字）与长句（30-50字）交替**：连续 3 句字数差异 <5 字建议改写（软提示；`check_quality.py` 检测 `cn_sentence_monotone`，info）
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

3. Re-run self-check to confirm no regressions（硬禁项 `writing_style`（三项标点）+ `去AI-禁词` 类必须归零；`句长规范` 类为软提示，尽量优化但不阻断）
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

## 字符级排版契约

正文与表格中的字符级排版必须在原子化 `.md` 中按下列规则书写，`markdown_to_docx.py` 的行内解析器会把这些标记渲染为对应的 Word run 格式（斜体 / 上标 / 下标 / 加粗），并保证每个 run 仍走中英双字体（含 `eastAsia`）。

- **斜体**：用 `*...*` 包裹。适用对象：
  - 物种拉丁学名：`*E. coli*`、`*Escherichia coli*`、`*Mus musculus*`。
  - 基因名（按学科惯例，人类基因常大写斜体）：`*TP53*`、`*BRCA1*`。
  - 统计符号：`*p*`、`*t*`、`*n*`、`*F*`、`*r*`（例：`*p* < 0.05`、`*n* = 30`）。
  - 拉丁缩写：`*in vitro*`、`*in vivo*`、`*et al.*`、`*vs.*`。
- **上标**：用 `<sup>...</sup>`。例：`10<sup>6</sup>` cells/mL、`cm<sup>2</sup>`、`Ca<sup>2+</sup>`。
- **下标**：用 `<sub>...</sub>`。例：`H<sub>2</sub>O`、`CO<sub>2</sub>`、`IC<sub>50</sub>`、`Na<sup>+</sup>/K<sup>+</sup>`。
  - **禁止裸写 `H2O` / `CO2` / `IC50`，禁止直接粘贴 Unicode 上下标字符（如 `²`、`₂`、`⁶`）**——必须用 `<sup>`/`<sub>` 标记。
- **加粗**：用 `**...**`，**仅限标题**（如分组小标题）。学位论文正文不得用加粗做强调；强调改用句式或斜体。
- **半角 / 全角**：中文句内标点用全角（`，。；：（）`）；英文、数字、DOI、URL、公式用半角；同一句内不得中英标点混用。

注意：`*p* < 0.05` 这类统计显著性标记中的 `*` 是斜体标记的合法用途，行内解析器会正确识别并保护既有显著性写法（如 `**P*<0.05` 不会被误吞为加粗）。

## Word Format Specification (Built-in Default Template)

完整字体、字号、页边距、页眉页脚、三线表边框等参数详见 `references/word-format-spec.md`（内置默认博士学位论文版面标准，由 `markdown_to_docx.py` 硬编码实现，`check_quality.py` 强制校验）。

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

## ❌ 反例黑名单（Anti-Patterns）

- ❌ 把全文末尾的统一参考文献计入正文字数，正文范围只到正文结束、参考文献之前。（注：综述/绪论章按 A③ **计入**正文字数，不再排除。）
- ❌ 把博士/硕士字数目标当硬门逼 AI 编数据/灌水凑字：地板是**软目标**（`check_quality.py` 已降为 warning），真实内容不够宁可少写也不得造数据。
- ❌ 看到 QUICK_START 的 init 示例就直接套 `--format-mode default_generic` 跑 init，未经用户确认样式即静默落成内置模板格式并放行 docx 导出。
- ❌ 在自定义信息不完整、状态仍为 `pending_template` 时生成 `.docx` 或跑格式验收，或手动绕过 `markdown_to_docx.py` 的拒绝。
- ❌ `outline` 数组为空就进入 Style Selection Gate 与 Step 1，缺 `scientific_question` 或研究章 `core_argument`。
- ❌ 把章节字数目标硬编码或在 init 后才定，应在 Step 0.5 与用户协商后写入 `chapter_targets`。
- ❌ 引用 `citation_guard` 未核验的文献，或在 guard 报 `ok=false`、双向校验失败时继续写作而不入人工核验队列。
- ❌ 用 `websearch` / `openalex-cli` / `tavily` 作为文献来源，或把 `sci-source-seed` 种子条目当可直接引用来源（须以 DOI／PMID 经 PubMed CLI 或 paper-search 正式核验）。
- ❌ 并行发起文献检索调用，必须串行且相邻调用间隔 ≥1s。
- ❌ 对图片材料做 OCR 或从文件名猜内容，图片一律 `pending_confirm`，须用户口述补充后才能引用。
- ❌ 编造实验数据或参考文献，引用数值／结论必须可追溯到 `materials/` 对应 entry。
- ❌ 跳过 `write-cycle` 预写门禁就写新小节，它是唯一加载跨章记忆的机制。
- ❌ 把材料与方法、分组、统计等结构化数据写成散文段落，3 项以上同属性数据必须用 Markdown 管道三线表。
- ❌ 主 agent 自评 DoD 清单代替独立subagent盲检，或上一节／上一章 `delegate_review verify` 未 exit 0 就开始下一节／下一章。
- ❌ 把结果全部前置、后面集中讨论，研究章结果与讨论必须按实验逐一耦合，且每个实验至少配一张图或表。

## Acceptance Checklist

格式类参数（字体/字号/边框/对齐/页眉页脚/摘要/目录间距等）由脚本硬编码并强制校验，**不在此复述**，以 `check_quality.py` 各类别通过为准。本清单只保留需人工确认的项：

- [ ] `check_quality.py --enforce-full-structure` 各类别（三线表 / 引用格式 / 标点 / 缩略语 / 字体字号 / 页眉页脚 / **参考文献著录格式**）全部通过
- [ ] Body target 接近学位软目标值（博士 ~50,000 / 硕士 ~30,000，或用户在 Step 0.5 协商的更高值；综述/绪论已计入正文，A③）且各章字数已写入 profile；不足只提示不阻断，严禁编数据凑字
- [ ] 结构满足：引言 + 研究章 + 结论，总章数 >= 5；参考文献统一在全文末尾
- [ ] 原子化工作流：编号校验通过、章节自检已跑、小节快照已建、快照/回滚可用
- [ ] Humanization pass 已完成（humanizer-zh 或人工清单）
- [ ] 缩略语注册表与图号注册表已填充并交叉校验通过
- [ ] **查重预检（人工，本技能不做查重）：** 技能不计算重复率、不对接任何查重系统；改写 ≠ 降重。提交知网/万方查重前，基于 Non-Negotiable 第 20 条产出逐段"原文-改写"对照表（`docx/reuse_map.md`：所在章节 / 原文出处 [N] / SCI 原文片段 / 中文改写文本 / 状态 confirmed/pending），确认全部为中文改写且有引用标注，再由用户自行送第三方查重。

> **🔴 硬规则（全局）：每节收口自检清单（G1-G6 + S1-S5）与每章收口自检清单（G1-G6 + S1-S7）未逐项确认通过，不得向用户声明"该节/该章完成"。** 能脚本核的项必须跑脚本取证据（`ok=true` / 零 error）；人工项逐条打 ✅ 后方可放行。此规则优先于任何上下文压力或用户催促。

## 发现 AI 跳步/编数据了怎么办（用户自救）

以下话术可直接复制粘贴给 AI，逼它把过程摊到明面上：

- 「每完成一章贴四样给我：git log commit 列表、.review_pass/ 文件清单、citation_guard_report.json 的 ok 字段、本章每个关键数值对应原文哪张图的对照表。拿不出就回对应 Step 重跑」
- 「把本章所有实验数值列成表，每行标注来自 materials_archive.json 哪个 entry 哪个字段；追溯不到的全部标红等我核」
- 「AI 应一节一节写、每节存文件做检查；你一次性甩整章给我 = 跳过了所有质检」
