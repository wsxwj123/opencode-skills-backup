# Skill Seekers - 一键制作 Skills 的终极工具

> 🎯 从文档、GitHub、PDF 和代码库自动生成高质量 AI Skills

## ✨ 这是什么?

这个 skill 将开源工具 [Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) 打包为一个可在 OpenCode 和 Claude Code 中直接使用的 Skill,让你可以**一键**从任何来源创建新的 Skills!

## 🚀 立即开始(3 步)

### 1. 验证安装

```bash
cd ~/.config/opencode/skills/skill-seekers
./verify.sh
```

### 2. 选择场景

**场景 A: 为当前项目创建 Skill** (推荐新手)
```bash
skill-seekers-codebase --directory . --output output/my-project/
```

**场景 B: 从文档网站创建** (最快)
```bash
skill-seekers install --config react
```

**场景 C: 在 OpenCode 中使用** (最简单)
```
直接告诉 AI: "用 skill-seekers 为当前项目生成 skill"
```

### 3. 打包和安装

```bash
skill-seekers package output/my-project/
skill-seekers install-agent output/my-project/ --agent opencode
```

## 📚 核心功能

| 功能 | 命令 | 耗时 |
|------|------|------|
| 🏠 本地代码分析 | `skill-seekers-codebase --directory .` | 2-10 分钟 |
| 🌐 文档网站抓取 | `skill-seekers scrape --url <url>` | 10-30 分钟 |
| 🐙 GitHub 仓库 | `skill-seekers github --repo <repo>` | 5-15 分钟 |
| 📄 PDF 文档 | `skill-seekers pdf --pdf <file>` | 2-10 分钟 |
| 🔄 多源统一 | `skill-seekers unified --config <json>` | 20-45 分钟 |
| ⚡ 一键完成 | `skill-seekers install --config <name>` | 20-45 分钟 |

## 💡 在 OpenCode 中使用

直接用自然语言告诉 AI:

```
"用 skill-seekers 为当前项目生成 skill"
"用 skill-seekers 从 Vue.js 官网创建 skill"  
"分析 facebook/react 仓库并生成 skill"
"从这个 PDF 创建 skill"
```

AI 会自动执行所有步骤!

## 🎯 支持的来源

✅ **本地代码库** - 任何编程语言(Python, JS, Go, Rust...)
✅ **文档网站** - 任何静态文档站(React, Vue, Django...)
✅ **GitHub 仓库** - 公开或私有仓库(需 token)
✅ **PDF 文档** - 技术手册、论文(支持 OCR)
✅ **统一多源** - 组合以上任意来源

## 🤖 支持的平台

### LLM 平台
- Claude AI
- Google Gemini  
- OpenAI ChatGPT
- 通用 Markdown

### AI 代理
- Claude Code
- OpenCode ⭐
- Cursor
- Windsurf
- VS Code / Copilot
- 其他 10+ 代理

## 📖 文档导航

- **[SKILL.md](SKILL.md)** - 完整文档(推荐阅读)
- **[USAGE.md](USAGE.md)** - 使用指南和场景
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - 命令速查表
- **[README_SKILL.md](README_SKILL.md)** - 快速开始指南

## ⚡ 常用命令

```bash
# 一键完成(最简单)
skill-seekers install --config react

# 本地项目
skill-seekers-codebase --directory . --depth deep

# GitHub 仓库
skill-seekers github --repo owner/repo --include-issues

# 文档网站
skill-seekers scrape --url https://example.com --name myskill

# 配置管理
skill-seekers config --github

# 验证安装
./verify.sh
```

## 🔧 配置优化

### 设置 GitHub Token(推荐)

避免速率限制(60/小时 → 5000/小时):

```bash
skill-seekers config --github
# 或
export GITHUB_TOKEN=ghp_your_token
```

### 启用 AI 增强

提升 Skill 质量(⭐⭐ → ⭐⭐⭐⭐⭐):

```bash
# 本地增强(免费,推荐)
skill-seekers enhance output/myskill/ --ai-mode local

# API 增强(需要 key)
export ANTHROPIC_API_KEY=sk-ant-xxx
skill-seekers enhance output/myskill/ --ai-mode api
```

## 🎓 学习路径

### 新手(第一次使用)

1. 运行 `./verify.sh` 验证安装
2. 阅读 [README_SKILL.md](README_SKILL.md) 快速入门
3. 尝试 `skill-seekers install --config react`
4. 查看生成的文件: `ls output/react/`

### 进阶(熟悉基础后)

1. 阅读 [USAGE.md](USAGE.md) 学习常见场景
2. 尝试分析本地项目
3. 学习统一多源功能
4. 配置 GitHub token 和 AI 增强

### 专家(深度使用)

1. 阅读完整 [SKILL.md](SKILL.md)
2. 学习大型文档拆分策略
3. 配置多个 GitHub 账户
4. 使用异步模式和并行处理

## ❓ 常见问题

<details>
<summary>Q: 如何避免 GitHub 速率限制?</summary>

```bash
# 设置 GitHub Token
export GITHUB_TOKEN=ghp_your_token
# 或使用配置向导
skill-seekers config --github
```
</details>

<details>
<summary>Q: 本地增强 vs API 增强?</summary>

**本地增强(推荐):**
- ✅ 免费(使用 Claude Code Max)
- ✅ 质量 9/10
- ❌ 稍慢(30-60 秒)

**API 增强:**
- 需要 API key
- 速度快(10-20 秒)
- 适合批量处理
</details>

<details>
<summary>Q: 如何处理 10K+ 页文档?</summary>

```bash
# 1. 评估页数
skill-seekers estimate --config large.json

# 2. 拆分配置
skill-seekers split-config large.json --strategy router

# 3. 并行抓取
for config in large-*.json; do
  skill-seekers scrape --config $config &
done
wait

# 4. 生成路由
skill-seekers generate-router large-*.json
```
</details>

## 🔗 相关资源

- 🌐 官方网站: https://skillseekersweb.com/
- 📦 GitHub: https://github.com/yusufkaraaslan/Skill_Seekers
- 📚 完整文档: https://github.com/yusufkaraaslan/Skill_Seekers/tree/main/docs
- 🐛 问题反馈: https://github.com/yusufkaraaslan/Skill_Seekers/issues
- 📋 项目看板: https://github.com/users/yusufkaraaslan/projects/2

## 🎉 开始创建你的第一个 Skill!

```bash
# 验证安装
./verify.sh

# 选择场景并执行
skill-seekers install --config react

# 或在 OpenCode 中告诉 AI
"用 skill-seekers 为当前项目生成 skill"
```

---

**提示:** 将这个文件添加到收藏夹以便快速访问!

**许可证:** MIT - 详见原仓库 LICENSE 文件
