---
name: academic-gate
description: 学术写作技能的结构签字物理门禁说明。本目录同时是一个 Claude Code 插件——放进 ~/.claude/skills/ 后重启一次，PreToolUse 钩子由 Claude Code 自动加载，拦截"未确认大纲就写正文"。当用户问门禁为什么拦我、怎么解锁、怎么确认结构签字、门禁没生效怎么办时使用。
---

# 学术写作结构签字门禁

## 这是什么

8 家学术写作技能（general-sci-writing / review-writing / nsfc-proposal / sci2doc / revise-sci / reviewer-response-sci / reviewer-simulator / polish-sci）共用的一道**物理门禁**：

> **用户没有明确确认大纲/storyline 之前，任何写入正文文件的操作都会被拦下。**

这不是提示词纪律，是 `PreToolUse` 钩子在工具层拦截——AI 想跳步也跳不过去。

## 🔴 为什么做成插件（本目录的存在理由）

**旧做法**：钩子由技能的 Phase 0 调 `install_gate_hook.py` 安装，写进 `~/.claude/settings.json`。

**旧做法的致命缺陷**：安装这一步**依赖 AI 真的去执行**。而这道门禁的作用恰恰是拦住"AI 想跳步"——**最需要它的场景（AI 跳过流程），恰恰是它不会被装上的场景**。这是循环依赖。

**现做法**：本目录带 `.claude-plugin/plugin.json`，Claude Code 启动时把它当 `academic-gate@skills-dir` 插件加载，**钩子由 Claude Code 自己装，全程不经过 AI**。

## 装法

把本目录放进 `~/.claude/skills/`，**重启一次 Claude Code**。验证：

```bash
claude plugin list        # 应出现 academic-gate@skills-dir
```

⚠️ 钩子在启动时加载，**无法热生效**——放进去当次会话仍然没有保护，重启后才有。

## 被拦住了怎么办

拦截信息形如：

```
[学术门禁]「structure_signoff」未通过：<项目根> 尚未落盘结构签字
```

**这说明流程被跳了，不是 bug。** 正确做法：

1. 回到对应技能的流程，把大纲/storyline 跟用户过一遍
2. **用户明确确认后**（且仅在此之后），运行该技能打印的 `SIGNOFF_CMD` 落盘签字
3. 再继续写正文

🔴 **严禁在用户未确认时自行运行 confirm** —— 那等于伪造用户签字。

## 门禁没生效怎么办

按顺序排查：

| 现象 | 原因 | 处置 |
|---|---|---|
| `claude plugin list` 里没有 `academic-gate@skills-dir` | 没重启，或目录不在 `~/.claude/skills/` 下 | 重启；确认目录位置 |
| 有插件但不拦 | `gate_registry.json` 里该技能 `signoff: false` | 查 registry，这可能是有意的 |
| Codex 里不拦 | Codex 也有这套钩子（事件名、配置结构、拦截 JSON 都一样），但**要按 Codex 的方式装、并且要你亲手点信任**：它读的是本目录的 `.codex-plugin/plugin.json`；装完必须在 Codex 里跑一次 `/hooks`，把这几条钩子逐条信任，**没信任的钩子会被直接跳过**（不报错） | 装好并信任后，真的学术写作项目（有状态文件的那种）在 Codex 上照拦不误。两件必知的事：<br>① **改过 `hooks/hooks.json` 之后信任会自动作废**——Codex 按钩子定义算一个 hash 记账，定义一变就当没信任过，得再跑一次 `/hooks`（改 `scripts/` 里的 Python 不影响）。<br>② **只是撞了名字的陌生项目，在 Codex 上不拦、只记一条审计**：别人目录里恰好有个 `sections/` 或 `state.json`，但没有我们技能的状态签名，这种情况在 Claude Code 上是弹一句"要不要按学术项目管"让你选，而 **Codex 的拦截框没有"允许一次"**——硬拦会把不相干的项目卡死，唯一出路是去停掉整个插件。所以那一档按放行处理，只在审计里留一条记录。 |
| OpenCode 里不拦 | **OpenCode 只认它自己的 JS 插件，从来不读这套钩子配置** | 已知限制，不是回归：那端只有技能能用，门禁在那边不存在 |
| 拦截理由显示两次 | 插件钩子 + 旧的自装钩子并存 | 无害（两条指向同一份逻辑、不会误放行）；跑一次任一技能的 `env_preflight` 会自动摘掉旧的 |
| **Windows 上五个钩子全都不响** | 钩子命令是 POSIX shell 形态（`exec "$(command -v python3 \|\| command -v python)" …`），需要 bash 才能跑。**跟你从哪个终端启动 Claude Code 无关**——Claude Code 自己去找 bash：机器上装了 **Git for Windows** 就用它自带的 Git Bash，没装就没法跑 | 装 [Git for Windows](https://git-scm.com/downloads/win)（装完重启 Claude Code 即可，不必从 Git Bash 窗口里启动）。<br>五条 handler 都已显式声明 `"shell": "bash"`：没装 Git Bash 时 Claude Code 会明确报 `Hook "…" requires bash but Git Bash was not found`，而不是悄悄改用 PowerShell 跑一串它读不懂的命令。<br>🔴 但**报错不等于拦截**：官方只把退出码 2 当阻断，钩子起不来一律算"非阻断错误"，工具照常执行——所以此时**拦层是哑的**（门禁等于不存在），别把"没被拦"当成"检查通过了"。这条报错每个会话每条钩子只提示一次，错过就没了。<br>**开局没看到学术项目状态卡 = 钩子没在岗**——这是最快的自检：卡片首行会带 `academic-gate v<版本号>`。<br>TODO：仍未做真正的跨壳改造（命令还是 bash 形态，PowerShell 上依然跑不了）。本轮只把"静默退化"换成了"一次性明确报错"。彻底解法是改 exec 形态（`command` + `args`，不经壳），改动面涉及全部 5 条 handler，需单独验证 |

## 目录内容

```
academic-gate/
├── .claude-plugin/plugin.json   插件声明（name 写死，不靠目录名推导）
├── .codex-plugin/plugin.json    同上，给 Codex 用（两份逐字节一致，改一份要一起改）
├── hooks/hooks.json             5 条 handler：喂 3 个事件 + 拦 Write 类 + 拦 Bash
├── scripts/
│   ├── academic_gate_hook.py    【拦·写文件】PreToolUse(Write|Edit|MultiEdit|NotebookEdit)。
│   │                            判是不是学术项目 → 伪造签字/盲检凭证、未补盲检就写新正文、
│   │                            未结构签字 → deny；认不出项目一律放行（fail-open）
│   ├── bash_guard_hook.py       【拦·Bash】PreToolUse(Bash)。**会 deny 你的 Bash 命令**：
│   │                            AI 代跑 structure_signoff_gate.py confirm、用 shell 绕开
│   │                            脚本直写 structure_signoff.json / .review_pass/、经 shell
│   │                            写未过盲检的受管正文。黑名单、拦常见形态，不完备
│   ├── context_feed_hook.py     【喂】SessionStart / UserPromptSubmit / PostToolUse。
│   │                            **每轮会往 AI 上下文注入一段文本**（项目状态卡：项目根、
│   │                            技能、哪些节声明完成但没盲检、盲检命令）。非学术项目输出空、
│   │                            全绿时也不注入；只读项目文件，不写你的项目目录
│   ├── context_guard_core.py    三个钩子共用的唯一判定实现（分档/差集/清洗/审计）+
│   │                            排障 CLI：python3 context_guard_core.py explain <路径>
│   ├── structure_signoff_gate.py 签字落盘/校验
│   └── gate_registry.json       各技能的受管文件范围与 signoff 开关
└── SKILL.md                     本文件
```

**这个插件会在你机器上写的东西**（只此三处）：`<项目根>/.academic_gate_audit.jsonl`（只记
deny/ask、Codex 上按放行处理的那一档、与"这次没检查成"，同目录已有 `.gitignore` 时追加一行忽略、没有则不创建）、
`${CLAUDE_PLUGIN_DATA}` 下的去重/待报小文件、插件自己目录里的心跳。**不联网、不读密钥。**
陌生目录的边界如实说：撞了通用产物名（如 `drafts/section_*.md`）的目录**零残留**；但写到
我们的凭证名（`.review_pass/` 或 `structure_signoff.json`）时会在那个目录留一行审计。

上面 5 个 `.py` 与 `gate_registry.json` 跟 `_shared/` 逐字节一致，由 `sync_vendored.py` 守卫。**改任一份都要走同步流程**，别单独改这里的副本。
