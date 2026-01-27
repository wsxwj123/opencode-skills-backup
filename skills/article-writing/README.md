# Article Writing Skill

## 简介

这是一个用于撰写Nature级SCI论文的专业skill，专注于广义药物递送系统领域。

## 核心功能

- ✅ 逻辑严密的Scientific Story构建
- ✅ 分阶段精准文献检索与索引管理
- ✅ 持久化记忆系统（防止上下文丢失）
- ✅ 版本控制与快照回滚（完整备份）
- ✅ 审稿人视角模拟与质量检查
- ✅ 海明威式科学写作（简练、清晰）

## 快速开始

### 1. 初始化项目
```
使用命令: /init

AI将询问基本信息（项目名、目标期刊、递送系统类型、疾病模型），并创建完整的项目文件结构。
```

### 2. 预审模式
```
使用命令: /preview

提供实验设计大纲和Figure列表，AI将生成3000词可行性报告，包括：
- 创新性分析（与竞争工作对比）
- 数据完整性检查
- 潜在审稿人质疑
```

### 3. 故事脉络构建
```
使用命令: /storyline

与AI共同确定论文逻辑（精确到每段的论点），生成storyline.json。
```

### 4. 文献检索
```
使用命令: /literature phase1

批量检索20-30篇核心文献，建立literature_index.json。
后续写作时会自动补充相关文献。
```

### 5. 逐节撰写
```
使用命令: 
/write abstract
/write introduction
/write results_3.1
/write discussion

每完成一节自动：
- 字数统计
- 质量检查
- 更新进度
- 创建快照
```

### 6. 最终合并
```
使用命令: /merge

生成Word格式的完整论文（Main Text + Supplementary Info）。
```

## 全局命令

| 命令 | 功能 |
|------|------|
| `/init` | 初始化新项目 |
| `/resume` | 恢复写作（加载所有上下文） |
| `/preview` | 预审模式（可行性报告） |
| `/storyline` | 构建故事脉络 |
| `/literature [phase]` | 文献检索 |
| `/write [section]` | 撰写指定章节 |
| `/check` | 质量检查 |
| `/reviewer [mode]` | 审稿人模拟 |
| `/snapshot [desc]` | 手动快照 |
| `/rollback` | 版本回滚 |
| `/stats` | 统计仪表盘 |
| `/merge` | 最终合并 |

## 项目文件结构

```
manuscript_project/
├── project_config.json          # 项目配置
├── storyline.json               # 故事脉络（选项B粒度）
├── writing_progress.json        # 实时进度
├── context_memory.md            # 上下文快照（3版本）
├── literature_index.json        # 文献数据库
├── figures_database.json        # Figure元数据
├── reviewer_concerns.json       # 审稿人质疑库
├── version_history.json         # 版本历史
├── manuscripts/                 # Markdown稿件
│   ├── 01_Abstract.md
│   ├── 02_Introduction.md
│   ├── 03_Methods.md
│   ├── 04_Results_*.md
│   ├── 05_Discussion.md
│   ├── 06_Conclusion.md
│   ├── Full_Manuscript.md
│   └── Full_Manuscript.docx
├── figures/                     # 用户上传的Figure
└── backups/                     # 快照备份（最多10个）
```

## 核心特性

### 1. 持久化记忆
- 每次完成小任务自动更新`context_memory.md`
- 保留3个版本（当前、v-1、v-2）
- 对话重启时自动加载所有上下文

### 2. 版本控制
- 自动快照：完成每个章节后
- 手动快照：用户主动调用
- 完整备份：包含所有JSON、MD、figures/
- 最多10个快照（循环覆盖）

### 3. 文献管理
- 三阶段检索：Phase 1（核心）→ Phase 2（实时补充）→ Phase 3（机制）
- 自动去重（DOI + 标题相似度）
- DOI验证（交叉检查标题）
- 引用顺序：按添加到索引的顺序（Vancouver style）

### 4. 质量控制
- 字数检查（各章节+总计）
- 引用密度检查（按章节标准）
- Figure编号连续性
- AI高频词自动替换
- 数据冲突检测

### 5. 审稿人模拟
- Storyline阶段：检查逻辑漏洞
- Final阶段：完整审稿报告
- 预置质疑库（按递送系统分类）

## 写作标准

### 字数限制
- Abstract: ≤250词
- Introduction: 800-1500词
- Main Text总计: 5000-7000词
- 参考文献: 30-50篇

### 文献时间窗口
- 背景统计：≤2年
- Gap陈述：≤5年
- 创新点：≤5年（IF>10）
- 机制讨论：≤10年
- 方法学：不限年份

### 引用密度
- Introduction: 论点1-2篇，讨论3-4篇
- Results: 不引用
- Discussion: 论点1-2篇，展望3-4篇
- Methods: 仅方法学原始论文

## 注意事项

1. **首次使用**：必须先运行`/init`初始化项目
2. **恢复写作**：重新开始对话时使用`/resume`加载上下文
3. **重大修改前**：使用`/snapshot`备份当前状态
4. **Figure顺序**：用户按顺序提供，AI不会自动重排（防止遗漏）
5. **统计显著性**：直接报告P值，不使用*号

## 故障排除

### Q: 对话中断后如何恢复？
A: 使用`/resume`命令，AI会自动加载所有上下文文件并显示摘要。

### Q: 如何回滚到之前的版本？
A: 使用`/rollback`命令，选择要恢复的快照版本。

### Q: 如何避免重复引用同一文献？
A: AI会自动检查`literature_index.json`中的DOI和标题，重复文献只更新`cited_in_sections`。

### Q: 如何处理Figure编号混乱？
A: AI会检测并提醒用户，但不会自动修正（防止遗漏），用户需手动确认。

## 版本信息

- **版本**: 1.0.0
- **创建日期**: 2024-01-27
- **适用领域**: 药物递送系统、纳米医学、生物材料
- **目标期刊**: Nature/Science/Cell及其子刊

## 联系方式

如有问题或建议，请通过OpenCode平台反馈。

---

**祝撰写顺利！**
