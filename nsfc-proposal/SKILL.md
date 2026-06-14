---
name: nsfc-proposal
description: Use when drafting, restructuring, or polishing Chinese NSFC proposals (2026 template), especially when strict section-by-section gating, hypothesis-objective-content-problem consistency, literature verification via paper-search MCP, and anti-AI Chinese academic writing constraints are required. 触发词：国自然、国家自然科学基金、基金申请书、科研申请、NSFC、标书、本子、面上项目、青年基金。
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

## Core Terminology
SQ is the upstream root; H/O/RC/KSQ form the 1:1 consistency backbone derived from it.

| Symbol | Chinese | Role | Example |
|--------|---------|------|---------|
| SQ | 科学问题 (Scientific Question) | Field-level open problem distilled in P1; root for H and KSQ (not part of the 1:1 chain). SQ 不持有下行映射字段，关联由 H/KSQ 的 `mapped_from_sq` 反向建立 | "XXX的分子机制尚不清楚" |
| H | 假说 (Hypothesis) | Causal claim derived from SQ | "A蛋白通过B通路调控C过程" |
| O | 目标 (Objective) | What you **do** (action-oriented) | "阐明XXX的机制" |
| RC | 研究内容 (Research Content) | Specific investigation; links to methods | "通过ChIP-seq分析A蛋白的结合位点" |
| KSQ | 关键科学问题 (Key Scientific Question) | What you **answer** (question-oriented), distilled from SQ | "XXX如何调控YYY？" |

Mapping constraint: H-n ↔ O-n ↔ RC-n ↔ KSQ-n (strict one-to-one, no cross-linking allowed).
SQ vs KSQ: SQ is the broad open problem stated in P1; KSQ is the focused, answerable question distilled from SQ and bound 1:1 to its H/O/RC. One SQ may seed one or more KSQ; each SQ must trace to ≥1 H and ≥1 KSQ (rule V-01).

**If user asks a conceptual question about any of H/O/RC/KSQ/SQ/mapping:** load `references/02_核心机制.md` and answer from it before continuing with workflow phases.

## Inputs Required
Collect before execution:
- Project basics: title, discipline code, project type, research attribute, duration, budget.
- 🔴 **科学问题属性（四选一，强制）**：与上面的"研究属性"是**两个独立必填字段**，不可混为一谈。研究属性=分类评审的「自由探索类/目标导向类」；科学问题属性=申请书另一独立必填项，四类官方标准措辞如下，Phase 0 必须选定其一并写入 profile 的 `science_problem_attribute`：
  - 鼓励探索、突出原创
  - 聚焦前沿、独辟蹊径
  - 需求牵引、突破瓶颈
  - 共性导向、交叉融通
- Existing materials: draft files, prior work, platform/conditions, related projects.
- User constraints: word targets per section, preferred P2 sub-structure, H/O/RC/KSQ mapping count.

### 2026模板硬约束速查表
| 项目 | 硬限 |
|------|------|
| 正文总页数 | ≤30页（约18000-25000字），页数估算替代字数硬门控 |
| 中文摘要 | ≤400汉字 |
| 英文摘要 | ≤300英文词 |
| P4 其他需要说明的情况 | ≤500字 |
| P3_4 完成基金项目情况总结 | ≤500字 |
| 研究属性（分类评审） | 必选「自由探索类」或「目标导向类」二选一 |
| 科学问题属性（独立必填，≠研究属性） | 四选一：鼓励探索·突出原创 / 聚焦前沿·独辟蹊径 / 需求牵引·突破瓶颈 / 共性导向·交叉融通；Phase 0 未选定则 gate-check 阻断（`failed_at=profile`） |
| 伦理审查（涉人类受试者/实验动物/生物安全/人类遗传资源时） | 须在可行性分析中说明伦理审查批件或送审计划 |

## Tooling Rules
Academic literature retrieval follows topic-dependent routing (Mandatory):

1. **Determine field type first:**
   - Life science / Medicine / Clinical / Biochemistry / Pharmacology → **PubMed CLI first**
   - CS / AI / Engineering / Physics / Interdisciplinary → **paper-search MCP first** (arXiv/Google Scholar)

2. **PubMed CLI** (life science primary): Use `esearch`/`efetch`/`einfo` (path `~/edirect/`). Must append `< /dev/null`, use proxy `http_proxy=http://127.0.0.1:7897`.
   Example: `export http_proxy=http://127.0.0.1:7897 && esearch -db pubmed -query "xxx" < /dev/null | efetch -format abstract`
   Auto-install if `~/edirect/esearch` missing: `sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"`

3. **paper-search MCP** (CS/AI primary / preprints / fallback when PubMed yields no results):
   Tool names: `mcp__paper-search-mcp__search_pubmed`, `mcp__paper-search-mcp__search_arxiv`, `mcp__paper-search-mcp__search_biorxiv`, `mcp__paper-search-mcp__search_medrxiv`

Do not use generic web search/fetch tools for citation evidence in proposal claims.
**严禁** 使用 `tavily`、`websearch` 或 `openalex`（pyalex），无论有无 DOI/PMID.
**Serial Search (MANDATORY):** Execute all retrieval calls sequentially (including both PubMed CLI and paper-search MCP). Never parallelize search requests. Enforce ≥1s interval between consecutive calls.

## Non-Conflict Canon (Conflict Resolution Rules)
> These rules resolve specific contradictions discovered during operation. When any instruction in SKILL.md or its references conflicts with a rule here, this section takes precedence.

Apply these resolutions when references conflict:
1. No-bullet narrative applies to proposal body sections only; diagnostics/review reports may use structured lists.
2. Interaction extras (reverse questioning, suggested follow-up questions, extended thinking) are optional by context, not mandatory on every response.
3. Merge order is fixed: references at the end of final merged manuscript.
4. P2 should not include numbered literature markers; citation numbering is restricted to P1.

(V-01 validation implementation note — SQ nodes carry no `mapped_to_h` field — moved to `references/02_核心机制.md` §2.3.)

*Source: accumulated from operation feedback; last reviewed 2026-05.*

## Execution Workflow

### Write Mode
Follow phased gates in order:
1. Phase 0: initialize project profile, section targets, mapping cardinality.
   - 🔴 **必须选定「科学问题属性」四选一**（鼓励探索·突出原创 / 聚焦前沿·独辟蹊径 / 需求牵引·突破瓶颈 / 共性导向·交叉融通），写入 profile `science_problem_attribute`。注意与「研究属性（自由探索类/目标导向类）」区分，二者是独立字段。未选定将在 Phase 7 `gate-check` 触发 `failed_at=profile` 阻断。
2. Phase 1: write P1 with full citation pipeline and verification.
   - 每节先跑 `python scripts/state_manager.py --root . write-cycle --section P1`（逐节预算/上下文注入的预写门控，完整参数见 references/08）；不得跳过直接硬写。
   - Input: confirmed project profile (title, discipline, H/O/RC/KSQ mapping counts).
   - Output: `sections/P1_立项依据.md` + `data/literature_index.json` (all P1 citations verified) + updated `context_memory.md`.
   **Citation Type by Context for P1 (立项依据，MANDATORY):** specific mechanistic/experimental claims (具体科学论点) must cite Original Articles as primary evidence; clinical evidence cites Clinical Trials at the same priority; preprints are last-resort, labeled `[Preprint]`, used only when no peer-reviewed equivalent exists. Full context-to-type mapping and the `role` taxonomy (gap_evidence / method_support / prior_work / comparison / background) live in `references/04_文献管理.md`.
3. Phase 2: write P2 研究内容（contains all sub-content: H/O/RC/KSQ, methods, innovations, annual plan）.
   - 每节先跑 `python scripts/state_manager.py --root . write-cycle --section P2`（逐节预算/上下文注入的预写门控，完整参数见 references/08）；不得跳过直接硬写。
   - Input: verified P1; H/O/RC/KSQ mapping counts from Phase 0; consistency_map.json with SQ entries.
   - consistency_map 条目结构（mapped_from_sq / mapped_to_objective / supports_method 等字段名）见 `references/02_核心机制.md` §2.2，按其字段名产出避免 validate 报错。
   - Output: `sections/P2_研究内容.md` + updated `data/consistency_map.json` (H→O→RC→KSQ→M→IN all links validated) + `sections/figure_prompts.md`.
   - Sub-content order: 研究假说(H) → 研究目标(O) → 研究内容(RC) → 关键科学问题(KSQ) → 研究方案与技术路线(M) → 特色与创新之处(IN) → 年度研究计划.
   - No literature numbers anywhere in P2. Paragraph narrative throughout; annual plan may use year-based paragraphs.
   - Every M must trace back to a specific RC; every IN must trace to RC and M.
   - **Figure Prompt Generation（AI绘图提示词）：** Phase 2 完成后，为技术路线图等必要图表生成绘图提示词，保存至 `sections/figure_prompts.md`。模板与生成规则见 `references/10_Figure_Prompt规范.md`。
4. Phase 3: write P3 研究基础（4 sub-files）.
   - 每节先跑 `python scripts/state_manager.py --root . write-cycle --section P3_1`（其余子节同理 P3_2/P3_3/P3_4；逐节预算/上下文注入的预写门控，完整参数见 references/08）；不得跳过直接硬写。
   - Input: P2 confirmed; team CV, platform data, and prior publications from Phase 0 profile.
   - Output:
     - `sections/P3_1_研究基础与可行性分析.md` (prior work + feasibility evidence per M + risk mitigation)
     - `sections/P3_2_工作条件.md` (equipment, facilities, missing conditions and remedies)
     - `sections/P3_3_正在承担的相关项目.md` (ongoing projects; explain overlap/difference from this project)
     - `sections/P3_4_完成基金项目情况.md` (completed grants summary ≤500字 + deliverables list)
   - Each M in consistency_map must have at least one feasibility entry (F) sourced from P3_1 or P3_2.
   - **伦理审查（涉人类受试者/实验动物/生物安全/人类遗传资源时为硬项）：** P3_1 可行性分析须说明已获或计划申请的伦理审查批件（如医学伦理委员会、实验动物福利伦理、生物安全审批、人类遗传资源采集/保藏/利用审批），尚未取得的注明送审计划与时间节点。不涉及上述情形则无需展开。
   - P3_3 and P3_4 may use list format (tables allowed).
5. Phase 4: write P4 其他需要说明的情况（≤500字）.
   - 每节先跑 `python scripts/state_manager.py --root . write-cycle --section P4`（逐节预算/上下文注入的预写门控，完整参数见 references/08）；不得跳过直接硬写。
   - Input: P3 confirmed.
   - Output: `sections/P4_其他需要说明的情况.md`.
   - Cover: concurrent grant applications, senior PI prior grants, postdoc status, AI usage declaration, ethics/biosafety/human-genetic-resource approvals (若涉及，与 P3_1 伦理说明呼应), any other required disclosures.
6. Phase 5: write 预算说明书（B1-B3）.
   - Input: P2 confirmed (M entries define budget items); project profile (budget_total, duration).
   - Output:
     - `sections/B1_预算说明_直接费用.md` (equipment; materials; tests; travel/conference; publications; labor; consulting — three-line tables where required)
     - `sections/B2_预算说明_合作外拨.md` (co-institution allocation, or "无")
     - `sections/B3_预算说明_其他来源.md` (other funding sources)
   - Budget total must equal profile `budget_total`; each major budget item traces to an M entry.
7. Phase 6: write 中英文摘要（abstract-last, based on full draft）.
   - Input: all sections P1–P4 confirmed; run `python scripts/state_manager.py --root . load --global` for full-text summary.
   - Output: `sections/00_摘要_中文.md` (≤400汉字) + `sections/00_摘要_英文.md` (≤300英文词).
   - Keywords must align with `consistency_map.keywords_trace`.
8. Phase 7: 全文自审与终稿 + merge.
   - Input: all sections (00, B1-B3, P1-P4, REF) confirmed.
   - Run `diagnosis_engine.py full-review` and `consistency_mapper.py validate` (完整参数见 Script Entry Points); fix all ERROR-level issues.
   - Run `python scripts/word_counter.py summary sections` and `python scripts/state_manager.py --root . page-estimate --sections-dir sections`; if >30 pages, trim specific locations.
   - Run `humanizer_zh.py scan-all` before final output.
   - Output: `output/申请书_合并.md` (merge order: 00摘要 → B1-B3预算 → P1 → P2 → P3_1~P3_4 → P4 → REF).

At each phase:
- snapshot
- sync required state files
- halt for user confirmation

### Polish Mode
1. Import draft and split into atomic section files by original heading hierarchy.
   - Fallback: if heading hierarchy is ambiguous or absent, present detected section list to user for manual confirmation before splitting.
2. Generate strict review report first (`polish_review_report`).
   - Fallback: if `diagnosis_engine.py` fails, output a manual checklist covering: consistency / citation / writing style / format/length dimensions.
3. Agree priority with user (rewrite vs polish vs keep).
   - **Hard block:** do not proceed to step 4 until user explicitly confirms priority order per section or sets a global default. Accept responses like "rewrite P1, polish P2, keep P3".
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
- `data/mcp_literature_cache.json`
- `data/manual_review_queue.json`
- `context_memory.md`
- `project_state.json`
- `history_log.json`

Any missing sync blocks phase progression.

**State Corruption Fallback:** If any required state file is missing or unparseable (JSON decode error), run `python scripts/state_manager.py --root . sync-all --auto-fix` to restore defaults. (`init --repair` does not exist; `sync-all --auto-fix` is the correct repair command.) Do not proceed without valid state files.

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
- `failed_at=profile`: 科学问题属性未选定或取值非四类官方措辞之一。回到 Phase 0 与用户确认四选一，写入 profile `science_problem_attribute`（`python scripts/state_manager.py --root . profile --json '{"science_problem_attribute":"聚焦前沿、独辟蹊径"}'`），再 re-run `gate-check`。
- `failed_at=sync`: run `sync-all --auto-fix`, then re-run `gate-check`.
- `failed_at=citation`: repair index/cache, re-run `verify-all --require-mcp`, then `gate-check`.
- `failed_at=matrix`: run `matrix-check` and `reorder`, then `gate-check`.
- `failed_at=review`: fix D/C dimensions from review report, then `gate-check`.

**Dual-Track Citation Verification:** Provide MCP retrieval cache in `data/mcp_literature_cache.json` and run online validation without `--offline` whenever network is available. Final gate must enforce `--require-mcp`.

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
- `references/10_Figure_Prompt规范.md`

## Output Contract
Deliverables should include:
- section files under `sections/` (canonical filenames):
  `P1_立项依据.md`, `P2_研究内容.md`,
  `P3_1_研究基础与可行性分析.md`, `P3_2_工作条件.md`, `P3_3_正在承担的相关项目.md`, `P3_4_完成基金项目情况.md`,
  `P4_其他需要说明的情况.md`,
  `B1_预算说明_直接费用.md`, `B2_预算说明_合作外拨.md`, `B3_预算说明_其他来源.md`,
  `00_摘要_中文.md`, `00_摘要_英文.md`, `REF_参考文献.md`
- updated state and data files
- review reports in `data/`
- merged manuscript in `output/` (md/docx if requested)

When reporting to user, state:
- what was changed
- which gate passed/failed
- what is blocked and exact unblock action

## Script Entry Points
正文仅保留5条最常用核心命令；write-cycle 各节 token 预算、verify-entry / matrix-check / validate-one / polish-review / validate-order / 阶段稿 merge / word_counter 等完整调用与子命令清单见 `references/08_脚本清单与合并规则.md`。

- init: `python scripts/state_manager.py --root . init`
- sync-all (repair): `python scripts/state_manager.py --root . sync-all --auto-fix`
- gate-check (full, requires MCP): `python scripts/state_manager.py --root . gate-check --sections-dir sections --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --mcp-cache data/mcp_literature_cache.json --mcp-ttl-days 30 --require-mcp`
- merge: `python scripts/section_merger.py merge --sections-dir sections --output output/申请书_合并.md`
- full-review: `python scripts/diagnosis_engine.py full-review --sections-dir sections --consistency data/consistency_map.json --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --output data/diagnosis_report.json`

Phase 7 引用的 `consistency_mapper.py validate` 完整形式：`python scripts/consistency_mapper.py --path data/consistency_map.json validate`。
其余脚本（write-cycle 逐节预算、citation_validator verify-all/verify-entry/matrix-check、humanizer_zh scan-all、load 变体、word_counter summary）为生产级工作流工具，完整 flag 见 references/08。


## Regression Tests
`tests/` directory not yet built. Unit test suite is planned but not implemented.
`test-prompts.json` 仅验证触发与门禁交互，脚本逻辑需人工抽查。

---

## Figure Prompt 触发规则
- 技术路线图：Phase 2 必须生成；研究框架图：Phase 1 推荐生成；预期结果用占位符 `[Preliminary Data Fig N]`。
- 统一色板（深蓝=主线索，绿色=创新点，橙色=预期产出），每张图须映射到 consistency_map 中至少一个 RC。
- 完整提示词模板与生成规则见 `references/10_Figure_Prompt规范.md`。
