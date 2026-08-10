# 跨平台适配（Claude Code / OpenCode / Codex）

> **同源提醒**：本文件与 dev-flow 的 `references/PLATFORMS.md` 同源，只留 task-flow 用得到的部分（派子代理、模型映射、计划确认工具映射）。dev-flow 那份更新映射时，检查本文件要不要同步——靠这行文件头互相提醒，没有硬引用。
> task-flow 的流程骨架平台无关，只有"怎么派子代理、用哪个模型、怎么让用户确认计划"是平台专有写法。读到 SKILL.md 或 reference 里的 Claude 术语时，按本表换算。

## 命脉确认：派独立子代理，三平台都原生支持

角色隔离（补遗、独立验收盲评、红队攻防、fan-out 并行）靠"派独立子代理、给它文件路径和任务、不让它看会话历史"实现。这个能力三家都有，**不需要降级**。

| 能力 | Claude Code | OpenCode | Codex |
|---|---|---|---|
| 派独立子代理 | Agent/Task 工具，`subagent_type`+`model`+`run_in_background` | 原生 subagent，独立 child session 上下文隔离 | 原生 subagent，独立线程隔离、可并行（`max_threads` 默认 6） |
| 只读子代理（做物理隔离用，如独立验收盲评） | `Explore` 类型（无 Edit/Write） | 只读 subagent / `permission: deny` | `sandbox_mode = read-only` |

> task-flow 派子代理是"临时写 prompt + 传文件路径"，逐字 prompt 写在 reference 里（补遗在 01、盲评+终判在 02、红队在 03），跨平台天然通用。

## 模型映射（"高推理 / 高性价比"具体填谁）

| 角色用途 | 抽象 | Claude Code | OpenCode | Codex |
|---|---|---|---|---|
| 补遗、独立验收盲评、抽账终判、红队攻防 | 高推理模型 | opus（claude-opus-4-8） | 配置里最强推理模型 | gpt-5.6 系列高推理档 |
| 常规执行子代理（分析/整理，看额度选） | 高推理 或 高性价比 | opus 或 fable | 对应两档 | 对应两档 |

> 别把版本号写死进流程（模型会换代）——用"高推理/高性价比"这两个角色词，具体映射只维护在本表。

## 计划与合同确认（立项收尾让用户看 计划分节 + CHECKLIST）

| 平台 | 做法 |
|---|---|
| Claude Code | ExitPlanMode 出计划卡片（plan 模式）；非 plan 模式则停下、提醒用户看 `.taskflow/<任务>/PROJECT.md` 计划分节 和 `CHECKLIST.md` |
| OpenCode | Plan 主 agent；或纯文字停下等确认 + 提醒看 PROJECT.md 计划分节 / CHECKLIST.md |
| Codex | 审批模式（approval modes）；或纯文字停下 + 提醒看 PROJECT.md 计划分节 / CHECKLIST.md |

> 卡点本质是"停下等用户确认"这个纯文字行为，任何平台都成立。计划卡片只是锦上添花。

## 安装路径

| | Claude Code | OpenCode | Codex |
|---|---|---|---|
| 触发 | description 自动加载 / `/skill` | description 自动（直接读 `~/.claude/skills/`）/ @提及 | description 自动 / `$SkillName` 显式 |
| 安装 | `~/.claude/skills/task-flow/` | 自己的 skills 目录 ＋兼容读 `~/.claude/skills/` | `~/.codex/skills/`、`~/.agents/skills/`（不读 `~/.claude/skills/`） |

> task-flow 完全自包含：单独下载 `task-flow/` 文件夹就能用，不引用 dev-flow 任何文件。
