---
name: skills-backup
description: 自动备份 OpenCode skills 到 GitHub 仓库的技能。当用户请求备份 skills 时，自动将 /Users/wsxwj/.config/opencode/skills 目录备份到指定的 GitHub 仓库。支持初始化备份仓库、增量备份、提交和推送操作。
---

# Skills Backup 技能

## 概述

这个技能用于自动备份 OpenCode skills 到 GitHub 仓库。当用户说"备份 skills"或类似请求时，自动执行备份流程。

## 功能特性

1. **初始化备份仓库** - 首次使用时设置 GitHub 仓库
2. **增量备份** - 只备份有变化的文件
3. **自动提交** - 创建有意义的提交信息
4. **推送备份** - 推送到远程 GitHub 仓库
5. **状态检查** - 显示备份状态和变更信息

## 使用方式

当用户请求备份 skills 时，执行以下步骤：

### 1. 检查环境
- 确认 skills 目录存在
- 检查 Git 是否已安装
- 验证 GitHub 仓库配置

### 2. 执行备份
```bash
python3 /Users/wsxwj/.config/opencode/skills/backup-skills/scripts/backup_skills.py
```

### 3. 查看备份状态
```bash
python3 /Users/wsxwj/.config/opencode/skills/backup-skills/scripts/backup_skills.py --status
```

## 配置要求

### GitHub 仓库设置
1. 在 GitHub 上创建一个新的仓库（如 `opencode-skills-backup`）
2. 获取仓库 URL：`https://github.com/<username>/<repo-name>.git`
3. 设置 Git 远程仓库

### 本地配置
1. 确保有 Git 访问权限
2. 配置 Git 用户名和邮箱
3. 设置 SSH 密钥或使用 HTTPS 认证

## 脚本说明

### backup_skills.py
主备份脚本，包含以下功能：
- 备份目录检查
- 文件差异检测
- Git 操作执行
- 备份状态报告

### git_operations.py
Git 操作封装：
- 初始化仓库
- 添加文件
- 提交变更
- 推送远程

### skill_utils.py
技能文件工具：
- 文件遍历
- 变更检测
- 备份策略

## 使用示例

**基本备份：**
```
用户：请备份我的 skills
AI：正在备份 skills 到 GitHub...
```

**查看状态：**
```
用户：skills 备份状态如何？
AI：正在检查备份状态...
```

**强制备份：**
```
用户：强制重新备份所有 skills
AI：正在执行强制备份...
```

## 故障排除

### 常见问题
1. **Git 未安装** - 安装 Git：`brew install git`
2. **权限问题** - 检查文件权限和 Git 配置
3. **网络问题** - 确保可以访问 GitHub
4. **仓库未初始化** - 运行初始化脚本

### 调试模式
```bash
python3 /Users/wsxwj/.config/opencode/skills/backup-skills/scripts/backup_skills.py --debug
```

## 注意事项

1. 备份前建议先查看变更
2. 敏感信息（如 API 密钥）不应包含在备份中
3. 定期检查备份完整性
4. 保持备份仓库的 .gitignore 文件更新

## 参考文档

详细配置指南请查看：
- [GitHub 仓库设置](references/github_setup.md)
- [备份工作流程](references/backup_workflow.md)