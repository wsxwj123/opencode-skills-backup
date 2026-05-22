---
name: general-skills-backup
description: Use when the user asks to backup or sync their Codex skills. This skill auto-detects Windows/macOS and syncs the whole skills directory to the user's configured Git remote, handling cross-platform line ending and path differences.
---

# Skills Backup & Sync (Cross-Platform)

这个 Skill 用于在 Windows 和 macOS 之间自动同步 Codex Skills。
它解决了跨平台路径问题（`/Users/...` vs `C:\Users\...`）和换行符冲突。

## 触发短语（面向最终用户）
当用户说以下任一句时，都按“备份全部 skills”处理：
- `调用general-skills-backup备份所有skill`
- `备份所有skill`
- `同步所有skill`
- `backup all skills`

## Agent 执行规则（必须遵守）
1. 如果用户只给触发短语，没有提供仓库地址：
先检测本机 skills 根目录（默认 `~/.config/opencode/skills`）的 `.git` 和 `origin` 是否存在。
2. 若已完成初始化：
直接执行全量同步脚本 `scripts/sync_skills.py`。
3. 若未完成初始化：
提示用户提供一次 `repo-url`，然后执行 `scripts/quick_start.py --repo-url <url>` 完成初始化并首轮同步。
4. 初始化完成后，后续再次触发“备份所有skill”时，不再追问，直接同步。
5. 除非用户明确要求，不执行“只同步部分 skill”。

## 代理与端口规则（必须遵守）
1. 在首次执行网络相关步骤前，先询问用户：`你使用的 Clash Verge 代理端口是多少（HTTP/HTTPS）？`
2. 如果用户未提供端口，按顺序自动回退：先 `7897`，失败再 `7890`。
3. 所有需要联网的操作必须通过本 skill 的脚本触发，不直接拼接 `git pull/push` 作为主流程。
4. macOS/Linux 建议命令格式：
   `HTTP_PROXY=http://127.0.0.1:<port> HTTPS_PROXY=http://127.0.0.1:<port> ALL_PROXY=socks5://127.0.0.1:<port> python3 <script>`
5. Windows PowerShell 建议命令格式：
   `$env:HTTP_PROXY="http://127.0.0.1:<port>"; $env:HTTPS_PROXY="http://127.0.0.1:<port>"; $env:ALL_PROXY="socks5://127.0.0.1:<port>"; python <script>`

## 脚本限制（必须遵守）
仅允许调用以下脚本完成备份流程：
- `scripts/quick_start.py`
- `scripts/bootstrap_repo.py`
- `scripts/sync_skills.py`
- `scripts/auto_sync.py`
- `setup_auto_backup.py`

禁止在主流程中用零散 `git` 命令替代以上脚本（诊断信息查询除外，如 `git remote -v`）。

## 功能
- **自动识别系统**：在 Windows 和 Mac 上都能直接运行。
- **智能同步**：先拉取（Pull）远程更新，再推送（Push）本地修改，最大程度避免冲突。
- **冲突预防**：自动创建 `.gitattributes` 处理换行符（CRLF/LF）问题。
- **一键初始化**：首次使用可用脚本自动完成 `git init`、`origin` 配置、首推送。
- **特定同步**：支持只同步指定的 Skill。

## 前置要求
1. 确保已安装 `git` 和 Python 3。
2. 在 GitHub 上创建一个自己的仓库（空仓库即可）。

## 开箱即用（推荐）
首次只需要这一个命令：

```bash
HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 ALL_PROXY=socks5://127.0.0.1:7897 python3 ~/.config/opencode/skills/general-skills-backup/scripts/quick_start.py --repo-url <你的GitHub仓库地址>
```

示例：

```bash
HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 ALL_PROXY=socks5://127.0.0.1:7897 python3 ~/.config/opencode/skills/general-skills-backup/scripts/quick_start.py --repo-url https://github.com/<username>/codex-skills-backup.git
```

Windows（PowerShell）示例：

```powershell
$env:HTTP_PROXY="http://127.0.0.1:7897"; $env:HTTPS_PROXY="http://127.0.0.1:7897"; $env:ALL_PROXY="socks5://127.0.0.1:7897"; python $env:USERPROFILE\.config\opencode\skills\general-skills-backup\scripts\quick_start.py --repo-url https://github.com/<username>/codex-skills-backup.git
```

若 7897 无法连通，则将端口改为 7890 重试。

`quick_start.py` 会自动完成：
1. 初始化/检查 git 仓库与分支
2. 配置 `origin`
3. 执行首次同步
4. 询问是否安装每小时自动备份

## 高级初始化（可选）
如果 `origin` 配错了，可用 bootstrap 强制覆盖：

```bash
python3 ~/.config/opencode/skills/general-skills-backup/scripts/bootstrap_repo.py --repo-url <你的GitHub仓库地址> --force-origin
```

## 使用方法
在 Codex 中直接告诉 AI：
- "备份 skills" (同步所有)
- "同步 skills" (同步所有)
- "备份 xlsx 技能" (仅同步 xlsx)
- "同步 writing-plans 和 theme-factory" (同步指定的两个技能)

或手动运行：

```bash
HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 ALL_PROXY=socks5://127.0.0.1:7897 python3 ~/.config/opencode/skills/general-skills-backup/scripts/sync_skills.py
```

仅同步指定 skill：

```bash
HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 ALL_PROXY=socks5://127.0.0.1:7897 python3 ~/.config/opencode/skills/general-skills-backup/scripts/sync_skills.py writing-plans theme-factory
```

如果提示 `git is not available in PATH`，先安装 Git 并重开终端。

## 自动备份 (Auto Backup)
你可以设置每小时自动备份，确保技能永不丢失。

**安装方法：**
在 `general-skills-backup` 目录中运行：
```python
python3 setup_auto_backup.py
```
或者让 AI 帮你运行："设置自动备份"。

**自动备份特性：**
- **频率**：每小时运行一次。
- **日志**：记录在 `general-skills-backup/logs/history.md`。
- **静默**：后台运行，不打扰工作。

## 运行原理
该 Skill 会执行 `scripts/sync_skills.py` 脚本：
1. 检测当前操作系统。
2. 检查 Git 仓库和 `origin` 是否已配置（未配置会提示执行 `bootstrap_repo.py`）。
3. 执行 `git stash` (保存未提交修改)。
4. 执行 `git pull --rebase` (拉取最新代码)。
5. 执行 `git stash pop` (恢复本地修改)。
6. 根据指令执行 `git add .` (全部) 或 `git add <skill_name>` (特定)。
7. 执行 `git commit` (提交信息包含系统名称)。
8. 执行 `git push`。
