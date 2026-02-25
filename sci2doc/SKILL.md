---
name: sci2doc
description: Use when converting SCI paper materials into a Chinese doctoral thesis draft with strict chapter structure, atomic markdown workflow, gate checks, and rollback safety.
---

# Sci2Doc

## Overview

This skill converts SCI paper materials (PDF/Word plus user context) into a Chinese doctoral thesis draft.

This skill is process-first, not one-shot generation.

The workflow is built around:
- `state_manager.py` for anti-forgetfulness, token budgeting, gate checks, snapshot/rollback
- `atomic_md_workflow.py` for atomic subsection markdown files, numbering validation, merge, self-check, section-level snapshot

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
14. Abbreviation consistency is mandatory:
    - First occurrence of any abbreviation must expand as: `中文全称（English Full Name, ABBR）`
    - All subsequent occurrences use bare abbreviation only, no re-expansion.
    - Use `abbreviation_registry.py` to register, track, and auto-strip redundant expansions.
    - A formal abbreviation table page (three-line format, alphabetically sorted) must be generated in front matter.
15. Three-line table format is mandatory for all tables:
    - Top border: 1.5pt solid
    - Header-body separator: 0.5pt solid
    - Bottom border: 1.5pt solid
    - No vertical lines, no other horizontal lines
    - Use Markdown `| col1 | col2 |` syntax in atomic `.md` files; `markdown_to_docx.py` auto-converts to Word three-line tables.
    - Table captions use five-point KaiTi (楷体五号, 10.5pt), centered above the table.
16. Writing style constraints are mandatory:
    - No em dashes (——). Use commas, periods, or restructure the sentence instead.
    - Statements only, no rhetorical or direct questions in body text. Every sentence must be declarative.
    - Result descriptions must be objective, fair, and neutral. No subjective adjectives (e.g. 令人惊讶的、显著优于、远超预期). State data and let readers judge.
    - Result discussions must be correct, precise, and provide extended analysis (e.g. compare with prior work, explain mechanisms, note limitations).
    - Language must be plain and accessible. Avoid overly formal/literary phrasing, archaic words, and jargon without explanation.
    - No metaphors of any kind (e.g. 如同、好比、仿佛、犹如、像...一样、...的桥梁、...的基石).
    - No parallelism/排比 constructions (e.g. repeating sentence patterns for rhetorical effect).
    - Use `check_quality.py` `check_writing_style()` to auto-detect violations.

## Single Source of Truth

The thesis target profile is stored in:
- `thesis_profile.json`

Default profile is created by `state_manager.py init` and can be updated with:
- `state_manager.py profile`

All scripts should follow this profile to avoid rule conflicts.

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
├── 04_图表文件/             # 图表描述文件（AI/用户手动放置）
├── .state/                 # gate-check 状态
├── backups/                # 快照备份（自动创建）
├── snapshots/              # section-snapshot（自动创建）
├── project_state.json      # 项目状态
├── thesis_profile.json     # 论文配置
├── context_memory.md       # 运行时上下文记忆
├── chapter_index.json      # 章节结构索引
├── literature_index.json   # 文献引用索引
├── figures_index.json      # 图表引用索引
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

### 1) Initialize Project

```bash
python3 scripts/state_manager.py --project-root "${save_path}" init \
  --title "论文中文题目" --author "作者姓名" --major "学科"
```

Then verify profile:

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile --show
```

If needed, update negotiated targets:

```bash
python3 scripts/state_manager.py --project-root "${save_path}" profile \
  --body-target 80000 --abstract-min 1500 --abstract-max 2500 \
  --references-min 80 --min-chapters 5 \
  --chapter-target 1:12000 --chapter-target 2:17000
```

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

### 6) Chapter Self-Check (Immediate)

```bash
python3 scripts/atomic_md_workflow.py --project-root "${save_path}" \
  self-check --docx "${save_path}/02_分章节文档/第2章_自动合并.docx"
```

Notes:
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

Optional high-fidelity chapter docx merge:

```bash
python3 scripts/merge_chapters.py \
  --input-dir "${save_path}/02_分章节文档" \
  --output "${save_path}/03_合并文档/完整博士论文.docx" \
  --require-high-fidelity
```

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

## Humanization Contract

Before finalizing each chapter:

1. Run technical self-check (word count + quality)
2. Revise style using humanizer-zh principles:
- avoid templated transitions
- avoid repetitive rhetorical scaffolding
- remove empty high-level claims
- keep evidence-first paragraph logic
3. Re-check quality
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

## Abbreviation Contract

All abbreviations must be tracked via `abbreviation_registry.json` to ensure consistency across chapters.

### First Occurrence Rule

The first time an abbreviation appears in the thesis body, it must be expanded as:

```
中文全称（English Full Name, ABBR）
```

Example:
```
聚合酶链式反应（Polymerase Chain Reaction, PCR）
```

All subsequent occurrences use bare `PCR` only. Never re-expand.

### Workflow

1. **During writing**: When writing each subsection `.md`, include the full expansion on first use.
2. **After postwrite**: `state_manager.py postwrite` automatically:
   - Extracts abbreviations from all chapter markdown files
   - Registers new ones with chapter/section metadata
   - Strips redundant expansions in non-first-occurrence chapters
3. **Before final merge**: Run `abbreviation_registry.py validate` to confirm cross-references.
4. **Front matter**: Generate the abbreviation table page with `abbreviation_registry.py table`.

### CLI Quick Reference

```bash
# List all registered abbreviations
python3 scripts/abbreviation_registry.py --project-root "${save_path}" list

# Register manually
python3 scripts/abbreviation_registry.py --project-root "${save_path}" register \
  --abbr PCR --full-cn "聚合酶链式反应" --full-en "Polymerase Chain Reaction" \
  --chapter 2 --section 2.1

# Delete an incorrect entry
python3 scripts/abbreviation_registry.py --project-root "${save_path}" unregister --abbr PCR

# Update an existing entry
python3 scripts/abbreviation_registry.py --project-root "${save_path}" update \
  --abbr PCR --full-cn "新的中文全称"

# Extract from a markdown file (with auto-register)
python3 scripts/abbreviation_registry.py --project-root "${save_path}" extract \
  --file path/to/section.md --chapter 2 --section 2.1 --auto-register

# One-shot: extract + register + strip redundant expansions
python3 scripts/abbreviation_registry.py --project-root "${save_path}" process \
  --file path/to/section.md --chapter 3 --section 3.1 --in-place

# Generate abbreviation table markdown
python3 scripts/abbreviation_registry.py --project-root "${save_path}" table

# Cross-reference validation
python3 scripts/abbreviation_registry.py --project-root "${save_path}" validate
```

## File Layout

Typical project tree:

```text
<project_root>/
├── thesis_profile.json
├── project_state.json
├── context_memory.md
├── history_log.json
├── chapter_index.json
├── literature_index.json
├── figures_index.json
├── abbreviation_registry.json
├── atomic_md/
│   └── 第2章/
│       ├── 2.1_引言.md
│       ├── 2.2_实验A_材料方法.md
│       └── 2.3_实验A_结果讨论.md
├── 02_分章节文档_md/
├── 03_合并文档_md/
├── 02_分章节文档/
├── 03_合并文档/
└── .state/
```

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
