---
name: nsfc-proposal
description: Use when drafting, restructuring, or polishing Chinese NSFC proposals (2026 template), especially when strict section-by-section gating, hypothesis-objective-content-problem consistency, literature verification via paper-search MCP, and anti-AI Chinese academic writing constraints are required. 触发词：国自然、国家自然科学基金、基金申请书、科研申请、NSFC。
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
Four entities form the consistency backbone of every NSFC proposal. All must map 1:1.

| Symbol | Chinese | Role | Example |
|--------|---------|------|---------|
| H | 假说 (Hypothesis) | Causal claim derived from SQ | "A蛋白通过B通路调控C过程" |
| O | 目标 (Objective) | What you **do** (action-oriented) | "阐明XXX的机制" |
| RC | 研究内容 (Research Content) | Specific investigation; links to methods | "通过ChIP-seq分析A蛋白的结合位点" |
| KSQ | 关键科学问题 (Key Scientific Question) | What you **answer** (question-oriented) | "XXX如何调控YYY？" |

Mapping constraint: H-n ↔ O-n ↔ RC-n ↔ KSQ-n (strict one-to-one, no cross-linking allowed).

**If user asks a conceptual question about any of H/O/RC/KSQ/SQ/mapping:** load `references/02_核心机制.md` and answer from it before continuing with workflow phases.

## Inputs Required
Collect before execution:
- Project basics: title, discipline code, project type, research attribute, duration, budget.
- Existing materials: draft files, prior work, platform/conditions, related projects.
- User constraints: word targets per section, preferred P2 sub-structure, H/O/RC/KSQ mapping count.

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

## Non-Conflict Canon (Authoritative)
Apply these resolutions when references conflict:
1. No-bullet narrative applies to proposal body sections only; diagnostics/review reports may use structured lists.
2. Interaction extras (reverse questioning, suggested follow-up questions, extended thinking) are optional by context, not mandatory on every response.
3. Merge order is fixed: references at the end of final merged manuscript.
4. V-01 consistency validation must not require nonexistent `mapped_to_h` fields on SQ nodes. Validate by traversing H and KSQ links from SQ references.
5. P2 should not include numbered literature markers; citation numbering is restricted to P1.

## Execution Workflow

### Write Mode
Follow phased gates in order:
1. Phase 0: initialize project profile, section targets, mapping cardinality.
2. Phase 1: write P1 with full citation pipeline and verification.
   - Input: confirmed project profile (title, discipline, H/O/RC/KSQ mapping counts).
   - Output: `sections/P1_立项依据.md` + `data/literature_index.json` (all P1 citations verified) + updated `context_memory.md`.
   **Citation Type by Context for P1 (立项依据，MANDATORY):**
   - Background / research gap overview (前言/综述) → Reviews or Systematic Reviews preferred.
   - Specific mechanistic/experimental claims (具体科学论点) → Original Articles (mandatory primary evidence).
   - Clinical evidence → Clinical Trials (same priority as Original Articles).
   - Emerging findings → Preprints (label as [Preprint]; use only when no peer-reviewed equivalent exists).
3. Phase 2: write P2 and enforce strict H/O/RC/KSQ one-to-one mapping.
   - Input: verified P1; confirmed H/O counts and KSQ list from project profile.
   - Output: `sections/P2_研究方案.md` + updated `data/consistency_map.json` (all H→O→RC→KSQ links validated).
4. Phase 3: write 研究方案/技术路线（P3）.
   - Input: verified P2 + user confirmation; consistency_map.json with H/O/RC/KSQ links.
   - Output: `sections/P3_研究方案.md` + updated `context_memory.md`.
   - Each technical route must trace back to at least one RC; include flowcharts or milestones as structured text.
   - No free-standing methods without corresponding RC linkage.

   **Figure Prompt Generation（AI绘图提示词）：** Phase 3 完成后，为技术路线图、框架图等必要图表生成绘图提示词，保存至 `sections/figure_prompts.md`。提示词模板与生成规则详见文末**附录：Figure Prompt 规范**。
5. Phase 4: write 可行性分析（P4）.
   - Input: P3 confirmed; project profile (platform, team, prior data).
   - Output: `sections/P4_可行性分析.md`.
   - Cover technical feasibility, team capacity, and equipment/resource availability; cite preliminary data where available.
   - Must not introduce new hypotheses not already declared in P2.
6. Phase 5: write 创新性（P5）.
   - Input: P1 literature_index.json + P2 H/O mapping confirmed.
   - Output: `sections/P5_创新性.md`.
   - State innovation points as numbered claims; each claim must contrast explicitly with existing work cited in P1.
   - Max 3-5 innovation points; avoid vague superlatives.
7. Phase 6: write 预期成果与研究计划（P6）.
   - Input: P3 technical route + project duration from project profile.
   - Output: `sections/P6_预期成果与计划.md`.
   - Annual milestones must align with RC timeline; deliverables (papers, patents, datasets) tied to specific phases.
   - Budget allocation narrative must reference methods in P3.
8. Phase 7: write 研究基础与条件（P7）+ global consistency + merge.
   - Input: all sections P1-P6 confirmed; team CV and platform data from project profile.
   - Output: `sections/P7_研究基础.md` + `output/申请书_合并.md` (merged manuscript).
   - Run `diagnosis_engine.py full-review` and `consistency_mapper.py validate` before merge; fix all ERROR-level issues.
   - Chinese/English abstracts generated last from merged content; run `humanizer_zh.py scan-all` before final output.

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

**State Corruption Fallback:** If any required state file is missing or unparseable (JSON decode error), run `python scripts/state_manager.py --root . init --repair` to restore defaults. Do not proceed without valid state files.

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

## Output Contract
Deliverables should include:
- section files under `sections/`
- updated state and data files
- review reports in `data/`
- merged manuscript in `output/` (md/docx if requested)

When reporting to user, state:
- what was changed
- which gate passed/failed
- what is blocked and exact unblock action

## Script Entry Points
Use scripts under `scripts/` from proposal project root:
- `python scripts/state_manager.py --root . init`
- `python scripts/state_manager.py --root . load --section P1 --minimal`
- `python scripts/state_manager.py --root . write-cycle --section P1 --token-budget 4000`
- `python scripts/state_manager.py --root . sync-all --auto-fix`
- `python scripts/state_manager.py --root . gate-check --sections-dir sections --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --mcp-cache data/mcp_literature_cache.json --mcp-ttl-days 30 --require-mcp`
- `python scripts/consistency_mapper.py --path data/consistency_map.json validate`
- `python scripts/consistency_mapper.py --path data/consistency_map.json validate-one V-01`
- `python scripts/citation_validator.py verify-all --index data/literature_index.json --p1 sections/P1_立项依据.md --mcp-cache data/mcp_literature_cache.json --mcp-ttl-days 30 --require-mcp --manual-review data/manual_review_queue.json --log data/verification_run_log.json`
- `python scripts/citation_validator.py verify-entry --index data/literature_index.json --p1 sections/P1_立项依据.md --ref-number 1 --mcp-cache data/mcp_literature_cache.json --require-mcp`
- `python scripts/citation_validator.py matrix-check --p1 sections/P1_立项依据.md --index data/literature_index.json --ref sections/REF_参考文献.md`
- `python scripts/humanizer_zh.py scan-all sections`
- `python scripts/diagnosis_engine.py full-review --sections-dir sections --consistency data/consistency_map.json --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --output data/diagnosis_report.json`
- `python scripts/diagnosis_engine.py polish-review --sections-dir sections --consistency data/consistency_map.json --index data/literature_index.json --p1 sections/P1_立项依据.md --ref sections/REF_参考文献.md --json-output data/diagnosis_report.json --md-output data/polish_review_report.md`
- `python scripts/section_merger.py validate-order --sections-dir sections`
- `python scripts/section_merger.py merge --sections-dir sections --output output/申请书_合并.md`
- `python scripts/section_merger.py merge --sections-dir sections --only P1_立项依据.md,P2,REF_参考文献.md --output output/阶段稿_合并.md`
- `python scripts/word_counter.py summary sections`

These scripts are production-ready workflow utilities for iterative proposal drafting and polishing.


## Regression Tests
- `python3 -m unittest discover -s tests -p 'test_*.py'`

---

## 附录：Figure Prompt 规范

为申请书中需要的图（技术路线图、研究框架图、预期结果示意图等）生成绘图提示词，存入 `sections/figure_prompts.md`：

```
[FIGURE PROMPT — <figure role, e.g., Technical Roadmap / Research Framework / Preliminary Data>]
TYPE: Workflow | Conceptual framework | Mechanistic schematic | Data plot | Experimental design
SUBJECT: <specific content, e.g., "Three-phase technical roadmap for investigating X mechanism in Y disease model">
STYLE: BioRender风格, 科研示意图, 最高分辨率, white background (#FFFFFF), suitable for NSFC proposal submission [默认BioRender风格；如需其他风格（如简约线条风 / PowerPoint扁平风 / 手绘概念图），在启动时告知]
COLOR SCHEME: Primary #1A5276 (dark blue, main flow) | Secondary #148F77 (green, key innovations) | Accent #D35400 (orange, expected outputs) | Neutral #566573 | Background #FFFFFF
ELEMENTS:
  - Phase/Stage boxes: <label, sequential left→right or top→bottom>
  - Connecting arrows: solid arrows for sequential flow, dashed for feedback loops
  - Key innovation markers: highlighted box or star symbol at innovation points
  - Input/Output labels: brief text labels at start and end nodes
  - <Additional element if needed>
LAYOUT: <Horizontal flow 3-phase | Vertical hierarchy | Mixed: top-level + branching sub-tasks> | aspect ratio 16:9 preferred for roadmap
TYPOGRAPHY: Chinese labels allowed for NSFC figures, Arial/SimHei 9-10pt, phase headers bold, sub-labels regular
HIERARCHY LEVELS: <e.g., Level 1: 3 main phases | Level 2: 2-3 tasks per phase | Level 3: key outputs>
KEY MESSAGE: <one sentence summarizing what this diagram communicates to reviewers>
AVOID: 3D effects, excessive colors (>4 colors), clip art, stock icons, overly complex branching that obscures the main logic
```

**生成规则：**
- 技术路线图（技术路线 / 研究方案）：Phase 3 必须生成
- 研究框架图（总体框架）：Phase 1 推荐生成（研究逻辑适合可视化时）
- 预期结果示意图：用占位符 `[Preliminary Data Fig N]` 标注
- 所有图使用统一色板（深蓝=主线索，绿色=创新点，橙色=预期产出）
- 每张图必须能在 consistency_map.json 中映射到至少一个 RC（研究内容）
