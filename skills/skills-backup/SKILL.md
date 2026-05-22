---
name: skills-backup
description: Backup/sync local OpenCode skills to wsxwj123/opencode-skills-backup repository under the skills/ subdirectory. Supports full sync and specific skill sync.
---

# Skills Backup & Sync

该 Skill 用于把本机 `~/.config/opencode/skills` 的内容同步到：

- 仓库：`https://github.com/wsxwj123/opencode-skills-backup`
- 子目录：`skills/`

## 功能
- 全量同步本机 skills -> 远端 `skills/`
- 按技能名定向同步（例如只同步 `article-writing`）
- 自动备份（定时运行）
- 跨平台可用（Windows/macOS）

## 前置要求
1. 已安装 Python 3
2. 已安装 Git
3. 对仓库 `wsxwj123/opencode-skills-backup` 具备推送权限

## 使用方法
在 OpenCode 中直接告诉 AI：
- “备份 skills”
- “同步 skills”
- “备份 xlsx 技能”
- “同步 writing-plans 和 theme-factory”

## 自动备份
安装自动备份：

```bash
python3 ~/.config/opencode/skills/skills-backup/setup_auto_backup.py
```

或直接告诉 AI：`设置自动备份`

## 可选环境变量
- `SKILLS_BACKUP_REPO_URL`：覆盖默认仓库地址
- `SKILLS_BACKUP_TARGET_SUBDIR`：覆盖默认子目录（默认 `skills`）

## 运行原理
该 Skill 执行 `scripts/sync_skills.py` / `scripts/auto_sync.py`：
1. 临时克隆目标仓库
2. 将本机 skills 镜像到仓库 `skills/`
3. 提交并推送到远端
