# Article Writing Skill (v2.15)

## 简介

这是一个用于撰写Nature级SCI论文的专业skill，专注于广义药物递送系统领域。**v2.15版本**在融合写作基础上进一步加入章节级上下文隔离、双层记忆和Token预算守卫。

## 核心升级 (v2.15)

- 🔒 **章节级上下文隔离**：`/write [section]` 默认只读取当前章节上下文。
- 🧠 **双层记忆模型**：全局 `context_memory.md` + 章节 `section_memory/<section>.md`。
- 📉 **Token Budget Guard**：加载阶段自动估算预算并降载，避免爆 token。

- 🔥 **Results & Discussion融合**：不再割裂！在阐述结果的同时立即进行深度讨论（机制、对比、意义），不再单独设立Discussion章节（仅保留Conclusion）。
- 🧠 **智能快照系统**：AI主动判断是否需要备份（生成内容/关键决策/新文献），而非僵化触发。
- 👁️ **上下文显式验证**：每次回复前强制检查并显示`storyline`、`literature_index`等文件的加载状态，杜绝"假装查阅"。
- 📝 **弹性写作深度**：根据论点重要性自动调整篇幅。核心论点（Key Claims）必须深度展开（>200词分析），次要数据简洁总结。

## 快速开始

### 1. 初始化项目
```
/init
```

### 2. 预审模式
```
/preview
```

### 3. 故事脉络构建 (新版)
```
/storyline
# 注意：此时会自动规划"Results & Discussion"融合章节
```

### 4. 撰写章节 (融合模式)
```
/write results_3.1
# AI将执行：描述数据 -> 解释机制 -> 对比文献 -> 阐述意义
```

## 全局命令

| 命令 | 功能 | v2.0特性 |
|------|------|----------|
| `/init` | 初始化新项目 | - |
| `/resume` | 恢复写作 | **自动执行Context Check** |
| `/preview` | 预审模式 | - |
| `/storyline` | 构建提纲 | **自动规划融合式章节** |
| `/literature` | 文献检索 | - |
| `/write [section]` | 撰写章节 | **自动执行深度分析 + 智能快照** |
| `/check` | 质量检查 | - |
| `/reviewer` | 审稿人模拟 | - |
| `/snapshot` | 手动快照 | **AI也会智能触发** |
| `/rollback` | 版本回滚 | - |
| `/merge` | 最终合并 | - |

## 核心机制

### 1. 上下文显式验证
每次写作前，AI会输出：
```markdown
[Context Check]
- Storyline: ✅ Loaded
- Lit Index: ✅ Loaded
- Fig Database: ✅ Loaded
```
确保它真的"看"到了你的数据。

### 2. 弹性写作深度
- **Key Claim**: 必须包含 数据+统计+机制+对比+意义。拒绝流水账。
- **Minor Data**: 简洁陈述。

### 3. 智能快照
AI会在每次重要的交互后主动思考："我需要备份吗？" 如果需要，会自动执行`/snapshot`。

## 文件结构

```
manuscript_project/
├── project_config.json
├── storyline.json               # 结构已更新，支持融合章节
├── writing_progress.json
├── context_memory.md            # 三版本保留
├── literature_index.json
├── figures_database.json
├── manuscripts/                 # 生成的MD/Docx
└── backups/                     # 完整快照
```

---

**版本**: 2.0.0
**更新日期**: 2024-01-28
**适用期刊**: Nature/Science/Cell及其子刊
