# Changelog - Article Writing Skill

## [2.11.0] - 2026-01-30

### 🛡️ 检索健壮性升级

#### 核心变更
- **Abstract Recovery Protocol (摘要补全协议)**: 针对检索结果中摘要缺失的情况，建立了强制性的三级回退机制。
  - **Mandatory Chain**: Google Scholar (Primary) > Semantic Scholar > Tavily。
  - **Strict Policy**: 严禁因摘要缺失直接丢弃相关性高的文献，必须跑完上述补全流程。仅当所有工具失效时才允许标记为 Missing。

## [2.10.0] - 2026-01-30

### 🤖 自动化与输出净化

#### 核心变更
- **State Manager Automation**: 引入 `scripts/state_manager.py`，实现跨平台、标准化的状态加载与原子化更新，彻底告别手动读写多个状态文件的繁琐。
- **Clean Output Protocol**: 强制 `[Context Check]` 块仅作为内部验证日志，**严禁**出现在用户最终回复中，提供沉浸式的无干扰交互体验。
- **Version Compatibility**: 脚本内置 `context_memory.md` 的版本轮转逻辑 (v-1, v-2)，确保历史回溯功能的稳定性。

## [2.9.0] - 2024-01-30

### 📏 引用规范与上下文强化

#### 核心变更
- **Strict Citation Format**: 强制正文引用使用 `[n]` 格式，严禁其他变体。在每个小节末尾自动附上该节引用的参考文献列表（Vancouver style）。
- **Mandatory Context Read**: 强化了上下文检查协议，明确要求在每次回复前读取所有 5 个核心文件（含 `writing_progress.json`）。
- **Final Enforcement**: 将引用格式规则加入到最高优先级的系统执行指令中。

---

## [2.8.0] - 2024-01-30

### 🔄 全局状态持久化 (Continuity Upgrade)

#### 核心变更
- **Global Context Persistence**: 强制在**每次回复结束前**自动更新 `context_memory.md`。无论是在进行问答、头脑风暴还是写作，当前的对话状态、决策和待办事项都会被实时保存。
- **Auto-Snapshot Logic**: 智能快照现在会监控 `context_memory.md` 的实质性变更，确保在对话中断后能无缝恢复到最新状态。

---

## [2.7.0] - 2024-01-29

### 🚫 去除 AI 味关键升级

#### 核心变更
- **NO BULLET POINTS POLICY (段落式写作强制令)**:
  - 明确禁止在正文（Abstract, Intro, Results, Discussion）中使用列点符号。
  - 强制要求使用逻辑连接词（Furthermore, Consequently）将观点串联成连贯段落，模拟真人科学家的写作习惯。
- **Final System Enforcement**:
  - 在 Skill 末尾增加了最高优先级的执行指令，再次强调"强制交互版块"（反向拷问/你可能想知道）和"禁止列点"规则，防止 LLM 在长上下文中遗忘。

---

## [2.6.0] - 2024-01-29

### 💬 交互深度恢复

#### 核心变更
- **强制交互版块恢复**: 在 v2.x 迭代中遗漏的 "反向拷问" 和 "你可能想知道" 版块已重新实装为强制输出协议。
- **Reverse Interrogation**: 每次回复都必须挑战用户的假设或指出盲点。
- **Proactive Suggestions**: 每次回复都必须预测用户的下一步需求。

---

## [2.5.0] - 2024-01-29

### 🛡️ 逻辑完整性升级 (SI重构)

#### 核心变更
- **SI 认知重构**: 明确定义 SI 为 "Integral Evidence Chain" (完整证据链) 而非单纯的防御工具。Main Text 展示"结果与意义"，SI 展示"确信度与过程细节"。
- **Context-Aware SI 建议**: 废除机械的药剂学套路提问。AI 必须基于当前小节的具体逻辑断点（Logical Gap），主动分析缺失的中间证据（如阴性对照、优化过程、方法验证），并据此提出精准的 SI 建议。

---

## [2.4.0] - 2024-01-29

### 🛡️ 逻辑完整性升级

#### 核心变更
- **SI 主动建议与整合回路 (SI Proactive Loop)**:
  - 在撰写 Results 小节时，AI 不再是一次性输出。
  - **Reflect**: 完成初稿后，AI 必须基于药剂学专业知识，主动反思"需要什么补充证据？"（如处方筛选、稳定性、阴性对照）。
  - **Propose**: 向用户建议具体的 SI 列表。
  - **Integrate**: 获得用户反馈后，自动重写该小节，将 SI 引用（如 `Figure S1`）自然融入论证逻辑，形成最终版。

---

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
