# Skill Seekers - 使用指南

## 什么是这个 Skill?

这个 skill 打包了完整的 Skill Seekers 工具,让你可以在 OpenCode 和 Claude Code 中直接使用它来创建新的 Skills。

## 快速开始

### 1. 在 OpenCode 中使用

```bash
# 打开 OpenCode,然后告诉 AI:
"使用 skill-seekers 分析当前项目并生成一个 skill"

# 或更具体:
"用 skill-seekers 从 https://react.dev 创建一个 React skill"
```

### 2. 常用场景

#### 场景 A: 为现有项目创建 Skill

```
我: 帮我为当前项目创建一个 skill,深度分析,包含 AI 增强

OpenCode 会执行:
1. skill-seekers-codebase --directory . --depth full --ai-mode local --output output/my-project/
2. skill-seekers package output/my-project/ --no-open
3. skill-seekers install-agent output/my-project/ --agent opencode
```

#### 场景 B: 从文档网站创建 Skill

```
我: 从 Vue.js 官网创建一个 skill

OpenCode 会执行:
1. skill-seekers scrape --url https://vuejs.org --name vue --description "Vue.js framework"
2. skill-seekers enhance output/vue/ --ai-mode local
3. skill-seekers package output/vue/
4. skill-seekers install-agent output/vue/ --agent opencode
```

#### 场景 C: 从 GitHub 仓库创建 Skill

```
我: 分析 facebook/react 仓库并生成 skill

OpenCode 会执行:
1. export GITHUB_TOKEN=<your-token>  # 如果已配置
2. skill-seekers github --repo facebook/react --include-issues --include-changelog
3. skill-seekers enhance output/react/ --ai-mode local
4. skill-seekers package output/react/
5. skill-seekers install-agent output/react/ --agent all
```

#### 场景 D: 从 PDF 创建 Skill

```
我: 从 docs/manual.pdf 提取内容并生成 skill

OpenCode 会执行:
1. skill-seekers pdf --pdf docs/manual.pdf --name manual --extract-tables --ocr
2. skill-seekers enhance output/manual/ --ai-mode local
3. skill-seekers package output/manual/
```

#### 场景 E: 统一多源创建 Skill

```
我: 创建一个综合 skill,包含 Django 文档、GitHub 仓库和我的本地代码

OpenCode 会创建统一配置并执行:
1. 创建 unified config (docs + github + local)
2. skill-seekers unified --config configs/django_unified.json
3. skill-seekers detect-conflicts output/django/
4. skill-seekers enhance output/django/ --ai-mode local
5. skill-seekers package output/django/
6. skill-seekers install-agent output/django/ --agent opencode
```

## 自动化工作流

### 工作流 1: 一键生成(最简单)

```
我: 一键生成 React skill

OpenCode:
skill-seekers install --config react
# 自动: 抓取 → 增强 → 打包 → 上传
```

### 工作流 2: 完整自定义

```
我: 
1. 评估 Tailwind CSS 文档页数
2. 如果少于 500 页就全部抓取
3. 使用本地 AI 增强
4. 打包并安装到 OpenCode

OpenCode 会逐步执行:
1. skill-seekers estimate --url https://tailwindcss.com
2. (判断页数)
3. skill-seekers scrape --url https://tailwindcss.com --name tailwind
4. skill-seekers enhance output/tailwind/ --ai-mode local
5. skill-seekers package output/tailwind/
6. skill-seekers install-agent output/tailwind/ --agent opencode
```

## 配置管理

### 设置 GitHub Token(提高速率限制)

```
我: 帮我配置 GitHub token

OpenCode:
skill-seekers config --github
# 打开交互式向导
```

### 添加多个 GitHub 账户

```
我: 配置多个 GitHub 账户(个人、工作、开源)

OpenCode:
skill-seekers config
# → 选择 "1. GitHub Token Setup"
# → 添加 3 个配置文件
```

### 查看当前配置

```
我: 显示 skill-seekers 配置

OpenCode:
skill-seekers config --show
```

## 高级技巧

### 技巧 1: 批量处理

```
我: 为 configs/ 目录下所有配置生成 skills

OpenCode 会批量执行:
for config in configs/*.json; do
  skill-seekers install --config "$config" --no-upload
done
```

### 技巧 2: 大型文档优化

```
我: Godot 文档有 40K 页,帮我优化处理

OpenCode 会:
1. skill-seekers split-config configs/godot.json --strategy router
2. 并行抓取所有子配置
3. skill-seekers generate-router configs/godot-*.json
4. 生成路由 skill
```

### 技巧 3: 使用私有配置仓库

```
我: 从我们团队的私有仓库获取配置

OpenCode:
1. export GITHUB_TOKEN=<your-token>
2. 注册私有源
3. 从私有源获取配置
4. 生成 skill
```

### 技巧 4: 恢复中断的任务

```
我: 昨天的 React 抓取被中断了,继续完成

OpenCode:
1. skill-seekers resume --list  # 列出可恢复任务
2. skill-seekers resume github_react_20260126_143022  # 恢复特定任务
```

## 常见问题

### Q1: 如何选择分析深度?

**A:** 根据项目大小和需求选择:
- `surface`: 小项目(<1000 文件),快速概览
- `deep`: 中型项目(推荐),平衡速度和质量
- `full`: 大型项目,完整分析
- `c3x`: 需要设计模式和架构分析

### Q2: 本地增强 vs API 增强?

**A:** 推荐使用本地增强:
- ✅ 免费(使用 Claude Code Max 计划)
- ✅ 无需 API key
- ✅ 质量相当(9/10)
- ❌ 稍慢(30-60 秒 vs 10-20 秒)

API 增强适合:
- 需要批量处理
- 在 CI/CD 中使用
- 没有 Claude Code Max

### Q3: GitHub 速率限制怎么办?

**A:** 三个方法:
1. 设置 GitHub Token(60/小时 → 5000/小时)
2. 配置多个账户自动切换
3. 使用 `--rate-limit-strategy wait` 自动等待

### Q4: 如何处理超大文档?

**A:** 使用拆分策略:
1. 先评估: `skill-seekers estimate`
2. 拆分配置: `skill-seekers split-config`
3. 并行抓取所有子配置
4. 生成路由 skill 统一访问

### Q5: 生成的 skill 在哪里?

**A:** 
- 源文件: `output/<name>/`
- 打包文件: `output/<name>.zip`
- 已安装: `~/.config/opencode/skills/<name>/`

## 输出格式

### 支持的目标平台

```bash
# Claude AI (默认)
skill-seekers package output/myskill/ --target claude

# Google Gemini
skill-seekers package output/myskill/ --target gemini

# OpenAI ChatGPT
skill-seekers package output/myskill/ --target openai

# 通用 Markdown
skill-seekers package output/myskill/ --target markdown
```

### 生成的文件结构

```
output/myskill/
├── SKILL.md           # 主文档
├── skill.yaml         # 元数据
├── references/        # 参考文档
│   ├── api/
│   ├── guides/
│   └── examples/
├── knowledge/         # 知识库
│   ├── patterns.json
│   └── examples.json
└── metadata/          # 统计和冲突
    └── stats.json
```

## 性能优化建议

### 1. 使用异步模式(大型文档)

```bash
skill-seekers scrape --config large.json --async --workers 8
# 速度提升 2-3 倍
```

### 2. 利用缓存

```bash
# 第一次
skill-seekers scrape --config react.json

# 重建(秒级)
skill-seekers scrape --config react.json --skip-scrape
```

### 3. 并行处理

```bash
# 同时抓取多个配置
for config in configs/*.json; do
  skill-seekers scrape --config "$config" &
done
wait
```

### 4. 跳过不需要的分析

```bash
skill-seekers-codebase \
  --directory . \
  --skip-patterns \        # 跳过模式检测
  --skip-test-examples \   # 跳过测试示例
  --output output/quick/
```

## 安全最佳实践

### 1. 使用环境变量管理密钥

```bash
# ~/.bashrc 或 ~/.zshrc
export ANTHROPIC_API_KEY=sk-ant-xxx
export GITHUB_TOKEN=ghp_xxx
export GOOGLE_API_KEY=xxx
export OPENAI_API_KEY=sk-xxx
```

### 2. 配置文件权限

```bash
# Skill Seekers 自动设置 600 权限
ls -la ~/.config/skill-seekers/config.json
# -rw------- (只有所有者可读写)
```

### 3. 使用 .gitignore

```gitignore
# .gitignore
output/
*.zip
*.tar.gz
configs/*_private.json
.env
```

## 故障排除快速参考

| 问题 | 命令 |
|------|------|
| GitHub 速率限制 | `skill-seekers config --github` |
| 增强失败 | `skill-seekers enhance output/x/ --ai-mode local` |
| 大文档超时 | `skill-seekers split-config configs/x.json` |
| 安装失败 | `skill-seekers install-agent output/x/ --agent opencode --force` |
| PDF OCR 失败 | `pip install pytesseract Pillow && brew install tesseract` |
| 恢复中断任务 | `skill-seekers resume --list` |
| 测试配置 | `skill-seekers config --test` |

## 更多资源

- 主文档: [SKILL.md](./SKILL.md)
- 官方文档: https://github.com/yusufkaraaslan/Skill_Seekers/tree/main/docs
- 中文 README: https://github.com/yusufkaraaslan/Skill_Seekers/blob/main/README.zh-CN.md
- 快速开始: https://github.com/yusufkaraaslan/Skill_Seekers/blob/main/QUICKSTART.md
- 问题反馈: https://github.com/yusufkaraaslan/Skill_Seekers/issues

## 贡献指南

如果你想改进这个 skill:

1. Fork 原仓库: https://github.com/yusufkaraaslan/Skill_Seekers
2. 创建 feature 分支
3. 提交 PR

或者直接提交 Issue 报告问题或建议新功能!

---

**提示:** 这个 skill 已经安装在 `~/.config/opencode/skills/skill-seekers/`,你可以直接在 OpenCode 中使用!
