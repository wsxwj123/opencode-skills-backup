# Skill Seekers 快速参考

## 一键命令

```bash
# 🚀 最快速 - 一键完成所有流程
skill-seekers install --config <name>

# 示例
skill-seekers install --config react      # React
skill-seekers install --config django     # Django
skill-seekers install --config vue        # Vue.js
```

## 常用命令

### 本地项目

```bash
# 分析当前目录
skill-seekers-codebase --directory . --output output/my-project/

# 选择深度
skill-seekers-codebase --directory . --depth surface  # 快速
skill-seekers-codebase --directory . --depth deep     # 标准(推荐)
skill-seekers-codebase --directory . --depth full     # 完整
skill-seekers-codebase --directory . --depth c3x      # 超深度
```

### 文档网站

```bash
# 使用预设配置
skill-seekers scrape --config configs/react.json

# 自定义 URL
skill-seekers scrape --url https://example.com --name myskill

# 评估页数(先评估再抓取)
skill-seekers estimate --url https://example.com
```

### GitHub 仓库

```bash
# 基础分析
skill-seekers github --repo owner/repo

# 完整分析(推荐)
skill-seekers github --repo owner/repo \
    --include-issues \
    --include-changelog \
    --include-releases

# 使用认证(避免速率限制)
export GITHUB_TOKEN=ghp_your_token
skill-seekers github --repo owner/repo
```

### PDF 文档

```bash
# 基础提取
skill-seekers pdf --pdf docs/manual.pdf --name myskill

# 完整功能
skill-seekers pdf --pdf docs/manual.pdf --name myskill \
    --extract-tables \
    --ocr \
    --parallel
```

## 工作流命令

### 增强

```bash
# 本地增强(免费,推荐)
skill-seekers enhance output/myskill/ --ai-mode local

# API 增强(需要 API key)
skill-seekers enhance output/myskill/ --ai-mode api

# 自动选择
skill-seekers enhance output/myskill/ --ai-mode auto
```

### 打包

```bash
# 默认(Claude)
skill-seekers package output/myskill/

# 其他平台
skill-seekers package output/myskill/ --target gemini
skill-seekers package output/myskill/ --target openai
skill-seekers package output/myskill/ --target markdown

# 自动上传
skill-seekers package output/myskill/ --upload
```

### 安装

```bash
# 安装到 OpenCode
skill-seekers install-agent output/myskill/ --agent opencode

# 安装到所有代理
skill-seekers install-agent output/myskill/ --agent all

# 强制覆盖
skill-seekers install-agent output/myskill/ --agent opencode --force
```

## 配置管理

```bash
# 交互式配置
skill-seekers config

# GitHub Token
skill-seekers config --github

# 查看配置
skill-seekers config --show

# 测试连接
skill-seekers config --test
```

## 恢复任务

```bash
# 列出可恢复任务
skill-seekers resume --list

# 恢复特定任务
skill-seekers resume <task-id>

# 清理旧任务
skill-seekers resume --cleanup
```

## 高级功能

### 统一多源

```bash
# 创建配置
cat > unified.json << 'EOF'
{
  "name": "myproject",
  "sources": [
    {"type": "documentation", "base_url": "https://docs.example.com/"},
    {"type": "github", "repo": "owner/repo"},
    {"type": "pdf", "pdf_path": "docs/manual.pdf"}
  ]
}
EOF

# 统一抓取
skill-seekers unified --config unified.json
```

### 大型文档拆分

```bash
# 评估
skill-seekers estimate --config large.json

# 拆分
skill-seekers split-config large.json --strategy router

# 并行抓取
for config in large-*.json; do
  skill-seekers scrape --config $config &
done
wait

# 生成路由
skill-seekers generate-router large-*.json
```

### 异步模式(2-3x 速度)

```bash
# 启用异步
skill-seekers scrape --config large.json --async --workers 8

# 无速率限制
skill-seekers scrape --config large.json --async --no-rate-limit
```

## 在 OpenCode 中使用

直接告诉 AI:

```
"用 skill-seekers 为当前项目生成 skill"
"用 skill-seekers 从 React 官网创建 skill"
"分析 facebook/react 仓库并生成 skill"
"从 docs/manual.pdf 创建 skill"
```

## 环境变量

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
export ANTHROPIC_API_KEY=sk-ant-xxx    # Claude AI 增强
export GITHUB_TOKEN=ghp_xxx            # GitHub 访问
export GOOGLE_API_KEY=xxx              # Gemini 平台
export OPENAI_API_KEY=sk-xxx           # OpenAI 平台
```

## 参数速查

### 分析深度

- `surface` - 快速(1-2 分钟)
- `deep` - 标准(5-10 分钟,推荐)
- `full` - 完整(20-60 分钟)
- `c3x` - 超深度(20-60 分钟,含设计模式)

### AI 模式

- `none` - 无增强
- `local` - 本地增强(免费,推荐)
- `api` - API 增强(需要 key)
- `auto` - 自动选择

### 目标平台

- `claude` - Claude AI(默认)
- `gemini` - Google Gemini
- `openai` - OpenAI ChatGPT
- `markdown` - 通用 Markdown

### AI 代理

- `opencode` - OpenCode
- `claude` - Claude Code
- `cursor` - Cursor
- `windsurf` - Windsurf
- `all` - 所有代理

## 常见问题快速解决

| 问题 | 解决方案 |
|------|----------|
| GitHub 速率限制 | `skill-seekers config --github` |
| 增强失败 | `skill-seekers enhance --ai-mode local` |
| 大文档超时 | `skill-seekers split-config` + 并行 |
| 安装失败 | `skill-seekers install-agent --force` |
| PDF OCR 失败 | `pip install pytesseract Pillow` |

## 验证安装

```bash
# 运行验证脚本
./verify.sh

# 或手动检查
which skill-seekers
skill-seekers --version
skill-seekers config --show
```

## 完整工作流示例

### 示例 1: 快速生成

```bash
skill-seekers install --config react
```

### 示例 2: 完整自定义

```bash
skill-seekers estimate --url https://tailwindcss.com
skill-seekers scrape --url https://tailwindcss.com --name tailwind
skill-seekers enhance output/tailwind/ --ai-mode local
skill-seekers package output/tailwind/
skill-seekers install-agent output/tailwind/ --agent opencode
```

### 示例 3: GitHub 深度分析

```bash
export GITHUB_TOKEN=ghp_your_token
skill-seekers github --repo django/django \
    --include-issues --include-changelog --include-releases
skill-seekers enhance output/django/ --ai-mode local
skill-seekers package output/django/
skill-seekers install-agent output/django/ --agent all
```

### 示例 4: 本地项目

```bash
skill-seekers-codebase --directory . --depth full --ai-mode local
skill-seekers package output/my-project/ --no-open
skill-seekers install-agent output/my-project/ --agent opencode
```

## 获取帮助

- 📖 完整文档: [SKILL.md](SKILL.md)
- 🚀 使用指南: [USAGE.md](USAGE.md)
- 🌐 官方文档: https://github.com/yusufkaraaslan/Skill_Seekers
- 🐛 问题反馈: https://github.com/yusufkaraaslan/Skill_Seekers/issues

---

**提示:** 将此文件添加到书签或打印出来作为速查表!
