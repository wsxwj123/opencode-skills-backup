# 去 AI 化写作协议 (Anti-AI Protocol)

> 被 SKILL.md 的 Role 区与 **Phase 8 (`/write`)、Phase 10 (`/check`)** 引用。
> **每次撰写或润色英文正文段落前必须 `Read` 本文件**；`/check` 跑 `style_checker.py` 作为客观兜底。
> 本协议自包含；`humanizer-zh` skill 若已装可作辅助参考但非强制依赖。

## 目标读者画像

以美国 STEM 博士研究生（PhD candidate）日常阅读、自然书写的水平为基准——朴素、平实、信息密度优先；笔触受 Nature 资深编辑把关（Role 设定不变），但**克制使用编辑级精炼修辞**，避免炫技。

## 禁词表 (The "Stop" List)

完整清单以 `scripts/style_checker.py` 的 `FORBIDDEN_EXACT` 为准（约 30 词，写作前可 `grep FORBIDDEN_EXACT scripts/style_checker.py` 查全），下方为高频代表：
- 严禁词："delve into", "comprehensive landscape", "pivotal role", "realm", "tapestry", "underscore", "testament", "elucidate", "unveil", "pronounced", "substantial"。
- 首句套话："It is well known", "It is worth noting", "Interestingly", "Remarkably", "In recent years"。
- 严禁结构：三段式排比 ("seamless, intuitive, and powerful")、虚假范围 ("from X to Y")、否定式排比 ("not only... but also...")。

## 🔴 禁修辞 (No Rhetorical Devices)

严禁文学性修辞——隐喻、拟人、明喻、夸张、对偶、设问、引经据典等。例外：领域内已固化的术语隐喻（如 "molecular switch"、"signaling cascade"）保留；新造的、装饰性的修辞一律删。

## 🔴 禁生僻词 (No Obscure Vocabulary)

- 通用动词/形容词用平实词：用 `show / find / use / large / small`，不用 `elucidate / unveil / pronounced / substantial`；用 `cause / lead to`，不用 `precipitate / engender`。
- 例外保留：领域专业术语（如 `apoptosis / pharmacokinetics`）不算生僻，必须用准确术语。
- 判定原则：能用一个 GRE 范围内的常见词替代且不丢精度的，就替换。

## 🔴 禁造词 (No Neologisms)

严禁拼接新词或自造缩略——所有词、所有缩写必须能在权威词典 / 领域教科书 / 已发表文献中找到原型。首次出现的缩写必须给全称（如 "extracellular vesicles (EVs)"）。AI 凭语感造的新组合词（"transformomics"、"diseasability" 之类）一律删。

## 🔴 禁长难句 (No Long/Complex Sentences)

- **硬上限：单句 ≤ 30 词**（含从句）。超过即拆。
- **从句深度 ≤ 2 层**——禁止"主句套定语从句套状语从句"三层嵌套。
- 一句话只承担一个核心论点，复合论点拆成两句。

## 🔴 被动为主 (Passive Voice as Primary)

- **段落整体被动占比 50–70%**（SCI Article 实验描述主流）。
- Methods / Results 描述实验操作与观察 → **优先被动**（"Cells were treated with..."、"Apoptosis was assessed by..."）。
- Discussion 表达作者推断 / 主观判断 → 可适当主动（"We propose..."、"These data suggest..."），但仍以被动为主。
- 被动 < 40% 视为过于口语化；> 70% 视为冗余呆板，均扣分。

## 写作范式

- **数据驱动 (Data-First)**：用数据说话，拒绝 "significant effect" 这种空话，必须写 "5-fold increase (P<0.001)"。
- **No Bullet Points**：正文严禁列点，必须写成连贯段落。

## 句长节奏

- 同段落内混合**短句（≤12 词）**与**中句（15-25 词）**——不要求 25-40 词的长句（与"禁长难句"统一）。
- 严禁连续 3 句以上句长相近（差异 < 5 词）——避免 AI 式齐整。
- 同一概念在同段落不重复同表述，用同义替换或结构重组。
- 改写后段落长度控制在原文 ±15% 以内。
- 连续段落首句禁用相同句式（如连续 "This study..."、"The results..."、"We found..."）。

## 深度改写策略 (Anti-Similarity Protocol)

- **词汇层 (Lexical)**：术语不动；术语周围的非术语通用词降到 PhD 平实层（如 `significant → clear/large`，不再升级为 `pronounced/marked/substantial`——那是编辑级修饰，违反目标读者画像）。禁止直接使用原始文献完整短语（≥4 连续词），必须拆解重构。
- **句法层 (Syntactic)**：被动为主；将因果从句拆为独立句而非套层从句。禁止模板化过渡（"Furthermore"、"In addition"、"Moreover"），改用逻辑内嵌或自然连接（"Because..."、"This in turn..."）。
- **结构层 (Structural)**：允许调整段内论点顺序（不破逻辑链）；可适度插入作者推断句（"This likely reflects..."、"One plausible explanation is..."）模拟真人推理痕迹。

## 自我审查

输出任何段落前，必须运行自检（句长 / 句长方差 / 段首重复 / 被动占比 / 是否含修辞、生僻词、造词）；`/check` 阶段跑 `style_checker.py` 量化打分作为客观兜底。

## 学科语感适配（可选）

如当前研究方向的 `configs/*.json` 含 `writing_style` 字段（目前 `drug_delivery` / `computer_science` 有），写作时优先读取并遵循其语态偏好、推荐/避免动词、过渡短语和句长范围；**未配置该字段时使用本协议通用规则即可，不报错**——本协议已自给自足。
