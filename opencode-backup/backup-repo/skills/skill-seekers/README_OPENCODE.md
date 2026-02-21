# 欢迎使用 Skill Seekers! 🎉

> 🚀 **OpenCode / Claude Code 专用版本 - 已完成打包和配置**

## 这是什么?

Skill Seekers 是一个强大的工具,可以将文档、代码和 GitHub 仓库**自动转换**为高质量的 AI Skills。

这个 skill 已经为 OpenCode 和 Claude Code 完全配置好,开箱即用!

---

## ⚡ 3 秒快速开始

### 在 OpenCode 中(最简单)

直接告诉 AI:

```
"用 skill-seekers 为当前项目生成一个 skill"
```

就这么简单! AI 会自动处理一切。

### 命令行使用

```bash
# 分析当前项目
skill-seekers-codebase --directory . --output output/my-project/

# 一键生成 React skill
skill-seekers install --config react
```

---

## 📖 文档导航

**根据你的需求选择:**

| 如果你想... | 阅读这个 |
|-------------|----------|
| 🎯 **快速测试** | [GET_STARTED.md](GET_STARTED.md) ← 从这里开始! |
| 📚 **完整学习** | [SKILL.md](SKILL.md) |
| 💡 **看实际案例** | [EXAMPLES.md](EXAMPLES.md) |
| 🚀 **学习场景** | [USAGE.md](USAGE.md) |
| ⚡ **查命令** | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| 🔍 **验证安装** | 运行 `./verify.sh` |
| 🧪 **测试功能** | 运行 `./test-skill.sh` |

---

## 🎯 能做什么?

Skill Seekers 可以从以下来源创建 Skills:

| 来源 | 命令 | 耗时 |
|------|------|------|
| 🏠 本地项目 | `skill-seekers-codebase --directory .` | 2-10 分钟 |
| 🌐 文档网站 | `skill-seekers scrape --url <url>` | 10-30 分钟 |
| 🐙 GitHub | `skill-seekers github --repo <repo>` | 5-15 分钟 |
| 📄 PDF | `skill-seekers pdf --pdf <file>` | 2-10 分钟 |
| 🔄 多源统一 | `skill-seekers unified --config <json>` | 20-45 分钟 |

---

## ✅ 验证状态

```bash
$ ./verify.sh

✅ Python 3.10.11 (>= 3.10)
✅ skill-seekers 已安装 (v2.7.2)
✅ Skill 目录存在
✅ SKILL.md 存在
✅ 所有关键检查通过!
```

---

## 🚀 推荐流程

### 新手(第一次使用)

```bash
# 1. 验证
./verify.sh

# 2. 快速测试
skill-seekers install --config react --no-upload

# 3. 查看结果
ls output/react/

# 4. 学习更多
cat GET_STARTED.md
```

### 日常使用

**在 OpenCode 中:**
```
"用 skill-seekers 为当前项目生成 skill"
"用 skill-seekers 从 Tailwind 官网创建 skill"
"分析 django/django 仓库并生成 skill"
```

**命令行:**
```bash
skill-seekers-codebase --directory . --depth deep
skill-seekers package output/my-project/
skill-seekers install-agent output/my-project/ --agent opencode
```

---

## 💪 核心优势

✅ **一键打包** - 从配置到安装全自动  
✅ **多源支持** - 代码、文档、GitHub、PDF  
✅ **AI 增强** - 质量从 ⭐⭐ 提升到 ⭐⭐⭐⭐⭐  
✅ **冲突检测** - 自动发现文档和代码的不一致  
✅ **多平台** - Claude、Gemini、OpenAI、通用 Markdown  
✅ **大文档优化** - 自动拆分和并行处理  
✅ **速率管理** - 多账户配置和自动切换  

---

## 📂 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 完整文档(推荐) |
| `GET_STARTED.md` | 3 分钟快速开始 ⭐ |
| `USAGE.md` | 使用指南和场景 |
| `EXAMPLES.md` | 实际案例 |
| `QUICK_REFERENCE.md` | 命令速查表 |
| `skill.yaml` | OpenCode 配置 |
| `verify.sh` | 验证脚本 |
| `test-skill.sh` | 测试脚本 |

---

## 🎓 学习路径

```
第 1 天: GET_STARTED.md → 快速测试 → 验证安装
第 2 天: EXAMPLES.md → 学习实际案例 → 尝试简单项目
第 3 天: USAGE.md → 学习工作流 → 尝试复杂场景
第 4 天: SKILL.md → 深入学习 → 配置优化
```

---

## 🆘 需要帮助?

### 方式 1: 在 OpenCode 中问 AI
```
"skill-seekers 怎么用?"
"如何为当前项目生成 skill?"
"GitHub 速率限制怎么办?"
```

### 方式 2: 查看文档
```bash
cat GET_STARTED.md      # 快速开始
cat SKILL.md            # 完整文档
cat EXAMPLES.md         # 实际案例
```

### 方式 3: 运行验证
```bash
./verify.sh             # 检查安装
./test-skill.sh         # 测试功能
```

### 方式 4: 在线资源
- 🌐 https://skillseekersweb.com/
- 📦 https://github.com/yusufkaraaslan/Skill_Seekers
- 🐛 https://github.com/yusufkaraaslan/Skill_Seekers/issues

---

## 🎉 开始使用

**最简单的方式:**

```
打开 OpenCode,告诉 AI: "用 skill-seekers 帮我生成一个 skill"
```

**命令行方式:**

```bash
skill-seekers install --config react
```

---

**提示:** 建议先阅读 [GET_STARTED.md](GET_STARTED.md) 快速上手!

---

**原仓库:** https://github.com/yusufkaraaslan/Skill_Seekers  
**许可证:** MIT  
**版本:** 2.7.4  
**打包日期:** 2026-01-27
