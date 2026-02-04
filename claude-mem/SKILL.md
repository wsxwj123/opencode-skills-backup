---
name: claude-mem
description: Persistent memory compression system for Claude Code. Automatically captures tool usage, generates semantic summaries, and provides search tools for querying project history across sessions.
github_url: https://github.com/thedotmack/claude-mem
github_hash: 1341e93fcab15b9caf48bc947d8521b4a97515d8
version: 9.0.12
created_at: 2026-02-04T00:00:00Z
entry_point: scripts/run.sh
dependencies: ["bun>=1.0.0", "node>=18.0.0"]
tools:
  - name: search
    description: "Search memory index with full-text queries. Params: query, limit, project, type, obs_type, dateStart, dateEnd, offset, orderBy. Returns compact index with IDs (~50-100 tokens/result)."
  - name: timeline
    description: "Get chronological context around results. Params: anchor (observation ID) OR query (finds anchor automatically), depth_before, depth_after, project. Shows what was happening around specific observations."
  - name: get_observations
    description: "Fetch full details for filtered IDs. Params: ids (array, required), orderBy, limit, project. ALWAYS batch multiple IDs. Returns complete details (~500-1000 tokens/result)."
  - name: __IMPORTANT
    description: "Workflow documentation. Always follow 3-layer pattern: 1) search (get index), 2) timeline (get context), 3) get_observations (fetch details). 10x token savings."
---

# Claude-Mem: Persistent Memory System

Claude-Mem 是一个为 Claude Code 设计的持久化记忆压缩系统。它会自动捕获工具使用记录、生成语义摘要，并提供搜索工具用于跨会话查询项目历史。

## 核心功能

- **持久化记忆**: 会话结束后仍保留上下文
- **渐进式披露**: 分层记忆检索，带令牌成本可见性
- **MCP 搜索工具**: 使用自然语言查询项目历史
- **Web UI 查看器**: 实时记忆流在 http://localhost:37777
- **隐私控制**: 使用 `<private>` 标签排除敏感内容
- **自动运行**: 无需手动干预

## 系统架构

1. **5 个生命周期钩子**: SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd
2. **智能安装**: 缓存依赖检查器（预钩子脚本）
3. **Worker 服务**: HTTP API（端口 37777），由 Bun 管理
4. **SQLite 数据库**: 存储会话、观察、摘要
5. **mem-search Skill**: 使用渐进式披露进行自然语言查询
6. **Chroma 向量数据库**: 混合语义 + 关键词搜索

## MCP 搜索工具 - 3 层工作流

**标准流程（始终遵循）：**

1. **search** - 获取带 ID 的索引（~50-100 tokens/结果）
   ```
   search(query="authentication bug", type="bugfix", limit=10)
   ```

2. **timeline** - 获取有趣结果周围的时间线上下文
   ```
   timeline(anchor=<ID>, depth_before=3, depth_after=3)
   ```

3. **get_observations** - 仅获取过滤后 ID 的完整详情
   ```
   get_observations(ids=[123, 456])  # 始终批量处理
   ```

**为什么**: 10倍令牌节省。在获取完整详情前先过滤。

## 系统要求

- **Node.js**: 18.0.0 或更高
- **Bun**: JavaScript 运行时和进程管理器（缺失时自动安装）
- **uv**: Python 包管理器用于向量搜索（缺失时自动安装）
- **SQLite 3**: 用于持久化存储（内置）

## 配置

设置在 `~/.claude-mem/settings.json` 中管理（首次运行时自动创建默认值）。

主要配置项：
- AI 模型选择
- Worker 端口
- 数据目录
- 日志级别
- 上下文注入设置

## 使用方式

此 Skill 作为 MCP 服务器运行，提供 4 个工具供 Claude 使用：

1. `search` - 搜索记忆索引
2. `timeline` - 获取时间线上下文
3. `get_observations` - 获取观察详情
4. `__IMPORTANT` - 工作流文档

**示例对话：**

> 用户：查找之前关于身份验证的工作
> 
> Claude 调用：`search(query="authentication", limit=20)`
> 
> Claude 查看结果，识别相关 ID
> 
> Claude 调用：`get_observations(ids=[123, 456, 789])`

## 故障排除

- 如果 Worker 服务未启动，运行：`bun /path/to/repo/plugin/scripts/worker-service.cjs start`
- 日志位置：`~/.claude-mem/logs/worker-YYYY-MM-DD.log`
- 查看 Web UI：http://localhost:37777

## 许可证

AGPL-3.0（ragtime/ 目录单独采用 PolyForm Noncommercial License 1.0.0）
