---
name: bettafish
description: 运行 BettaFish 舆情分析系统（源码初始化、依赖安装、Web 启动、命令行报告与 MindSpider 爬虫）。当用户提到 BettaFish、舆情分析系统部署、报告重生成时使用。
github_url: https://github.com/666ghj/BettaFish
github_hash: ec733a9c0febe9ddbfb4add757613a0ac59e0df9
version: 0.1.0
created_at: 2026-03-06T23:00:01.499292
entry_point: scripts/wrapper.py
dependencies:
  - python>=3.9
  - git
  - pip
  - playwright
---

# BettaFish

将 [666ghj/BettaFish](https://github.com/666ghj/BettaFish) 封装为可复用 skill，支持本地一键初始化与常用命令调度。

## 适用场景

- 用户要部署/运行 BettaFish
- 用户要生成或重生成综合报告（`report_engine_only.py`）
- 用户要单独运行 MindSpider 爬虫流程
- 用户要在本地更新到指定提交版本并复现

## 触发词（建议）

- "BettaFish"
- "舆情分析系统部署"
- "运行 BettaFish"
- "重生成报告 / report_engine_only"
- "MindSpider 爬虫"
- "初始化 BettaFish 环境"

## 快速用法

通过入口脚本 `scripts/wrapper.py` 调用：

```bash
python scripts/wrapper.py <command> [args...]
```

### 常用命令

- `init`：克隆仓库并检出 `github_hash`
- `update`：拉取远端并重新检出 `github_hash`
- `install`：安装 `requirements.txt`
- `playwright-install`：安装 Playwright 浏览器驱动
- `run-app`：运行 `python app.py`
- `run-report-engine [-- ...]`：运行 `report_engine_only.py`（参数透传）
- `run-mindspider [-- ...]`：运行 `MindSpider/main.py`（参数透传）
- `exec -- <command...>`：在仓库根目录执行任意命令

## 默认仓库路径

`~/.cache/opencode-skills/bettafish-repo`

可通过参数 `--repo-dir` 覆盖。

## 备注

- 本 skill 只做包装，不改写上游项目逻辑。
- 首次运行建议顺序：`init -> install -> playwright-install -> run-app`。
- 最小可运行说明见：`references/quickstart.md`。
