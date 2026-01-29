---
name: skills-backup
description: Use when the user asks to backup or sync their skills. This skill automatically detects the OS (Windows/Mac) and syncs the entire skills directory to the configured Git repository, handling cross-platform conflicts like line endings and paths.
---

# Skills Backup & Sync (Cross-Platform)

这个 Skill 用于在 Windows 和 macOS 之间自动同步 OpenCode Skills。
它解决了跨平台路径问题（`/Users/...` vs `C:\Users\...`）和换行符冲突。

## 功能
- **自动识别系统**：在 Windows 和 Mac 上都能直接运行。
- **智能同步**：先拉取（Pull）远程更新，再推送（Push）本地修改，最大程度避免冲突。
- **冲突预防**：自动创建 `.gitattributes` 处理换行符（CRLF/LF）问题。
- **特定同步**：支持只同步指定的 Skill。

## 前置要求
1. 确保 `skills` 目录是一个 Git 仓库：
   ```bash
   cd ~/.config/opencode/skills
   git init
   git remote add origin <你的GitHub仓库地址>
   ```
2. 确保已安装 Python 3。

## 使用方法
在 OpenCode 中直接告诉 AI：
- "备份 skills" (同步所有)
- "同步 skills" (同步所有)
- "备份 xlsx 技能" (仅同步 xlsx)
- "同步 writing-plans 和 theme-factory" (同步指定的两个技能)

## 运行原理
该 Skill 会执行 `scripts/sync_skills.py` 脚本：
1. 检测当前操作系统。
2. 检查 Git 状态。
3. 执行 `git stash` (保存未提交修改)。
4. 执行 `git pull --rebase` (拉取最新代码)。
5. 执行 `git stash pop` (恢复本地修改)。
6. 根据指令执行 `git add .` (全部) 或 `git add <skill_name>` (特定)。
7. 执行 `git commit` (提交信息包含系统名称)。
8. 执行 `git push`。
