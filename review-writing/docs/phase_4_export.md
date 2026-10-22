> 本文件由 SKILL.md 拆分而来，仅在主文件指示时读取。

# Phase 4: Export & Finalization（Step 1–3 与 Step 5b–8；Step 4 / 4a–4d / 5 原文留在 SKILL.md）

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
   python3 scripts/validate_citations.py --live --live-used-only --fail-on-orphan --fail-on-live --fail-on-trace --retries 2
   # 🔴 --fail-on-live / --fail-on-trace 必带：不带时联网核验失败（编造 DOI 打 404）
   #    只打 [LIVE-FAIL] 行而退出码仍为 0，会被误读成通过。
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

   > **【P4·文献抽验·用户必做】** 综述的命是引文。文献进正文前用户应抽 2-3 篇让 AI 报 PMID/DOI 自己去 PubMed 核对。⚠️ 你在 Windows 上 edirect 联网核验常跑不起来（本 SKILL 已注明 edirect 在 PowerShell/CMD 不可用），**一旦不能真的联网查，AI 必须停下告诉用户，绝不许硬着头皮编 DOI/年份**。`validate_citations.py --live` 跑不起来时明说「联网核验不可用」，不许自判通过。
3. **Export bibliography:**
   ```
   [Zotero] python3 scripts/zotero_manager.py --export-bibtex \
              --output exports/references.bib --root-key ROOT_KEY
   [None/EndNote]   python3 scripts/export_bibtex.py \
              --input data/literature_index.json \
              --output exports/references.bib \
              --clean
   ```

（Step 4 编译、4a 合并参考表、4b 跨节连贯性扫描、4c 缩写一致性扫描、4d 交叉引用核查、5 字数校验：原文在 SKILL.md `## Phase 4` 节，被验收考卷逐字锁定，未外移。）

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

