# BettaFish 最小可运行 Quickstart

本说明提炼自上游 README，用于本 skill 的快速执行。

## 1) 环境前提

- Python 3.9+
- 可用的 `pip`
- （可选）`playwright` 浏览器依赖（用于爬虫能力）
- 数据库与模型 API 配置通过项目根目录 `.env` 提供

## 2) 一键准备（推荐顺序）

在 skill 目录中执行：

```bash
python scripts/wrapper.py init
python scripts/wrapper.py install
python scripts/wrapper.py playwright-install
```

说明：
- `init` 会克隆仓库并 checkout 到 skill 固定提交版本（可复现）。
- `install` 按 `requirements.txt` 安装依赖。
- `playwright-install` 安装浏览器驱动。

## 3) 启动主系统

```bash
python scripts/wrapper.py run-app
```

默认从 `app.py` 启动。

## 4) 命令行报告重生成

```bash
# 使用默认参数
python scripts/wrapper.py run-report-engine

# 透传参数示例
python scripts/wrapper.py run-report-engine -- --query "土木工程行业分析" --skip-pdf --verbose
```

## 5) MindSpider 独立运行

```bash
# 初始化
python scripts/wrapper.py run-mindspider -- --setup

# 仅话题提取
python scripts/wrapper.py run-mindspider -- --broad-topic --date 2024-01-20

# 完整流程
python scripts/wrapper.py run-mindspider -- --complete --date 2024-01-20
```

## 6) 常见排查

- `requirements.txt 不存在`：说明仓库未正确初始化，先执行 `init`。
- 启动失败且提示环境变量：检查 `.env` 是否按上游说明配置。
- Playwright 相关报错：重新执行 `playwright-install`。

## 7) 版本一致性

本 skill 固定到以下提交：

- `ec733a9c0febe9ddbfb4add757613a0ac59e0df9`

需要重对齐时可执行：

```bash
python scripts/wrapper.py update
```
