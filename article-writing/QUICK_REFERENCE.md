# Article Writing Skill - 快速参考卡片 (v2.15.2)

## 🚀 核心升级 (v2.15.2)

- 🔒 **章节级上下文隔离**：写 `section` 时默认只加载该节上下文，拒绝跨章节正文污染。
- 🧠 **双层记忆**：全局 `context_memory.md` + 章节 `section_memory/<section>.md`，减少失忆和串章。
- 📉 **Token Budget Guard**：加载前估算 token，超预算自动降载（tail + compact）。
- 🔥 **Results/Discussion融合**：结果与机制讨论一体化输出，不割裂。

---

## ⚡ 快速开始

```
1. /init              → 初始化
2. /preview           → 预审报告
3. /storyline         → 构建提纲 (融合模式)
4. /write [section]   → 撰写 (默认本章局部上下文)
```

---

## 📋 全局命令

| 命令 | 功能 |
|------|------|
| `/init` | 初始化项目 |
| `/resume` | 恢复写作 (自动检查上下文) |
| `/preview` | 预审报告 |
| `/storyline` | 构建融合式提纲 |
| `/literature` | 文献检索 |
| `/write [sec]` | 撰写章节 (Results+Discussion) |
| `/check` | 质量检查 |
| `/reviewer` | 审稿人模拟 |
| `/snapshot` | 手动快照 (AI也会自动触发) |
| `/rollback` | 版本回滚 |
| `/stats` | 进度仪表盘 |
| `/merge` | 最终合并 |
| `/export_bib` | 导出参考文献 |

---

## 🛡️ 写作原则 (v2.15.2)

### 0. 预加载（默认）
建议在写作前统一走强制入口（全局历史 + 当前章节索引，默认不读正文草稿）：
```bash
python scripts/state_manager.py write-cycle --section results_3.1 --token-budget 6000 --tail-lines 80
```
若要续写已有章节，再追加：
```bash
python scripts/state_manager.py write-cycle --section results_3.1 --include-draft --token-budget 6000 --tail-lines 80
```
默认即 strict；仅调试时追加 `--preflight-lenient`。
输出中需检查：
- `scope` = `section-local`
- `loaded_files` 仅包含该章节相关文件
- `budget_report` 显示是否发生自动降载
- 写完章节后：先预览再落盘
```bash
python scripts/state_manager.py sync-literature --dry-run --strict-references
python scripts/state_manager.py write-cycle --section results_3.1 --finalize --sync-literature --sync-apply --strict-references --summary "..."
```
- 字数统计（默认排除 References）：
```bash
python scripts/state_manager.py word-count
python scripts/state_manager.py word-count --section results_3.1
```
- 进度仪表盘与回滚：
```bash
python scripts/state_manager.py stats
python scripts/state_manager.py rollback --target snapshot
python scripts/state_manager.py rollback --target literature_sync
```
- 合并与导出：
```bash
python scripts/merge_manuscript.py --manuscript-dir manuscripts
python scripts/merge_manuscript.py --manuscript-dir manuscripts --skip-docx
python scripts/export_bibtex.py --index-file literature_index.json --output-file references.bib
```
- 默认只改写 `md`；如需改写 Word 再显式加 `--rewrite-docx`
- 可选：`--reference-style nature`（默认 `vancouver`）
- 可选：`--similarity-threshold 0.93 --conflict-threshold 0.85`
- 冲突默认阻断 apply；仅人工确认后可加 `--allow-conflicts`
- 可选：`--backup-keep 20 --backup-max-days 30`
- 可选一条链路：
```bash
python scripts/state_manager.py write-cycle --section results_3.1
# ...写作...
python scripts/state_manager.py write-cycle --section results_3.1 --finalize --sync-literature --sync-apply --strict-references --summary "..."
```

### 1. 强制回复结构
每次回复末尾必须包含：
- **执行内容** (含 `🧪 实验逻辑批判` if data input)
- **📊 状态仪表盘** (字数、SI、状态同步)
- **🤔 反向拷问**
- **💡 你可能想知道**

### 2. 深度融合
❌ **错误**：先写Results (数字)，后写Discussion (意义)。
✅ **正确**：Results段落直接包含：
   - 数据 (Data)
   - 机制 (Mechanism)
   - 对比 (Comparison)
   - 意义 (Significance)

### 3. 数据精确性
❌ "significant effect"
✅ "5-fold increase (P<0.001)"

---

**版本**: 2.15.2
**最后更新**: 2026-02-11
