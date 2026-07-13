---
name: review-writing
description: "Universal assistant for writing high-impact academic literature reviews (Nature/Cell/Lancet level). Supports real-time Zotero integration, outline persistence, and multi-mode reference management. Use when writing a comprehensive review article requiring systematic search, synthesis, and citation management. 触发词：写综述、文献综述、综述写作、literature review、review article、改综述、完善综述、继续写综述、improve review。"
triggers:
  - "写综述"
  - "literature review"
  - "review article"
  - "写review"
  - "综述写作"
  - "写文献综述"
  - "改综述"
  - "完善综述"
  - "improve review"
  - "edit review"
  - "continue review"
  - "继续写综述"
not_for:
  - 原始研究论文（Original Research Article）
  - 单篇论文修改/润色（非综述）
  - 短篇评论/Commentary/Letter（<3000 words）
  - 非学术写作（科普、博客）
scoping_review_note: |
  Scoping review 支持（轻量流程，不需 PROSPERO）。Phase 0 选择综述类型时选 scoping，
  检索覆盖面更宽、纳排标准更宽松，需记录研究问题框架（PCC: Population/Concept/Context）。
systematic_review_note: |
  Systematic review / Meta-analysis 支持（系统综述模式）。Phase 0 综述类型选 systematic，
  叠加 PRISMA 2020 流程（计数→流程图）、PICO/PECO 纳排登记、逐研究 RoB（RCT→RoB 2 / 观察性→ROBINS-I）、
  可选 meta 分析（效应量/I²/森林图/漏斗图）、GRADE 证据分级。细则见
  references/systematic_review_methodology.md。本技能产出结构化数据与表格，不自动注册 PROSPERO、
  不内置数值合并引擎（合并交由 stats 工具/matplotlib 配图）。
why_how_what_note: |
  WHY-HOW-WHAT 轻量模式。Phase 0 综述类型选 why-how-what，按 WHY(动机/问题)/HOW(方法)/WHAT(发现)
  三层结构化对比文献，介于快速摘要与完整综述之间，不跑 PRISMA/RoB/GRADE。细则见
  references/why_how_what_mode.md。
---

# General Literature Review Writing Specialist

## Quick Reference Card

### Phase 路由（读 state.json 后立即判断）
> **⚠️ 前置门：`state.json` 不存在时，先执行 Mode Handshake Gate（问 Write/Polish Mode）并等用户回答，再进 Phase 0.1。不要跳过 Mode Gate 直接收参数。**

| state.json 状态 | 跳转到 |
|-----------------|--------|
| 不存在 | **先过 Mode Handshake Gate** → Phase 0.1 |
| phase=0, 无 mode 字段 | Phase 0.5（继续初始化）→ 完成后进 **Phase 1.5**（调研先于提纲） |
| phase=0, mode="polish" | Phase 0-P（📖 读 `docs/phase_0p_polish_mode.md`） |
| phase=1.5 | Phase 1.5（探索检索 + 研究空白，检查是否已完成） |
| phase=1.6 | Phase 1.6（对标综述库 + 框架指南） |
| phase=1.7 | Phase 1.7（据调研建提纲 + 用户确认 + 结构签字落锁） |
| phase=2 | Phase 2（跳过 completed_sections） |
| phase=3 或 pending_sections 非空 | Phase 3（跳过 completed_sections） |
| phase=4, completed=true | Phase 4 导出完成 → 进 Phase 5（投稿包） |
| phase=5, completed=true | 已完成，告知用户 |

### 每 Phase 关键动作
> **核心顺序：调研先于提纲。** 提纲是"读透文献后的产物"，不是开工前置。先 Phase 1.5 探索检索/研究空白 + Phase 1.6 对标框架，再 Phase 1.7 据调研建提纲并确认、落结构签字。
- **Phase 0:** 收参数 → 检测环境 → 创建项目 → git init
- **Phase 1.5:** 定 RQ/PICO → 基于真实文献识别热点/争议/空白 → `data/research_gap.json` → 委托盲检 → **HALT**（用户确认选题方向）
- **Phase 1.6:** 检索 5–10 篇对标综述 → `data/benchmark_reviews.json` + `data/framing_guide.md` → 委托盲检 → **HALT**
- **Phase 1.7:** 据调研（selected gap + 对标框架）建提纲 → 用户确认 → **结构签字落锁** → Zotero 集合树 → **HALT**
- **Phase 2:** 逐节搜索（**串行，≥1s 间隔**）→ 写入 Zotero/index → **HALT** dedup
- **Phase 3:** Read framing_guide 搭框架 → 逐节写作 → citation spot-check → 逐节质量自检（内部 checklist，禁 HTML/禁调 reviewer-simulator）→ **HALT**
- **Phase 4:** 引用总量校验 → citation guard → 编译 → 连贯性扫描 → 缩写扫描 → 导出
- **Phase 5:** 对齐 gsw submission-guide/compliance-gate → 生成投稿包（Cover Letter/Title Page/CRediT/COI/Funding/DAS/Keywords...）→ 委托盲检

### 绝对禁止
- 并行搜索调用
- websearch/tavily 查文献
- 跳过逐节质量自检（内部 checklist）
- 跳过 state.json 更新
- 跳过 Git Checkpoint

---

## Role & Core Philosophy

An academic consultant for high-impact literature reviews (Nature Reviews, Cell, Lancet Digital Health), working across biomedicine and CS/AI.

- **Synthesis, not Summary:** Connect and contrast studies. Build new theoretical frameworks.
- **Arbitration:** Identify contradictions and analyze *why* they exist.
- **Storytelling:** Every review must have a narrative arc.
- **Figure-Driven:** High-impact papers are built around figures.

---

## Constraints & Standards

1. **Length:** 7,000–10,000 words (English); 15,000–20,000 characters (Chinese). Read target from `outline.md`.
2. **Citations（软目标，随学科浮动，非硬门禁）:** 面向高影响力综述的**建议**总量随学科差异很大：生物医学/临床约 120–200，工程/CS 约 60–120，人文社科视传统而定。以**覆盖领域主线**为准，不是凑数。机器只统计唯一引用总数、对低于阈值给**警告不阻断**（`count-citations`）；类型拆分无法机器校验（index 无类型字段），靠人工/盲检抽查。类型配比按论点性质择用、**非固定配额**：
   - Background/overview → Reviews preferred.
   - Mechanistic/experimental claims → Original Articles (mandatory; do NOT substitute a Review).
   - Clinical claims → Clinical Trials.
   - Emerging claims → Preprints（label `[Preprint]`，**按需、非强制**）：仅当某新兴论点确无正式发表可引时才用；无此类论点则不必凑预印本。
   - **文献量不足时怎么办**：先分清是"领域本就小/短篇综述"还是"检索不充分"。前者按实际写、在搜索日志注明检索范围，不硬凑；后者回 Phase 2 补检索（扩同义词 / 放宽年限 / 换库）。**绝不为达数而引入弱相关或未读文献**——凑数引用比数量少更伤质量。
3. **Numbering:** Global Sequential (`[1]`, `[2]`, … `[N]`). Never reset per chapter.
4. **Timeliness:** Core focus past 5 years.
5. **Truthfulness:** ZERO TOLERANCE for hallucinated citations. Verify every paper via search tools.
6. **No Bullet Points** in body text. Paragraphs only.
7. **Local Reference List:** Append `## References` at end of every draft file.
8. **Journal-Specific Adaptation:** Read `Target Journal` from `outline.md` and apply these differentiators:

| Aspect | Nature Reviews | Cell / Cell Press | Lancet Digital Health |
|--------|---------------|-------------------|----------------------|
| Tone | Authoritative, synthesizing | Mechanistic, hypothesis-driven | Clinical, evidence-based |
| Figure emphasis | Conceptual schematics dominate | Data-rich multi-panel figures | Clinical workflow diagrams |
| Citation balance | Reviews + seminal papers | Original articles heavy | Clinical trials + guidelines |
| Unique convention | "Box" sidebars for definitions | "Graphical Abstract" required | "Panel" for sub-analyses |
| Word budget | 8,000–10,000 | 7,000–9,000 | 5,000–8,000 |

> These are starting heuristics. Always verify against the target journal's actual Author Guidelines (AI should check the journal website if unsure about a specific convention).

---

## Search Tool Priority (Universal)

Detection is **capability-based**, NOT client-name-based:

| Priority | Tool | When to use |
|----------|------|-------------|
| 1st (Medical/Bio) | PubMed CLI (`esearch`/`efetch`) | Medical, biomedical, clinical topics |
| 1st (CS/AI) | paper-search MCP (`search_arxiv`, `search_pubmed`) | CS, AI, pure engineering |
| 2nd | paper-search MCP (`search_google_scholar`) | Papers not found on PubMed or arXiv; cross-disciplinary; grey literature |
| 3rd | paper-search MCP (`search_arxiv`, `search_pubmed`) | Fallback when PubMed CLI unavailable |
| Exception | ChatGPT Browsing tool | If current client is ChatGPT web with Browsing, it can directly access PubMed/Scholar |

> **Google Scholar补充规则：** PubMed检索完成后，若某节文献数量仍不足或主题偏交叉学科（工程/社科/政策），追加 `search_google_scholar` 补搜。Google Scholar收录范围更广，PubMed未收录的会议论文、技术报告、交叉学科期刊通常可在此找到。但Google Scholar无DOI强制要求，获取记录后须通过 `validate_citations.py --live` 验证。

**Detection:** Check AI tool list for `search_pubmed`/`search_arxiv`/`search_google_scholar` → paper-search MCP available ✅

**Forbidden:** `websearch`, `tavily`, generic web search tools. Do not use them for academic retrieval.
Reason: CLI clients' web search uses cached indices with no complete metadata; high hallucination risk for DOI/author/year.

**PubMed CLI command** (read `pubmed_proxy` from `outline.md`):

> **Windows:** edirect does not run in PowerShell/CMD. Use WSL bash, or skip to paper-search MCP fallback.

```bash
# Mac/Linux/WSL bash — ensure edirect is on PATH (AI client shells often skip ~/.bashrc)
export PATH="${HOME}/edirect:${PATH}"

# If pubmed_proxy=none:
esearch -db pubmed -query "QUERY" < /dev/null | efetch -format abstract
# If pubmed_proxy=http://127.0.0.1:PORT:
http_proxy=http://127.0.0.1:PORT esearch -db pubmed -query "QUERY" < /dev/null | efetch -format abstract
```

**Serial Search (MANDATORY):** All search calls must be serial, ≥1s interval. NO parallel search calls.

---

## Anti-AI Writing Style

> 📖 Full ban lists (EN/CN), Deep Rewriting protocol, and Abbreviation/Acronym Management rules live in `references/writing_guidelines.md` §4. **Read it before writing/polishing any section.** Quick reminders:
> - EN ban examples: Moreover, Crucial, Landscape, Delve into, "It is worth noting", "Not only…but also", trailing "-ing" clauses.
> - CN ban examples: 值得注意的是、此外、综上所述、深入探讨、至关重要、一方面……另一方面.
> - Rhythm: never 3+ consecutive similar-length sentences. Active voice preferred.
> - Abbreviation first-use: `Full Name (ABBR)` (EN) / `中文全称（英文全称, ABBR）` (CN); reuse ABBR after first definition; never abbreviate in the title.

---

## Subagent Delegation (Optional)

> 📖 可委托任务清单及规则详见 `references/subagent_guide.md`

**NOT delegatable:** Outline design, synthesis writing, 逐节质量自检的修订/HALT decisions, user interaction, HALT decisions.

---

## Mode Handshake Gate (Mandatory)

Before any **writing / search / import / Zotero-mutating** action, ask exactly **one** question and wait for explicit user answer:

- `Write Mode` — build review from scratch (→ Phase 0)
- `Polish Mode` — import existing draft, diagnose, revise section by section (→ Phase 0-P)

**Do not proceed until user explicitly selects a mode.**

> **Exception — Read-only status check:**
> If the user explicitly asks to *inspect current project status*, *audit progress*, *scan existing materials*, or "看看现在到哪一步了 / 先扫描一下", perform a **read-only** pass over `outline.md`, `state.json`, `drafts/`, `data/`, and `scripts/` first, then present a status report. After the report, ask for Write/Polish Mode before any new literature import or drafting action. If `state.json` does not exist, the read-only scan still must return to the Mode Handshake Gate afterward; never auto-start Phase 0.
> Read-only means: no file writes, no Zotero API mutations, no search calls.

> **Route map:**
> ```
> Write Mode:  Phase 0 (init) → Phase 1.5 (research gap) → Phase 1.6 (benchmark reviews+framing) → Phase 1.7 (outline from research + sign-off) → Phase 2 (search) → Phase 3 (write) → Phase 4 (export) → Phase 5 (submission pack)
> Polish Mode: Phase 0 (init) → Phase 0-P (import+diagnose) → Phase 3 (write) → Phase 4 (export) → Phase 5 (submission pack)
> ```
> **调研先于提纲**：Write Mode 先调研（1.5 研究空白 + 1.6 对标框架），提纲在 Phase 1.7 据调研结果建立并落结构签字——提纲是读透文献后的产物，不是开工前置。
> Phase 1.5 / 1.6 / 1.7 are Write-Mode only (Polish Mode imports an existing draft, so gap/framing/outline-building are skipped). Phase 5 runs in both modes.
>
> Resume rule: if `state.json` already exists in the project folder, read it first.  
> If `"mode": "polish"` → skip to Phase 0-P Step 6 (resume pending sections).  
> If `"phase" ≥ 1` (Write Mode) → jump to the appropriate phase directly.
>
> **Project path discovery (cross-session resume):**
> When user says "继续写综述" / "continue review" without specifying a path:
> 1. Check CWD for `state.json` → if found, use CWD as project root
> 2. Check CWD subdirectories (1 level deep) for `state.json` → if exactly 1 found, use it; if multiple, list and ask user
> 3. If not found → ask user for project path: "请提供综述项目目录路径（包含 state.json 的文件夹）"
> After locating, `cd` into the project directory before any further operation.

> **🔁 接续与决定日志（每次进入/续写的第一动作，项目已存在时必做）：**
> 1. 定位到项目根后，**第一件事先跑 Phase 0.5 打印的 `RESUME_CMD`**（绝对路径指向 `_shared/session_journal.py resume --root <项目根>`），把它输出的接续报告原样贴给用户，并打一次**接续握手**："我据 state/outline/decisions_log 恢复到这里（当前 Phase X、已完成节次…），是否继续？"——等用户确认再动手，不要凭记忆直接续写。
> 2. **用户中途插入任何临时要求**（改结构、调顺序、换重点等），立即用 `session_journal.py log --root <项目根> --note "用户要求：<原话>"` 追加到 `decisions_log.md`（append-only，后续会话必读），再执行。
> 3. `RESUME_CMD` 只读展示、绝不阻断；新项目（state.json 尚不存在）跳过本步，直接走 Mode Handshake Gate。

---

## 开场监工卡（每次启动本技能必须原样打印给用户）

> **[必做] 每次进入本技能（含续写恢复），在选定 Write/Polish 模式后、出提纲前，先把下面这张卡原样贴给用户。** 目的是让你（用户）知道正常流程该在哪儿停、该抽查什么，别被 AI 一口气写到底。

```
📋 综述写作监工卡（写综述容易踩的坑，请盯这几条）
1. 正常会停好几次等你拍板：提纲确认 → 选题方向 → 对标框架 → 每写完一节验收。
   AI 一口气从头写到尾是不正常的，遇到这几处它必须停下来问你。
2. 文献真伪要你亲自抽查：随手挑几条引用的 PMID / DOI，自己去 PubMed / 期刊页搜一下核对。
   （尤其 Windows 上文献检索工具 edirect 常失效，AI 可能凭印象编出看着像真的假文献。）
3. 每写完一节就停下来给你验收：别让 AI 连着写好几节，写一节你看一节再放行。
4. 门禁说"通过"不能只信一句话：要求 AI 把门禁脚本的原始输出原文贴出来，
   不接受只说"✅ 通过"——没有原始输出就当没通过。
```


**Principle:** Complete ALL checks once before any other work. Prevent mid-task failures.

### 0.1 Collect Parameters

Ask all parameters at once. State defaults; user may accept silently.

| Parameter | Default | Notes |
|-----------|---------|-------|
| Review title/topic | (required) | Used as project folder name |
| Project location | **current working directory** | Path where `[TITLE]/` folder will be created |
| Target journal | (required) | Affects word count and citation density |
| Writing language | **English** | English / Chinese (Chinese: only changes writing language, same search tools) |
| Discipline | **Medical/Biomedical** | Determines search tool priority |
| **Review type** | **narrative** | `narrative`（叙述性）/ `critical`（批判性）/ `scoping`（范围综述）/ `systematic`（系统综述/Meta）/ `why-how-what`（三层轻量对比）。<br>• **scoping**：不需 PROSPERO，检索更宽，研究问题用 PCC（Population/Concept/Context）替代 PICO，Phase 0 末尾提示 scoping 记录要求。<br>• **systematic**：叠加 PRISMA 2020 + PICO/PECO + RoB（RoB 2/ROBINS-I）+ 可选 meta + GRADE。选此档则读取 `references/systematic_review_methodology.md`，并在各 Phase 挂接其触发点（见下「系统综述模式触发点」）。<br>• **why-how-what**：WHY/HOW/WHAT 三层结构化对比，介于快速摘要与完整综述之间，无 PRISMA/RoB/GRADE。选此档则读取 `references/why_how_what_mode.md`。 |
| Word count target | EN: 7,000–10,000 words / CN: 15,000–20,000 chars | |
| Total citations | 软目标(随学科浮动，非硬门禁)：生物医学~120–200 / 工程CS~60–120；仅警告不阻断 | 类型拆分与预印本按需，见 Constraints §2 |
| Reference manager | **Zotero** | Zotero / None / EndNote |
| Subagent model | Same as current session | AI scans available models, user confirms |

**If Chinese writing selected**, notify at end of Phase 0:
> 本技能使用 PubMed/paper-search MCP 检索英文文献。中文数据库（CNKI/万方）补充流程详见 `references/citation_styles.md` § CNKI / 万方中文文献导入。建议在初稿完成后统一补充，避免 gid 编号冲突。

#### 系统综述模式触发点（仅当 Review type = systematic）

> 📖 全部细则见 `references/systematic_review_methodology.md`（选 systematic 档时必读）。本文件只列挂接点：

| Phase | 触发点 | 动作 |
|-------|--------|------|
| **0** | PICO/PECO 登记 | 检索前把纳排标准（PICO 干预型 / PECO 暴露型）写入 `outline.md`；提示用户可选 PROSPERO 注册（本技能不代注册）。 |
| **2** | PRISMA 计数 | 每轮检索/去重后写入计数：`set-screening-counts`（identified/deduplicated/screened/excluded/included），维护「排除原因」表。 |
| **3** | RoB 逐研究评级 | RCT → RoB 2；观察性 → ROBINS-I；产出逐研究 RoB 表（domain × study）。 |
| **3**（可选） | meta 分析 | 仅当用户要求合并：选效应量（OR/RR/MD/SMD）、报告 I²/Q、产出森林图/漏斗图数据（数值合并交 stats 工具，配图交 matplotlib/seaborn）。 |
| **4** | GRADE + 输出 | 逐结局 GRADE 分级（high/moderate/low/very low + 降/升级因素）；导出 PRISMA 流程图数据块 + RoB 汇总 + SoF/GRADE 表。 |

PRISMA 计数读写命令（systematic 模式专用）：

```bash
python3 scripts/state_manager.py set-screening-counts --identified N --deduplicated N
python3 scripts/state_manager.py set-screening-counts --screened N --excluded N --included N
python3 scripts/state_manager.py get-screening-counts   # 读回校验
```

### 0.2 Full Environment Check

Run the 9-step environment detection (Step 0–8) (📖 full commands in `references/env_check.md`): Step 0 OS+Python, 1 curl, 2 git, 3 Zotero+pyzotero, 4 edirect, 5 proxy+PubMed connectivity, 6 NCBI key, 7 paper-search MCP, 8 required scripts. Display ✅/❌ per step. Record `os` / `git_available` / `pubmed_proxy` / `search_fallback` for Phase 0.5 to write into `outline.md`.

**All 8 must resolve before Phase 0.5.** Failure routing:

| Failed step | Blocking? | Consequence / route |
|-------------|-----------|---------------------|
| 0 Python < 3.7 | **YES** | Abort; guide upgrade (python.org / `brew install python` / `winget install Python.Python.3`). |
| 1 curl missing | **YES** | System-level issue; resolve before continuing (Windows: curl ships with PowerShell 5.1+). |
| 2 git missing | No | Not blocking, but **ASK** user to install (no snapshot fallback → no rollback without git). 装好重跑；拒装则确认知悉后继续，Checkpoints 静默跳过（`git_available: false`）。 |
| 3 Zotero/pyzotero (Zotero mode) | **YES** (Zotero mode) | `pip install pyzotero`; install Zotero desktop. None/EndNote mode → skip Step 3. |
| 4 edirect missing (Medical/Bio) | No | Auto-fallback to paper-search MCP → write `search_fallback: paper-search-mcp`; Windows → WSL or fallback. |
| 5 PubMed unreachable | No | Auto-scan proxy ports; if all fail → fallback to paper-search MCP, notify user. |
| 6 NCBI key unset | No | Optional; default 3 req/s rate limit. |
| 7 paper-search MCP absent | No | PubMed CLI only; inform user MCP is optional. |
| 8 required script missing | **YES** | Abort; verify SKILL_DIR path or re-install the skill. |

> ⚠️ At least one of Step 4/5/7 must yield a working retrieval path (edirect OR paper-search MCP). If **both** PubMed CLI and paper-search MCP are unavailable → HALT (see Edge Cases). Never fall back to websearch/tavily.

### 0.3 Zotero First-Time Setup (Zotero mode only)

> 📖 完整设置步骤（账号注册、API key 生成、权限配置、连接测试、安全规则）详见 `references/zotero_setup.md`。

**凭据持久化：存一次，之后自动复用。** 凭据存于 `~/.config/academic-skills/zotero.json`（用户主目录、chmod 600、不入 git，与技能仓库分离）。

- **已存凭据** → 所有命令自动读取，**无需**再传 `--lib-id/--api-key`。开工时先 `--status` 验证即可（不带凭据参数）。
- **未存凭据** → 引导用户去 https://www.zotero.org/settings/keys 拿 userID + API key（勾选 write 权限），运行一次：

```bash
# 首次：保存凭据（仅需一次）
python3 scripts/zotero_manager.py save-credentials --lib-id [NUMBER] --api-key [KEY]

# 之后：无需再传凭据
python3 scripts/zotero_manager.py --status
# Expected: ✅ Connected to Zotero library ...
```

优先级：命令行参数 > 已存 config > 提示保存。`api_key` 绝不明文回显（日志仅显示后 4 位）。若命令行显式传入 `--lib-id/--api-key` 仍可覆盖 config（不落盘）。

If `--status` lists multiple libraries (personal + group), show the list and ask user which to use, then re-run `save-credentials` with the chosen `lib_id`.

### 0.4 Subagent Model Detection

```
1. List all models available in current AI client
2. Present list to user
3. Ask: which model for subagent tasks? (default: same as current session)
4. Write choice to outline.md: subagent_model: <name>
```

### 0.5 Initialize Project Files

After all checks pass, run `scripts/init_project.py`. It creates the folder structure,
copies the active scripts (REQUIRED_SCRIPTS), writes `state.json` + `outline.md` (templates below), and runs
`git init` + the initial `[review] Phase 0: project initialized` commit (skips git silently if
unavailable). Cross-platform (pure pathlib, no heredoc).

> **⚠️ AI: resolve the three arguments before running:**
> - `--title` = the review title from Phase 0.1.
> - `--base`  = project location from Phase 0.1 (default: current working directory `.`).
> - `--skill-dir` = directory containing this skill. Lookup table:
>
> | Client | `[SKILL_DIR]` (Mac/Linux) | `[SKILL_DIR]` (Windows) |
> |--------|--------------------------|------------------------|
> | Claude Code | `~/.claude/skills/review-writing` | `C:\Users\<name>\.claude\skills\review-writing` |
> | Cursor | `~/.cursor/skills/review-writing` or project `.cursor/skills/review-writing` | `C:\Users\<name>\.cursor\skills\review-writing` |
> | Windsurf | `~/.windsurf/skills/review-writing` | `C:\Users\<name>\.windsurf\skills\review-writing` |
> | Other | Auto-detect: 📖 `references/env_check.md` § SKILL_DIR Auto-Detection | same |

```bash
python3 "[SKILL_DIR]/scripts/init_project.py" \
  --title "[review title]" \
  --base "[PROJECT_BASE]" \
  --skill-dir "[SKILL_DIR]"
# Writes: drafts/ exports/ scripts/ data/ tmp/ figures/ + figures/figure_index.md
#         + state.json {"phase":0,...} + outline.md template + git init & first commit.
```

> **⚠️ Working directory rule:** All commands in Phase 1–4 are run from inside `[PROJECT_BASE]/[TITLE]/`.
> After initialization: `cd "[PROJECT_BASE]/[TITLE]"` (the script prints this path).
>
> **Note:** Phase 0.5 only creates folder structure + copies scripts + writes state.json/outline.md. Zotero collection tree (`--init`) is NOT run here; it runs in Phase 1.7 (Write Mode, after the outline is built from research) or Phase 0-P Step 5 (Polish Mode). Phase 0.5 完成后进入 **Phase 1.5**（调研先于提纲）。

The script writes `[TITLE]/state.json`:
```json
{"phase": 0, "completed_sections": [], "zotero_root_key": ""}
```

…and the `[TITLE]/outline.md` template (AI fills Parameters/Environment fields after Phase 0.1–0.4). The template is auto-generated by `init_project.py`; do NOT recreate it manually. Key fields: Title / Target Journal / Language / Reference Manager / Review Type / Word Count Target / Citation Requirements / Discipline / os / git_available / pubmed_proxy / zotero_lib_id / search_fallback / subagent_model / RQ-PICO / Outline sections / Current Status.

---

## Phase 0-P: Polish Mode

> 📖 **完整步骤详见 `docs/phase_0p_polish_mode.md`**，进入 Polish Mode 时必须读取该文件。

**前置条件：** Phase 0.1–0.5 已完成（outline.md + state.json + scripts 已就位）。

**步骤概要：**
1. **Step 0:** 验证参数（不重复收集）+ 格式依赖检测（.docx / .pdf）
2. **Step 1:** 接收草稿（.md / .docx / .pdf / 粘贴文本）→ `tmp/draft_import.md`
3. **Step 2:** 按标题层级原子拆分 → `drafts/section_XX_XX.md`（**必须用户确认后才写文件**）
4. **Step 3:** 诊断报告（字数 / 引用密度 / AI 特征）→ keep / polish / rewrite / missing
5. **Step 4:** 用户分配优先级（**Hard Block，每节必须有明确标签**）
6. **Step 5:** 引文导入 → `data/literature_index.json`（保留原始 [N] 编号）
7. **Step 6:** 初始化 state.json → 路由到 Phase 3

**路由表：**
| Section type | Path |
|---|---|
| `missing` | Phase 3 内部处理：先搜索再写（不回退 Phase 2） |
| `rewrite` | Phase 3（可选 Round 2 搜索） |
| `polish` | Phase 3（跳过搜索，直接修订） |
| `keep` | 跳过（已在 completed_sections） |

All sections complete → Phase 4 (export + compile).

---


## Git Checkpoint (Reusable Pattern)

After every `state.json` update, run this block if `git_available: true` in `outline.md`:

```bash
git add -A && git commit -m "[review] <MESSAGE>" --allow-empty-message 2>/dev/null || true
```

If git not available → skip silently (`|| true` handles clean-tree case too).
Format: `[review] Phase X.Step: <description>`. 📖 消息表 + Rollback 命令详见 `references/git_rollback.md`。

---

## Phase 1.5: Research Gap Identification（Write Mode only）

> **⭐ 执行顺序（调研先于提纲）：这是 Phase 0 之后的第一个实质阶段。** 提纲不在这里建——先调研（1.5 空白 + 1.6 对标框架），到 **Phase 1.7** 才据调研结果建提纲并落结构签字。

**触发时机：** Phase 0 初始化后立即进入（提纲尚未建立，先摸清领域再据此建提纲）。Polish Mode 跳过（已有成稿）。
**Entry: Read `outline.md`（此时仅有模板骨架）+ `state.json`. If `phase ≥ 1.6`（对标框架已完成）→ already done, skip.**
> **Phase gate:** `state.json` 不存在 → HALT，提示先完成 Phase 0 初始化（Phase 0.5 生成 outline.md/state.json）。

**目的：** 建提纲、搭框架之前，先用**已检索到的真实文献**把这个领域摸清楚：有哪些热点、哪些争议、哪些机制线索、哪些没人填的空白，再让用户挑选题方向。综述的新意不是靠多引文献堆出来的，而是找到一个**有证据支撑、又还没被人好好综述过**的空白。提纲要等这一步读透了才动手。

### 步骤

0. **先定 RQ/PICO（提纲的语义锚点）：** 与用户确认研究问题 RQ/PICO（scoping review 用 PCC：Population/Concept/Context），写入 `outline.md` 的 `## Research Question` 区。RQ/PICO 明确后，探索性检索与后续提纲各节才有检验标准。（完整提纲结构在 Phase 1.7 据调研结果建立，此处只锚定研究问题。）

1. **初始化 index 并取证文献：** 先建空索引 `python3 scripts/state_manager.py init-index`（幂等，创建 `data/literature_index.json` + `data/synthesis_matrix.json`）。围绕 RQ/PICO 做一轮**探索性检索**（串行，≥1s 间隔，工具优先级同 Phase 2）。**探索阶段只写 `data/literature_index.json`（不依赖 Zotero 集合树——集合树在 Phase 1.7 建提纲后才创建）**，每篇跑 `citation_guard.py`——**gap 只能由 verified 文献推出**。本步入库可与 Phase 2 共享 index（不重复入库）。
   > ⚠️ 红线：gap 必须从真实文献证据推出，**禁止脑补**。每个 gap 关联 ≥1 篇支撑文献 `[n]`，且该 `[n]` 已 citation_guard verified。

2. **识别四类信号**，写入 `data/research_gap.json`：
   - `candidate_topics[]`：候选选题方向（每个含一句话 framing + 支撑 refs）
   - `hotspots`：近年高频/高被引主题（含 support_refs）
   - `controversies`：文献中的矛盾发现/未决争论（含对立双方 refs）
   - `gaps`：研究空白（每个含 `id` / `description` / `support_refs[]` / 为何是空白）
   - `novelty_risk`：候选选题与**既有综述/已发表工作**的重叠度比较，标 high/medium/low + 理由（防止"重复造轮子"）

   ```json
   {
     "candidate_topics": [{"topic": "...", "framing": "...", "support_refs": [3, 7]}],
     "hotspots": [{"theme": "...", "support_refs": [3, 12]}],
     "controversies": [{"issue": "...", "side_a_refs": [5], "side_b_refs": [9], "note": "..."}],
     "gaps": [{"id": "gap-1", "description": "...", "support_refs": [7, 12], "why_gap": "..."}],
     "novelty_risk": [{"topic": "...", "overlapping_reviews": [...], "risk": "low", "reason": "..."}]
   }
   ```

3. **DoD 自检（gate `research-gap-dod`，委托独立subagent盲检）：**
   ```bash
   python3 scripts/delegate_review.py pack --checklist references/dod_checklist.json \
     --gate research-gap-dod --files data/research_gap.json --workdir .
   # → 派独立subagent（Claude Code 用 academic-blind-reviewer），不给写作上下文，按任务包返回 JSON
   python3 scripts/delegate_review.py verify --checklist references/dod_checklist.json \
     --gate research-gap-dod --return .review_return_research-gap-dod.json
   # 退出码非 0 = fail-closed，据subagent证据修复后重跑，未过不得声明完成
   ```
   gate 5 项：G1 每 gap ≥1 verified 文献支撑 / G2 与 literature_index 一致（无孤儿）/ G3 从真实证据推出（禁脑补）/ G4 含 novelty_risk 比较 / G5 占位符清零。逐项内容以 `references/dod_checklist.json` 为唯一真源。

4. **更新 state + Git Checkpoint：**
   ```bash
   python3 scripts/state_manager.py set-phase --phase 1.5
   git add -A && git commit -m "[review] Phase 1.5: research gap identified" --allow-empty-message 2>/dev/null || true
   ```

**HALT. 向用户展示 candidate_topics / gaps / novelty_risk，等用户确认选题方向后再进 Phase 1.6。**

5. **🔴 选定主线落盘衔接（防长会话丢主线，HALT 确认后必做）：** 用户确认选题方向后，立即把"选定的综述主线（选题方向 + 核心 gap）"显式固化，作为 Phase 2/3 的主线依据，不靠隐式记忆：
   - 在 `research_gap.json` 被选中的 gap/candidate_topic 上加 `"selected": true` 标记；
   - 同时把"选定主线 = 选题方向 + 核心 gap 一句话"写入 `outline.md` 顶部的主线锚点区（无则在文件首行新增 `## 综述主线（锚点）` 区块）。
   - 落盘后再补一次 Git Checkpoint。

---

## Phase 1.6: Benchmark Review Library + Framing Guide（Write Mode only）

**触发时机：** Phase 1.5 选题确认后、**Phase 1.7 建提纲前**（对标框架既指导 Phase 1.7 的提纲结构，也在 Phase 3 搭正文框架时复用）。Polish Mode 跳过。
**Entry: Read `outline.md` + `state.json`. If `phase ≥ 1.7`（提纲已定）→ already done, skip.**
> **Phase gate:** `phase < 1.5` → HALT，提示先完成 Phase 1.5。

**目的：** 好综述的框架不是拍脑袋想出来的。找近年 5–10 篇**对标综述**（同领域顶刊 review），看它们怎么分章节、怎么讲道理、图和正文怎么配合、引言-主体-展望怎么组织，把这些可复用的套路提炼出来，Phase 3 搭正文框架时直接照着用。

### 步骤

1. **检索对标综述：** 工具优先级同 Phase 2（串行，≥1s）。目标 5–10 篇近年同领域高水平综述（Nature Reviews / Cell / Lancet 系等）。每篇**必须真实存在并走 citation_guard 验证**——禁编造。
   > ⚠️ 红线：对标综述真实存在、走 `citation_guard.py` 验证，不编造标题/期刊/年份。

2. **建对标库 `data/benchmark_reviews.json`：** 每篇含
   ```json
   [{
     "title": "...", "journal": "Nature Reviews ...", "year": 2023,
     "framework_outline": "该综述的章节框架（背景→机制→应用→挑战→展望 ... 具体到节）",
     "highlights": "亮点：如何 framing、如何仲裁矛盾、图怎么用",
     "verified": true
   }]
   ```

3. **提炼 `data/framing_guide.md`：** 从对标库归纳**可操作**的写作思路，至少覆盖：
   - 可复用的章节框架骨架（漏斗引言 → 主题主体 → 展望）
   - 论证思路（如何从 setup → evidence → synthesis → implication）
   - 图表与正文的关系（概念框架图放哪、每节图承担什么角色）
   - 引言-主体-展望的组织套路
   - 对**本综述**的具体建议（结合 Phase 1.5 的 gap，而非泛泛而谈）

4. **DoD 自检（gate `benchmark-reviews-dod`，委托独立subagent盲检）：**
   ```bash
   python3 scripts/delegate_review.py pack --checklist references/dod_checklist.json \
     --gate benchmark-reviews-dod --files data/benchmark_reviews.json data/framing_guide.md --workdir .
   python3 scripts/delegate_review.py verify --checklist references/dod_checklist.json \
     --gate benchmark-reviews-dod --return .review_return_benchmark-reviews-dod.json
   ```
   gate 4 项：B1 ≥5 篇 verified / B2 每篇含框架大纲 / B3 framing_guide 含可操作建议 / B4 占位符清零。真源见 `references/dod_checklist.json`。（framing_guide 是否真被用于搭框架，是 Phase 3 才发生的动作，不在此 Phase 1.6 gate 里核，改由 Phase 3 framing hook 强制落实、见 SKILL.md Phase 3 “Framing hook”。）

5. **更新 state + Git Checkpoint：**
   ```bash
   python3 scripts/state_manager.py set-phase --phase 1.6
   git add -A && git commit -m "[review] Phase 1.6: benchmark reviews + framing guide" --allow-empty-message 2>/dev/null || true
   ```

**HALT. 向用户展示对标库与 framing_guide 要点，确认后进 Phase 1.7（据调研建提纲）。**

> **🔗 Phase 1.7 + Phase 3 挂接（强制）：** Phase 1.7 建提纲结构、Phase 3 各节搭正文框架前，都必须 `Read data/framing_guide.md`，并使结构与其提炼的可复用框架对齐（由 Phase 3 “Framing hook” 强制落实）。这是 Phase 1.6 产出的落地点，不得跳过。

---

## Phase 1.7: Outline from Research + Structure Sign-off + Collection Tree

> **执行顺序：Phase 0 → 1.5（研究空白）→ 1.6（对标框架）→ 本阶段 1.7 → Phase 2。** 提纲是读透调研后的产物，所以先做完 1.5/1.6 才轮到这一步。**进入条件：`phase ≥ 1.6`（`data/research_gap.json` 已有 `selected` 主线 + `data/framing_guide.md` 就位）；若 `phase < 1.6` → HALT，回去先做 Phase 1.5 / 1.6。**

**Start: Read `outline.md` + `state.json` + `data/research_gap.json`（取 `selected` gap/选题方向）+ `data/framing_guide.md`（对标框架）+ `data/benchmark_reviews.json`. If state.json shows phase≥2, skip.**
**Polish Mode: if `state.json` contains `"mode": "polish"`, skip Phase 1.5/1.6/1.7 entirely and go to Phase 3.**

1. **据调研建提纲（不是凭空设计）：** RQ/PICO 已在 Phase 1.5 定义。以 **Phase 1.5 选定的 gap/主线** 为骨架、参照 **Phase 1.6 framing_guide 的可复用章节框架**，提出提纲结构："Funnel" Introduction + "Thematic" Body（≤2 层级）。每个主体节次应能对应到某个 gap / 争议 / 主线分支，避免与既有对标综述结构简单雷同（呼应 novelty_risk）。
   - Scoping review：研究问题用 PCC（Population / Concept / Context）。
2. **对齐对标框架：** 显式说明本提纲如何借鉴/区别于 framing_guide 提炼的结构（由 Phase 3 “Framing hook” 强制落实）。
3. **Confirm outline with user.** Update `outline.md`.

   > **⚠️ 迭代闸（Iteration Gate）：提纲在此可回修。**
   > Phase 2 检索完成后，若揭示出提纲遗漏了重大分支或主要争议（例如：某类方法在文献中被大量讨论但提纲无对应节次），允许回到此步修改提纲，并记录修改理由：
   > ```
   > [Outline revision after Phase 2 search]
   > Reason: Phase 2 revealed that X is a major branch in literature (~N papers) but
   >         was not covered in the original outline. Added Section X.X.
   > Impact: Related sections [list] may need additional citation targets.
   > ```
   > 修改后须更新 `outline.md`，重新确认 Zotero 集合树（`--init` 是幂等的），并用 Git Checkpoint 记录版本。**不得因回修提纲而删除已完成节次的已有文献入库记录。**

   > **[结构签字·强制门禁落锁]** 用户在对话里明确确认提纲后（且**仅在此之后**），运行 Phase 0.5 `init_project.py` 打印的那条 `SIGNOFF_CMD`（已含解析好的绝对路径与项目根）落盘签字——即 `python "<.../_shared/structure_signoff_gate.py>" confirm --root <项目根> --note "<用户确认原话摘录>"`。这一步解锁正文写作：**未落签字，PreToolUse hook 会物理拦截任何对 `drafts/*.md` 的写入**（这是防跳步的硬门，不是提示词纪律）。该 hook 由 Phase 0 `init_project.py` 开工时经 `_shared/install_gate_hook.py` 自动安装并校验（备份原 settings / 只追加不覆写 / 校验失败即回滚），init 回显 `门禁保护[active]` 即在岗生效；若回显 `[degraded]` 或 `[error]`（安装/校验未通过），hook 未在岗、物理拦截降级为提示词纪律，此时需人工留意别在未签字时写 `drafts/`。若后续回修提纲（上方迭代闸允许），改完让用户重新确认并重跑本命令覆盖签字。⚠️ 严禁在用户未确认时自行运行 confirm——那等于伪造用户签字。

4. **规划贯穿全文的概念框架图（提纲确认后，Phase 1.7 内完成）：**
   在 `figures/figure_index.md` 中注册一条 `Figure 0`（概念框架图），要求：
   - 覆盖全文逻辑主线（背景→机制/方法→应用/挑战→展望），体现各节之间的内在逻辑联系
   - 包含 Key Message（一句话）、草稿 Caption（出版级精确度）、节次映射关系
   - 写作时（Phase 3）各节需在文中引用该图，"如 Figure 1 所示"
   ```
   ## Figure 0: [Conceptual Framework — Title of Review]
   - Type: Conceptual overview
   - Section: ALL (全文贯穿)
   - Key Message: [one sentence summarizing the review's core argument/framework]
   - Caption: [draft — publication-ready, ≤150 words]
   - Node mapping: [e.g., "Section 1.1→Background box; Section 2.X→Mechanism module; Section 3.X→Application module"]
   ```

6. **Initialize Zotero collections (Zotero mode):**
   ```bash
   # First check if collection tree already exists (idempotent, safe on re-entry):
   ROOT_KEY=$(python3 scripts/zotero_manager.py --status --find-root-title "[TITLE]" \
     2>/dev/null) && echo "Root exists: $ROOT_KEY" \
     || python3 scripts/zotero_manager.py --init --title "[TITLE]" --outline outline.md
   ```
   - `--find-root-title` exit 0 → root already exists (stdout = key, reuse it); exit 3 → no match, the `||` branch runs `--init`; exit 4 → ambiguous (multiple same-named roots), stdout lists candidate keys. **Stop and ask user to pick** rather than letting `--init` create a duplicate.
   - Creates root collection + subcollections matching outline hierarchy.
7. **Initialize index files (None/EndNote mode):**
   ```bash
   python3 scripts/state_manager.py init-index
   # Creates empty data/literature_index.json + data/synthesis_matrix.json + figures/figure_index.md (idempotent).
   ```
8. **Update state.json** (writes phase=1.7 + zotero_root_key, preserving other keys):
   ```bash
   python3 scripts/state_manager.py set-phase --phase 1.7
   python3 scripts/state_manager.py set-root-key --key "[key from step 6]"   # Zotero mode only; skip in None/EndNote
   ```
9. **Git Checkpoint** (见复用块, msg: `[review] Phase 1.7: outline confirmed (post-research)`)

**HALT. Wait for user to confirm outline before Phase 2.**

---

## Phase 2: 系统主检索（Systematic Main Search）+ Real-Time Write

> （探索性检索已在 Phase 1.5 完成，本阶段是系统化主检索。）

**Start: Read `outline.md` + `state.json`. Skip sections already in `completed_sections`.**
> **主线依据（防丢主线）：** 开写前 Read `data/research_gap.json`，取 `selected` 的 gap/选题方向作为本轮检索与写作的综述主线，确保不偏离 Phase 1.5 选定的核心 gap。
> **Phase gate:** if `state.json` does not exist or `phase < 1.7`（提纲未据调研建立/未落结构签字）→ HALT; tell user "先完成 Phase 1.5（研究空白）→ 1.6（对标框架）→ 1.7（据调研建提纲 + 结构签字），系统主检索按提纲逐节进行"; do not proceed.

### Search Priority by Discipline

> Use the **Search Tool Priority (Universal)** table above (§ Search Tool Priority). Primary = PubMed CLI for Medical/Bio/Interdisciplinary, paper-search MCP for CS/AI; fallback is the other; `websearch`/`tavily` are forbidden in all disciplines.

### Per-Section Search Loop
```
for each section in outline.md (e.g., section ID = "2.1"):
  SECTION_FILE="tmp/papers_2_1.json"   # replace dots with underscores in section ID

  1. Check state.json → if section in completed_sections, SKIP
  2. Search ≥10 papers → collect metadata: title, authors, year, doi, abstract, source
     - Every paper must have abstract; if missing → re-fetch via efetch or paper-search
     - Still no abstract after retry → mark abstract:missing, skip for now
  2a. [可复现性] 记录检索日志：
      python3 scripts/state_manager.py append-search-log \
        --section X.X --query "QUERY" --database pubmed \
        --n-hits N_HITS --n-screened N_SCREENED
      # N_HITS = 搜索工具返回的原始命中数；N_SCREENED = 阅读标题/摘要后判断相关保留的数量
      # 检索日志写入 data/search_log.json（独立文件，不影响 literature_index.json）
  2b. [相关性筛选] 入库前逐篇判断（不得"搜到即入库"），保留条件：标题/摘要与本节 RQ/PICO（或 PCC）直接相关。排除标记（language / off_topic / quality / outdated）— 📖 详见 `references/scripts_reference.md` § Phase 2 入库前相关性筛选。最终保留的才进入 `tmp/papers_X_X.json`。
  3. Save metadata to tmp/papers_X_X.json  (e.g., section 1.1 → tmp/papers_1_1.json)
  4. Write papers (run ONLY the branch matching the project's Reference Manager; they are alternatives, not sequential):
     [Zotero] python3 scripts/zotero_manager.py --add-batch \
       --section "X.X" --papers tmp/papers_X_X.json \
       --root-key ROOT_KEY --index data/literature_index.json
       # ROOT_KEY from state.json; --add-batch deduplicates at write time + auto-writes literature_index.json.

     [None/EndNote] python3 scripts/state_manager.py append-literature \
       --section X.X --papers tmp/papers_X_X.json --index data/literature_index.json \
       --source-provider SP
       # SP: pubmed-cli (default) or paper-search. openalex/tavily/websearch FORBIDDEN (citation_guard blocks).
       # CNKI/Wanfang refs go via manual RIS import — 📖 references/citation_styles.md § CNKI/万方。

     Required fields per entry: `global_id` (int), `title`, `authors`, `year`, `doi` or `pmid`, `abstract`, `related_sections` (array, e.g. `["1.1"]`).
     > ⚠️ Use `related_sections` (array), NOT `section` (string). One paper can belong to multiple sections simultaneously — 📖 详见 `references/scripts_reference.md` § Related-Sections 字段规则。
  5. [None/EndNote] Bootstrap synthesis matrix entry for this section (auto-skips if row exists):
      ```bash
      python3 scripts/matrix_manager.py bootstrap \
        --index data/literature_index.json \
        --matrix data/synthesis_matrix.json \
        --section X.X --round 1
      ```
  6. Run anti-hallucination guard (all modes):
       python3 scripts/citation_guard.py \
         --index data/literature_index.json \
         --log data/citation_guard_report.json \
         --write-back
     If guard exits non-zero → do NOT continue to next section; fix flagged entries first.
     `--write-back` 把每条的 verified 与 per-entry checked_at 落盘到 literature_index.json，下一节复用已验条目、跳过重复联网核验（L1 短路，TTL 30 天）。verified 由脚本写、不靠 AI 记。
  7. Confirm write success → update state.json (add section to completed_sections):
     python3 scripts/state_manager.py complete-section --section X.X
     # Adds X.X to completed_sections (idempotent), preserves all other keys.
  8. Git Checkpoint (见复用块, msg: [review] Phase 2: section X.X search complete)
  9. Continue to next section
```

**Global target:** ≥100 papers total (before dedup). If a section yields <10 papers, warn and prompt user to broaden keywords.

**Chinese writing mode:** Search tools identical to English mode. Read language setting from outline.md.

### Phase 2.5: Dedup + Global ID Assignment

**⚠️ HALT before dedup.** Show user: total papers found, estimated duplicates, sections covered.
Wait for explicit "Continue".

```
[Zotero] ⚠️ --add-batch already deduplicates at write time (DOI exact + title fuzzy ≥0.85).
         Normal workflow does NOT need --dedup here — SKIP this step.
         📖 `--dedup` is repair-only and has a gid-resync caveat — see `references/edge_cases.md`
            ("Zotero --dedup gid 失同步") before ever running it.

[None/EndNote]   python3 scripts/state_manager.py reindex \
           --storyline outline.md --index data/literature_index.json \
           --matrix data/synthesis_matrix.json
```

Dedup rules (None/EndNote mode reindex):
1. Primary key: DOI exact match
2. Fallback: normalized title (lowercase + strip punctuation) → SequenceMatcher ≥0.85
3. On duplicate: keep canonical entry, merge related_sections
4. `global_id` reassigned in canonical section outline order (1.1 → 1.2 → 2.1 → ...)

**Update `state.json`（仅更新 phase 字段，不覆盖 completed_sections / zotero_root_key）：**
```bash
python3 scripts/state_manager.py set-phase --phase 2
# Sets phase=2 only; completed_sections / zotero_root_key / mode / pending_sections preserved.
```

**Git Checkpoint** (见复用块, msg: `[review] Phase 2.5: dedup + global ID assigned`)

---

## Phase 3: Section-by-Section Writing

**Entry: Read `outline.md` + `state.json` first. 并 Read `data/research_gap.json` 取 `selected` 的 gap/选题方向作为综述主线依据，开写各节须围绕该核心 gap，不偏离 Phase 1.5 选定的主线。If `state.json` phase < 3 (Write Mode), update to phase=3:**
```bash
# Only run if current phase < 3 (read state.json first; Polish Mode already enters at phase=3).
# Do NOT regress a phase=4 project back to 3.
python3 scripts/state_manager.py set-phase --phase 3
```
**Skip completed sections (check `completed_sections` list).**

> **🔗 Framing hook (Write Mode, MANDATORY before building any section's framework):** `Read data/framing_guide.md` (produced in Phase 1.6) and use its reusable章节框架/论证思路 as the basis for each section's structure — do NOT fall back to a generic default template. (Polish Mode: file may not exist — skip if absent.) This IS where framing-guide alignment is actually enforced; the Phase 1.6 benchmark gate no longer checks this Phase 3 action, and the resulting structure is reviewed downstream by manuscript-dod (R15/R16/R18).

**Polish Mode branch (if `state.json` contains `"mode": "polish"`):**
```
Before starting any section, read state.json → pending_sections:
  missing → no draft exists: run systematic main search (same as Phase 2 per-section loop Steps 2-6) INLINE here, then proceed to step 1 below. Do NOT navigate back to Phase 2; all search+write happens within this Phase 3 section loop.
  rewrite → existing draft exists in drafts/section_XX_XX.md: read it as context, then fully rewrite
  polish  → existing draft exists in drafts/section_XX_XX.md: read it; fix ONLY AI-flags + thin citations;
            keep structure and arguments intact; do NOT overwrite with fresh draft
  keep    → skip entirely (already in completed_sections)

If pending_sections is empty → all sections complete; proceed to Phase 4.
```

### Per-Section Cycle

0. **🔴 开写前置闸门 (Mandatory，脚本硬拦截)**：开写本 section 前必须先跑 `python3 scripts/prewrite_gate.py --section X.X --root .`，exit≠0 禁止开写。它统一硬检查：上一节完成（上一节 ∈ `state.json.completed_sections`）、大纲就位（`outline.md` 含本节标题）、素材就位（`data/synthesis_matrix.json` 本节文献矩阵非空）、上一节占位符清零（`drafts/` 无 `CITE_PENDING`/`DATA_PENDING`/`【待`）；上一节盲检结果（`.review_pass/<上一节>.json`）缺失即 prewrite_gate 硬拦 exit 1，禁止开写；必须先跑 delegate_review verify --section <上一节> 落盘通过标记。**盲检subagent确实跑不起来时**，用 `--allow-manual-review "<理由>"` 显式人工放行（仅放行盲检项、留痕审计，见规则 10 的逃生口）；不加则门禁默认硬拦行为不变。PASS 时脚本会注明"仅覆盖形式层，语义正确性未自动核验"。Polish Mode `keep` 节跳过本节循环故无需跑。

1. **Load context:**
   ```
   [Zotero] python3 scripts/zotero_manager.py --get-section "X.X" \
              --root-key ROOT_KEY
   [None/EndNote]   python3 scripts/matrix_manager.py focus --section X.X
            # Shows papers + existing claim bindings for this section from synthesis_matrix.json
            # Also read data/literature_index.json filtered by related_sections containing X.X
   [Polish Mode] Also read existing drafts/section_XX_XX.md (rewrite: as reference; polish: as base to edit)
   ```

2. **Round 2 search** (targeted, ≥5 additional papers for specific claims):
   - **Write Mode:** triggered when Phase 2 found <10 papers for this section, or the writer identifies specific claims that lack supporting evidence during Step 4 drafting
   - **Polish Mode `rewrite`:** RECOMMENDED. Run targeted search if diagnosis flagged citations/500w < 2.
   - **Polish Mode `polish`:** only if Phase 0-P Step 3 diagnosis flagged citations/500w < 2
   - **`keep` sections:** skip
   - If user explicitly requests Round 2 for any section → execute regardless of above criteria
   - Add new papers same way as Phase 2 (batch add + dedup).

3. **Figure (MANDATORY): read then write.**
   a. **Read** `figures/figure_index.md` → find existing entries where `Section: [SectionID]`. If an entry exists, load its Caption and Key Message as writing context for Step 4.
   b. **Write** (append) new figure definition if not yet defined for this section:
   ```
   ## Figure N: [Title]
   - Type: Schematic | Conceptual overview | Workflow | Mechanistic pathway
   - Section: [SectionID]
   - Key Message: [one sentence]
   - Caption: [draft caption — precise, publication-ready]
   ```
   > `figures/figure_index.md` is the canonical figure registry for ALL modes (Write, Polish, None). It is NOT inside `drafts/`.

3.5. **🧭 引文核证脚手架（帮你写对的辅助，不是卡后续的墙）：** 落笔前，为本节**承重论点**（load-bearing：机制断言、疗效/因果结论、关键定量声明等支撑全节论证的句子）逐条把"论点 ↔ 它要引的文献"对齐，用文献**检索时原样落盘的真实 abstract**（`data/synthesis_matrix.json` 已含 claim↔文献的绑定，abstract 取自 `data/literature_index.json` 的 `abstract` 字段，**不是可事后编的 key_finding**）判断该引用是否真支撑这句话，写入项目根 `claim_evidence.json`（list，每条：`{section, claim_sentence, is_load_bearing, ref_id, retrieved_abstract, verdict∈support/weak/contradict/unknown, evidence_quote, user_confirmed}`）。背景陈述句列入即可（`is_load_bearing:false`），批量过目、不逐条阻断。
   > **跨节复用（脚本自动读写 `ref_evidence_cache.json`，AI 不必手记字段）：** 已在别节验过的文献，本节该行的 `retrieved_abstract` 可留空，脚本按 `ref_id` 从项目根 `ref_evidence_cache.json` 自动回填真实 abstract；完全同一 `(ref_id, 论点句)` 且此前已 `user_confirmed` 的承重句，脚本自动复用其 verdict 与确认，不再反向验证、不再 AskUserQuestion。只有**新的 (文献, 论点) 组合**才需重新判支撑并逐条确认。核证后脚本强制把已验 abstract 与已确认承重 verdict 落盘，已验状态由脚本维护。此复用**不放松门禁**：缺 abstract、承重句 contradict/unknown、未 `user_confirmed`，仍 fail-closed（见下 exit 2）。
   然后跑 Phase 0.5 打印的 `CITATION_CHECK_CMD`（绝对路径指向 `_shared/citation_claim_check.py --root <项目根>`；读项目根 `claim_evidence.json`，渲染 claim↔引用支撑矩阵表）：
   - **承重句** `contradict` / `unknown` / 缺 `retrieved_abstract` / 未 `user_confirmed` → 脚本 fail-closed（exit 2）。对每个被拦的承重句，用 **AskUserQuestion 逐条**呈现（论点 + 拟引文献 + abstract 摘录 + 机器判定），让用户裁决：换引文 / 改写论点 / 确认支撑（确认后在该条置 `user_confirmed:true` 重跑）。
   - **背景句** 的 weak/contradict 只在矩阵表里标红提示，**批量**过目即可，不逐条打断。
   - **定位**：这是帮你把引用挂对的脚手架——带着"引用确实支撑论点"的把握再落笔。通过后进 Step 4。（复用已建的 synthesis_matrix，不重复建库。）

4. **Draft:** Write to `drafts/section_XX_XX.md` (zero-pad each part to 2 digits, e.g., section 1.1 → `drafts/section_01_01.md`, section 2.10 → `drafts/section_02_10.md`). Paragraphs only. Citation format `[N]` (N = gid).
   - **Reference the figure caption from Step 3a.** The draft must describe and introduce the figure using its planned caption and key message.
   - Apply Anti-AI Writing rules (English or Chinese mode per outline.md).
   - 行内格式遵守 `references/writing_guidelines.md` 的字符级排版契约（物种/基因/统计符号/拉丁缩写斜体 `*...*`；上下标 `^...^`/`~...~`，禁裸 H2O/CO2；半角全角规则）。
   - Synthesis not summary; arbitration of contradictions; alternate claim/evidence order.
   - **Abbreviation rule:** First occurrence of any abbreviation in this section must use "Full Name (ABBR)" format. If the abbreviation was already defined in a previous section, use ABBR directly. `exports/abbreviation_list.md` does not exist yet (it is generated in Phase 4 Step 4c); to check prior definitions, grep the already-written `drafts/section_*.md` files for the `Full Name (ABBR)` pattern.

5. **Citation spot-check** (lightweight, runs per-section; catches hallucinated `[N]` before 逐节质量自检):
   ```bash
   # Scans all drafts/ but only this section's file matters (previous sections already passed).
   # --fail-on-orphan exits non-zero if any [N] in draft has no match in literature_index.json.
   python3 scripts/validate_citations.py --drafts-dir drafts --index-path data/literature_index.json --fail-on-orphan
   ```
   - Checks every `[N]` in drafts exists in `literature_index.json` (or Zotero gid pool).
   - If any `[N]` is orphan (not in index) → fix immediately: either find the real gid or remove the citation.
   - Does NOT do online DOI/PMID verification here (that's Phase 4 `citation_guard.py`'s job).
   - [Zotero mode] Also cross-check against `--get-section` output: every gid used in draft should appear in the section's Zotero collection.

6. **逐节质量自查（主 agent 轻量自查，为 Step 10 盲检兜底——不在此派独立盲检）：** 落笔后先由主 agent 自查一遍，尽早改掉明显问题、减少 Step 10 往返。**独立盲检不在这里做**：原每节两次委派（Step 6 评 D1-D5 + Step 10 跑 manuscript-dod）评分轴高度重叠，已合并为 Step 10 的**单次** manuscript-dod 盲检（D1 新颖并入 R23、D2 仲裁→R8、D3 证据→R7+R9、D4 连贯→R18、D5 去 AI→R5 已等价覆盖）。故本步只自查、不落盘、不阻断、不派 subagent；真正的独立盲检 + fail-closed 门禁 + 修复循环全在 Step 10。
   **🔴 硬约束：这是本技能内部的轻量质量 checklist，不是 reviewer-simulator 技能。禁止调用或进入 reviewer-simulator 技能，禁止逐节生成任何 HTML 审稿报告（report_*.html 或其他报告文件）。**
   **量化兜底（先跑脚本再自读）：** 先跑 style_checker 拿客观信号，**high/medium 项必须先改掉；破折号命中即 hard_fail 一票否决，必须清零**；`info` 软项（long_sentence / excessive_passive_voice）只提醒不阻断、不扣分，择优处理。
   ```bash
   python3 scripts/style_checker.py --file drafts/section_01_01.md --passive-max 0.30
   # 硬项(计分/hard_fail,可致 exit 1)：forbidden_ai_phrases / scare_quotes / explanatory_colon_in_prose / trailing_ing_clause / bullet_points / decorative_em_dash(破折号,hard_fail一票否决) ...
   # 软项(severity=info,只报告不扣分不阻断)：long_sentence(>30词) / excessive_passive_voice(>30%)
   # exit 0 = 通过(score≥阈值)；非 0 = 据 issues 里的 high/medium 项修复后重跑（info 项不影响退出码）
   ```
   然后主 agent 自读本节，对照 `references/reviewer_checklist.md` 的 D1-D5（新颖 / 仲裁 / 证据 / 连贯 / 去 AI）过一遍，把一眼能看出的问题就地改掉。这只是自查，是否通过不决定能否进下一步——门禁在 Step 10。

7. **Word count check:**
   ```bash
   python3 scripts/word_counter.py --file drafts/section_01_01.md --language en   # or --language cn for Chinese; read from outline.md
   ```
   Key sections target: >500 words (EN) / >1,500 chars (CN); Supporting: >200 words / >600 chars.
   **If user explicitly requested a shorter length** (e.g., "~800 characters"): defer to user's request; treat the skill's minimums as guidance for quality, not a hard gate. Do not loop-prompt the user to write more if they have already confirmed their target length.

8. **Update state.json (MANDATORY, do not skip):**
   ```bash
   python3 scripts/state_manager.py complete-section --section X.X
   # Adds X.X to completed_sections AND removes it from any pending_sections bucket (Polish Mode),
   # preserving all other keys. Idempotent.
   ```
   A section must never appear in both `completed_sections` and `pending_sections` simultaneously (the command guarantees this).

9. **Git Checkpoint** (见复用块, msg: `[review] Phase 3: section X.X draft complete`)

10. **DoD 自检清单（硬规则）：逐项确认通过后才可声明本节完成，不得跳过任何一项。**

    **🔴 进入下一节前置闸口：上一节 delegate_review verify 必须 exit 0（含 R15 结构完整性），否则不得开始下一节撰写。写完即检，不过不进。**

    **🔴 委托盲检（不得主 agent 自评）**：你刚写完本节，自评会失真地默认通过、且易漏项。落盘前必须把 DoD 清单**委托给独立上下文的subagent盲检**，自己不直接打勾：
    1. 生成任务包：`python3 scripts/delegate_review.py pack --checklist references/dod_checklist.json --gate manuscript-dod --files <本节文件> --workdir .`（会在 stderr 打印 `RETURN_PATH=...`，即subagent返回要写入的约定路径）
    2. **派一个独立subagent**（不给它本节写作上下文），把任务包原样贴给它，要求把 JSON 数组写到 `RETURN_PATH`。**可直接复制执行的派发指令**：
       - Claude Code：用 `Task` 工具，`subagent_type="academic-blind-reviewer"`（无此 agent 时退回 `general-purpose`），prompt = pack 打印出的整段任务包原文（含"你的角色/待检文件/检查清单/返回格式/返回写到这个文件"），**不附加任何本节写作说明**。
       - 其他平台（Codex/OpenCode 等无此 agent）：新开一个干净上下文的subagent/子会话，同样只贴任务包原文。
    3. 校验返回：`python3 scripts/delegate_review.py verify --checklist references/dod_checklist.json --gate manuscript-dod --return <subagent返回.json> --section <当前section_id> --root <项目根>`；退出码非 0（任一缺项 / fail / 无证据）= **fail-closed**。**修复循环（原 Step 6 的修复委派并入此处）：** 任一项失败即派一个**修复子代理**（输入 = 盲检返回的结构化意见 + 本节 `drafts/section_XX_XX.md`，不给写作上下文）做针对性修改，改完重跑 `pack → verify` 复评；修满 2 轮仍失败 → **HALT**，输出结构化反馈（【问题】+ 证据锚点 + 根源分析 + 修复方向）交用户裁决。是否修订 / 是否 HALT 的决策由主会话把关，不可委托。**未过不得声明完成。** verify 通过会落盘 `.review_pass/<当前section_id>.json`，下一节 `prewrite_gate.py` 会**硬校验**它（缺失即拒绝开写）。
       > **诚实边界：** verify 的 `ok:true` 只代表清单每项都被裁决且形式合规——**PASS 仅覆盖形式层，语义正确性由盲检subagent主观判断、未自动核验**。
       > **【P4·盲检降级告警】** ⚠️ 若环境派不出真正独立的subagent（非 Claude Code、无 `academic-blind-reviewer`），**绝不能同一 AI 自问自答冒充盲检**。告诉用户「本环境盲检不可靠，请你亲自复核本节」，别让自证闭环静默跑。
    4. **🚪 逃生口（盲检subagent确实跑不起来时，且仅此时）**：若平台无 `academic-blind-reviewer`、通用subagent也反复失败/取不到返回，导致 `verify` 无法落盘标记、下一节被 `prewrite_gate` 永久锁死——**不要卡死或静默跳过**。改为人工逐项盲检本节 DoD 后，用显式放行开锁并留痕：
       ```bash
       python3 scripts/prewrite_gate.py --section <下一节id> --root . \
         --allow-manual-review "谁放行 + 为何盲检subagent不可用 + 已人工核过哪些项"
       ```
       它只放行"上一节盲检"这一项（其余硬检查照常），并写 `.review_pass/<上一节>.json`(manual:true) + 追加 `.review_pass/MANUAL_REVIEW_AUDIT.log`；理由为空则拒绝放行。此后每次 `prewrite_gate` 都会在 warnings 里点名"人工放行、语义未经独立盲检"。**门禁默认行为不变**：不加此参数时，缺盲检标记照旧硬拦。

    `manuscript-dod` gate 共 **23 项（21 硬门禁 + R20/R22 两软报告）**，覆盖：通用（引文一一对应 / citation_guard / 符合 storyline / 占位清零 / 去 AI / 字数）、review 特有（综合非罗列 / 矛盾仲裁 / 引用类型匹配 / 检索日志 / 框架图一致）、systematic 额外（PRISMA 自洽 / RoB / GRADE）、结构完整性、**覆盖全面性 / 关键文献遗漏与引用偏倚 / 论证 arc 连贯 / 学术合规披露（R16-R19 盲检质量核）/ 新颖性与贡献（R23 盲检质量核）**、字符级机器门禁（R21）。**本次盲检已一并承接原 Step 6 逐节自检的 D1-D5 轴：D1 新颖→R23、D2 仲裁→R8、D3 证据→R7+R9、D4 连贯→R18、D5 去 AI→R5，故每节只在此做一次独立盲检，不再于 Step 6 重复委派。** **逐项内容 / severity / 核验命令以 `references/dod_checklist.json` 为唯一真源**——上面 `pack` 步骤运行时会把该 gate 的每个 item（id / name / check / script）完整打印进盲检任务包，此处不逐条枚举以免与 JSON 漂移。systematic 3 项仅 Review type = systematic 时检查，其余全类型通用。

    - **R21 语法拼写与字符级格式(🔴机器硬门禁,可阻断)**,跑 `python3 scripts/proofread.py --manuscript-dir drafts --report proofread_report.json --fail-on misspelling,chinese_punct,subsup_bare`。stdlib-only、自包含。高置信三类**零容忍**——misspelling(英文常见错拼)、chinese_punct(中文标点漏入英文)、subsup_bare(应上下标却裸写,如 H2O/CO2/IC50,CJK 安全边界),命中任一即 `ok=false`(脚本 exit 1),据 `proofread_report.json` 的 `fail_on_hits` 定位修复后重跑。其余类别(英美拼写混用、单位格式、术语写法不一致、数字千分位、Methods 时态、学术错拼/中文错别字等)仅在报告里提示、不阻断,由作者择一统一。与 R5 去AI(style_checker)互补:R5 管文风,R21 管字符级机器错。

    附带软报告项（不计入硬门禁退出码，由盲检subagent LLM 判断）：

    - **R20 常识合理性(🟡软报告,不阻断)**,盲检subagent顺带扫正文是否有明显常识/事实硬伤(单位量级离谱、生理/机制常识错误、跨文献综合时的事实拼接错误、前后数值逻辑矛盾等)。**仅提示不阻断**,只在发现明显硬伤时记入盲检反馈供用户裁决,绝不自动改内容。与引用/文献核验门禁区分:本项管"综述论述的内容常识上是否成立"。

    - **R22 拉丁短语斜体软提醒(🟡软/人工确认,不阻断)**,`proofread.py` 的 `latin_italic_missing` 类别:正文里 `in vitro`/`in vivo`/`ex vivo`/`in situ`/`de novo`/`post hoc`/`per se` 等公认须斜体的拉丁短语若裸写(未被 `*...*` 斜体标记包裹)则报告。**仅提示,不阻断、不进 `--fail-on`、不扣分**,由人工确认是否补斜体(`et al.`/`e.g.`/`vs.` 等正体惯例不在词表内)。

11. **📋 DoD 结论摆出 + HALT（展示式，不新增硬墙）：** 本节 `delegate_review verify` 盲检通过（exit 0 且 `.review_pass/<section>.json` 已落盘）后，先把**逐项 DoD 结论**摆给用户——从subagent返回的 JSON 里**逐条列出每个 `manuscript-dod` item**（id/name + verdict + 证据锚点摘录，以返回 JSON 的实际条目为准、不手点项号，含 systematic 3 项、结构完整性、R16-R19 覆盖全面性/引用偏倚/论证连贯/合规披露、R23 新颖性与贡献、字符级 R21；R5 里降软的长句/被动如命中只作 info 提示、不影响通过；破折号为硬门禁 hard_fail、命中即不通过）。再附本节 summary（content / logic / citation count / word count）。**然后 HALT 等用户确认，才写下一节。** 这是"展示 + 可继续"：盲检已过即可放行，此处只保证用户看到每项结论、有机会叫停，不新增硬门。Wait for "Continue".

### Figure Prompt Generation

**Trigger:** Run ONCE after ALL sections in Phase 3 are complete (all sections in `completed_sections`).
Generate prompts for every entry in `figures/figure_index.md`. Write output to `figures/figure_prompts.md`.

> 📖 Use the figure-prompt template in `references/writing_guidelines.md` §5 (TYPE / SUBJECT / STYLE / COLOR SCHEME / ELEMENTS / LAYOUT / TYPOGRAPHY / KEY MESSAGE / AVOID).

**配图（opt-in，默认关）：** 默认不生成配图；仅当用户明确要求「生成配图 / 画图代码」（生信/统计图）时启用 → 调用本地 matplotlib / seaborn skill 生成**可运行代码（非图片）**，遵循：按数据选图型（bar / box / line / scatter+回归 / forest / funnel（meta 用）/ volcano · MA（差异表达用）/ heatmap / network / concept map）、APA caption、色盲安全配色（viridis / cividis）、300 DPI、轴标签带单位、禁 3D / 饼图。systematic 模式下可据此生成 PRISMA 流程图 / RoB 红绿灯图 / forest / funnel 代码。

---

## Phase 4: Export & Finalization

**Start: Read `outline.md` + `state.json`. If state.json shows phase=4 and completed=true, skip.**

**⚠️ MANDATORY entry gate: block Phase 4 when pending sections remain (Polish Mode):**
```bash
python3 scripts/state_manager.py check-pending
```
Write Mode has no `pending_sections` field so this gate is a no-op (no key → empty dict → pass).

> **⚠️ HALT before Round 3 sweep.** Show user:
> - Sections to search: [list from outline.md]
> - Estimated: ~5–10 new preprints per section
>
> Ask: "Proceed with Round 3 preprint sweep? (yes / skip)"
> **Do not proceed until explicit user answer.** If "skip" → record `"round3_papers": 0` in state.json and jump to Step 2.

1. **Round 3 search:** Scan arXiv/preprints (last 6 months) for each section topic → add to relevant sections.
2. **Citation consistency + online validation:**

   **Polish Mode guard** (skip Steps 2a–2b when EITHER condition below holds; on hit, append `Citations not validated — manual review required.` to outline.md Current Status):
   ```bash
   # Empty index — no citations to validate
   python3 -c "import json,pathlib; p=pathlib.Path('data/literature_index.json'); exit(0 if (not p.exists() or len(json.loads(p.read_text(encoding='utf-8') or '[]'))==0) else 1)" && echo "GUARD: empty index → skip 2a-2b"
   # OR state.json marks citations as not imported
   python3 -c "import json,pathlib; s=json.loads(pathlib.Path('state.json').read_text(encoding='utf-8')); exit(0 if s.get('citations_imported') is False else 1)" && echo "GUARD: citations_imported=false → skip 2a-2b"
   ```
   **引用总量校验（警告性，不阻断；尊重用户自定的短篇长度）:**
   ```bash
   python3 scripts/state_manager.py count-citations --drafts-dir drafts --threshold 150
   ```
   > **类型分布（人工核对）：** literature_index.json 未记录 Original/Review/Preprint 类型字段，无法机器统计。AI 对照 Constraints §2 的**软目标**（按学科浮动、类型配比按论点性质、预印本按需）人工抽查 index，明显失衡时提示用户；不按固定配额卡数。

   ```bash
   python3 scripts/check_global_citation_sequence.py
   python3 scripts/validate_citations.py --live --live-used-only --fail-on-orphan --retries 2
   # Final citation guard pass: write verification results back to index
   python3 scripts/citation_guard.py \
     --index data/literature_index.json \
     --log data/citation_guard_report.json \
     --write-back \
     --manual-review data/manual_review_queue.json
   ```
   If non-zero exit → list all gaps; block compilation until resolved.
   `--write-back`: persists `verified:true/false` fields into literature_index.json for traceability.
   `--manual-review`: writes unverifiable entries to `data/manual_review_queue.json` for human check; does NOT block compilation unless `--require-mcp` is also set.

   > **【P4·文献抽验·用户必做】** 综述的命是引文。文献进正文前用户应抽 2-3 篇让 AI 报 PMID/DOI 自己去 PubMed 核对。⚠️ 你在 Windows 上 edirect 联网核验常跑不起来（本 SKILL 已注明 edirect 在 PowerShell/CMD 不可用）——**一旦不能真的联网查，AI 必须停下告诉用户，绝不许硬着头皮编 DOI/年份**。`validate_citations.py --live` 跑不起来时明说「联网核验不可用」，不许自判通过。
3. **Export bibliography:**
   ```
   [Zotero] python3 scripts/zotero_manager.py --export-bibtex \
              --output exports/references.bib --root-key ROOT_KEY
   [None/EndNote]   python3 scripts/export_bibtex.py \
              --input data/literature_index.json \
              --output exports/references.bib \
              --clean
   ```
4. **Compile:** Merge all section drafts in correct order:
   ```bash
   # Zero-padded filenames (section_01_01.md, section_01_02.md, ...) sort correctly with glob
   cat drafts/section_*.md > exports/Final_Review.md
   # Verify: ls drafts/section_*.md should list files in outline order
   # If any file uses non-padded name, rename first:
   #   mv drafts/section_1_1.md drafts/section_01_01.md
   ```
   > **导出范围注记：** Markdown（`exports/Final_Review.md`）是中间产物；最终 docx 由本技能 Step 5d 的 `scripts/export_docx.py` 产出。字符级排版契约里的上下标 `^...^`/`~...~` 通过 pandoc 的 `+superscript+subscript` 扩展转换，正文/标题字体（Times New Roman、标题加粗）由 `templates/reference.docx` 锁定（该模板由 `scripts/make_reference_docx.py` 烘焙）。
   4a. **Consolidate references into ONE global list** (run immediately after the `cat` merge):
   ```bash
   python3 scripts/consolidate_references.py \
     --md exports/Final_Review.md \
     --index data/literature_index.json
   ```
   > 写作阶段（Phase 3 规则 7）每节自带 `## References` 是**自包含核验用**——保证每节引用都能当场对账。`cat` 拼接会把这些每节列表全部塞进最终稿，导致 docx 出现多个参考表。本步把正文里散落的所有每节 `## References` 块**剥掉**，按全局编号 `[n]` 升序在**文末重建唯一一个** `## References`（Vancouver 条目来自 `literature_index.json`）。脚本幂等；若某 `[n]` 在 index 查不到，stderr 警告但不阻断导出（退出码仍 0），按需补 index 后重跑。
   4b. **Cross-section coherence scan** (on compiled `exports/Final_Review.md`):
   Read the full compiled text sequentially and check:
   - **Transition continuity:** The opening of each section/subsection must logically connect to the closing of the previous one. Flag abrupt topic jumps with no bridging sentence.
   - **Cross-references:** If Section 3.2 discusses a mechanism introduced in Section 2.1, it should contain an explicit reference ("as discussed in Section 2.1" or equivalent). Flag implicit back-references that assume the reader remembers without a pointer.
   - **Argument arc:** The review's overall narrative should follow the outline's intended logic (e.g., "background → mechanisms → applications → challenges → future"). Flag sections that repeat points already made elsewhere or contradict earlier conclusions without acknowledging the contradiction.
   - **Introduction funnel check:** Introduction must narrow from broad field → specific gap → this review's contribution. Flag introductions that jump directly to specifics without establishing context.
   - **Conclusion echo check:** Conclusion must directly address the Research Question(s) from `outline.md` and reference key findings from body sections. Flag conclusions that introduce new claims not supported in the body.
   - If violations found → AI fixes inline in `exports/Final_Review.md`, adds transition sentences or cross-references, and propagates changes back to source `drafts/section_XX_XX.md`.

   4c. **Abbreviation consistency scan** (on compiled `exports/Final_Review.md`):
   - Scan for all uppercase sequences ≥2 chars (candidate abbreviations) and parenthetical definitions like `Full Name (ABBR)` or `中文全称（英文全称, ABBR）`.
   - **Check:** Every abbreviation used bare (without parenthetical definition) in the text must have exactly ONE prior definition. Flag: (a) undefined abbreviations, (b) abbreviations re-defined in multiple sections, (c) abbreviations defined but never used again.
   - Generate `exports/abbreviation_list.md` table (see format in `references/writing_guidelines.md` §4 Abbreviation Management).
   - Title and abstract must not contain unexpanded abbreviations (except universally known: DNA, RNA, PCR, HIV, WHO, FDA).
   - If violations found → list them; AI fixes inline in `exports/Final_Review.md` and propagates back to the source `drafts/section_XX_XX.md`.
5. **Final word count:** Verify total ≥ target in `outline.md`.

5b. **结构化"未来方向/开放问题"段（强制，Phase 4 交付前）：**
   若结论节不含独立 Future Directions 段，在此强制补写并插入 `exports/Final_Review.md` + 反向同步到最后一节 `drafts/section_XX_XX.md`。
   规则：≥3 条具体可操作方向，每条含 gap 原因 + 突破路径，不引入正文未建立的概念。
   📖 格式模板详见 `references/writing_guidelines.md` §6。

5c. **元数据块（导出前补全）：** 在 `exports/Final_Review.md` 末尾追加 Manuscript Metadata 块（search cutoff / databases / COI / funding）。
   📖 字段模板详见 `references/writing_guidelines.md` §7。

5d. **导出 docx（最终交付物）：** 所有 md 修复（4b/4c/5/5b/5c）完成后，将 `exports/Final_Review.md` 编译为 `exports/Final_Review.docx`：
   ```bash
   python3 scripts/export_docx.py --md exports/Final_Review.md --out exports/Final_Review.docx
   # 若使用 BibTeX/CSL 渲染参考文献，追加：--bib exports/references.bib [--csl style.csl]
   ```
   样式由 `templates/reference.docx` 锁定（正文 Times New Roman 12pt、标题 TNR 加粗），上下标 `^...^`/`~...~` 经 pandoc `+superscript+subscript` 转为真实上下标。pandoc 缺失时脚本会报清晰错误并退出。

6. **Update state.json (merge, do NOT overwrite):**
   ```bash
   python3 scripts/state_manager.py set-phase --phase 4 --completed true
   ```
   Only `phase` and `completed` are mutated; `completed_sections`, `mode`, `pending_sections`, `zotero_root_key`, `citations_imported` are preserved untouched.
7. **Git Checkpoint** (见复用块, msg: `[review] Phase 4: export finalized`)
8. **Update outline.md** current status section (human-readable summary).

**进入 Phase 5（投稿包）。** Phase 4 导出完成后不直接结束，继续生成投稿材料。

---

## Phase 5: Submission Pack

**触发时机：** Phase 4 导出完成后（`phase=4, completed=true`）。Write 与 Polish 两模式都执行。
**Entry: Read `outline.md` + `state.json`. If `phase=5, completed=true` → already done, skip.**
> **Phase gate:** `phase < 4` 或 Phase 4 未 completed → HALT，提示先完成 Phase 4 导出。

**📖 进入本阶段必读：**
1. `references/submission_checklist.md`（综述版投稿清单 + 强制/询问分级 + 红线 + 产出路径）
2. general-sci-writing 的 `references/submission-guide.md` 与 `references/compliance-gate.md` 的逐项标准——**只读，不改 gsw**。读取以对齐 Cover Letter 询问明细、CRediT 11 类分配、Acknowledgements 类别、合规门禁判定。
3. `references/presubmission_checklist.md`（投稿前作者自检清单，**soft 提醒不阻断**）：终稿交付前对照逐项自查，重点是机器无法可靠裁决、需作者掌握原始数据/图像/外部工具的项（图像不当处理、Source Data、查重、注册号、报告规范附件、投稿材料齐全等）。已被本技能 hard 门禁覆盖的维度不重复，仅提醒，不阻断交付。

### 强制 / 询问分级（对齐 gsw，不静默留白）

| 件 | 级别 | 无内容时的处理 |
|----|------|---------------|
| Cover Letter / Title Page / CRediT / COI / Funding / DAS / Keywords(3–6) | **强制** | COI/Funding/DAS 无则按 submission_checklist 标准句声明"无"，不留空 |
| ORCID / Acknowledgements 致谢对象 | **询问** | 向用户索取；未提供 → 显式标 "not provided" / 各类 N/A |
| Highlights / Suggested·Opposed Reviewers | **按目标刊** | Cell 系等要求时给；Reviewers 须逐一核 COI 回避，严禁伪造邮箱 |

### 步骤

1. **逐项询问**（不要静默用空白）：通讯作者信息 + ORCID、各作者 CRediT role、COI、Funding（funder + grant number）、致谢对象、目标刊是否要 Highlights / Suggested Reviewers。明细见 submission_checklist.md 第 1 节 + gsw submission-guide.md 第 1 节。

2. **生成投稿包**（写入 `exports/`，路径以 submission_checklist.md 第 6 节为准）：
   - `exports/cover_letter.md` — 综述卖点是 synthesis/framing/gap→展望；引用 Phase 1.5 gap + Phase 1.6 framing 作为"为何此刻需要这篇综述"。
   - `exports/title_page.md` — 题名（禁缩写）/ 作者 / 单位 / 通讯(含邮箱) / ORCID。
   - `exports/author_contributions.md` — CRediT（综述常用 role；未覆盖的 11 类标 N/A，分配细则见 gsw 第 5 节）。
   - `exports/coi_statement.md` — 无则 "The authors declare no competing interests."
   - `exports/funding.md`（可并入 title page）— 无则 "This work received no specific external funding."
   - `exports/data_availability.md` — 综述无原始数据 → "Data sharing not applicable — no new datasets were generated or analysed."（systematic 有提取数据则给获取方式）。
   - `exports/keywords.md` — 3–6 个，不照抄标题词。
   - `exports/acknowledgements.md` — 各类别（非作者贡献者/技术平台/讨论反馈），无则 N/A。
   - `exports/highlights.md`（按目标刊）/ `exports/suggested_reviewers.md`（按需，逐一核 COI 回避）。

3. **合规核对**（综述相关项，对齐 gsw compliance-gate）：署名 ICMJE 四准则、Reviewer COI 回避；伦理/注册号/统计报告对 narrative 综述标 N/A，仅 systematic/scoping 走 PRISMA。细则见 submission_checklist.md 第 3–4 节。

4. **DoD 自检（gate `submission-pack-dod`，委托独立subagent盲检）：**
   ```bash
   python3 scripts/delegate_review.py pack --checklist references/dod_checklist.json \
     --gate submission-pack-dod \
     --files exports/cover_letter.md exports/title_page.md exports/author_contributions.md \
             exports/coi_statement.md exports/keywords.md --workdir .
   python3 scripts/delegate_review.py verify --checklist references/dod_checklist.json \
     --gate submission-pack-dod --return .review_return_submission-pack-dod.json
   # 退出码非 0 = fail-closed，据subagent证据修复后重跑，未过不得声明完成
   ```
   gate 5 项：S1 强制件齐全（Cover Letter+Title Page+CRediT+COI+Keywords）/ S2 COI·Funding·DAS 非空（无则声明无）/ S3 Keywords 3–6 且不与标题雷同 / S4 通讯作者一致 / S5 无占位符·无伪造。真源见 `references/dod_checklist.json`。

5. **更新 state + Git Checkpoint：**
   ```bash
   python3 scripts/state_manager.py set-phase --phase 5 --completed true
   git add -A && git commit -m "[review] Phase 5: submission pack" --allow-empty-message 2>/dev/null || true
   ```

**完成。向用户交付投稿包，列出已生成文件与询问级标 N/A 的项。**

---

## Reference Manager Modes

Three modes: **Zotero**（推荐，实时写入）/ **None**（纯本地 JSON + BibTeX）/ **EndNote**（同 None，最后手动导入）。

> 📖 各模式详细说明见 `references/citation_styles.md` § Reference Manager Modes

---

## Edge Cases

> 📖 完整列表详见 `references/edge_cases.md`

| Issue | Handling |
|-------|---------|
| Zotero API key invalid / 403 error | Re-run `save-credentials` with a fresh key; do NOT proceed until `--status` returns ✅ |
| Mid-search crash | state.json `completed_sections` tracks progress; resume skips done |
| PubMed CLI + paper-search MCP both unavailable | HALT; suggest install edirect or enable paper-search MCP; do NOT fallback to websearch/tavily |

---

## Scripts Reference

> 📖 完整 CLI 参数和用法详见 `references/scripts_reference.md`

18 个活跃脚本（`[project]/scripts/`，Phase 0 init 时全量镜像 `scripts/*.py`，除 `test_*.py` 与 `init_project.py`）：
`zotero_manager.py` | `state_manager.py` | `matrix_manager.py` | `word_counter.py` | `validate_citations.py` | `citation_guard.py` | `check_global_citation_sequence.py` | `export_bibtex.py` | `prewrite_gate.py` | `delegate_review.py` | `style_checker.py` | `proofread.py` | `abbreviation_consistency.py` | `consolidate_references.py` | `export_docx.py` | `make_reference_docx.py` | `citation_utils.py`（import-only） | `citation_guard_core.py`（import-only）

> `scripts/init_project.py` 是 Phase 0.5 一次性脚手架（从 SKILL_DIR 运行，不复制进项目），负责创建目录/全量镜像上述脚本/写 state.json+outline.md/git init。`state_manager.py` 新增 `set-phase` / `complete-section` 子命令管理 workflow `state.json`。

---

## Interaction Rules

- **Read `outline.md` + `state.json`** at the start of EVERY phase and EVERY section loop.
- **State update is mandatory:** Update `state.json` immediately after every section and phase change.
- **Step-by-step stop:** HALT after each section. Output summary. Wait for "Continue".
- **Anti-Flattery:** Objective only.
- **Reverse Questioning:** Challenge user assumptions when warranted.
- **Point-by-Point Reply:** Address every query, no skipping.

---

## 发现 AI 跳步/漏做了怎么办（用户自救）

怀疑 AI 偷工减料时，直接把下面的话贴给它（可复制）：

- 「查进度：把 `state.json` 当前 Phase、`drafts/` 下已完成的节、`research_gap.json` / `benchmark_reviews.json` 在不在，逐一报我」（不在=跳了 Phase 1.5/1.6）
- 「对每条用到的引用跑 `validate_citations.py --live --live-used-only`，把原始输出贴我；`--live` 跑不起来就直说『联网核验不可用』，不许自判通过」
- 「每写完一节该停下让我验收，别一路写到底」
