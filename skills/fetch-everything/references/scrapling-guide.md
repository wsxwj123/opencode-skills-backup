# Scrapling 本地抓取指南

## 定位

Scrapling 是 `fetch-everything` 的核心本地回退方案，用于处理在线服务拿不到、存在风控或依赖动态渲染的页面。

它适合：

- 微信公众号链接
- 普通服务返回验证页的站点
- 需要更强隐身能力的目标站点
- 需要本地复现与稳定调参的抓取任务

## 推荐抓取顺序

如果统一执行器已经可用，通常不需要手动依次执行这些命令；它们主要用于排障和手动精调。

### 1. HTTP 快速路线

```bash
scrapling extract get "<url>" output.md
```

适合先快速验证目标站点是否可直接返回正文。

### 2. 隐身路线

```bash
scrapling extract stealthy-fetch "<url>" output.md --timeout 45000 --network-idle
```

适合轻到中度反爬页面。

### 3. 动态浏览器路线

```bash
scrapling extract fetch "<url>" output.md --timeout 45000 --network-idle
```

适合依赖 JavaScript 渲染的页面。

## 什么时候继续调 Scrapling

继续调参通常值得的情况：

- 已经拿到部分正文，但还想减少噪音
- 页面内容依赖加载时机
- 需要更稳定的 selector 抽取
- 需要 cookie / header / referer

常见调参项：

- `--proxy`
- `--timeout`
- `--network-idle`
- `--wait`
- `--css-selector`
- `--extra-headers`

其中 `fetch` / `stealthy-fetch` 的 `--timeout` 单位通常是**毫秒**，不是秒。

## 什么时候停止自动化尝试

出现以下情况时，应明确说明限制：

- 页面明确要求人工验证码
- 需要登录态且用户未提供访问前提
- 多种本地/在线方案都只返回同样的验证壳

此时可建议用户提供：cookie、正文、截图或可访问副本。
