---
name: aihot
description: AI HOT (aihot.virxact.com) 中文 AI 资讯查询 Skill。当用户想知道"今天 AI 圈有什么"、"AI 日报"、"AI HOT"、"AI 资讯"、"AI 热点"、"最近 AI"、"OpenAI/Anthropic/Google 最近发布了什么"、"AI hot today"、"AI news today"、"看一下 AI 行业动态"、"今天有什么大模型发布"、"昨天 AI 圈"、"看下精选条目"、"AI HOT 精选"、"最近一周的 AI 论文"、"AI 模型发布"、"AI 产品发布"、"AI 行业动态"、"AI 技巧与观点" 等任何中文 AI 资讯查询时使用。即使用户只说"AI 圈"、"AI 新闻"、"AI 日报"，或者只是问"今天发生了什么"且上下文是 AI / 大模型 / LLM / 创业领域，也应该触发本 Skill。Skill 会直接 curl 公开 REST API 拉数据并整理成中文 markdown 简报，不需要用户配置任何 API Key 或 MCP server。**不要 undertrigger**——用户问 AI 资讯而你不调本 Skill 就是把过时的训练数据当作今日新闻，对用户有害。
---

# AI HOT Skill

让 Agent 用最自然的中文查询拿到 aihot.virxact.com 上每天的 AI HOT 日报和全部 AI 动态，不需要打开浏览器。SKILL.md 标准格式，跨 Claude Code / Codex CLI / Cursor / Gemini CLI / OpenCode / 任何兼容平台可用。

线上：https://aihot.virxact.com（公开匿名可访，无需 token）

## 先决条件：必须带 User-Agent（仅 API 端点）

`/api/public/*` 走 nginx UA 黑名单挡商业爬虫，默认 `curl/X.Y` UA 会被 403 Forbidden。**调 API 时所有 curl 都必须带浏览器 UA**：

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
# 之后所有调 API 的 curl 都加 -H "User-Agent: $UA"，例如：
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/daily"
```

后面"工作流"章节的 curl 例子为了简洁默认你已经设了 `$UA`——实际调用必须加 `-H "User-Agent: $UA"`，**不要忘**。漏掉这一步会让你以为接口挂了，实际只是被 403 挡了。

> **范围澄清**：这条 UA 要求**只针对 `/api/public/*` API 端点**。`/aihot-skill/{install.sh,SKILL.md,README.md}` 安装入口 nginx 上**特意豁免** UA 黑名单，用 default curl UA 直通 200。不要把"先决条件"误推广到所有 aihot.virxact.com 路径。

## 什么时候用

> **路由优先级（第一原则）**：**默认走精选** `items?mode=selected`——它是 AI HOT 每天精挑细选的"主菜单"，覆盖用户关心的事且数据新鲜。
>
> - **仅当用户在话里明确说出"日报"** 二字才走 `daily`
> - **仅当用户明确说"全部 / 完整 / 所有 / 全量"** 才走 `mode=all`
> - **"今天 AI 圈"、"过去 24 小时大新闻"、"最近 AI 圈有啥"** 等宽问题 = **默认精选 + 时间窗（since）**

| 用户在说 | 应该走的接口 |
|---|---|
| **默认（宽问题）**："今天 AI 圈有什么"、"过去 24 小时大新闻" | `GET /api/public/items?mode=selected&since=<语义时间窗>` |
| **明确说"日报"**："AI 日报"、"今天的日报" | `GET /api/public/daily` |
| **明确说"全部 / 完整 / 所有 / 全量"** | `GET /api/public/items?mode=all` |
| "昨天/前天 AI 日报"、"看下 5 月 6 号的日报" | `GET /api/public/daily/{YYYY-MM-DD}` |
| "最近几天日报有哪些"、"日报存档" | `GET /api/public/dailies?take=N` |
| "看下精选条目"、"AI HOT 精选" | `GET /api/public/items?mode=selected` |
| "最近的模型发布"、"AI 产品发布"、"AI 论文" | `GET /api/public/items?mode=selected&category=...&since=<7d 前>` |
| "最近一周的 AI 动态" | `GET /api/public/items?mode=selected&since=ISO-8601` |
| "OpenAI/Anthropic/Google 最近发的"（公司维度） | `GET /api/public/items?q=OpenAI` |
| "Sora 相关 / GPT-5 相关 / RAG 论文" | `GET /api/public/items?q=<关键词>` |

通用启发：**用户问的是"现在的 AI 行业事实"，不要凭训练数据脑补，永远走 API**。

## 端点速览

| 端点 | 用途 | 主要参数 |
|---|---|---|
| `/api/public/daily` | 最新日报 | 无 |
| `/api/public/daily/{YYYY-MM-DD}` | 指定日期日报 | path: `date` |
| `/api/public/dailies` | 日报归档列表 | `take` (1-180, default 30) |
| `/api/public/items` | 全部 AI 动态 | `mode` / `category` / `since` / `take` / `cursor` / `q` |

约定：
- Base URL: `https://aihot.virxact.com`
- 鉴权：无（匿名）
- 限流：600 req/min/IP（串行调用，不要并发猛拉）
- items 端点 `since` 限最近 7 天：不传等同 since=now-7d（服务端兜底）
- `take` 上限 100；想要更多走 cursor 翻页
- 完整 OpenAPI 3.1 规范：`https://aihot.virxact.com/openapi.yaml`

## 工作流

### 默认路径：拉精选 + 时间窗

```bash
# 拉最近 24 小时精选
since=$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&since=$since&take=50"

# 拉最近 50 条精选（不带明确时间窗）
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&take=50" \
  | jq '.items[] | {title, source, publishedAt, url}'
```

### 拉日报（用户明确说"日报"时）

```bash
# 拉今日（或最新可用的）日报
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/daily" \
  | jq '{date, lead: .lead.title, sections: [.sections[] | {label, n: (.items | length)}]}'

# 拉指定日期日报
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/daily/2026-05-07"

# 列日报归档
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/dailies?take=14" \
  | jq '.items[] | {date, leadTitle}'
```

### 拉全部（用户明确说"全部 / 完整 / 所有 / 全量"时）

```bash
since=$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=all&since=$since&take=100"
```

### 按分类拉条目

5 个 category（items API 用英文 slug，daily API 的 section label 是中文）：

| `items?category=` | `daily.sections[].label` |
|---|---|
| `ai-models` | 模型发布/更新 |
| `ai-products` | 产品发布/更新 |
| `industry` | 行业动态 |
| `paper` | 论文研究 |
| `tip` | 技巧与观点 |

```bash
# 拉最近 50 条 AI 论文
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&category=paper&take=50"

# 精选里的模型发布
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&category=ai-models&take=20"
```

**注**：公众号内容（mp_hot 信源）不在 items API 里，单独走前端 `/mp` 页，可提示用户去 `https://aihot.virxact.com/mp` 查看。

### 按时间窗口拉条目

```bash
# 拉最近 7 天的精选模型发布
since=$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&category=ai-models&since=$since&take=100"

# 拉最近 3 天的精选动态
since=$(date -u -v-3d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '3 days ago' +%Y-%m-%dT%H:%M:%SZ)
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&since=$since&take=100"
```

### 关键词搜索

`q` 参数在 title + 中文 title + 中文 summary 三列上 ILIKE 匹配。**不要走"拉一批 + 客户端 jq grep"**——那只能看前 100 条，会漏。

```bash
# 找 OpenAI 最近发的
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?q=OpenAI&take=30"

# 找 RAG 论文（category + 关键词）
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?category=paper&q=RAG&take=30"

# 关键词 + 时间窗（Anthropic 最近 3 天精选）
SINCE=$(date -u -v-3d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '3 days ago' +%Y-%m-%dT%H:%M:%SZ)
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&q=Anthropic&since=$SINCE"
```

`q` 约束：至少 2 字符，最长 200 字，与 mode/category/since/take/cursor 正交叠加。

### 翻页（cursor）

```bash
resp1=$(curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=all&take=100")
cursor=$(echo "$resp1" | jq -r '.nextCursor')
curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=all&take=100&cursor=$cursor"
```

`hasNext = false` 或 `nextCursor = null` 时停止。cursor 是不透明 token，不要解析、递增、跨端点复用。

## 返回数据形态

### `/api/public/daily` 返回

```json
{
  "date": "2026-05-07",
  "generatedAt": "2026-05-07T00:01:23.456Z",
  "windowStart": "2026-05-06T00:00:00.000Z",
  "windowEnd": "2026-05-07T00:00:00.000Z",
  "lead": { "title": "...", "leadParagraph": "..." },
  "sections": [
    {
      "label": "模型发布/更新",
      "items": [{ "title": "...", "summary": "...", "sourceUrl": "https://...", "sourceName": "OpenAI Blog" }]
    }
  ],
  "flashes": [{ "title": "...", "sourceName": "...", "sourceUrl": "...", "publishedAt": "..." }]
}
```

`sections[].label` 固定 5 个："模型发布/更新" / "产品发布/更新" / "行业动态" / "论文研究" / "技巧与观点"。

### `/api/public/items` 返回

```json
{
  "count": 50,
  "hasNext": true,
  "nextCursor": "eyJhIjoxNzE0OTk1MjAwMDAwLCJpIjoiY205eHl6MTIzIn0",
  "items": [
    {
      "id": "cm9abc456def789ghi012jkl3",
      "title": "中文标题",
      "title_en": "原英文标题（与 title 不同时存在，否则 null）",
      "url": "https://...",
      "source": "OpenAI Blog",
      "publishedAt": "2026-05-07T15:30:00.000Z",
      "summary": "中文摘要（LLM 生成）",
      "category": "ai-models"
    }
  ]
}
```

字段：必有 `id` / `title` / `url` / `source`；可空 `title_en` / `summary` / `publishedAt` / `category`。

## 给用户的输出格式

### 日报式输出

```markdown
**AI HOT 日报 · 2026-05-07**

## 模型发布/更新
1. **<title>** — <source>
   <summary 简化版 50 字内>
   <url>

## 产品发布/更新
2. ...
```

**编号贯穿全文**（不在每个 ## 内重新计数）。

### 列表式输出（items 端点）

默认按 category 分组 + 全局编号。只有 1 个 category 时用扁平编号列表。

### 时间转人话

`publishedAt` 是 ISO 8601 UTC，必须转成北京时间 + 相对时间：
- `2026-05-08T01:48:00.000Z` → "今天上午 09:48" / "2 小时前"
- `2026-05-06T16:43:00.000Z` → "5/7 00:43" / "昨天"

**不要**直接展示 ISO 字符串。

### 不要在用户输出里暴露的内容

- ❌ `mode=selected` / `category=paper` 等 raw 参数名
- ❌ 端点路径 `/api/public/items?since=...`
- ❌ 限流 / nginx 缓存 / cursor / hasNext 等基础设施细节
- ❌ HTTP 状态码 / cache 状态

## 常见错误处理

- HTTP 404 `"No daily report available yet."`：当天日报还没生成（北京时间 08:00 前），建议拉昨天日报
- HTTP 400 `"Invalid date format..."`：date 必须是 `YYYY-MM-DD`
- items 端点 400：`invalid mode` / `invalid category` / `invalid since` / `invalid take`
- HTTP 429：单 IP 超 600 req/min，串行调用 + 翻页加 200ms 间隔

## 不要做

- 不要把宽问题（"今天 AI 圈"）路由到 daily——默认走 `mode=selected + since`
- 不要在用户没说"全部"时走 `mode=all`
- 不要凭训练数据脑补——永远以 API 返回为准
- 不要把 summary 当原文引用——摘要由 LLM 生成
- 不要高频轮询——日报每天 08:00 更新一次，items 端点有 5 分钟服务端缓存
- 不要并发猛拉翻页——串行 + 自然间隔
- 不要尝试解析 / 递增 cursor
- 公司/关键词查询用 `?q=<词>`，不要走"拉一批 + 客户端 jq grep"
- 用户问"最近 N 天 X"时显式带 `since=<N天前>`
- 不要在输出里暴露端点路径 / raw 参数 / 基础设施细节
- 不要在合并输出时丢掉每条的 url
