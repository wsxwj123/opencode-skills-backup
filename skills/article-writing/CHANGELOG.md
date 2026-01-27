# Changelog - Article Writing Skill

## [1.0.0] - 2024-01-27

### 🎉 初始发布

#### 核心功能
- ✅ 完整的Nature级SCI论文写作工作流
- ✅ 8个阶段的写作流程（初始化→预审→storyline→文献检索→撰写→质检→审稿模拟→合并）
- ✅ 12个全局命令系统
- ✅ 持久化记忆系统（3版本context_memory）
- ✅ 完整备份的版本控制（最多10个快照）
- ✅ 分阶段文献检索（Phase 1-3）
- ✅ 审稿人视角模拟（按递送系统分类）
- ✅ 质量控制系统（6项自动检查）

#### 文件结构
```
article-writing/
├── skill.md (1897行，主skill文件)
├── README.md (使用说明)
├── USAGE_GUIDE.md (完整示例)
├── QUICK_REFERENCE.md (快速参考)
├── templates/
│   ├── project_init.json (项目初始化模板)
│   ├── reviewer_concerns.json (审稿人质疑库，5种递送系统)
│   └── search_rules.json (文献检索规则)
└── scripts/ (预留Python脚本目录)
```

#### 核心约束
- **字数限制**: Abstract≤250, Intro 800-1500, Main 5000-7000
- **文献时间窗口**: 背景≤2年，创新≤5年(IF>10)，机制≤10年
- **引用密度**: Introduction论点1-2篇/讨论3-4篇，Results不引用
- **Storyline原则**: Main仅直接证据，SI为间接证据
- **统计显著性**: 直接报告P值，不用*号

#### 特色设计
1. **选项B粒度storyline**: 精确到每段的论点、证据需求、文献状态
2. **三版本context_memory**: 防止误操作，可回溯2步
3. **完整快照备份**: 包含所有JSON、MD、figures/（使用硬链接优化空间）
4. **文献去重机制**: DOI+标题相似度双重检查
5. **AI味自动替换**: 主动替换黑名单词汇并告知用户
6. **数据冲突检测**: 自动识别Figure间的矛盾数据

#### 支持的递送系统
- Nanocarrier (纳米载体)
- Viral_Vector (病毒载体)
- Cell_Therapy (细胞治疗)
- Living_Bacteria (活菌递送)
- Exosome (外泌体)

#### 审稿人质疑库
预置了35+个潜在质疑点，按以下维度分类：
- 按递送系统类型（5类）
- 按实验类型（体内、体外、表征）
- 预防策略（可直接用于Discussion）

#### 文献检索策略
- **主力**: paper-search (PubMed, Google Scholar)
- **补充**: arxiv (预印本)
- **兜底**: tavily (仅概念澄清)
- **分级检索**: 5种强度（背景2篇→创新5篇）

#### 自动化功能
- 每完成小节自动：字数统计+质量检查+进度更新+快照
- 每次对话开始自动：加载8个核心文件+生成上下文摘要
- AI高频词自动替换（delve into→investigate等）
- Figure编号连续性检查（但不自动修正，需用户确认）

---

## 技术细节

### 依赖工具
- `paper-search_search_*` (PubMed, Google Scholar, bioRxiv等)
- `arxiv_search_papers` (arXiv预印本)
- `tavily_tavily-search` (概念澄清，备用)
- `pandoc_convert_contents` (Markdown→Word转换)
- `filesystem_*` (文件读写、目录管理)

### 数据结构
- `storyline.json`: 嵌套字典，支持多层级（Introduction→para_1→claim）
- `literature_index.json`: 数组，每篇文献含13个字段
- `figures_database.json`: 数组，每个Figure含12个字段
- `context_memory.md`: Markdown格式，人类可读

### 性能优化
- 使用硬链接避免figures/重复占用空间
- 快照限制10个，循环覆盖最旧的
- DOI验证使用交叉检查，避免重复调用API

---

## 已知限制

### 当前版本不支持
1. ❌ 自动Figure重编号（需用户手动确认）
2. ❌ 直接编辑Word格式（输出为通用格式，需手动调整）
3. ❌ 自动生成Graphical Abstract
4. ❌ Cover Letter撰写
5. ❌ Highlights提取

### 计划在未来版本支持
- [ ] 自动生成期刊特定格式（Nature模板、Science模板）
- [ ] AI驱动的Graphical Abstract概念设计
- [ ] 基于storyline自动生成Highlights
- [ ] Cover Letter模板化生成
- [ ] 与参考文献管理软件集成（Zotero/EndNote）

---

## 用户反馈

### 期望改进方向
- 如有建议，请通过OpenCode平台反馈

---

## 维护信息

- **维护状态**: 积极维护
- **兼容性**: OpenCode v1.x
- **测试状态**: 初步测试通过
- **文档完整性**: 100% (skill.md + README + USAGE_GUIDE + QUICK_REFERENCE)

---

## 致谢

感谢用户提供详细的需求和反馈，使本skill能够精确满足Nature级论文写作的复杂需求。

---

**下一个版本预计功能**：
- Python脚本：自动合并Markdown文件
- 期刊投稿清单生成器
- 更多递送系统的审稿人质疑库
