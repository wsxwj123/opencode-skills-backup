# teacher-paper 状态（接续点）

**当前 v3.32.1** · darwin **86**（opus 盲评，2026-06-22）· 回归 **182/182** · 仓库 wsxwj123/opencode-skills-backup main

> 旧文档 `PLAN-2026-06-15-v3.16-全面修复.md` / `SESSION-2026-06-15-全记录.md` 是 v3.16 时代历史，仅供追溯。本文件为当前权威态。

## 版本演进（v3.21 → v3.31）

| 版本 | 主题 | 关键 |
|------|------|------|
| v3.21.0 | Batch6 darwin 反馈 | 听力稿位置/手抄凭证/Phase3.5机器化/allow审计 |
| v3.22.0 | 物理出卷反馈 P0+P1 | figure显式门禁/答案去重/干扰项同质/卷头常数/数值规约 |
| v3.23.0 | P2 系列 | 难度锚定表/理科preset题量范围/考点前缀聚合/物理量合理性 |
| v3.24.0 | 全科9路实测 R1-R5 | 题目去重根因/手抄凭证溯源/列表dict校验/figure健壮性/占位率warn |
| v3.25.0 | 终审门禁 Phase 3.8 | 合并排版后整卷对账（题号/答案越界/标题层级/解析缺失） |
| v3.26.0 | git+盲检+环境扫描 | 工程自动git/逐题commit/独立子代理盲检Phase3.9/setup扫git |
| v3.27.0 | 回滚协议精确化 | 定点修复vs单题回滚区分/禁用reset --hard |
| v3.31.0 | 排版铁律+上下标渲染 | 「排版铁律」分工表(①版式②上下标③全半角④标记)；lint 补半角标点/全角字母/斜体非乘法/化学式CJK边界修复/裸下标漏花括号；make_paper `_split_subsup` 真富文本上下标(解决 F_合/v_max 硬伤) |
| **v3.32.0** | **git门禁+告警落盘+题级检查集成修复** | **git 逐题存档升为硬门禁(items/未提交→exit2，`--allow-uncommitted` 逃生，无git/嵌套父库不触发)；所有 warn 落盘 `build/校验告警.md`(含「排版自检」分节)；🔴修集成bug：题级检查(排版/缺图/英语引号)原挂在 `is_question=meta.score!=None` 后，最小格式 score 不在 meta→静默全跳过，改为按 paper 块有无 question/stem 判定(`_atom_has_question`)，并修 `total+=float(m["score"])` 的 KeyError。单测全绿曾掩盖此缺口(测试直调函数绕过门控)，已加 Z6-Z9+opus端到端兜底** |
| **v3.32.1** | **格式文档统一** | **SKILL.md「原子题最小格式」原是扁平 schema(`id/type/body/options/score` 顶层)，assemble.py 只认块格式(`paper[]/answer[]/meta`)无扁平转换→照旧文档写题产不出内容；改写为块格式示例并标注 num/score 在 meta。make_paper.py 顶部 block 注释字体改对(黑体→宋体，对齐 render() 与 formatting-rules.md)。真跑 build 验证文档=代码** |

## 三层自检架构（核心资产）

| 层 | Phase | 性质 | 查什么 | 产物 |
|----|-------|------|--------|------|
| 1 | 3.5 | 机器规则 | 命题质量：考点重复/难度梯度/题干长度/干扰项同质/同源考点/物理量 | `Phase3.5_自审表.md` |
| 2 | 3.8 | 机器规则 | 整卷结构：题号对账/客观题答案越界/标题层级/解析缺失 | `终审表.md` |
| 3 | 3.9 | 独立子代理 | 内容正确性：答案对错/解析推理/材料断章/难度名实（机器查不了） | 子代理回报 |

> 实测验证：埋"答案错+解析矛盾"卷，机器两层全绿放行，子代理盲检抓出 67% 错误率——三层缺一不可。

## 门禁与开关

- **硬门禁 exit2**：完整性/溯源/忠实节选/措辞/缺图/figure显式声明/时政时效/字数/终审对账（答案越界·残卷）/**git逐题存档（items未提交→拒绝出卷）**
- **软提醒 warn（不阻断，落盘 `build/校验告警.md`）**：排版字符 `_check_typography`（markdown标记/中文半角标点/全角字母数字/斜体非乘法/理科上下标ASCII/裸下标漏花括号）、英语全角引号、考点重复、难度梯度、干扰项同质等
- **9 个 `--allow-*` 降级开关**：unsourced/missing-figure/length/incomplete/wording/excerpt/stale/final-audit/**uncommitted**，多开关聚合审计
- **工程版本管理**：init 自动 `git init`+首次commit；每题 `assemble.py commit`（**build 硬门禁强制**）；单题回滚 `git checkout [HEAD~1] -- items/NN.json`（禁用 reset --hard）；无 git/嵌套父库则门禁不触发

## 排版契约（v3.31 核心，写 items JSON 必守）

| 维度 | 谁负责 | AI 必守 |
|------|--------|---------|
| 居中/层级/字体/字号/行距 | make_paper 按 block 自动 | 选对 block(section/sub/question/material)，禁手设字体/空格居中/空行撑距 |
| 上下标 | 简单 Unicode / 复杂 `_{}`/`^{}` | H₂O/x² 用 Unicode；F_{合}/v_{max} 多字符中文下标用 `_{}`/`^{}` 脚本渲染 |
| 全半角 | AI 写文本 | 中文标点全角、英文/英语题/数字半角、不夹全角字母数字 |
| 富文本标记 | 渲染器只认 `_{}`/`^{}` | 禁 `**`/`*`/`~~`/`#`/`[](url)`/`<i>`；无斜体；乘号用 × |

## 待办（按优先级，darwin v3.27 评估提出）

| 优先级 | 待办 | 来源 |
|--------|------|------|
| 🔴 P0 真bug | blueprint 解析失败静默降级——用户给样卷却默默换通用骨架（assemble.py `_resolve_blueprint`），应升 STOP/AskUserQuestion | darwin 短板1 |
| 🟡 P1 | 科目文档路由依赖 AI 自律读 references/subjects，无 build 前门禁验证"是否已读" | darwin 短板2 |
| 🟡 P1 | 英语引号规则歧义——写入端无兜底，仅 H1 门禁对已生成文件查错 | darwin 短板3 |
| 🟢 P2 | `_CHEM_RE` 仍是保守白名单（含数字下标式约30个），生僻式漏报；通用模式 `[A-Z][a-z]?\d+` 因 A4/x1 误报风险未采用 | v3.31 opus 评估 |
| 🟢 P3 深水区 | block_len 按学段自动分级（小学散文被卡九年级区间）/ 连线题型 `type:matching` / 化学方程式配平校验 / figure 题组共享（一图带多题）/ 选项分布均衡 | 9路实测 |

## 回滚 tag 链

`v3.23.0-pre-r-series` → `v3.24.0-pre-final-audit` → `v3.25.0-pre-git` → 各版本发布 tag v3.21.0~v3.27.0（v3.31 未打 tag，父仓库未提交）
