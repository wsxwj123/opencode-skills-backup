# 🎉 欢迎使用 Skill Seekers!

> ⚡ **你现在拥有了一个可以自动创建 Skills 的 Skill!**

---

## 🎯 这个 Skill 能做什么?

**简单来说:** 把任何文档、代码或仓库变成 AI 可以使用的 Skill!

```
文档网站 ────┐
             │
GitHub 仓库 ──┼──→ Skill Seekers ──→ 高质量 AI Skill
             │
本地代码 ────┤
             │
PDF 文档 ────┘
```

---

## ⚡ 30 秒快速测试

### 在 OpenCode 中(推荐)

```
直接告诉 AI: "用 skill-seekers 为当前项目生成 skill"
```

### 命令行

```bash
# 验证安装
./verify.sh

# 快速测试
skill-seekers install --config react --no-upload
```

---

## 📚 从哪里开始?

### 🎯 你是第一次使用
👉 **[GET_STARTED.md](GET_STARTED.md)** - 3 分钟快速上手

### 📖 你想完整学习
👉 **[NAVIGATION.md](NAVIGATION.md)** - 文档导航地图

### 💡 你想看实际例子
👉 **[EXAMPLES.md](EXAMPLES.md)** - 10 个真实案例

### ⚡ 你想快速查命令
👉 **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - 命令速查表

---

## 🚀 5 个常用场景

### 1️⃣ 为当前项目创建 Skill

```bash
skill-seekers-codebase --directory . --output output/my-project/
```

或在 OpenCode 中:
```
"用 skill-seekers 为当前项目生成 skill"
```

### 2️⃣ 从文档网站创建 Skill

```bash
# 一键完成(最简单)
skill-seekers install --config react

# 或自定义 URL
skill-seekers scrape --url https://vuejs.org --name vue
```

### 3️⃣ 从 GitHub 创建 Skill

```bash
# 设置 token(可选,避免速率限制)
export GITHUB_TOKEN=ghp_your_token

# 分析仓库
skill-seekers github --repo facebook/react
```

### 4️⃣ 从 PDF 创建 Skill

```bash
skill-seekers pdf --pdf docs/manual.pdf --name manual
```

### 5️⃣ 统一多源创建

```bash
# 组合文档、GitHub、PDF 为一个 skill
skill-seekers unified --config configs/unified.json
```

---

## 🎁 特色功能

### ✨ AI 增强

将基础 skill (⭐⭐) 提升为专业级 (⭐⭐⭐⭐⭐)

```bash
# 本地增强(免费,推荐)
skill-seekers enhance output/myskill/ --ai-mode local
```

### 🔍 冲突检测

自动发现文档和代码的不一致:

- 🔴 代码中缺失(有文档但未实现)
- 🟡 文档中缺失(已实现但未记录)
- ⚠️ 签名不匹配(参数不同)

### 🚄 大文档优化

自动拆分 10K+ 页文档并并行处理:

```bash
skill-seekers split-config large.json --strategy router
# 自动拆分 → 并行抓取 → 生成路由
```

### 🔄 多平台支持

一次打包,适配多个 LLM:

```bash
skill-seekers package output/myskill/ --target claude
skill-seekers package output/myskill/ --target gemini
skill-seekers package output/myskill/ --target openai
```

---

## ✅ 安装状态

```
Python: ✅ 3.10.11
命令: ✅ skill-seekers, skill-seekers-codebase
目录: ✅ ~/.config/opencode/skills/skill-seekers/
文档: ✅ 完整(中文)
配置: ✅ OpenCode 兼容
脚本: ✅ verify.sh, test-skill.sh
状态: ✅ 可以使用!
```

---

## 🔧 推荐配置(可选)

### 设置 GitHub Token

避免速率限制(60/小时 → 5000/小时):

```bash
skill-seekers config --github
```

### 配置 AI 增强

使用本地 Claude Code 免费增强:

```bash
# 已默认支持,无需额外配置
# 使用 --ai-mode local 即可
```

---

## 📞 获取帮助

### 📖 文档
- [GET_STARTED.md](GET_STARTED.md) - 快速开始
- [SKILL.md](SKILL.md) - 完整文档
- [NAVIGATION.md](NAVIGATION.md) - 文档导航

### 🔧 工具
```bash
./verify.sh      # 验证安装
./test-skill.sh  # 测试功能
```

### 🌐 在线
- https://skillseekersweb.com/
- https://github.com/yusufkaraaslan/Skill_Seekers

### 💬 在 OpenCode
```
"skill-seekers 怎么用?"
"如何为项目生成 skill?"
```

---

## 🎊 准备就绪!

**你现在可以:**

✅ 在 OpenCode 中用自然语言创建 Skills  
✅ 命令行快速打包文档和代码  
✅ 一键生成多平台适配的 Skills  
✅ 自动检测文档和代码冲突  
✅ 处理大型文档(10K+ 页)  
✅ 管理多个 GitHub 账户  

---

## 🚀 立即开始!

**最快方式:**
```
打开 OpenCode,说: "用 skill-seekers 为当前项目生成 skill"
```

**命令行方式:**
```bash
cd ~/.config/opencode/skills/skill-seekers
./verify.sh
cat GET_STARTED.md
```

---

**🎉 祝你创建 Skills 愉快!**

有任何问题,查看 [NAVIGATION.md](NAVIGATION.md) 找到对应文档!

---

**版本:** 2.7.4  
**状态:** ✅ Ready  
**日期:** 2026-01-27
