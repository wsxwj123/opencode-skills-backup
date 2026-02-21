# 🎯 立即开始使用 Skill Seekers

## 3 分钟快速测试

### 第 1 步: 验证安装 (30 秒)

```bash
cd ~/.config/opencode/skills/skill-seekers
./verify.sh
```

**预期输出:** ✅ 所有关键检查通过!

---

### 第 2 步: 选择一个场景 (2 分钟)

#### 🏠 场景 A: 测试本地项目(最简单)

```bash
# 创建测试项目
mkdir -p /tmp/test-project
cd /tmp/test-project

# 创建简单的 Python 文件
cat > main.py << 'EOF'
def greet(name):
    """问候某人"""
    return f"你好, {name}!"

if __name__ == "__main__":
    print(greet("世界"))
EOF

# 分析项目(快速模式)
skill-seekers-codebase \
    --directory . \
    --depth surface \
    --output output/test-project/

# 查看结果
ls output/test-project/
cat output/test-project/SKILL.md
```

#### 🌐 场景 B: 测试文档抓取(需要网络)

```bash
# 使用预设配置(最快)
skill-seekers install --config react --no-upload

# 或评估页数(更快)
skill-seekers estimate --url https://react.dev
```

#### 🐙 场景 C: 测试 GitHub 分析(需要 token)

```bash
# 设置 token
export GITHUB_TOKEN=ghp_your_token

# 分析小型仓库
skill-seekers github --repo yusufkaraaslan/Skill_Seekers
```

---

### 第 3 步: 在 OpenCode 中使用 (30 秒)

1. 打开 OpenCode
2. 告诉 AI:

```
"用 skill-seekers 为当前项目生成 skill"
```

3. 等待 AI 自动执行所有步骤!

---

## 命令速查

| 需求 | 命令 |
|------|------|
| 本地项目 | `skill-seekers-codebase --directory .` |
| 文档网站 | `skill-seekers scrape --url <url> --name <name>` |
| GitHub | `skill-seekers github --repo <owner/repo>` |
| 一键完成 | `skill-seekers install --config <name>` |
| 配置 | `skill-seekers config` |
| 验证 | `./verify.sh` |

---

## 下一步

### 🎓 学习更多

- 📖 [SKILL.md](SKILL.md) - 完整文档
- 🚀 [USAGE.md](USAGE.md) - 使用指南  
- ⚡ [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 命令速查
- 💡 [EXAMPLES.md](EXAMPLES.md) - 实际案例

### 🔧 配置优化

```bash
# 设置 GitHub token(推荐)
skill-seekers config --github

# 查看配置
skill-seekers config --show
```

### 🎯 尝试真实项目

```bash
# 为你的项目创建 skill
cd ~/your-project
skill-seekers-codebase --directory . --depth deep --output output/my-project/
skill-seekers package output/my-project/
skill-seekers install-agent output/my-project/ --agent opencode
```

---

## 常见问题

**Q: 需要 API key 吗?**  
A: 不需要! 使用本地增强(`--ai-mode local`)完全免费。

**Q: 支持哪些编程语言?**  
A: 所有主流语言(Python, JS, Go, Rust, Java, C++...)

**Q: 能分析私有仓库吗?**  
A: 可以! 设置 `GITHUB_TOKEN` 后即可访问。

**Q: 要等多久?**  
A: 
- 本地项目: 2-10 分钟
- 文档网站: 10-30 分钟
- GitHub 仓库: 5-15 分钟
- 一键流程: 20-45 分钟

---

## 获取帮助

- 💬 在 OpenCode 中问 AI: "skill-seekers 怎么用?"
- 📖 查看完整文档: [SKILL.md](SKILL.md)
- 🌐 访问官网: https://skillseekersweb.com/
- 🐛 报告问题: https://github.com/yusufkaraaslan/Skill_Seekers/issues

---

**🚀 现在就开始创建你的第一个 Skill 吧!**

```bash
skill-seekers install --config react
```

或在 OpenCode 中:
```
"用 skill-seekers 为当前项目生成 skill"
```
