# 一键打包 OpenCode + Claude Code Skills

> 使用 `pack-opencode-skill.sh` 从任意来源快速创建双平台兼容的 AI Skills

## 🎯 功能特性

✅ **4 种数据源**：GitHub / 文档网站 / 本地代码 / PDF  
✅ **双平台兼容**：自动生成 OpenCode 和 Claude Code 元数据  
✅ **AI 增强**：可选的本地免费增强（使用 Claude Code Max）  
✅ **自动安装**：直接安装到两个平台的 skills 目录  
✅ **智能命名**：自动从输入源推断 skill 名称  

---

## 🚀 快速开始

### 1. 从 GitHub 仓库创建

```bash
./pack-opencode-skill.sh github microsoft/TypeScript --name typescript
```

**执行流程**：
1. 抓取 GitHub 仓库（代码 + README + Issues）
2. AI 增强（提取关键概念和示例）
3. 生成双平台元数据
4. 安装到 OpenCode 和 Claude Code

### 2. 从文档网站创建

```bash
./pack-opencode-skill.sh docs https://react.dev --name react --max-pages 200
```

**适用场景**：
- 官方文档（React, Vue, Django 等）
- API 参考文档
- 技术教程网站

### 3. 从本地代码库创建

```bash
./pack-opencode-skill.sh codebase ./my-project --name my-project --depth full
```

**分析深度**：
- `surface`：快速扫描（1-2 分钟）
- `deep`：标准分析（5-10 分钟，推荐）
- `full`：完整分析（20-60 分钟）

### 4. 从 PDF 文档创建

```bash
./pack-opencode-skill.sh pdf ~/Downloads/manual.pdf --name manual
```

**支持**：
- 普通 PDF（文本提取）
- 扫描 PDF（OCR）
- 加密 PDF（需要密码）

---

## 📋 命令参数

### 通用选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--name NAME` | 指定 skill 名称 | 自动推断 |
| `--no-enhance` | 跳过 AI 增强 | 启用增强 |
| `--no-claude` | 不安装到 Claude Code | 双平台安装 |
| `--help` | 显示帮助信息 | - |

### 模式特定选项

**docs 模式**：
- `--max-pages N`：最大抓取页数（默认 500）

**codebase 模式**：
- `--depth LEVEL`：分析深度 surface/deep/full（默认 deep）

---

## 💡 使用示例

### 示例 1: 快速创建 React Skill

```bash
# 最简单的方式（自动命名）
./pack-opencode-skill.sh docs https://react.dev

# 完整控制
./pack-opencode-skill.sh docs https://react.dev \
  --name react \
  --max-pages 200 \
  --no-enhance
```

### 示例 2: 分析开源项目

```bash
# 设置 GitHub Token（避免速率限制）
export GITHUB_TOKEN=ghp_your_token

# 创建 skill
./pack-opencode-skill.sh github facebook/react --name react-source
```

### 示例 3: 为团队项目创建 Skill

```bash
# 完整分析（包含设计模式和架构）
./pack-opencode-skill.sh codebase ~/work/my-api \
  --name my-api \
  --depth full
```

### 示例 4: 从技术手册创建 Skill

```bash
# PDF 文档
./pack-opencode-skill.sh pdf ~/Documents/api-manual.pdf \
  --name api-manual
```

---

## 🔧 在 OpenCode 中使用

创建 skill 后，在 OpenCode 中可以这样使用：

```
"使用 react skill：先总结它的内容，然后回答我的问题"

"根据 typescript skill 的文档，如何定义泛型接口？"

"参考 my-api skill，给我一个完整的 REST API 示例"
```

---

## 🎨 生成的文件结构

```
~/.config/opencode/skills/my-skill/
├── .opencode-skill          # OpenCode 元数据
├── .claude-skill            # Claude Code 元数据
├── .skillrc                 # 通用配置
├── SKILL.md                 # 主文档（AI 读取）
├── README.md                # 快速开始
├── references/              # 详细参考
│   ├── api/                # API 文档
│   ├── guides/             # 指南
│   └── examples/           # 示例
└── knowledge/              # 知识库
    ├── patterns.json       # 代码模式
    └── examples.json       # 提取的示例
```

---

## ⚙️ 高级配置

### 环境变量

```bash
# GitHub 访问（推荐）
export GITHUB_TOKEN=ghp_your_token

# Claude API（用于 API 增强模式）
export ANTHROPIC_API_KEY=sk-ant-xxx

# HTTP 代理（默认已设置）
export HTTP_PROXY=http://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897
```

### 自定义安装位置

脚本默认安装到：
- OpenCode: `~/.config/opencode/skills/`
- Claude Code: `~/.claude/skills/`

如需修改，编辑脚本中的变量：
```bash
SKILLS_DIR_OPENCODE="$HOME/.config/opencode/skills"
SKILLS_DIR_CLAUDE="$HOME/.claude/skills"
```

---

## 🐛 故障排除

### 问题 1: GitHub 速率限制

**症状**：`API rate limit exceeded`

**解决**：
```bash
# 设置 GitHub Token
export GITHUB_TOKEN=ghp_your_token

# 重新运行
./pack-opencode-skill.sh github owner/repo --name myskill
```

### 问题 2: AI 增强失败

**症状**：`Enhancement failed`

**解决**：
```bash
# 跳过增强（skill 仍可用）
./pack-opencode-skill.sh docs https://example.com --no-enhance
```

### 问题 3: 输出目录不存在

**症状**：`输出目录不存在`

**原因**：skill-seekers 命令执行失败

**解决**：
1. 检查网络连接（文档抓取需要网络）
2. 检查输入路径是否正确
3. 查看详细错误信息

### 问题 4: Claude Code 目录不存在

**症状**：`Claude Code skills 目录不存在`

**解决**：
```bash
# 创建目录
mkdir -p ~/.claude/skills

# 或跳过 Claude Code 安装
./pack-opencode-skill.sh docs https://example.com --no-claude
```

---

## 📊 性能参考

| 来源类型 | 数据量 | 耗时 | 增强耗时 |
|---------|--------|------|---------|
| GitHub 小型仓库 | <100 文件 | 2-5 分钟 | +30 秒 |
| GitHub 大型仓库 | >1000 文件 | 10-15 分钟 | +2 分钟 |
| 文档网站 | 100-200 页 | 10-20 分钟 | +1 分钟 |
| 文档网站 | 500+ 页 | 30-60 分钟 | +3 分钟 |
| 本地代码 (deep) | 中型项目 | 5-10 分钟 | N/A |
| 本地代码 (full) | 大型项目 | 20-60 分钟 | N/A |
| PDF 文档 | 50-100 页 | 2-5 分钟 | +30 秒 |

---

## 🔗 相关资源

- **skill-seekers 官方文档**：[SKILL.md](SKILL.md)
- **使用指南**：[USAGE.md](USAGE.md)
- **快速参考**：[QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **GitHub 仓库**：https://github.com/yusufkaraaslan/Skill_Seekers

---

## 💬 获取帮助

1. **查看帮助**：`./pack-opencode-skill.sh --help`
2. **验证安装**：`./verify.sh`
3. **在 OpenCode 中询问**：
   ```
   "pack-opencode-skill.sh 怎么用？"
   "如何从 GitHub 创建 skill？"
   ```

---

**🎉 开始创建你的第一个双平台 Skill 吧！**

```bash
./pack-opencode-skill.sh github your-org/your-repo --name your-skill
```
