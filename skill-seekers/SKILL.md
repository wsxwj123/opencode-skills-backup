---
name: skill-seekers
description: 从文档网站、代码库和 GitHub 仓库自动生成 LLM Skills,支持 Claude、OpenCode 等多个 AI 平台
version: 2.7.4
---

# Skill Seekers - AI Skill 自动生成工具

## 概述

Skill Seekers 是一个强大的自动化工具,可以将文档网站、GitHub 仓库、PDF 文件和本地代码库转换为生产就绪的 AI Skills。支持 Claude Code、OpenCode、Cursor、Windsurf 等多个 AI 平台。

**核心能力:**
- 🌐 文档网站抓取与分析
- 🐙 GitHub 仓库深度解析
- 📄 PDF 文档提取(含 OCR)
- 💻 本地代码库分析(支持多语言 AST)
- 🔄 多源统一打包
- ✨ AI 增强优化
- 🤖 多平台自动适配

## 前置要求

```bash
# 安装 Skill Seekers
pip install skill-seekers

# 或使用 uv (更快)
uv pip install skill-seekers

# 安装完整功能(包含所有 LLM 平台支持)
pip install skill-seekers[all]
```

**环境变量配置(可选):**
```bash
export ANTHROPIC_API_KEY=sk-ant-xxx  # Claude AI 增强
export GITHUB_TOKEN=ghp_xxx          # GitHub 访问(提高速率限制)
export GOOGLE_API_KEY=xxx            # Gemini 平台支持
export OPENAI_API_KEY=sk-xxx         # OpenAI 平台支持
```

## 快速开始

### 方式 1: 分析本地代码库 (推荐用于现有项目)

```bash
# 分析本地项目
skill-seekers-codebase --directory /path/to/project --output output/my-skill/

# 选择分析深度
skill-seekers-codebase --directory ./myproject \
    --depth full \              # surface/deep/full
    --ai-mode local \           # 使用本地 Claude Code 增强
    --output output/myproject/

# 跳过某些分析加快速度
skill-seekers-codebase --directory ./myproject \
    --skip-patterns \           # 跳过模式检测
    --skip-test-examples \      # 跳过测试示例
    --output output/myproject/
```

### 方式 2: 抓取文档网站

```bash
# 使用预设配置(快速开始)
skill-seekers scrape --config configs/react.json

# 自定义 URL 抓取
skill-seekers scrape \
    --url https://react.dev/ \
    --name react \
    --description "React framework for building UIs"

# 评估页面数量(抓取前)
skill-seekers estimate --config configs/react.json
```

### 方式 3: 分析 GitHub 仓库

```bash
# 基础仓库分析
skill-seekers github --repo facebook/react

# 深度分析(包含 Issues 和 Releases)
skill-seekers github --repo django/django \
    --include-issues \
    --max-issues 100 \
    --include-changelog \
    --include-releases

# 使用认证(避免速率限制)
export GITHUB_TOKEN=ghp_your_token
skill-seekers github --repo owner/private-repo --profile work
```

### 方式 4: 提取 PDF 文档

```bash
# 基础 PDF 提取
skill-seekers pdf --pdf docs/manual.pdf --name myskill

# 高级功能(表格、OCR、并行)
skill-seekers pdf --pdf docs/manual.pdf --name myskill \
    --extract-tables \          # 提取表格
    --ocr \                     # OCR 扫描件
    --parallel \                # 并行处理
    --workers 8                 # 8 个工作线程

# 加密 PDF
skill-seekers pdf --pdf docs/encrypted.pdf --password mypass --name myskill
```

## 核心命令

### 1. 一键安装工作流

**最快速的端到端流程 - 从配置到上传的完全自动化:**

```bash
# 从官方配置安装(自动上传到 Claude)
skill-seekers install --config react

# 从本地配置文件安装
skill-seekers install --config configs/custom.json

# 无限制抓取(不限页数)
skill-seekers install --config godot --unlimited

# 预览工作流(不执行)
skill-seekers install --config react --dry-run

# 仅打包不上传
skill-seekers install --config django --no-upload
```

**执行的 5 个阶段:**
1. ✅ 获取配置(如果提供配置名)
2. ✅ 抓取文档(尊重速率限制)
3. ✅ AI 增强(必需,质量提升 3/10 → 9/10)
4. ✅ 打包 Skill
5. ✅ 上传到 Claude(如果设置了 API key)

### 2. 统一多源抓取

**组合文档 + GitHub + PDF 为一个技能,带冲突检测:**

```bash
# 使用现有统一配置
skill-seekers unified --config configs/react_unified.json

# 创建自定义统一配置
cat > configs/myframework_unified.json << 'EOF'
{
  "name": "myframework",
  "description": "从文档和代码生成完整框架知识",
  "merge_mode": "rule-based",
  "sources": [
    {
      "type": "documentation",
      "base_url": "https://docs.myframework.com/",
      "extract_api": true,
      "max_pages": 200
    },
    {
      "type": "github",
      "repo": "owner/myframework",
      "include_code": true,
      "code_analysis_depth": "surface"
    }
  ]
}
EOF

skill-seekers unified --config configs/myframework_unified.json
```

**冲突检测功能:**
- 🔴 代码中缺失(高优先级): 有文档但未实现
- 🟡 文档中缺失(中优先级): 已实现但未记录
- ⚠️ 签名不匹配: 参数或类型不同
- ℹ️ 描述不匹配: 说明不一致

### 3. 打包和上传

```bash
# 打包 Skill
skill-seekers package output/react/

# 自动上传到 Claude(需要 API key)
skill-seekers package output/react/ --upload

# 上传已有的 zip
skill-seekers upload output/react.zip

# 为不同平台打包
skill-seekers package output/react/ --target claude    # 默认
skill-seekers package output/react/ --target gemini    # Google Gemini
skill-seekers package output/react/ --target openai    # ChatGPT
skill-seekers package output/react/ --target markdown  # 通用 Markdown
```

### 4. 安装到 AI 代理

```bash
# 安装到特定代理
skill-seekers install-agent output/react/ --agent cursor
skill-seekers install-agent output/react/ --agent claude

# 一键安装到所有代理
skill-seekers install-agent output/react/ --agent all

# 强制覆盖已有安装
skill-seekers install-agent output/react/ --agent opencode --force

# 预览安装(不实际执行)
skill-seekers install-agent output/react/ --agent cursor --dry-run
```

**支持的 AI 代理:**
- Claude Code (`~/.claude/skills/`)
- OpenCode (`~/.config/opencode/skills/`)
- Cursor (`.cursor/skills/`)
- Windsurf (`~/.windsurf/skills/`)
- VS Code / Copilot (`.github/skills/`)
- Amp (`~/.amp/skills/`)
- Goose (`~/.config/goose/skills/`)
- Letta (`~/.letta/skills/`)
- Aide (`~/.aide/skills/`)
- Neovate Code (`~/.neovate/skills/`)

### 5. 配置管理

```bash
# 交互式配置向导
skill-seekers config

# GitHub Token 设置
skill-seekers config --github

# 查看当前配置
skill-seekers config --show

# 测试连接
skill-seekers config --test

# 添加多个 GitHub 配置文件(个人/工作/开源)
skill-seekers config
# → 选择 "1. GitHub Token Setup"
# → 添加多个配置文件
```

### 6. 恢复中断的任务

```bash
# 列出可恢复的任务
skill-seekers resume --list

# 恢复特定任务
skill-seekers resume github_react_20260117_143022

# 清理旧任务(7 天前)
skill-seekers resume --cleanup
```

## 高级功能

### 1. AI 增强

**将基础 Skill (⭐⭐) 转换为专业教程 (⭐⭐⭐⭐⭐):**

```bash
# 抓取时使用 API 增强(需要 ANTHROPIC_API_KEY)
skill-seekers scrape --config configs/react.json --enhance

# 使用本地 Claude Code 增强(免费,推荐)
skill-seekers scrape --config configs/react.json --enhance-local

# 单独增强已抓取的 Skill(API 模式)
skill-seekers enhance output/react/ --ai-mode api

# 单独增强(LOCAL 模式,免费)
skill-seekers enhance output/react/ --ai-mode local

# 自动模式(检测最佳选项)
skill-seekers enhance output/react/ --ai-mode auto

# 禁用增强
skill-seekers enhance output/react/ --ai-mode none
```

**增强内容包括:**
- 🔍 步骤说明 - 自然语言解释
- 🔧 故障排除 - 诊断流程和解决方案
- 📋 前置条件 - 为什么需要 + 设置说明
- 🔗 下一步 - 相关指南、变体、学习路径
- 💡 用例场景 - 实际应用场景

### 2. 大型文档处理(10K-40K+ 页)

**针对 Godot、AWS、Microsoft Docs 等超大文档:**

```bash
# 1. 先评估页数
skill-seekers estimate configs/godot.json

# 2. 自动拆分为子技能
python3 -m skill_seekers.cli.split_config configs/godot.json --strategy router

# 生成:
# - godot-scripting.json (5K 页)
# - godot-2d.json (8K 页)
# - godot-3d.json (10K 页)
# - godot-physics.json (6K 页)
# - godot-shaders.json (11K 页)

# 3. 并行抓取所有配置(4-8 小时 vs 20-40 小时!)
for config in configs/godot-*.json; do
  skill-seekers scrape --config $config &
done
wait

# 4. 生成智能路由/Hub 技能
python3 -m skill_seekers.cli.generate_router configs/godot-*.json

# 5. 打包所有技能
python3 -m skill_seekers.cli.package_multi output/godot*/
```

### 3. 异步模式(2-3 倍速度提升)

```bash
# 启用异步模式(8 工作线程,推荐大型文档)
skill-seekers scrape --config configs/react.json --async --workers 8

# 小型文档(100-500 页)
skill-seekers scrape --config configs/mydocs.json --async --workers 4

# 大型文档(2000+ 页,无速率限制)
skill-seekers scrape --config configs/largedocs.json --async --workers 8 --no-rate-limit
```

**性能对比:**
- 同步模式(线程): ~18 页/秒, 120 MB 内存
- 异步模式: ~55 页/秒, 40 MB 内存
- 结果: 快 3 倍, 内存减少 66%!

### 4. 私有配置仓库

**团队共享自定义配置(支持私有 Git 仓库):**

```bash
# 设置 GitHub Token(一次性)
export GITHUB_TOKEN=ghp_your_token_here

# 注册团队的私有仓库
skill-seekers config
# → 添加 Git 源
# → 输入仓库 URL: https://github.com/mycompany/skill-configs.git

# 从团队仓库获取配置
fetch_config(source="team", config_name="internal-api")

# 列出所有已注册源
list_config_sources()

# 移除源
remove_config_source(name="team")
```

**支持的平台:**
- GitHub (`GITHUB_TOKEN`)
- GitLab (`GITLAB_TOKEN`)
- Gitea (`GITEA_TOKEN`)
- Bitbucket (`BITBUCKET_TOKEN`)
- 任何 Git 服务器(`GIT_TOKEN`)

### 5. 速率限制策略

**4 种策略处理 GitHub API 限制:**

```bash
# prompt(默认) - 询问如何处理
skill-seekers github --repo owner/repo --rate-limit-strategy prompt

# wait - 自动等待(带倒计时)
skill-seekers github --repo owner/repo --rate-limit-strategy wait

# switch - 自动切换到另一个配置文件
skill-seekers github --repo owner/repo --rate-limit-strategy switch

# fail - 立即失败(适合 CI/CD)
skill-seekers github --repo owner/repo --rate-limit-strategy fail --non-interactive
```

## 配置文件示例

### 基础文档配置

```json
{
  "name": "react",
  "description": "React documentation",
  "base_url": "https://react.dev/",
  "start_urls": [
    "https://react.dev/learn",
    "https://react.dev/reference"
  ],
  "url_patterns": [
    "https://react.dev/learn/**",
    "https://react.dev/reference/**"
  ],
  "categories": {
    "api": ["reference", "api"],
    "guides": ["learn", "tutorial"],
    "examples": ["examples"]
  },
  "max_pages": 200
}
```

### 统一配置(文档 + GitHub)

```json
{
  "name": "myframework",
  "description": "Complete framework knowledge",
  "merge_mode": "rule-based",
  "sources": [
    {
      "type": "documentation",
      "base_url": "https://docs.myframework.com/",
      "extract_api": true,
      "max_pages": 200
    },
    {
      "type": "github",
      "repo": "owner/myframework",
      "include_code": true,
      "include_issues": true,
      "max_issues": 50,
      "code_analysis_depth": "deep"
    },
    {
      "type": "pdf",
      "pdf_path": "docs/manual.pdf",
      "extract_tables": true,
      "ocr": false
    }
  ]
}
```

### GitHub 配置

```json
{
  "name": "react-github",
  "repo": "facebook/react",
  "include_code": true,
  "include_issues": true,
  "max_issues": 100,
  "include_changelog": true,
  "include_releases": true,
  "code_analysis_depth": "deep",
  "languages": ["javascript", "typescript"]
}
```

## 常用工作流

### 工作流 1: 快速生成文档 Skill

```bash
# 1. 评估页数
skill-seekers estimate --url https://docs.example.com

# 2. 抓取文档
skill-seekers scrape \
    --url https://docs.example.com \
    --name example \
    --description "Example documentation"

# 3. AI 增强(本地免费)
skill-seekers enhance output/example/ --ai-mode local

# 4. 打包
skill-seekers package output/example/

# 5. 安装到 OpenCode
skill-seekers install-agent output/example/ --agent opencode

# 总耗时: 20-30 分钟
```

### 工作流 2: GitHub 仓库深度分析

```bash
# 1. 配置 GitHub Token(避免速率限制)
export GITHUB_TOKEN=ghp_your_token

# 2. 深度分析仓库
skill-seekers github --repo owner/repo \
    --include-issues \
    --include-changelog \
    --include-releases \
    --code-analysis-depth deep

# 3. 增强和打包
skill-seekers enhance output/repo/ --ai-mode local
skill-seekers package output/repo/

# 4. 安装到多个代理
skill-seekers install-agent output/repo/ --agent all

# 总耗时: 10-15 分钟(取决于仓库大小)
```

### 工作流 3: 统一多源 Skill

```bash
# 1. 创建统一配置(文档 + GitHub + PDF)
cat > configs/unified.json << 'EOF'
{
  "name": "myproject",
  "merge_mode": "rule-based",
  "sources": [
    {"type": "documentation", "base_url": "https://docs.myproject.com/"},
    {"type": "github", "repo": "owner/myproject"},
    {"type": "pdf", "pdf_path": "docs/manual.pdf"}
  ]
}
EOF

# 2. 统一抓取
skill-seekers unified --config configs/unified.json

# 3. 检测冲突
skill-seekers detect-conflicts output/myproject/

# 4. 增强和打包
skill-seekers enhance output/myproject/ --ai-mode local
skill-seekers package output/myproject/

# 5. 上传到 Claude
skill-seekers upload output/myproject.zip

# 总耗时: 30-45 分钟
```

### 工作流 4: 本地代码库 Skill

```bash
# 1. 分析本地项目(完整深度)
skill-seekers-codebase \
    --directory /path/to/project \
    --depth full \
    --ai-mode local \
    --output output/myproject/

# 2. 直接打包(已包含增强)
skill-seekers package output/myproject/ --no-open

# 3. 安装到 OpenCode 和 Claude
skill-seekers install-agent output/myproject/ --agent opencode
skill-seekers install-agent output/myproject/ --agent claude

# 总耗时: 5-10 分钟(取决于项目大小)
```

## 命令参数速查

### 通用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config FILE` | 配置文件路径 | - |
| `--output DIR` | 输出目录 | `output/<name>/` |
| `--name NAME` | Skill 名称 | 从配置推断 |
| `--force` | 强制覆盖已有文件 | `false` |
| `--dry-run` | 预览不执行 | `false` |

### 抓取参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--url URL` | 文档 URL | - |
| `--max-pages N` | 最大页数 | `500` |
| `--async` | 启用异步模式 | `false` |
| `--workers N` | 工作线程数 | `4` |
| `--skip-scrape` | 跳过抓取(使用缓存) | `false` |
| `--enhance` | API 增强 | `false` |
| `--enhance-local` | 本地增强 | `false` |

### GitHub 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--repo OWNER/NAME` | 仓库名 | - |
| `--include-issues` | 包含 Issues | `false` |
| `--max-issues N` | 最大 Issues 数 | `50` |
| `--include-changelog` | 包含 CHANGELOG | `false` |
| `--include-releases` | 包含 Releases | `false` |
| `--code-analysis-depth` | 代码分析深度 | `surface` |
| `--profile NAME` | GitHub 配置文件 | `default` |

### 代码库分析参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--directory DIR` | 项目目录 | - |
| `--depth LEVEL` | 分析深度 | `deep` |
| `--ai-mode MODE` | AI 增强模式 | `auto` |
| `--skip-patterns` | 跳过模式检测 | `false` |
| `--skip-test-examples` | 跳过测试示例 | `false` |

### 打包参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--target PLATFORM` | 目标平台 | `claude` |
| `--upload` | 自动上传 | `false` |
| `--no-open` | 不打开输出目录 | `false` |

## 故障排除

### 问题 1: GitHub 速率限制

**症状:** "API rate limit exceeded (60/hour)"

**解决方案:**
```bash
# 1. 设置 GitHub Token(提升到 5000/小时)
export GITHUB_TOKEN=ghp_your_token

# 2. 配置多个账户自动切换
skill-seekers config
# → 添加多个 GitHub 配置文件

# 3. 使用速率限制策略
skill-seekers github --repo owner/repo --rate-limit-strategy wait
```

### 问题 2: 增强失败

**症状:** "Enhancement failed: API key not found"

**解决方案:**
```bash
# 使用本地增强(免费,无需 API key)
skill-seekers enhance output/myskill/ --ai-mode local

# 或设置 API key
export ANTHROPIC_API_KEY=sk-ant-xxx
skill-seekers enhance output/myskill/ --ai-mode api
```

### 问题 3: 大型文档抓取超时

**症状:** 抓取 10K+ 页时超时或崩溃

**解决方案:**
```bash
# 1. 使用拆分策略
skill-seekers split-config configs/large.json --strategy router

# 2. 并行抓取子配置
for config in configs/large-*.json; do
  skill-seekers scrape --config $config &
done
wait

# 3. 生成路由技能
skill-seekers generate-router configs/large-*.json
```

### 问题 4: 安装到 AI 代理失败

**症状:** "Agent path not found: ~/.config/opencode/skills/"

**解决方案:**
```bash
# 1. 手动创建目录
mkdir -p ~/.config/opencode/skills/

# 2. 强制重新安装
skill-seekers install-agent output/myskill/ --agent opencode --force

# 3. 验证安装
ls -la ~/.config/opencode/skills/myskill/
```

### 问题 5: PDF 提取失败

**症状:** "PDF extraction failed: OCR not available"

**解决方案:**
```bash
# 安装 OCR 依赖
pip install pytesseract Pillow

# macOS 安装 tesseract
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# 重试提取
skill-seekers pdf --pdf docs/scanned.pdf --name myskill --ocr
```

## 输出结构

生成的 Skill 目录结构:

```
output/myskill/
├── SKILL.md                # 主文档(增强后的概述)
├── skill.yaml              # 元数据配置
├── references/             # 参考文档
│   ├── api/               # API 参考
│   ├── guides/            # 指南
│   ├── examples/          # 示例代码
│   └── tutorials/         # 教程
├── knowledge/             # 知识库
│   ├── patterns.json      # 代码模式
│   ├── examples.json      # 提取的示例
│   └── quick_reference.md # 快速参考
└── metadata/              # 元数据
    ├── source_info.json   # 源信息
    ├── stats.json         # 统计信息
    └── conflicts.json     # 冲突报告(如有)
```

打包后的文件:

```
myskill.zip                # Claude AI
myskill-gemini.tar.gz      # Google Gemini
myskill-openai.zip         # OpenAI ChatGPT
myskill-markdown.zip       # 通用 Markdown
```

## 最佳实践

### 1. 选择合适的分析深度

- `surface`: 快速(1-2 分钟),基础信息
- `deep`: 标准(5-10 分钟),推荐用于大多数项目
- `full`: 完整(20-60 分钟),用于复杂大型项目
- `c3x`: 超深度(20-60 分钟),包含设计模式和架构分析

### 2. 利用缓存加速

```bash
# 第一次抓取
skill-seekers scrape --config configs/react.json

# 后续重建(使用缓存,秒级完成)
skill-seekers scrape --config configs/react.json --skip-scrape

# 仅重新增强
skill-seekers enhance output/react/ --ai-mode local
```

### 3. 组合使用多个源

```bash
# 创建统一配置,结合多个信息源
{
  "sources": [
    {"type": "documentation", "base_url": "https://docs.example.com/"},
    {"type": "github", "repo": "owner/repo"},
    {"type": "pdf", "pdf_path": "docs/manual.pdf"},
    {"type": "local", "directory": "/path/to/code"}
  ]
}
```

### 4. 使用评估避免浪费时间

```bash
# 先评估再抓取
skill-seekers estimate --config configs/large.json
# 输出: 预估 12,500 页, 需要 2-3 小时

# 根据评估决定是否拆分
if [ pages > 1000 ]; then
  skill-seekers split-config configs/large.json --strategy router
fi
```

### 5. 批量处理多个项目

```bash
# 批量抓取多个配置
for config in configs/*.json; do
  echo "Processing $config..."
  skill-seekers install --config "$config" --no-upload
done

# 批量打包
for dir in output/*/; do
  skill-seekers package "$dir"
done

# 批量安装到所有代理
for zip in output/*.zip; do
  dir="${zip%.zip}"
  skill-seekers install-agent "$dir" --agent all
done
```

## 相关资源

- 官方网站: https://skillseekersweb.com/
- GitHub 仓库: https://github.com/yusufkaraaslan/Skill_Seekers
- PyPI 包: https://pypi.org/project/skill-seekers/
- 文档: https://github.com/yusufkaraaslan/Skill_Seekers/tree/main/docs
- 问题反馈: https://github.com/yusufkaraaslan/Skill_Seekers/issues
- 项目看板: https://github.com/users/yusufkaraaslan/projects/2

## 更新日志

### v2.7.4 (最新)
- ✅ 智能速率限制管理
- ✅ 多 GitHub 账户配置
- ✅ 恢复中断任务
- ✅ CI/CD 非交互模式
- ✅ 自助配置向导

### v2.6.0
- ✅ 三流 GitHub 架构(代码/文档/洞察)
- ✅ 统一代码库分析器
- ✅ C3.x 深度分析
- ✅ 增强路由生成

### v2.5.0
- ✅ 多 LLM 平台支持(Claude/Gemini/OpenAI/Markdown)
- ✅ 平台特定打包
- ✅ 可选依赖安装

### v2.4.0
- ✅ MCP SDK v1.25.0 升级
- ✅ FastMCP 框架
- ✅ 多代理支持(5 个 AI 代理)
- ✅ HTTP + stdio 传输

## 许可证

MIT License - 详见 LICENSE 文件

---

**快速链接:**
- [快速开始](#快速开始)
- [核心命令](#核心命令)
- [高级功能](#高级功能)
- [配置示例](#配置文件示例)
- [工作流](#常用工作流)
- [故障排除](#故障排除)
