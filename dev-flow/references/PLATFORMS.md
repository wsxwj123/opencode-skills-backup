# 跨平台适配（Claude Code / OpenCode / Codex）

dev-flow 的流程骨架平台无关，只有怎么派子代理、用哪个模型、怎么强制入口是平台专有写法。读到 SKILL.md 或阶段文件里的 Claude 术语，按本表换算。

## 派独立子代理：三平台都原生支持

角色隔离靠派独立子代理、只给它文件路径和任务、不让它看会话历史。三家都有，不需要降级。

| 能力 | Claude Code | OpenCode | Codex |
|---|---|---|---|
| 派独立子代理 | Agent/Task 工具，`subagent_type`+`model`+`run_in_background` | 原生 subagent，独立 child session 上下文隔离；@提及 / task 工具 | 原生 subagent，独立线程隔离、可并行（`max_threads` 默认6） |
| 子代理定义位置 | `.claude/agents/*.md`（也可临时写 prompt，dev-flow 就是临时写） | config 或 markdown agent | `~/.codex/agents/*.toml` 或 `.codex/agents/*.toml` |
| 只读子代理（做物理隔离用） | `Explore` 类型 | 只读 subagent / `permission: deny` | `sandbox_mode = read-only` |

> dev-flow 派子代理默认临时写 prompt 加传文件路径，不依赖 agents 目录，禁令写在 references 里，跨平台通用。本机装了对应具名 agent 的，按下面"本机增强"用 `subagent_type` 派，可选加速，不改流程。

## 续用子代理：同角色多轮循环别重派

改自己活的接着用，做检查的每轮换新的。打回重修、方案修订续用原代理（上下文还在，省一轮重读）。审查、测试设计、裁判、模块测试、安全审计每轮新开（裁判上下文里留着上轮失败堆栈的实现细节，续用等于绕过白名单；续用的审查员只核对旧意见。它们输入都是几份短文件，重开便宜）。跨角色唤醒（方案代理去当审查、开发代理去当裁判）一律禁止。续用消息开头原样重贴本阶段的逐字禁令（`tests/acceptance/` 只读等）。轻档同样：开发代理打回时续用，测试代理和裁判每轮新开；裁判只读，可用 code-reviewer 派。

| | Claude Code | OpenCode | Codex |
|---|---|---|---|
| 续话机制（仅作者角色用） | 派时命名，`SendMessage({to: 名字})` 续话，同一主会话内有效 | 未核实（child session 理论上可续） | 未核实（thread 理论上可 resume） |
| 不可用时 | 跨会话代理已不在 → 重派 | 未核实前一律回退：重派 + 结构化交接文件 | 同左 |

跨会话续接靠文件交接（PROJECT.md、PLAN.md）。

## 模型映射（SKILL.md 铁律5 的"高推理/高性价比"具体填谁）

| 角色用途 | 抽象 | Claude Code | OpenCode | Codex |
|---|---|---|---|---|
| 调研/方案/审查/测试设计/裁判/安全审计 | 高推理 | opus（默认）；用户要最强时 fable | 配置里最强推理模型 | gpt-5.6 系列高推理档 |
| 代码撰写（04 Step 0 问用户选；轻档沿用项目已选的，没选过的默认 opus） | 高推理 | opus 或 fable（fable 更强也更耗额度） | 对应两档 | 对应两档 |
| 接口同步、文档回写、代码地图、机械性改动（不含修测试夹具，那是测试设计代理的活） | 高性价比 | sonnet | 配置里便宜档 | 便宜档 |

> 流程里不写具体版本号（模型会换代），只用高推理、高性价比两个档位词，映射只维护在本表。本表只分模型档，不写思考强度。

## 本机增强：复用已装的具名 agent（可选，仅 Claude Code）

装了对应 agent 就用 `subagent_type` 派（省写人设，白拿只读隔离和 opus 默认）；没装就临时写 prompt，流程不变。`~/.claude/agents/` 里有对应角色的：

| dev-flow 角色 | subagent_type | 白拿的好处 |
|---|---|---|
| 02 调研·外部文档/GitHub | librarian | 带 WebSearch/WebFetch/context7 |
| 02 调研·本仓库定位 | explorer | 代码检索定位 |
| 02 出方案 | oracle | 架构决策/技术顾问 |
| 02 方案盲审·架构层 / 架构审查（可选那步） | architect-reviewer | 只有 Read/Bash（无 Write）＝物理只读隔离；自带 opus |
| 03 测试设计 | test-automator | 定义里就写着"黑盒只依据接口约定、不看实现"，正好是 03 的隔离要求 |
| 04 开发·后端/脚本 | backend-developer | 照方案写、自带单测 |
| 04 开发·前端 | designer | UI/UX 专项 |
| 04 快速小改 / 打回修 | fixer | 快速实现 |
| 05 代码审查 / 终判裁判 | code-reviewer | 只有 Read/Bash（无 Write）＝物理只读隔离；四维盲审；自带 opus |

`subagent_type` 只换人设、工具、模型，不替代隔离纪律：每次派或续话仍要注入本阶段的逐字禁令（文件交接路径、"隔壁同事做的"、`tests/acceptance/` 只读、《数据与指令隔离声明》），agent 定义里都没有。`architect-reviewer`、`code-reviewer` 没有 Edit/Write，但带 Bash，不算物理隔离。没有专用 security agent，05.5 用 `code-reviewer` 或临时 prompt。

## 技能触发 + 安装路径

| | Claude Code | OpenCode | Codex |
|---|---|---|---|
| 触发 | description 自动加载 / `/skill` | description 自动（**直接读 `~/.claude/skills/`**）/ @提及 | description 自动 / `$SkillName` 显式 |
| 安装路径 | `~/.claude/skills/` | 自己的 skills 目录 **＋兼容读 `~/.claude/skills/`、`~/.agents/skills/`** | `~/.codex/skills/`、`~/.agents/skills/`（**不读 `~/.claude/skills/`**） |

一份源三家可见：dev-flow 放 `~/.agents/skills/`（OpenCode、Codex 都读），`~/.claude/skills/dev-flow` 软链过去。

## 强制入口（每次注入"开发任务先走 dev-flow"提醒）

| 平台 | 做法 | 强度 |
|---|---|---|
| Claude Code | settings.json 的 `UserPromptSubmit` hook（GitHub 仓根目录 hooks/dev-flow-reminder.sh） | 硬（不经模型记忆） |
| OpenCode | 全局 `AGENTS.md` 写"开发任务先调 dev-flow"（它也兼容读 `~/.claude/CLAUDE.md`，现有指令自动生效） | 软（靠模型自觉），插件系统能否每次注入未确认 |
| Codex | config.toml `[hooks]` 或 `~/.codex/hooks.json` 配 `UserPromptSubmit` **命令型** hook（跑脚本打印提醒）；`AGENTS.md` 作后备 | 硬（注意：Codex 只有命令型 hook 真执行，prompt 型会被跳过） |

## 计划确认（卡点1 让用户看方案）

| 平台 | 做法 |
|---|---|
| Claude Code | ExitPlanMode 出计划卡片（plan 模式）；非 plan 模式提醒查看 PLAN.md |
| OpenCode | Plan 主 agent（受限、改动询问）；或纯文字停下等确认 + 提醒看 PLAN.md |
| Codex | 审批模式（approval modes）；或纯文字停下 + 提醒看 PLAN.md |

> 卡点本质是停下等用户确认，任何平台都成立，计划卡片只是锦上添花。

## 危险操作红线的配置文件对应

rules.md 红线里的关键配置：Claude Code 是 settings.json，OpenCode 是 `opencode.json`，Codex 是 `config.toml`，未经确认不动。

## 子代理降级路径（三平台当前用不到）

平台不支持独立子代理时：
- 首选：同一会话内分角色顺序执行，换角色前清理上下文、只重读交接文件（INTERFACE.md、PLAN.md）。这是最弱隔离，模型见过它要盲审的方案。
- 次选：请用户手动开新会话扮演审查或裁判，只贴交接文件。隔离最真，但靠用户配合。
