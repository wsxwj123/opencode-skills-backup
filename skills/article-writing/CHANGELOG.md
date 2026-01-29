# Changelog - Article Writing Skill

## [2.3.0] - 2024-01-29

### 🛡️ 逻辑熔断与检索优化

#### 核心变更
- **数据依赖熔断 (Hard Stop)**: 在撰写 Results/Discussion 章节前，强制检查 Figure 数据的完整性。若数据状态为 `pending`，AI 必须立即停止并请求数据，严禁编造或使用占位符。
- **文献检索优先级调整**:
  - **Primary**: PubMed (医学/药剂学首选)
  - **Secondary**: Semantic Scholar (速度/广度) + bioRxiv (预印本)
  - **Fallback**: Google Scholar (仅作补充)
  - **Forbidden**: Tavily (禁止用于学术检索)

---

## [2.2.0] - 2024-01-29

### 🛡️ 安全与规范升级

#### 核心变更
- **原子化文件管理**: 强制执行"一小节一文件"策略（如 `04_Results_3.1_Characterization.md`），彻底解决大文件覆盖导致的数据丢失问题。
- **写入安全协议**: 在执行 `write_file` 前必须先读取旧文件比对差异，若存在覆盖风险，自动创建 `.bak` 备份。
- **严格工具纪律**: 明确锁定文献检索工具优先级。
  - **Primary**: `paper-search` (PubMed/Scholar), `arxiv` (Preprints).
  - **Forbidden**: 禁止使用 `tavily` 检索学术引用（仅限宽泛概念查询）。

---

## [2.1.0] - 2024-01-28

### 🎉 核心升级

#### 生态兼容
- **BibTeX 导出**: 新增 `/export_bib` 命令，支持将 `literature_index.json` 导出为 `references.bib`，方便导入 Zotero/EndNote。
- **本地脚本实装**: 提供了 `scripts/export_bibtex.py` 和 `scripts/merge_manuscript.py`，支持脱离对话环境的自动化操作。

#### 写作质量
- **自我修正回路**: 在 `/write` 命令中植入 "Draft -> Critique -> Polish" 隐式思维链。AI 在输出前必须进行自我反思和润色，确保语言简练且逻辑严密。

---

## [2.0.0] - 2024-01-28

### 🔥 重大重构

#### 核心逻辑
- **Results & Discussion 融合**: 废弃独立 Discussion 章节。采用"数据呈现 -> 即时讨论 (机制/对比/意义)"的融合写作模式。
- **智能快照系统**: AI 主动判断快照时机（生成内容/关键决策/新数据），而非僵化触发。
- **上下文显式验证**: 强制检查并汇报历史文件（Storyline, Literature, Figures）的读取状态，杜绝幻觉。
- **弹性写作深度**: 引入 "Key Section" vs "Supporting Section" 概念。核心论点强制深度展开 (>200词)，次要数据简洁陈述。

#### 文件变更
- 更新 `storyline.json` 结构以支持融合章节。
- 重写 `skill.md` 以反映新的交互协议。

---

## [1.0.0] - 2024-01-27

### 🎉 初始发布

#### 核心功能
- ✅ 完整的Nature级SCI论文写作工作流
- ✅ 8个阶段的写作流程
- ✅ 12个全局命令系统
- ✅ 持久化记忆系统（3版本context_memory）
- ✅ 完整备份的版本控制
- ✅ 分阶段文献检索
- ✅ 审稿人视角模拟
- ✅ 质量控制系统
