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
  - 系统综述/Meta-analysis（需要完整 PRISMA 注册 + PROSPERO 流程，超出本技能范围）
scoping_review_note: |
  Scoping review 支持（轻量流程，不需 PROSPERO）。Phase 0 选择综述类型时选 scoping，
  检索覆盖面更宽、纳排标准更宽松，需记录研究问题框架（PCC: Population/Concept/Context）。
---

# General Literature Review Writing Specialist

## Quick Reference Card

### Phase 路由（读 state.json 后立即判断）
> **⚠️ 前置门：`state.json` 不存在时，先执行 Mode Handshake Gate（问 Write/Polish Mode）并等用户回答，再进 Phase 0.1。不要跳过 Mode Gate 直接收参数。**

| state.json 状态 | 跳转到 |
|-----------------|--------|
| 不存在 | **先过 Mode Handshake Gate** → Phase 0.1 |
| phase=0, 无 mode 字段 | Phase 0.5（继续初始化） |
| phase=0, mode="polish" | Phase 0-P（📖 读 `docs/phase_0p_polish_mode.md`） |
| phase=1 | Phase 1（检查是否已完成） |
| phase=2 | Phase 2（跳过 completed_sections） |
| phase=3 或 pending_sections 非空 | Phase 3（跳过 completed_sections） |
| phase=4, completed=true | 已完成，告知用户 |

### 每 Phase 关键动作
- **Phase 0:** 收参数 → 检测环境 → 创建项目 → git init
- **Phase 1:** 提纲 → 用户确认 → Zotero 集合树 → **HALT**
- **Phase 2:** 逐节搜索（**串行，≥1s 间隔**）→ 写入 Zotero/index → **HALT** dedup
- **Phase 3:** 逐节写作 → citation spot-check → Reviewer Simulator → **HALT**
- **Phase 4:** 引用总量校验 → citation guard → 编译 → 连贯性扫描 → 缩写扫描 → 导出

### 绝对禁止
- 并行搜索调用
- websearch/tavily 查文献
- 跳过 Reviewer Simulator
- 跳过 state.json 更新
- 跳过 Git Checkpoint

---

## Role & Core Philosophy

Expert academic consultant for high-impact literature reviews (Nature Reviews, Cell, Lancet Digital Health). Combines biomedicine and CS/AI domain expertise with elite writing skills.

- **Synthesis, not Summary:** Connect and contrast studies. Build new theoretical frameworks.
- **Arbitration:** Identify contradictions and analyze *why* they exist.
- **Storytelling:** Every review must have a narrative arc.
- **Figure-Driven:** High-impact papers are built around figures.

---

## Constraints & Standards

1. **Length:** 7,000–10,000 words (English); 15,000–20,000 characters (Chinese). Read target from `outline.md`.
2. **Citations:** Total ≥150. Original Articles ≥80, Reviews ≥50, Preprints ≥20.
   - Background/overview → Reviews preferred.
   - Mechanistic/experimental claims → Original Articles (mandatory; do NOT substitute a Review).
   - Clinical claims → Clinical Trials.
   - Emerging claims → Preprints (label `[Preprint]`).
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
| Exception | ChatGPT Browsing tool | If current client is ChatGPT web with Browsing — can directly access PubMed/Scholar |

> **Google Scholar补充规则：** PubMed检索完成后，若某节文献数量仍不足或主题偏交叉学科（工程/社科/政策），追加 `search_google_scholar` 补搜。Google Scholar收录范围更广，PubMed未收录的会议论文、技术报告、交叉学科期刊通常可在此找到。但Google Scholar无DOI强制要求，获取记录后须通过 `validate_citations.py --live` 验证。

**Detection:** Check AI tool list for `search_pubmed`/`search_arxiv`/`search_google_scholar` → paper-search MCP available ✅

**Forbidden:** `websearch`, `tavily`, generic web search tools — DO NOT use for academic retrieval.
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

**NOT delegatable:** Outline design, synthesis writing, Reviewer Simulator decisions, user interaction, HALT decisions.

---

## Mode Handshake Gate (Mandatory)

Before any **writing / search / import / Zotero-mutating** action, ask exactly **one** question and wait for explicit user answer:

- `Write Mode` — build review from scratch (→ Phase 0)
- `Polish Mode` — import existing draft, diagnose, revise section by section (→ Phase 0-P)

**Do not proceed until user explicitly selects a mode.**

> **Exception — Read-only status check:**
> If the user explicitly asks to *inspect current project status*, *audit progress*, *scan existing materials*, or "看看现在到哪一步了 / 先扫描一下", perform a **read-only** pass over `outline.md`, `state.json`, `drafts/`, `data/`, and `scripts/` first, then present a status report. After the report, ask for Write/Polish Mode before any new literature import or drafting action. If `state.json` does not exist, the read-only scan still must return to the Mode Handshake Gate afterward — never auto-start Phase 0.
> Read-only means: no file writes, no Zotero API mutations, no search calls.

> **Route map:**
> ```
> Write Mode:  Phase 0 (init) → Phase 1 (outline) → Phase 2 (search) → Phase 3 (write) → Phase 4 (export)
> Polish Mode: Phase 0 (init) → Phase 0-P (import+diagnose) → Phase 3 (write) → Phase 4 (export)
> ```
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

---

## Phase 0: Initialization & Environment Detection

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
| **Review type** | **narrative** | `narrative`（叙述性）/ `critical`（批判性）/ `scoping`（范围综述）。Scoping review：不需要 PROSPERO，检索覆盖更宽，研究问题框架用 PCC（Population/Concept/Context）替代 PICO，Phase 0 末尾提示 scoping 特有记录要求。Systematic review / Meta-analysis → 转到专用工具（超出本技能范围）。 |
| Word count target | EN: 7,000–10,000 words / CN: 15,000–20,000 chars | |
| Total citations | ≥150 (Original≥80, Review≥50, Preprint≥20) | |
| Reference manager | **Zotero** | Zotero / None / EndNote |
| Subagent model | Same as current session | AI scans available models, user confirms |

**If Chinese writing selected**, notify at end of Phase 0:
> 本技能使用 PubMed/paper-search MCP 检索英文文献。中文数据库（CNKI/万方）补充流程详见 `references/citation_styles.md` § CNKI / 万方中文文献导入。建议在初稿完成后统一补充，避免 gid 编号冲突。

### 0.2 Full Environment Check

Run the 8-step environment detection (📖 full commands in `references/env_check.md`): Step 0 OS+Python, 1 curl, 2 git, 3 Zotero+pyzotero, 4 edirect, 5 proxy+PubMed connectivity, 6 NCBI key, 7 paper-search MCP, 8 required scripts. Display ✅/❌ per step. Record `os` / `git_available` / `pubmed_proxy` / `search_fallback` for Phase 0.5 to write into `outline.md`.

**All 8 must resolve before Phase 0.5.** Failure routing:

| Failed step | Blocking? | Consequence / route |
|-------------|-----------|---------------------|
| 0 Python < 3.7 | **YES** | Abort; guide upgrade (python.org / `brew install python` / `winget install Python.Python.3`). |
| 1 curl missing | **YES** | System-level issue; resolve before continuing (Windows: curl ships with PowerShell 5.1+). |
| 2 git missing | No | Not blocking — all Git Checkpoints silently skip (`git_available: false`); recommend install for rollback. |
| 3 Zotero/pyzotero (Zotero mode) | **YES** (Zotero mode) | `pip install pyzotero`; install Zotero desktop. None/EndNote mode → skip Step 3. |
| 4 edirect missing (Medical/Bio) | No | Auto-fallback to paper-search MCP → write `search_fallback: paper-search-mcp`; Windows → WSL or fallback. |
| 5 PubMed unreachable | No | Auto-scan proxy ports; if all fail → fallback to paper-search MCP, notify user. |
| 6 NCBI key unset | No | Optional; default 3 req/s rate limit. |
| 7 paper-search MCP absent | No | PubMed CLI only; inform user MCP is optional. |
| 8 required script missing | **YES** | Abort; verify SKILL_DIR path or re-install the skill. |

> ⚠️ At least one of Step 4/5/7 must yield a working retrieval path (edirect OR paper-search MCP). If **both** PubMed CLI and paper-search MCP are unavailable → HALT (see Edge Cases). Never fall back to websearch/tavily.

### 0.3 Zotero First-Time Setup (Zotero mode only)

> 📖 完整设置步骤（账号注册、API key 生成、权限配置、连接测试、安全规则）详见 `references/zotero_setup.md`。

Key rule: `lib_id` → 写入 `outline.md`；`api_key` → 每次会话口头询问，**绝不写入任何文件**。

```bash
python3 scripts/zotero_manager.py --status --lib-id [NUMBER] --api-key [KEY]
# Expected: ✅ Connected to Zotero library ...
```

If `--status` lists multiple libraries (personal + group), show the list and ask user which to use. Write chosen `lib_id` to `outline.md`.

### 0.4 Subagent Model Detection

```
1. List all models available in current AI client
2. Present list to user
3. Ask: which model for subagent tasks? (default: same as current session)
4. Write choice to outline.md: subagent_model: <name>
```

### 0.5 Initialize Project Files

After all checks pass. Run `scripts/init_project.py` — it creates the folder structure,
copies the 9 active scripts, writes `state.json` + `outline.md` (templates below), and runs
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
> | Other | Auto-detect (run one-liner below) | same |

**"Other" client — auto-detect SKILL_DIR** (run from anywhere; uses `zotero_manager.py` as a stable cross-mode marker):

```bash
python3 -c "
import pathlib
dirs = [pathlib.Path.home()/p for p in [
    '.claude/skills/review-writing',
    '.cursor/skills/review-writing',
    '.windsurf/skills/review-writing',
    '.config/opencode/skills/review-writing']]
found = next((str(d) for d in dirs if (d/'scripts'/'zotero_manager.py').exists()), None)
print(found if found else 'NOT FOUND — run: find ~ -name zotero_manager.py -path */review-writing/*')
"
```

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
> **Note:** Phase 0.5 only creates folder structure + copies scripts + writes state.json/outline.md. Zotero collection tree (`--init`) is NOT run here — it runs in Phase 1 (Write Mode) or Phase 0-P Step 5 (Polish Mode).

The script writes `[TITLE]/state.json`:
```json
{"phase": 0, "completed_sections": [], "zotero_root_key": ""}
```

…and the `[TITLE]/outline.md` template (AI fills Parameters/Environment fields after Phase 0.1–0.4):
```markdown
# Review Configuration (READ THIS FILE at the start of every phase)

## Parameters
- Title: [user input]
- Target Journal: [user input]
- Language: [English / Chinese]
- Reference Manager: [Zotero / None / EndNote]
- Review Type: [narrative / critical / scoping]
- Word Count Target: [EN: 7,000–10,000 words / CN: 15,000–20,000 chars]
- Citation Requirements: ≥150 total (Original≥80, Review≥50, Preprint≥20)
- Discipline: [Medical-Biomedical / CS-AI / Interdisciplinary]

## Environment (filled after detection, read directly in later phases)
- os: [Darwin / Linux / Windows]
- git_available: [true / false]
- pubmed_proxy: [none / http://127.0.0.1:XXXX]
- zotero_lib_id: [numeric ID]
- search_fallback: [paper-search-mcp (when edirect unavailable)]
- subagent_model: [model name / same as main session]

## Research Question
- RQ / PICO: [filled after user confirms]

## Outline (filled after confirmation)
### 1. Introduction
#### 1.1 Background
#### 1.2 Scope
...

## Current Status
- Phase: Phase 0 complete
- Completed sections: none
- Zotero root collection key: [filled after Phase 1]
```

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

If git not available → skip silently. If nothing to commit (`git status` clean) → skip silently (`|| true` handles this).
AI: substitute `<MESSAGE>` with the checkpoint description. Format: `[review] Phase X.Step: <description>`.

| Checkpoint location | Commit message |
|---------------------|----------------|
| Phase 0.5 (in init script) | `[review] Phase 0: project initialized` |
| Phase 1 Step 9 | `[review] Phase 1: outline confirmed` |
| Phase 2 per-section Step 8 | `[review] Phase 2: section X.X search complete` |
| Phase 2.5 (after dedup) | `[review] Phase 2.5: dedup + global ID assigned` |
| Phase 3 per-section Step 9 | `[review] Phase 3: section X.X draft complete` |
| Phase 4 Step 7 | `[review] Phase 4: export finalized` |
| Phase 0-P Step 5 (after substep 3) | `[review] Phase 0-P: citations imported` |
| Phase 0-P Step 6 (after state init) | `[review] Phase 0-P: polish mode initialized` |

### Rollback (using the checkpoints above)

> 📖 Rollback 命令、Edge Cases（需要推倒重来 / Git 不可用）详见 `references/git_rollback.md`。

---

## Phase 1: Outline Confirmation + Collection Tree

**Start: Read `outline.md` + `state.json`. If state.json shows phase≥1, skip.**
**Polish Mode: if `state.json` contains `"mode": "polish"`, skip Phase 1 entirely — go to Phase 3.**

1. **Define RQ/PICO** (or PCC for scoping review) with user first. Write to `outline.md`.
   - RQ/PICO 是提纲的语义锚点：研究问题明确后，提纲各节才能有检验标准。
   - Scoping review：用 PCC 框架（Population / Concept / Context）替代 PICO。
2. **Propose outline structure** based on RQ/PICO: "Funnel" Introduction + "Thematic" Body. (≤2 hierarchy levels)
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

4. **规划贯穿全文的概念框架图（提纲确认后，Phase 1 内完成）：**
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
   # First check if collection tree already exists (idempotent — safe on re-entry):
   ROOT_KEY=$(python3 scripts/zotero_manager.py --status --find-root-title "[TITLE]" \
     --lib-id LIB_ID --api-key API_KEY 2>/dev/null) && echo "Root exists: $ROOT_KEY" \
     || python3 scripts/zotero_manager.py --init --title "[TITLE]" --outline outline.md \
        --lib-id LIB_ID --api-key API_KEY
   ```
   - `--find-root-title` exit 0 → root already exists (stdout = key, reuse it); exit 3 → no match, the `||` branch runs `--init`; exit 4 → ambiguous (multiple same-named roots), stdout lists candidate keys — **stop and ask user to pick** rather than letting `--init` create a duplicate.
   - Creates root collection + subcollections matching outline hierarchy.
7. **Initialize index files (None/EndNote mode):**
   ```bash
   python3 scripts/state_manager.py init-index
   # Creates empty data/literature_index.json + data/synthesis_matrix.json + figures/figure_index.md (idempotent).
   ```
8. **Update state.json** (writes phase=1 + zotero_root_key, preserving other keys):
   ```bash
   python3 scripts/state_manager.py set-phase --phase 1
   python3 scripts/state_manager.py set-root-key --key "[key from step 6]"   # Zotero mode only; skip in None/EndNote
   ```
9. **Git Checkpoint** (见复用块, msg: `[review] Phase 1: outline confirmed`)

**HALT. Wait for user to confirm outline before Phase 2.**

---

## Phase 2: Round 1 Literature Search + Real-Time Write

**Start: Read `outline.md` + `state.json`. Skip sections already in `completed_sections`.**
> **Phase gate:** if `state.json` does not exist or `phase < 1` → HALT; tell user "Phase 0 init must be completed first (run Phase 0.5 to create outline.md and state.json)"; do not proceed.

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
  2b. [相关性筛选] 入库前逐篇判断（不得"搜到即入库"）：
      - 保留条件：标题/摘要与本节 RQ/PICO（或 PCC）直接相关，且能提供引用价值的论据
      - 排除条件（需记录排除理由类型）：
        · 语言（非英文/中文）→ 标记 excluded: language
        · 超范围（话题偏离本节主题）→ 标记 excluded: off_topic
        · 质量问题（无同行评审且非顶级 preprint）→ 标记 excluded: quality
        · 时效（发表年份过早且无奠基价值）→ 标记 excluded: outdated
      - 最终保留的才进入 tmp/papers_X_X.json
  3. Save metadata to tmp/papers_X_X.json  (e.g., section 1.1 → tmp/papers_1_1.json)
  4. Write papers (run ONLY the branch matching the project's Reference Manager — they are alternatives, not sequential):
     [Zotero] python3 scripts/zotero_manager.py --add-batch \
       --section "X.X" --papers tmp/papers_X_X.json \
       --root-key ROOT_KEY --index data/literature_index.json \
       --lib-id LIB_ID --api-key API_KEY
       # ROOT_KEY = zotero_root_key from state.json (written by --init)
       # Safe: dedup-at-write-time — same paper across sections creates ONE Zotero item,
       # linked to multiple section collections; gid:N assigned at first creation and never changes.
       # --add-batch already writes to --index (literature_index.json); do NOT append separately.
       # **`--add-batch` 已自动写入 literature_index.json，不要再手动追加。**

     [None/EndNote] python3 scripts/state_manager.py append-literature \
       --section X.X --papers tmp/papers_X_X.json --index data/literature_index.json \
       --source-provider SP
       # SP = the actual search tool used for this section (see § Search Tool Priority):
       #   PubMed CLI (Medical/Bio, esearch/efetch)  → --source-provider pubmed-cli   (default; may omit)
       #   paper-search MCP (CS/AI, or PubMed-CLI fallback) → --source-provider paper-search
       # ⚠️ openalex / tavily / websearch 均被 citation_guard 列为 FORBIDDEN，不可用作 SP。
       # 仅 pubmed-cli 和 paper-search 可通过 citation_guard。
       # Per-entry source_provider already set in tmp/papers_X_X.json is preserved (setdefault, not overwrite).
       # gid auto-increments; DOI dup (case-insensitive) → only appends X.X to that record's related_sections.
       # Sets defaults per new entry: global_id, related_sections=[X.X], source_provider, source_id, verified=false.
       # NOTE: CNKI/Wanfang Chinese refs are NOT added here — they go via manual EndNote/RIS import
       #       (see Phase 0 note) + manual gid tag, bypassing this script and citation_guard's online checks.

     Required fields per entry: `global_id` (int), `title`, `authors`, `year`, `doi` or `pmid`, `abstract`, `related_sections` (array, e.g. `["1.1"]`).
     > ⚠️ Use `related_sections` (array), NOT `section` (string) — `matrix_manager.py` and `state_manager.py` filter by `related_sections`.
     >
     > **Multi-section membership (important):**
     > A paper may belong to multiple top-level sections **and** multiple subsections simultaneously. For example, one record may legitimately carry:
     > `"related_sections": ["2.1", "3.1", "4.1"]`
     > meaning the paper is a mechanistic anchor (2.1), a delivery-platform example (3.1), **and** a disease-mapping case (4.1).
     > Do **not** force a single-section assignment when the paper supports multiple review functions. `--add-batch` appends to `related_sections` on repeat calls (does not overwrite); Zotero side, the same item is linked to multiple section collections.
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
         --log data/citation_guard_report.json
     If guard exits non-zero → do NOT continue to next section; fix flagged entries first.
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

**Entry: Read `outline.md` + `state.json` first. If `state.json` phase < 3 (Write Mode), update to phase=3:**
```bash
# Only run if current phase < 3 (read state.json first; Polish Mode already enters at phase=3).
# Do NOT regress a phase=4 project back to 3.
python3 scripts/state_manager.py set-phase --phase 3
```
**Skip completed sections (check `completed_sections` list).**

**Polish Mode branch (if `state.json` contains `"mode": "polish"`):**
```
Before starting any section, read state.json → pending_sections:
  missing → no draft exists: run Round 1 search (same as Phase 2 per-section loop Steps 2-6) INLINE here, then proceed to step 1 below. Do NOT navigate back to Phase 2 — all search+write happens within this Phase 3 section loop
  rewrite → existing draft exists in drafts/section_XX_XX.md: read it as context, then fully rewrite
  polish  → existing draft exists in drafts/section_XX_XX.md: read it; fix ONLY AI-flags + thin citations;
            keep structure and arguments intact; do NOT overwrite with fresh draft
  keep    → skip entirely (already in completed_sections)

If pending_sections is empty → all sections complete; proceed to Phase 4.
```

### Per-Section Cycle

1. **Load context:**
   ```
   [Zotero] python3 scripts/zotero_manager.py --get-section "X.X" \
              --root-key ROOT_KEY --lib-id LIB_ID --api-key API_KEY
   [None/EndNote]   python3 scripts/matrix_manager.py focus --section X.X
            # Shows papers + existing claim bindings for this section from synthesis_matrix.json
            # Also read data/literature_index.json filtered by related_sections containing X.X
   [Polish Mode] Also read existing drafts/section_XX_XX.md (rewrite: as reference; polish: as base to edit)
   ```

2. **Round 2 search** (targeted, ≥5 additional papers for specific claims):
   - **Write Mode:** triggered when Phase 2 found <10 papers for this section, or the writer identifies specific claims that lack supporting evidence during Step 4 drafting
   - **Polish Mode `rewrite`:** RECOMMENDED — run targeted search if diagnosis flagged citations/500w < 2
   - **Polish Mode `polish`:** only if Phase 0-P Step 3 diagnosis flagged citations/500w < 2
   - **`keep` sections:** skip
   - If user explicitly requests Round 2 for any section → execute regardless of above criteria
   - Add new papers same way as Phase 2 (batch add + dedup).

3. **Figure — MANDATORY read then write:**
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

4. **Draft:** Write to `drafts/section_XX_XX.md` (zero-pad each part to 2 digits, e.g., section 1.1 → `drafts/section_01_01.md`, section 2.10 → `drafts/section_02_10.md`). Paragraphs only. Citation format `[N]` (N = gid).
   - **Reference the figure caption from Step 3a** — the draft must describe and introduce the figure using its planned caption and key message.
   - Apply Anti-AI Writing rules (English or Chinese mode per outline.md).
   - Synthesis not summary; arbitration of contradictions; alternate claim/evidence order.
   - **Abbreviation rule:** First occurrence of any abbreviation in this section must use "Full Name (ABBR)" format. If the abbreviation was already defined in a previous section, use ABBR directly. `exports/abbreviation_list.md` does not exist yet (it is generated in Phase 4 Step 4c) — to check prior definitions, grep the already-written `drafts/section_*.md` files for the `Full Name (ABBR)` pattern.

5. **Citation spot-check** (lightweight, runs per-section — catches hallucinated `[N]` before Reviewer Simulator):
   ```bash
   # Scans all drafts/ but only this section's file matters (previous sections already passed).
   # --fail-on-orphan exits non-zero if any [N] in draft has no match in literature_index.json.
   python3 scripts/validate_citations.py --drafts-dir drafts --index-path data/literature_index.json --fail-on-orphan
   ```
   - Checks every `[N]` in drafts exists in `literature_index.json` (or Zotero gid pool).
   - If any `[N]` is orphan (not in index) → fix immediately: either find the real gid or remove the citation.
   - Does NOT do online DOI/PMID verification here (that's Phase 4 `citation_guard.py`'s job).
   - [Zotero mode] Also cross-check against `--get-section` output: every gid used in draft should appear in the section's Zotero collection.

6. **Reviewer Simulator** — 执行 5 维度 16 项 Y/N checklist（📖 完整 16 项详见 `references/reviewer_checklist.md`）。5 个维度（每项任一 N 即该维度失败）：
   - **D1 Novelty & Contribution** — 是否提出新框架/假说/视角，明写"gap→contribution"，不只是罗列已有工作。
   - **D2 Arbitration & Critical Analysis** — 是否识别 ≥1 处文献矛盾，分析*为何*矛盾，并给出立场或调和解释（不骑墙）。
   - **D3 Evidence Density & Traceability** — 每个事实断言有引用、关键断言 ≥2 独立来源、证据类型与断言类型匹配（机制→原著，疗效→临床试验）。
   - **D4 Flow & Coherence** — 段首承接上段结论、本节有 setup→evidence→synthesis→implication 内在弧线、无可随意搬移的孤立段。
   - **D5 Anti-AI Compliance** — 零禁用词、句长有节奏（无连续 3 句近长）、被动句 ≤30%、无模板化转折开头。
   **优先委托独立 subagent 盲评**（消除"自写自评"偏差）：派一个 subagent，只给它 `drafts/section_XX_XX.md` 路径 + checklist，不给写作时的上下文，让它独立判定每项 Y/N 并返回结构化结果。无 subagent 能力的客户端 → 主 agent 自评，但必须切换到"审稿人视角"重新逐项核对（不默认通过）。
   **Gate:** 任何维度 ≥1 项失败 → 内部修订（最多 2 轮）。2 轮后仍失败 → **HALT**，输出结构化反馈（【问题】+ 证据锚点 + 根源分析 + 修复方向）。修订与 HALT 决策由主 agent 负责（不可委托）。

7. **Word count check:**
   ```bash
   python3 scripts/word_counter.py --file drafts/section_01_01.md --language en   # or --language cn for Chinese; read from outline.md
   ```
   Key sections target: >500 words (EN) / >1,500 chars (CN); Supporting: >200 words / >600 chars.
   **If user explicitly requested a shorter length** (e.g., "~800 characters"): defer to user's request; treat the skill's minimums as guidance for quality, not a hard gate. Do not loop-prompt the user to write more if they have already confirmed their target length.

8. **Update state.json — MANDATORY, do not skip:**
   ```bash
   python3 scripts/state_manager.py complete-section --section X.X
   # Adds X.X to completed_sections AND removes it from any pending_sections bucket (Polish Mode),
   # preserving all other keys. Idempotent.
   ```
   A section must never appear in both `completed_sections` and `pending_sections` simultaneously (the command guarantees this).

9. **Git Checkpoint** (见复用块, msg: `[review] Phase 3: section X.X draft complete`)

10. **HALT:** Output summary (content / logic / citation count / word count). Wait for "Continue".

### Figure Prompt Generation

**Trigger:** Run ONCE after ALL sections in Phase 3 are complete (all sections in `completed_sections`).
Generate prompts for every entry in `figures/figure_index.md`. Write output to `figures/figure_prompts.md`.

> 📖 Use the figure-prompt template in `references/writing_guidelines.md` §5 (TYPE / SUBJECT / STYLE / COLOR SCHEME / ELEMENTS / LAYOUT / TYPOGRAPHY / KEY MESSAGE / AVOID).

---

## Phase 4: Export & Finalization

**Start: Read `outline.md` + `state.json`. If state.json shows phase=4 and completed=true, skip.**

**⚠️ MANDATORY entry gate — block Phase 4 when pending sections remain (Polish Mode):**
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
   **引用总量校验（警告性，不阻断 —— 尊重用户自定的短篇长度）:**
   ```bash
   python3 scripts/state_manager.py count-citations --drafts-dir drafts --threshold 150
   ```
   > **类型分布（人工核对）：** literature_index.json 未记录 Original/Review/Preprint 类型字段，无法机器统计。AI 对照 Constraints 目标（Original≥80 / Review≥50 / Preprint≥20）人工抽查 index，明显失衡时提示用户。

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
3. **Export bibliography:**
   ```
   [Zotero] python3 scripts/zotero_manager.py --export-bibtex \
              --output exports/references.bib --root-key ROOT_KEY --lib-id LIB_ID --api-key API_KEY
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
   若结论节或最后正文节不含独立的"Future Directions/Open Questions"结构化段，在此强制补写，并插入到 `exports/Final_Review.md` 对应位置 + 反向同步到 `drafts/section_XX_XX.md`（最后一节）。
   要求：
   - ≥3 条具体、可操作的研究方向（不得只写泛化描述如"further studies are needed"）
   - 每条 ≥1 句说明"为什么当前无法回答"（gap 原因）
   - 每条 ≥1 句说明"突破路径"（具体方法/技术/数据类型）
   - 与正文论证对应，不引入正文未建立的概念
   格式示例（EN）：
   ```
   ## Future Directions and Open Questions
   **1. [Direction title]**
   Current knowledge gap: [why it cannot be answered now]. Recommended approach: [specific method/resource].
   **2. ...
   ```

5c. **元数据块（导出前补全）：** 在 `exports/Final_Review.md` 末尾追加：
   ```
   ---
   ## Manuscript Metadata
   - Search cutoff date: [YYYY-MM-DD — the date of the final search run]
   - Databases searched: [e.g., PubMed, arXiv, Google Scholar] (see data/search_log.json for full log)
   - Conflicts of interest: [author statement — ask user to provide, default: "None declared"]
   - Funding: [funding statement — ask user to provide, default: "Not specified"]
   ```
   > search_log.json was populated by `append-search-log` calls during Phase 2. If search_log.json is absent, reconstruct dates from git log.

6. **Update state.json — merge, do NOT overwrite:**
   ```bash
   python3 scripts/state_manager.py set-phase --phase 4 --completed true
   ```
   Only `phase` and `completed` are mutated; `completed_sections`, `mode`, `pending_sections`, `zotero_root_key`, `citations_imported` are preserved untouched.
7. **Git Checkpoint** (见复用块, msg: `[review] Phase 4: export finalized`)
8. **Update outline.md** current status section (human-readable summary).

---

## Reference Manager Modes

Three modes: **Zotero**（推荐，实时写入）/ **None**（纯本地 JSON + BibTeX）/ **EndNote**（同 None，最后手动导入）。

> 📖 各模式详细说明见 `references/citation_styles.md` § Reference Manager Modes

---

## Edge Cases

> 📖 完整列表详见 `references/edge_cases.md`

| Issue | Handling |
|-------|---------|
| Zotero API key invalid / 403 error | Re-ask user for api_key; do NOT proceed until --status returns ✅ |
| Mid-search crash | state.json `completed_sections` tracks progress; resume skips done |
| PubMed CLI + paper-search MCP both unavailable | HALT; suggest install edirect or enable paper-search MCP; do NOT fallback to websearch/tavily |

---

## Scripts Reference

> 📖 完整 CLI 参数和用法详见 `references/scripts_reference.md`

9 个活跃脚本（`[project]/scripts/`，Phase 0 init 时复制）：
`zotero_manager.py` | `state_manager.py` | `citation_utils.py`（import-only） | `export_bibtex.py` | `matrix_manager.py` | `word_counter.py` | `validate_citations.py` | `citation_guard.py` | `check_global_citation_sequence.py`

> `scripts/init_project.py` 是 Phase 0.5 一次性脚手架（从 SKILL_DIR 运行，不复制进项目），负责创建目录/复制上述脚本/写 state.json+outline.md/git init。`state_manager.py` 新增 `set-phase` / `complete-section` 子命令管理 workflow `state.json`。

---

## Interaction Rules

- **Read `outline.md` + `state.json`** at the start of EVERY phase and EVERY section loop.
- **State update is mandatory:** Update `state.json` immediately after every section and phase change.
- **Step-by-step stop:** HALT after each section. Output summary. Wait for "Continue".
- **Anti-Flattery:** Objective only.
- **Reverse Questioning:** Challenge user assumptions when warranted.
- **Point-by-Point Reply:** Address every query, no skipping.
