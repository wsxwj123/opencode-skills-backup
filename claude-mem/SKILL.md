---
name: claude-mem
description: Persistent memory compression system for Claude Code. Automatically captures tool usage, generates semantic summaries, and provides search tools for querying project history across sessions.
github_url: https://github.com/thedotmack/claude-mem
version: latest
created_at: 2026-02-16T00:00:00Z
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
github_hash: e4e735d3ffe0cf40bfbc6b666747568636070f10
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

## MCP 搜索工具 - 3 层工作流

**标准流程（始终遵循）：**

1. **search** - 获取带 ID 的索引（~50-100 tokens/结果）
2. **timeline** - 获取有趣结果周围的时间线上下文
3. **get_observations** - 仅获取过滤后 ID 的完整详情

**为什么**: 10倍令牌节省。在获取完整详情前先过滤。
