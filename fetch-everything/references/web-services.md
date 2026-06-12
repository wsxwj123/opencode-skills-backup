# 在线内容读取服务

## 定位

这些服务适合先做快速尝试，把网页内容尽快变成适合 AI 处理的文本结果；如果结果明显不对，就应及时切到本地方案。

默认目标仍然是：

- 尽快拿到正文
- 尽量输出 Markdown
- 失败后快速切换备选方案

## 服务分工

### 1. markdown.new
- **特点**：速度快，适合大多数普通网页
- **适用**：博客、新闻、产品介绍页、帮助文档
- **限制**：对动态页面、强风控站点、登录页支持有限

### 2. defuddle.md
- **特点**：可作为 markdown.new 的直接备选
- **适用**：普通网页抓取失败后的第二选择
- **限制**：稳定性一般，输出质量随站点而变化

### 3. r.jina.ai
- **特点**：对技术文档和结构化页面通常更稳定
- **适用**：开发文档、API 页面、GitHub 页面、教程
- **限制**：部分页面会超时或被限制

## 推荐分流

如果 `scripts/check_fetch_env.py` 可用，先做一次环境自检；确认本地执行环境具备能力后，再优先直接调用 `scripts/fetch_everything.py`。如果自检提示缺少 `requests` 或 Scrapling CLI 不可用，应先补齐环境。以下分流规则主要用于理解统一执行器的默认顺序，或在需要手动调参时使用。

### 普通网页
推荐顺序：
1. `markdown.new`
2. `defuddle.md`
3. `r.jina.ai`
4. `webfetch`
5. Scrapling 手动路线

### 技术文档
推荐顺序：
1. `r.jina.ai`
2. `webfetch`
3. `markdown.new`
4. Scrapling 手动路线

### 微信公众号 / 反爬站点
推荐顺序：
1. Scrapling HTTP
2. Scrapling StealthyFetcher
3. Scrapling DynamicFetcher
4. 浏览器自动化
5. 人工接力

在线服务如果直接返回验证页、环境异常页、空壳内容或明显缺正文，就不要在同一路线上反复消耗时间，应尽快切到本地方案。

## URL 格式

- `https://markdown.new/<原始URL>`
- `https://defuddle.md/<原始URL>`
- `https://r.jina.ai/<原始URL>`（原始 URL 需带 `http://` 或 `https://` 协议头）

> `r.jina.ai` 免费档限流较重；如需稳定使用，设置环境变量 `JINA_API_KEY`，执行器会自动带上鉴权头。

如果在线转换结果返回：
- 环境异常
- 验证页
- 502 / 超时
- 明显缺正文

就不要在同一服务上反复消耗时间，应尽快切换方案。
