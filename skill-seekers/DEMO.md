# 🎬 Skill Seekers 使用演示

本文档展示 Skill Seekers 的实际使用场景和效果。

## 演示 1: 在 OpenCode 中使用(最推荐)

### 对话示例

```
👤 用户: 用 skill-seekers 为当前项目生成一个 skill

🤖 OpenCode: 好的!我会使用 skill-seekers 分析当前项目并生成 skill。

[执行步骤]
1. 分析项目结构
2. 提取 API 和模式
3. 生成文档
4. 打包并安装

✅ 完成! Skill 已安装到: ~/.config/opencode/skills/my-project/
```

---

## 演示 2: 命令行快速测试

### 为 React 创建 Skill

```bash
# 验证安装
$ ./verify.sh
✅ 所有关键检查通过!

# 一键创建 React skill
$ skill-seekers install --config react --no-upload

✅ React skill 创建成功!
```

---

## 演示 3: 分析 GitHub 仓库

### 深度分析 Django

```bash
# 设置 token
$ export GITHUB_TOKEN=ghp_your_token

# 分析仓库
$ skill-seekers github --repo django/django \
    --include-issues --include-changelog --include-releases

✅ 分析完成: output/django/
```

---

## 演示 4: 统一多源

### 组合文档、GitHub 和 PDF

```bash
# 创建统一配置
$ cat > unified.json << 'EOF'
{
  "name": "fastapi",
  "sources": [
    {"type": "documentation", "base_url": "https://fastapi.tiangolo.com/"},
    {"type": "github", "repo": "tiangolo/fastapi"},
    {"type": "pdf", "pdf_path": "docs/guide.pdf"}
  ]
}
EOF

# 统一抓取
$ skill-seekers unified --config unified.json

✅ 统一 skill 创建完成!
⚠️  发现 5 个冲突(文档 vs 代码)
```

---

## 演示 5: 处理大型文档

### Godot Engine 40K 页

```bash
# 1. 评估
$ skill-seekers estimate configs/godot.json
📊 预估: 40,200 页

# 2. 拆分
$ skill-seekers split-config configs/godot.json --strategy router
✅ 拆分为 5 个子配置

# 3. 并行抓取
$ # 启动 5 个并行进程
✅ 55 分钟完成(vs 6-8 小时!)

# 4. 生成路由
$ skill-seekers generate-router configs/godot-*.json
✅ 智能路由已生成
```

---

## 演示 6: 配置多 GitHub 账户

```bash
$ skill-seekers config

选择: 1. GitHub Token Setup

添加配置文件:
- personal (prompt 策略)
- work (switch 策略)
- opensource (wait 策略)

✅ 3 个配置文件已添加

# 使用
$ skill-seekers github --repo company/repo --profile work
```

---

## 演示 7: 恢复中断任务

```bash
# 列出任务
$ skill-seekers resume --list

Job: github_react_20260126_143022
Progress: 75% (150/200 pages)

# 恢复
$ skill-seekers resume github_react_20260126_143022

✅ 从 75% 继续完成!
```

---

## 演示 8: 性能对比

```bash
# 同步模式
500 页 / 28 分钟 / 120 MB

# 异步模式
500 页 / 9 分钟 / 45 MB

⚡ 快 2.9 倍, 内存省 62%
```

---

## 演示 9: 质量对比

### 无增强 vs AI 增强

**基础版:** 75 行, 基础语法 ⭐⭐  
**增强版:** 500+ 行, 完整教程 ⭐⭐⭐⭐⭐

质量提升 300%!

---

## 演示 10: 完整工作流

```bash
# 1. 验证 (30 秒)
./verify.sh

# 2. 评估 (1-2 分钟)
skill-seekers estimate --url <url>

# 3. 抓取 (10-15 分钟)
skill-seekers scrape --url <url> --name <name>

# 4. 增强 (30-60 秒)
skill-seekers enhance output/<name>/ --ai-mode local

# 5. 打包 (10 秒)
skill-seekers package output/<name>/

# 6. 安装 (5 秒)
skill-seekers install-agent output/<name>/ --agent opencode

✅ 总耗时: 15-20 分钟
✅ 质量: ⭐⭐⭐⭐⭐
```

---

## 🎯 选择演示

| 你想... | 看演示 |
|---------|--------|
| 快速测试 | 1, 2 |
| GitHub 分析 | 3 |
| 多源统一 | 4 |
| 大文档处理 | 5 |
| 多账户 | 6 |
| 恢复任务 | 7 |
| 性能对比 | 8 |
| 质量对比 | 9 |
| 完整流程 | 10 |

---

## 🚀 立即尝试

**OpenCode:**
```
"用 skill-seekers 生成 skill"
```

**命令行:**
```bash
skill-seekers install --config react --no-upload
```

**完整文档:** [NAVIGATION.md](NAVIGATION.md)
