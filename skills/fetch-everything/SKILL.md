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
- **登录/验证页面**：可能需要 cookie、人工验证或浏览器会话

### 2. 智能选择抓取路径

**A. 普通网页：**
- 先试 `markdown.new/`
- 再试 `defuddle.md/`
- 再试 `r.jina.ai/`
- 必要时再用直接抓取或 Scrapling

**B. 技术文档：**
- 优先 `r.jina.ai/`
- 再试 `webfetch`
- 必要时 Scrapling HTTP 抓取

**C. 微信公众号 / 反爬页面：**
- 优先本地方案：Scrapling
- 推荐顺序：`extract get` → `extract stealthy-fetch` → `extract fetch`
- 如果只能拿到验证页、环境异常页或空壳内容，再考虑浏览器自动化/人工接力

**D. 动态页面：**
- 优先 Scrapling 的浏览器类 fetcher
- 需要时增加等待、选择器、自定义 header

### 3. 默认先走统一执行器

如果技能目录里的 `scripts/check_fetch_env.py` 可用，先做一次环境自检；确认本地脚本依赖和 Scrapling CLI 可用后，再优先使用 `scripts/fetch_everything.py` 作为默认入口。

它会自动完成：

1. 多路线抓取
2. 质量判定
3. 轻量清洗
4. 选择最优候选结果

只有在统一执行器失败、结果质量不足或需要手动调参时，才退回单独使用在线服务、Scrapling 子命令或浏览器自动化。

### 4. Markdown 优先，必要时降级

输出顺序建议为：

1. **高质量 Markdown**
2. 纯文本
3. HTML
4. 元数据 + 失败说明

不要因为拿不到完美 Markdown 就直接放弃；只要能稳定获取正文文本，也应交付。

### 5. 处理反爬与失败回退

遇到以下情况时，说明在线服务可能不足：

- 返回“环境异常”“去验证”“Access denied”“Captcha”
- 页面只有壳，没有正文
- 需要等待 JS 渲染
- 第三方服务超时或 502

这时应切换到本地方案：

- Scrapling HTTP 请求
- Scrapling StealthyFetcher
- Scrapling DynamicFetcher
- 浏览器自动化
- 用户提供 cookie / 正文 / 截图

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
1. 先尝试在线服务
2. 若出现环境异常，立即切到 Scrapling
3. 读取输出 Markdown，提炼正文
4. 去掉扫码、赞赏、推荐内容等噪音

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
在线内容读取服务的定位、优缺点与分流建议。

### references/scrapling-guide.md
Scrapling 的安装、CLI 使用、Python API、动态页面与手动调参说明。

### scripts/check_fetch_env.py
环境自检脚本。用于检查 Python、requests、技能脚本和 Scrapling CLI 是否可用，方便在分享给别人后先快速判断环境是否具备抓取能力。

### scripts/fetch_everything.py
统一抓取执行器。输入一个链接后，自动尝试在线服务与本地抓取路线，做质量判定和轻量清洗，并返回最佳结果。

### scripts/assess_fetch_quality.py
质量判定器。用于识别验证页、异常页、正文过短、结构不足等情况。

### scripts/clean_fetched_markdown.py
轻量清洗器。用于删除扫码、赞赏、推荐阅读、弹层按钮等高置信噪音。

### scripts/url-converter.py
本地路由脚本。它负责把原始链接转换为各类在线读取服务链接，并测试服务可用性；它不直接替代 Scrapling。
