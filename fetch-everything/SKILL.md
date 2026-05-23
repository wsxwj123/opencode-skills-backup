---
name: fetch-everything
description: 尽可能快速、准确、完整地获取网页内容，并默认输出 Markdown。只要用户提到抓取网页、提取文章正文、读取文档页面、处理微信公众号链接、转换网页为 Markdown、获取在线内容、提取页面关键信息，或遇到反爬/动态页面需要多种回退方案时，都应使用此技能。优先按站点类型智能分流：在线转换服务、直接抓取、Scrapling、本地浏览器自动化依次协作。
---

# Fetch Everything

## 概述

本技能用于“尽量把网页内容抓下来”，而不是只做单一的网页转 Markdown。

默认目标是：

1. **优先拿到正文**，不是整页噪音
2. **优先输出 Markdown**，便于后续交给 AI 处理
3. **按站点智能分流**，选择最快且成功率更高的方法
4. **失败时自动降级**，必要时切到 Scrapling 或浏览器方案

## 默认输出规范

返回结果时，优先包含以下信息：

- 来源 URL
- 使用的方法
- 提取结果（Markdown 优先）
- 如果失败：失败原因、已尝试的方法、下一步建议

## 核心工作流

### 1. 先判断目标类型

优先判断链接属于哪一类：

- **普通静态网页**：博客、新闻、说明页
- **技术文档**：API 文档、开发文档、GitHub 页面
- **微信公众号/社媒文章**：通常有风控、环境校验或大量附加 UI
- **动态页面**：依赖 JavaScript 渲染
- **登录/付费墙/验证页面**：需要 cookie、人工验证或浏览器会话；**与反爬不同——此类即使绕过也无法合法获取内容**

> **⚠️ HALT（登录/付费墙）**：识别到此类型后，立即告知用户"该页面需要登录或付费，无法自动获取正文"，并询问用户是否能提供 cookie、截图或正文文本，**不要自行尝试抓取**。

### 2. 默认入口：运行统一执行器

**绝大多数情况直接用统一执行器**，不要手动选路线：

```bash
# 环境自检（首次或排障时运行）
python3 scripts/check_fetch_env.py

# 主入口：自动完成多路线抓取 + 质量判定 + 清洗 + 选最优结果
python3 scripts/fetch_everything.py “<url>”

# 需要 JSON 元信息时
python3 scripts/fetch_everything.py “<url>” --json

# 需要保存到文件时
python3 scripts/fetch_everything.py “<url>” -o output.md
```

执行器内部已自动处理：短链接解析 → 站点类型识别 → 多路线抓取 → 质量打分 → 清洗 → 返回最优结果。**只有执行器失败、质量不足或需要手动调参时**，才进入步骤3的手动路线。

### 3. 手动路线参考（执行器降级 / Fallback）

执行器无法解决时，按站点类型手动选路线：

**A. 普通网页：**
- 先试 `https://markdown.new/<原始url>`
- 再试 `https://defuddle.md/<原始url>`
- 再试 `https://r.jina.ai/<原始url>`
- 必要时 Scrapling HTTP 抓取

**B. 技术文档：**
- 优先 `https://r.jina.ai/<原始url>`
- 再试 webfetch
- 必要时 Scrapling HTTP 抓取

**C. 微信公众号 / 反爬页面：**
- 直接用 Scrapling，不走在线服务（在线服务必触发风控）
- 推荐顺序：`extract get` → `extract stealthy-fetch` → `extract fetch`
- 仍只拿到验证页/空壳 → 浏览器自动化或人工接力

**D. 动态页面：**
- 优先 Scrapling DynamicFetcher（`extract fetch`）
- 需要时增加等待、选择器、自定义 header

### 4. Markdown 优先，必要时降级

输出顺序建议为：

1. **高质量 Markdown**
2. 纯文本
3. HTML
4. 元数据 + 失败说明

不要因为拿不到完美 Markdown 就直接放弃；只要能稳定获取正文文本，也应交付。

### 5. 处理反爬与失败回退

遇到以下情况时，说明在线服务不足，应切换本地方案：

- 返回”环境异常””去验证””Access denied””Captcha”
- 页面只有壳，没有正文
- 需要等待 JS 渲染
- 第三方服务超时或 502

切换顺序：

1. Scrapling HTTP 请求（`extract get`）
2. Scrapling StealthyFetcher（`extract stealthy-fetch`）
3. Scrapling DynamicFetcher（`extract fetch`）
4. 浏览器自动化
5. **HALT → 告知用户**：说明已尝试的方法和失败原因，请用户提供 cookie / 正文 / 截图

## Scrapling 使用建议

当站点存在风控、动态加载或微信页面提取不稳定时，优先考虑 Scrapling。

实战经验：微信公众号链接通常可通过 Scrapling 成功抓到正文，但输出中可能混入点赞、赞赏、扫码、推荐内容等尾部噪音，因此要注意二次清理。

推荐命令路径：

```bash
# HTTP 路线，适合先做快速验证
scrapling extract get "<url>" output.md

# 隐身路线，适合反爬更重的页面
scrapling extract stealthy-fetch "<url>" output.md --timeout 45000 --network-idle

# 浏览器动态路线，适合强 JS 页面
scrapling extract fetch "<url>" output.md --timeout 45000 --network-idle
```

注意：

- `fetch` / `stealthy-fetch` 的 `--timeout` 单位通常是**毫秒**
- UA、等待策略和请求头会明显影响成功率
- 即便抓取成功，也要检查内容是不是正文而不是验证页

## 使用示例

### 示例 1：提取公众号推送正文

用户：`看看这个微信公众号推送主要内容`

做法：
1. 运行统一执行器（自动识别微信域名，优先走 Scrapling）
2. 若执行器返回 partial / 仍是验证页，手动执行 `scrapling extract stealthy-fetch`
3. 读取输出 Markdown，提炼正文，去掉扫码、赞赏、推荐内容等噪音

### 示例 2：抓技术文档

用户：`提取这个 API 文档的主要接口说明`

优先：`r.jina.ai` → `webfetch` → Scrapling 手动路线

### 示例 3：抓动态页面

用户：`这个页面是 JS 渲染的，帮我提取主内容`

优先：Scrapling `fetch` / `stealthy-fetch`，必要时补充等待和选择器。

## 注意事项

1. **不要夸大成功率**：抓到文件不等于抓到正文
2. **优先交付可用结果**：正文 Markdown > 纯文本 > 失败说明
3. **公开内容优先**：对需要登录、验证码、私密页面，要说明访问前提
4. **保留方法信息**：方便后续复现与排障

## 资源参考

### references/web-services.md
**何时用**：手动选路线时查分流建议、各服务优缺点对比。

### references/scrapling-guide.md
**何时用**：Scrapling 抓取失败、需要调整 UA / 等待策略 / Python API 时查阅；含安装、CLI、动态页面调参说明。

### scripts/check_fetch_env.py
**何时用**：首次使用或排障时运行，确认 Python / requests / Scrapling CLI 均可用。
```bash
python3 scripts/check_fetch_env.py
```

### scripts/fetch_everything.py
**何时用**：所有常规抓取场景的默认入口（步骤2）。自动多路线抓取 + 质量判定 + 清洗。
```bash
python3 scripts/fetch_everything.py "<url>" --json
```

### scripts/assess_fetch_quality.py
**何时用**：执行器返回 partial / 需要手动判断已有内容质量时；从 stdin 读取文本，输出质量 JSON。
```bash
cat output.md | python3 scripts/assess_fetch_quality.py
```

### scripts/clean_fetched_markdown.py
**何时用**：Scrapling 抓到正文但混入扫码/赞赏/推荐噪音时手动清洗。
```bash
cat output.md | python3 scripts/clean_fetched_markdown.py
```

### scripts/url-converter.py
**何时用**：需要单独测试某个在线服务是否可达，或批量转换 URL 时；不直接替代 Scrapling。
```bash
python3 scripts/url-converter.py --url "<url>" --test-all
```
