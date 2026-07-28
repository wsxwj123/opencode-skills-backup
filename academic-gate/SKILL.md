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
| opencode / codex 里不拦 | **这两端从来就不读 Claude Code 的钩子配置**——门禁在那两端从未生效过 | 已知限制，不是回归 |
| 拦截理由显示两次 | 插件钩子 + 旧的自装钩子并存 | 无害（两条指向同一份逻辑、不会误放行）；跑一次任一技能的 `env_preflight` 会自动摘掉旧的 |

## 目录内容

```
academic-gate/
├── .claude-plugin/plugin.json   插件声明（name 写死，不靠目录名推导）
├── hooks/hooks.json             PreToolUse 钩子配置
├── scripts/
│   ├── academic_gate_hook.py    钩子本体（fail-open：自身出错时放行，不阻断用户）
│   ├── structure_signoff_gate.py 签字落盘/校验
│   └── gate_registry.json       各技能的受管文件范围与 signoff 开关
└── SKILL.md                     本文件
```

三个脚本与 `_shared/` 逐字节一致，由 `sync_vendored.py` 守卫。**改任一份都要走同步流程**，别单独改这里的副本。
