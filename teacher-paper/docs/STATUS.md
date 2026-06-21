# teacher-paper 状态（接续点）

**当前 v3.27.0** · darwin **88.0**（实测，2026-06-21）· 回归 **135/135** · 仓库 wsxwj123/opencode-skills-backup main

> 旧文档 `PLAN-2026-06-15-v3.16-全面修复.md` / `SESSION-2026-06-15-全记录.md` 是 v3.16 时代历史，仅供追溯。本文件为当前权威态。

## 版本演进（v3.21 → v3.27）

| 版本 | 主题 | 关键 |
|------|------|------|
| v3.21.0 | Batch6 darwin 反馈 | 听力稿位置/手抄凭证/Phase3.5机器化/allow审计 |
| v3.22.0 | 物理出卷反馈 P0+P1 | figure显式门禁/答案去重/干扰项同质/卷头常数/数值规约 |
| v3.23.0 | P2 系列 | 难度锚定表/理科preset题量范围/考点前缀聚合/物理量合理性 |
| v3.24.0 | 全科9路实测 R1-R5 | 题目去重根因/手抄凭证溯源/列表dict校验/figure健壮性/占位率warn |
| v3.25.0 | 终审门禁 Phase 3.8 | 合并排版后整卷对账（题号/答案越界/标题层级/解析缺失） |
| v3.26.0 | git+盲检+环境扫描 | 工程自动git/逐题commit/独立子代理盲检Phase3.9/setup扫git |
| v3.27.0 | 回滚协议精确化 | 定点修复vs单题回滚区分/禁用reset --hard |

## 三层自检架构（核心资产）

| 层 | Phase | 性质 | 查什么 | 产物 |
|----|-------|------|--------|------|
| 1 | 3.5 | 机器规则 | 命题质量：考点重复/难度梯度/题干长度/干扰项同质/同源考点/物理量 | `Phase3.5_自审表.md` |
| 2 | 3.8 | 机器规则 | 整卷结构：题号对账/客观题答案越界/标题层级/解析缺失 | `终审表.md` |
| 3 | 3.9 | 独立子代理 | 内容正确性：答案对错/解析推理/材料断章/难度名实（机器查不了） | 子代理回报 |

> 实测验证：埋"答案错+解析矛盾"卷，机器两层全绿放行，子代理盲检抓出 67% 错误率——三层缺一不可。

## 门禁与开关

- **硬门禁 exit2**：完整性/溯源/忠实节选/措辞/缺图/figure显式声明/时政时效/字数/终审对账（答案越界·残卷）
- **8 个 `--allow-*` 降级开关**：unsourced/missing-figure/length/incomplete/wording/excerpt/stale/final-audit，多开关聚合审计
- **工程版本管理**：init 自动 `git init`+首次commit；每题 `assemble.py commit`；单题回滚 `git checkout [HEAD~1] -- items/NN.json`（禁用 reset --hard）

## 待办（按优先级，darwin v3.27 评估提出）

| 优先级 | 待办 | 来源 |
|--------|------|------|
| 🔴 P0 真bug | blueprint 解析失败静默降级——用户给样卷却默默换通用骨架（assemble.py `_resolve_blueprint`），应升 STOP/AskUserQuestion | darwin 短板1 |
| 🟡 P1 | 科目文档路由依赖 AI 自律读 references/subjects，无 build 前门禁验证"是否已读" | darwin 短板2 |
| 🟡 P1 | 英语引号规则歧义——写入端无兜底，仅 H1 门禁对已生成文件查错 | darwin 短板3 |
| 🟢 P3 深水区 | block_len 按学段自动分级（小学散文被卡九年级区间）/ 连线题型 `type:matching` / 化学方程式配平校验 / figure 题组共享（一图带多题）/ 选项分布均衡 | 9路实测 |

## 回滚 tag 链

`v3.23.0-pre-r-series` → `v3.24.0-pre-final-audit` → `v3.25.0-pre-git` → 各版本发布 tag v3.21.0~v3.27.0
