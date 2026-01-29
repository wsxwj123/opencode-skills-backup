# Skill Seekers - AI Skill 自动生成工具

> 🎯 **一键打包文档、代码和 GitHub 仓库为可用的 AI Skills**

## 快速链接

- 📖 **[完整文档](SKILL.md)** - 详细的命令参考和使用指南
- 🚀 **[使用指南](USAGE.md)** - 常见场景和工作流示例
- ⚙️ **[配置说明](skill.yaml)** - 命令快捷方式和参数说明

## 这是什么?

Skill Seekers 是一个强大的工具,可以将以下内容自动转换为 AI Skills:

- 🌐 **文档网站** (React, Vue, Django 等官方文档)
- 💻 **本地代码库** (你的项目源码)
- 🐙 **GitHub 仓库** (开源项目)
- 📄 **PDF 文档** (技术手册、论文)

**支持平台:** Claude Code, OpenCode, Cursor, Windsurf 等 10+ AI 编程助手

## 5 分钟快速开始

### 1. 安装

```bash
# 最简单的方式
pip install skill-seekers

# 或完整安装(推荐)
pip install skill-seekers[all]
```

### 2. 第一次使用

选择以下任一场景:

#### 场景 A: 分析当前项目

```bash
skill-seekers-codebase --directory . --output output/my-project/
```

#### 场景 B: 从官方文档创建 Skill

```bash
# 使用预设配置(最快)
skill-seekers install --config react

# 或自定义 URL
skill-seekers scrape --url https://vuejs.org --name vue
```

#### 场景 C: 分析 GitHub 仓库

```bash
# 设置 token(可选,避免速率限制)
export GITHUB_TOKEN=ghp_your_token

# 分析仓库
skill-seekers github --repo facebook/react
```

### 3. 打包和安装

```bash
# 打包
skill-seekers package output/my-project/

# 安装到 OpenCode
skill-seekers install-agent output/my-project/ --agent opencode

# 或安装到所有 AI 代理
skill-seekers install-agent output/my-project/ --agent all
```

### 4. 在 OpenCode 中使用

打开 OpenCode,直接告诉 AI:

```
"使用 skill-seekers 为当前项目生成一个 skill"
```

## 核心功能

| 功能 | 说明 | 命令 |
|------|------|------|
| 📊 **本地代码分析** | 深度分析项目代码 | `skill-seekers-codebase --directory .` |
| 🌐 **文档抓取** | 抓取在线文档 | `skill-seekers scrape --url https://...` |
| 🐙 **GitHub 分析** | 分析仓库+Issues | `skill-seekers github --repo owner/repo` |
| 📄 **PDF 提取** | 提取 PDF 内容 | `skill-seekers pdf --pdf doc.pdf` |
| 🔄 **多源统一** | 组合多个来源 | `skill-seekers unified --config unified.json` |
| ✨ **AI 增强** | 智能优化内容 | `skill-seekers enhance output/skill/` |
| 📦 **多平台打包** | 适配不同 LLM | `skill-seekers package --target <platform>` |
| 🤖 **安装到代理** | 一键安装 | `skill-seekers install-agent --agent <name>` |

## 支持的平台和代理

### LLM 平台
- ✅ Claude AI
- ✅ OpenCode
- ✅ Google Gemini
- ✅ OpenAI ChatGPT
- ✅ 通用 Markdown

### AI 代理
- ✅ Claude Code
- ✅ OpenCode
- ✅ Cursor
- ✅ Windsurf
- ✅ VS Code / Copilot
- ✅ Amp, Goose, Letta, Aide, Neovate Code

## 使用场景示例

### 场景 1: 快速一键流程

```bash
# 最简单 - 从配置到安装全自动
skill-seekers install --config django
```

**包含:** 抓取 → AI 增强 → 打包 → 上传(可选)

### 场景 2: 完整自定义流程

```bash
# 1. 评估页数
skill-seekers estimate --url https://tailwindcss.com

# 2. 抓取文档
skill-seekers scrape --url https://tailwindcss.com --name tailwind

# 3. AI 增强(本地免费)
skill-seekers enhance output/tailwind/ --ai-mode local

# 4. 打包
skill-seekers package output/tailwind/

# 5. 安装到 OpenCode
skill-seekers install-agent output/tailwind/ --agent opencode
```

### 场景 3: 分析 GitHub 仓库

```bash
# 深度分析(含 Issues 和 CHANGELOG)
export GITHUB_TOKEN=ghp_your_token
skill-seekers github --repo django/django \
    --include-issues \
    --include-changelog \
    --include-releases

# 增强和安装
skill-seekers enhance output/django/ --ai-mode local
skill-seekers package output/django/
skill-seekers install-agent output/django/ --agent all
```

### 场景 4: 统一多源

```bash
# 创建统一配置(文档 + GitHub + PDF)
cat > unified.json << 'EOF'
{
  "name": "myproject",
  "sources": [
    {"type": "documentation", "base_url": "https://docs.myproject.com/"},
    {"type": "github", "repo": "owner/myproject"},
    {"type": "pdf", "pdf_path": "docs/manual.pdf"}
  ]
}
EOF

# 统一抓取和处理
skill-seekers unified --config unified.json
skill-seekers enhance output/myproject/ --ai-mode local
skill-seekers package output/myproject/
```

## 常见问题

### Q: 如何避免 GitHub 速率限制?

设置 GitHub Token:

```bash
export GITHUB_TOKEN=ghp_your_token
# 或运行配置向导
skill-seekers config --github
```

### Q: 本地增强 vs API 增强?

**本地增强(推荐):**
- ✅ 免费(使用 Claude Code Max)
- ✅ 无需 API key
- ✅ 质量 9/10

**API 增强:**
- 需要 ANTHROPIC_API_KEY
- 速度更快(10-20秒 vs 30-60秒)

### Q: 如何处理大型文档(10K+ 页)?

使用拆分策略:

```bash
# 1. 评估
skill-seekers estimate --config large.json

# 2. 拆分
skill-seekers split-config large.json --strategy router

# 3. 并行抓取
for config in large-*.json; do
  skill-seekers scrape --config $config &
done
wait

# 4. 生成路由
skill-seekers generate-router large-*.json
```

## 验证安装

运行验证脚本检查一切是否就绪:

```bash
./verify.sh
```

或手动检查:

```bash
# 检查命令
which skill-seekers
which skill-seekers-codebase

# 查看版本
skill-seekers --version

# 检查配置
skill-seekers config --show
```

## 文件结构

```
skill-seekers/
├── SKILL.md          # 完整文档(推荐阅读)
├── USAGE.md          # 使用指南和示例
├── skill.yaml        # 配置和命令快捷方式
├── README.md         # 本文件
├── verify.sh         # 验证脚本
└── (原仓库文件...)  # 原始 Skill_Seekers 仓库内容
```

## 获取帮助

- 📖 完整文档: [SKILL.md](SKILL.md)
- 🚀 使用指南: [USAGE.md](USAGE.md)
- 🌐 官方网站: https://skillseekersweb.com/
- 📦 GitHub: https://github.com/yusufkaraaslan/Skill_Seekers
- 🐛 问题反馈: https://github.com/yusufkaraaslan/Skill_Seekers/issues

## 下一步

1. ✅ 已安装 Skill Seekers
2. ✅ 已安装到 OpenCode Skills
3. 📖 阅读 [SKILL.md](SKILL.md) 了解完整功能
4. 🚀 尝试 [USAGE.md](USAGE.md) 中的示例
5. 💬 在 OpenCode 中告诉 AI: "用 skill-seekers 帮我生成一个 skill"

## 许可证

MIT License - 详见原仓库 LICENSE 文件

---

**快速命令参考:**

```bash
# 分析本地项目
skill-seekers-codebase --directory . --output output/my-project/

# 从文档网站
skill-seekers scrape --url https://example.com --name example

# 从 GitHub
skill-seekers github --repo owner/repo

# 一键完成
skill-seekers install --config react

# 配置管理
skill-seekers config

# 验证安装
./verify.sh
```

**在 OpenCode 中直接使用:**

```
"用 skill-seekers 为当前项目生成 skill"
"用 skill-seekers 从 Vue.js 官网创建 skill"
"分析 facebook/react 仓库并生成 skill"
```

🎉 开始创建你的第一个 AI Skill 吧!
