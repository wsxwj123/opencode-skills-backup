# Skill Seekers 使用示例

本文档提供实际的使用示例,让你快速上手 Skill Seekers。

## 示例 1: 为 React 项目创建 Skill(最简单)

### 场景
你想为 React 官方文档创建一个 Skill,以便在编码时快速查阅。

### 步骤

```bash
# 一键完成
skill-seekers install --config react

# 等待 20-30 分钟...
# ✅ React skill 已自动创建并上传到 Claude
```

### 结果
- 抓取了 ~200 页 React 文档
- AI 增强优化了内容质量
- 自动打包为 `react.zip`
- (可选)自动上传到 Claude

### 在 OpenCode 中安装
```bash
skill-seekers install-agent output/react/ --agent opencode
```

---

## 示例 2: 分析本地 Python 项目

### 场景
你有一个 Django 项目,想为它创建一个 Skill 供 AI 助手参考。

### 步骤

```bash
# 进入项目目录
cd ~/projects/my-django-app

# 深度分析项目(包含设计模式和架构)
skill-seekers-codebase \
    --directory . \
    --depth full \
    --ai-mode local \
    --output output/my-django-app/

# 等待 5-10 分钟...

# 打包
skill-seekers package output/my-django-app/ --no-open

# 安装到 OpenCode
skill-seekers install-agent output/my-django-app/ --agent opencode
```

### 结果
```
output/my-django-app/
├── SKILL.md                 # AI 生成的项目概述
├── references/
│   ├── api/                # API 文档
│   ├── models/             # 数据模型
│   └── views/              # 视图函数
├── knowledge/
│   ├── patterns.json       # 检测到的设计模式
│   └── examples.json       # 代码示例
└── metadata/
    └── stats.json          # 项目统计
```

---

## 示例 3: 从 GitHub 创建 FastAPI Skill

### 场景
你想学习 FastAPI,需要从官方仓库创建一个全面的 Skill。

### 步骤

```bash
# 1. 设置 GitHub Token(避免速率限制)
export GITHUB_TOKEN=ghp_your_token_here

# 2. 深度分析 FastAPI 仓库
skill-seekers github \
    --repo tiangolo/fastapi \
    --include-issues \
    --max-issues 100 \
    --include-changelog \
    --include-releases \
    --code-analysis-depth deep

# 等待 10-15 分钟...

# 3. AI 增强(本地免费)
skill-seekers enhance output/fastapi/ --ai-mode local

# 4. 打包
skill-seekers package output/fastapi/

# 5. 安装到所有 AI 代理
skill-seekers install-agent output/fastapi/ --agent all
```

### 结果
- GitHub 仓库结构和代码分析
- 前 100 个 Issues 及其解决方案
- CHANGELOG 和 Release 历史
- 常见问题和最佳实践

---

## 示例 4: 统一多源创建综合 Skill

### 场景
你的公司有内部框架,需要组合官方文档、GitHub 仓库和技术手册 PDF。

### 步骤

```bash
# 1. 创建统一配置
cat > configs/company-framework.json << 'EOF'
{
  "name": "company-framework",
  "description": "公司内部框架完整知识库",
  "merge_mode": "rule-based",
  "sources": [
    {
      "type": "documentation",
      "base_url": "https://docs.company.com/framework/",
      "extract_api": true,
      "max_pages": 300
    },
    {
      "type": "github",
      "repo": "company/framework",
      "include_code": true,
      "include_issues": true,
      "code_analysis_depth": "deep"
    },
    {
      "type": "pdf",
      "pdf_path": "docs/framework-manual-v2.pdf",
      "extract_tables": true,
      "ocr": false
    }
  ]
}
EOF

# 2. 统一抓取
skill-seekers unified --config configs/company-framework.json

# 等待 30-45 分钟...

# 3. 检测冲突(文档 vs 代码)
skill-seekers detect-conflicts output/company-framework/

# 4. AI 增强
skill-seekers enhance output/company-framework/ --ai-mode local

# 5. 打包并安装
skill-seekers package output/company-framework/
skill-seekers install-agent output/company-framework/ --agent opencode
```

### 结果
- 综合了 3 个来源的知识
- 自动检测文档和代码的不一致
- 标记了过时的文档
- 识别了未记录的功能

---

## 示例 5: 处理大型文档(Godot Engine 40K 页)

### 场景
Godot Engine 文档有 40,000+ 页,直接抓取会超时。

### 步骤

```bash
# 1. 评估页数
skill-seekers estimate configs/godot.json
# 输出: ~40,500 页

# 2. 自动拆分为子技能
skill-seekers split-config configs/godot.json --strategy router

# 生成:
# - godot-scripting.json (5K 页)
# - godot-2d.json (8K 页)
# - godot-3d.json (10K 页)
# - godot-physics.json (6K 页)
# - godot-shaders.json (11K 页)

# 3. 并行抓取所有子配置
for config in configs/godot-*.json; do
  echo "抓取: $config"
  skill-seekers scrape --config "$config" &
done
wait

# 4. 生成智能路由/Hub 技能
skill-seekers generate-router configs/godot-*.json

# 5. 批量打包
for dir in output/godot-*/; do
  skill-seekers package "$dir"
done

# 6. 安装路由 skill
skill-seekers install-agent output/godot/ --agent opencode
```

### 结果
- 5 个专业子技能(脚本、2D、3D、物理、着色器)
- 1 个智能路由技能(自动导航到相关子技能)
- 总耗时: 4-6 小时(并行)vs 20-40 小时(单线程)

---

## 示例 6: 从 PDF 手册创建 Skill

### 场景
你有一个 500 页的技术手册 PDF,需要转换为可搜索的 Skill。

### 步骤

```bash
# 普通 PDF
skill-seekers pdf \
    --pdf docs/technical-manual-v3.pdf \
    --name tech-manual \
    --extract-tables \
    --parallel \
    --workers 8

# 扫描 PDF(需要 OCR)
skill-seekers pdf \
    --pdf docs/scanned-manual.pdf \
    --name scanned-manual \
    --ocr \
    --extract-tables \
    --parallel

# 加密 PDF
skill-seekers pdf \
    --pdf docs/protected-manual.pdf \
    --password mypassword \
    --name protected-manual \
    --extract-tables

# 增强和打包
skill-seekers enhance output/tech-manual/ --ai-mode local
skill-seekers package output/tech-manual/
skill-seekers install-agent output/tech-manual/ --agent opencode
```

### 结果
- 文本内容提取(OCR 支持扫描件)
- 表格数据提取并格式化
- 图片提取和描述
- 并行处理(快 3 倍)

---

## 示例 7: 在 OpenCode 中自然语言使用

### 场景
你在 OpenCode 中工作,想直接用自然语言创建 Skills。

### 对话示例

#### 示例 A: 分析当前项目
```
我: 用 skill-seekers 为当前项目生成一个 skill

OpenCode 会自动:
1. 检测项目类型和语言
2. 分析代码结构
3. 提取 API 和模式
4. 生成文档
5. 打包并安装到 OpenCode
```

#### 示例 B: 从文档网站
```
我: 用 skill-seekers 从 Tailwind CSS 官网创建一个 skill

OpenCode 会自动:
1. 评估页数(~300 页)
2. 抓取所有文档
3. AI 增强内容
4. 打包并安装
```

#### 示例 C: 从 GitHub
```
我: 分析 django/django 仓库并生成 skill,包含 Issues 和 CHANGELOG

OpenCode 会自动:
1. 克隆仓库
2. 分析代码结构
3. 获取 Issues 和 CHANGELOG
4. 生成综合 skill
5. 安装到 OpenCode
```

---

## 示例 8: 批量处理多个项目

### 场景
你管理多个开源项目,想为每个项目创建 Skill。

### 步骤

```bash
# 创建项目列表
cat > projects.txt << 'EOF'
facebook/react
vuejs/core
django/django
pallets/flask
tiangolo/fastapi
EOF

# 批量处理
while read repo; do
  name=$(echo $repo | cut -d'/' -f2)
  echo "处理: $repo"
  
  # 抓取
  skill-seekers github --repo $repo \
    --include-issues --max-issues 50 \
    --include-changelog
  
  # 增强
  skill-seekers enhance output/$name/ --ai-mode local
  
  # 打包
  skill-seekers package output/$name/
  
  echo "✅ $name 完成"
  echo ""
done < projects.txt

# 批量安装到 OpenCode
for dir in output/*/; do
  skill-seekers install-agent "$dir" --agent opencode
done

echo "🎉 所有项目已处理完成!"
```

---

## 示例 9: 配置多个 GitHub 账户(团队使用)

### 场景
你的团队有多个 GitHub 账户(个人、工作、开源),需要自动切换避免速率限制。

### 步骤

```bash
# 1. 运行配置向导
skill-seekers config

# 2. 选择 "1. GitHub Token Setup"

# 3. 添加多个配置文件:

# 配置文件 1: personal
# Token: ghp_personal_token
# Rate limit strategy: prompt
# Timeout: 30 minutes

# 配置文件 2: work  
# Token: ghp_work_token
# Rate limit strategy: switch
# Timeout: 30 minutes

# 配置文件 3: opensource
# Token: ghp_oss_token
# Rate limit strategy: wait
# Timeout: 60 minutes

# 4. 使用特定配置文件
skill-seekers github --repo mycompany/private-repo --profile work
skill-seekers github --repo personal/project --profile personal
skill-seekers github --repo opensource/project --profile opensource
```

### 结果
- 自动切换账户避免速率限制
- 每个配置文件有独立的策略
- 支持私有仓库访问

---

## 示例 10: 恢复中断的任务

### 场景
昨天的 React 抓取被中断了,现在想继续完成。

### 步骤

```bash
# 1. 列出可恢复的任务
skill-seekers resume --list

# 输出:
# Job ID: github_react_20260126_143022
# Type: github
# Repo: facebook/react
# Started: 2026-01-26 14:30:22
# Progress: 75% (150/200 pages)
# Status: interrupted

# 2. 恢复任务
skill-seekers resume github_react_20260126_143022

# 从 75% 继续,不重新抓取已完成的部分

# 3. 清理旧任务(7 天前)
skill-seekers resume --cleanup
```

---

## 实用技巧

### 技巧 1: 使用异步模式加速
```bash
# 大型文档使用异步(快 2-3 倍)
skill-seekers scrape --config large.json --async --workers 8
```

### 技巧 2: 利用缓存快速重建
```bash
# 第一次抓取
skill-seekers scrape --config react.json

# 重建(秒级,使用缓存)
skill-seekers scrape --config react.json --skip-scrape
```

### 技巧 3: 预览不执行
```bash
# 查看将要执行的操作
skill-seekers install --config godot --dry-run
```

### 技巧 4: 跳过不需要的分析
```bash
# 快速分析(跳过模式检测和测试提取)
skill-seekers-codebase \
    --directory . \
    --skip-patterns \
    --skip-test-examples \
    --output output/quick/
```

### 技巧 5: 指定输出平台
```bash
# 同时为多个平台打包
skill-seekers package output/react/ --target claude
skill-seekers package output/react/ --target gemini
skill-seekers package output/react/ --target openai
```

---

## 故障排除示例

### 问题 1: GitHub 速率限制
```bash
# 症状: "API rate limit exceeded"

# 解决方案 1: 设置 token
export GITHUB_TOKEN=ghp_your_token

# 解决方案 2: 配置多账户
skill-seekers config --github

# 解决方案 3: 使用等待策略
skill-seekers github --repo owner/repo --rate-limit-strategy wait
```

### 问题 2: 增强失败
```bash
# 症状: "Enhancement failed: API key not found"

# 解决方案: 使用本地增强(免费)
skill-seekers enhance output/myskill/ --ai-mode local
```

### 问题 3: 大文档超时
```bash
# 症状: 抓取 10K+ 页超时

# 解决方案: 使用拆分策略
skill-seekers split-config large.json --strategy router
for config in large-*.json; do
  skill-seekers scrape --config $config &
done
wait
```

---

## 更多示例

完整示例和更新请访问:
- 📖 [USAGE.md](USAGE.md) - 详细使用指南
- 📚 [官方文档](https://github.com/yusufkaraaslan/Skill_Seekers/tree/main/docs)
- 💡 [GitHub Issues](https://github.com/yusufkaraaslan/Skill_Seekers/issues) - 社区问题和解决方案

---

**提示:** 收藏这个文件以便快速参考实际使用案例!
