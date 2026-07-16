# 跨平台适配（Claude Code / OpenCode / Codex）

dev-flow 的流程骨架平台无关，只有几处"怎么派子代理、用哪个模型、怎么强制入口"是平台专有写法。读到 SKILL.md 或阶段文件里的 Claude 术语时，按本表换算。

## 命脉确认：派独立子代理，三平台都原生支持

角色隔离（出方案≠挑毛病≠判定）靠"派独立子代理、给它文件路径和任务、不让它看会话历史"实现。这个能力三家都有，**不需要降级**。

| 能力 | Claude Code | OpenCode | Codex |
|---|---|---|---|
| 派独立子代理 | Agent/Task 工具，`subagent_type`+`model`+`run_in_background` | 原生 subagent，独立 child session 上下文隔离；@提及 / task 工具 | 原生 subagent，独立线程隔离、可并行（`max_threads` 默认6） |
| 子代理定义位置 | `.claude/agents/*.md`（也可临时写 prompt，dev-flow 就是临时写） | config 或 markdown agent | `~/.codex/agents/*.toml` 或 `.codex/agents/*.toml` |
| 只读子代理（做物理隔离用） | `Explore` 类型 | 只读 subagent / `permission: deny` | `sandbox_mode = read-only` |

> dev-flow 派子代理是"临时写 prompt + 传文件路径"，不读 agents 目录——所以强提示词是写在 references 里（02/03/04 的清单），跨平台天然通用。

## 模型映射（SKILL.md 铁律5 的"高推理/高性价比"具体填谁）

| 角色用途 | 抽象 | Claude Code | OpenCode | Codex |
|---|---|---|---|---|
| 调研/方案/审查/测试设计/裁判/安全审计 | 高推理模型 | opus（claude-opus-4-8） | 配置里最强推理模型 | gpt-5.6 系列高推理档 |
| 代码撰写（开发阶段问用户选） | 高推理 或 高性价比 | opus 或 fable | 对应两档 | 对应两档 |

> 别把具体版本号写死进流程（模型会换代）——用"高推理/高性价比"这两个角色词，具体映射只维护在本表。

## 技能触发 + 安装路径

| | Claude Code | OpenCode | Codex |
|---|---|---|---|
| 触发 | description 自动加载 / `/skill` | description 自动（**直接读 `~/.claude/skills/`**）/ @提及 | description 自动 / `$SkillName` 显式 |
| 安装路径 | `~/.claude/skills/` | 自己的 skills 目录 **＋兼容读 `~/.claude/skills/`、`~/.agents/skills/`** | `~/.codex/skills/`、`~/.agents/skills/`（**不读 `~/.claude/skills/`**） |

**一份源、三家可见的省事做法**：把 dev-flow 放 `~/.agents/skills/`（OpenCode、Codex 都读），再从 `~/.claude/skills/dev-flow` 软链过去。OpenCode 现状放着不动就能读 `~/.claude/skills/`。

## 强制入口（每次注入"开发任务先走 dev-flow"提醒）

| 平台 | 做法 | 强度 |
|---|---|---|
| Claude Code | settings.json 的 `UserPromptSubmit` hook（本仓库 hooks/dev-flow-reminder.sh） | 硬（不经模型记忆） |
| OpenCode | 全局 `AGENTS.md` 写"开发任务先调 dev-flow"（它也兼容读 `~/.claude/CLAUDE.md`，现有指令自动生效） | 软（靠模型自觉）——插件系统能否每次注入未确认 |
| Codex | config.toml `[hooks]` 或 `~/.codex/hooks.json` 配 `UserPromptSubmit` **命令型** hook（跑脚本打印提醒）；`AGENTS.md` 兜底 | 硬（注意：Codex 只有命令型 hook 真执行，prompt 型会被跳过） |

## 计划确认（卡点1 让用户看方案）

| 平台 | 做法 |
|---|---|
| Claude Code | ExitPlanMode 出计划卡片（plan 模式）；非 plan 模式提醒查看 PLAN.md |
| OpenCode | Plan 主 agent（受限、改动询问）；或纯文字停下等确认 + 提醒看 PLAN.md |
| Codex | 审批模式（approval modes）；或纯文字停下 + 提醒看 PLAN.md |

> 卡点本质是"停下等用户确认"这个纯文字行为，任何平台都成立。计划卡片只是锦上添花。

## 危险操作红线的配置文件对应

rules.md 🔴 红线里"改 settings.json"是 Claude 专属——OpenCode 对应 `opencode.json`、Codex 对应 `config.toml`，同样未经确认不许乱动。

## 子代理降级路径（三平台当前用不到，为未来弱平台兜底）

万一某平台不支持独立子代理：
- **首选降级**：同一会话内分角色顺序执行，每换角色前显式清理上下文、只重读交接文件（INTERFACE.md/PLAN.md）。**诚实标注**：这是最弱隔离——模型其实见过它要盲审的方案，"自己判自己"的风险回来了，只有文件交接能部分挽救。
- **次选降级**：要求用户手动开新会话扮演审查/裁判角色，只把交接文件贴进去。隔离最真，但打断体验、靠用户配合。
