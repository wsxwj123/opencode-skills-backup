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

## Single Source of Truth

The thesis target profile is stored in:
- `thesis_profile.json`

Default profile is created by `state_manager.py init` and can be updated with:
- `state_manager.py profile`

All scripts should follow this profile to avoid rule conflicts.

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
python3 scripts/state_manager.py --project-root "${save_path}" word-count
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
