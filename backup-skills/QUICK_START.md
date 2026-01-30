# OpenCode Skills Backup - 快速开始指南

## 🎯 概述

这个技能可以自动备份你的 OpenCode skills 到 GitHub 仓库。当你请求"备份 skills"时，AI 会自动执行备份流程。

## 📁 目录结构

```
backup-skills/
├── SKILL.md                  # 技能主文档
├── scripts/                  # 备份脚本
│   ├── backup_skills.py     # 主备份脚本
│   ├── git_operations.py    # Git 操作封装
│   ├── skill_utils.py       # 技能文件工具
│   └── test_backup.py       # 测试脚本
├── references/              # 参考文档
│   ├── github_setup.md     # GitHub 设置指南
│   └── backup_workflow.md  # 备份工作流程
└── assets/                 # 模板文件
    ├── .gitignore.template # Git 忽略模板
    └── README.template.md  # README 模板
```

## 🚀 快速开始

### 步骤 1: 测试技能
```bash
cd /Users/wsxwj/.config/opencode/skills/backup-skills
python3 scripts/test_backup.py
```

### 步骤 2: 设置 GitHub 仓库
1. 在 GitHub 上创建新仓库：`opencode-skills-backup`
2. 获取仓库 URL：`https://github.com/<username>/opencode-skills-backup.git`
3. 设置 Git 远程仓库（首次使用时备份脚本会提示）

### 步骤 3: 执行备份
```bash
# 基本备份
python3 scripts/backup_skills.py

# 查看备份状态
python3 scripts/backup_skills.py --status

# 调试模式
python3 scripts/backup_skills.py --debug
```

## 🤖 AI 使用方式

当你想备份 skills 时，只需对 AI 说：

**基本备份：**
```
请备份我的 skills
```

**查看状态：**
```
skills 备份状态如何？
```

**强制备份：**
```
强制重新备份所有 skills
```

AI 会自动：
1. 检查环境
2. 初始化备份仓库（如果需要）
3. 复制 skills 文件
4. 创建 Git 提交
5. 推送到 GitHub
6. 生成备份报告

## ⚙️ 配置选项

### 环境变量
创建 `.env` 文件（可选）：
```bash
GITHUB_TOKEN=your_personal_access_token
GITHUB_USERNAME=your_username
BACKUP_DIR=/Users/wsxwj/.config/opencode/skills
```

### Git 配置
```bash
# 设置用户信息
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"

# 设置代理（如果需要）
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

## 🔧 高级功能

### 定时备份
使用 cron 设置定时备份：
```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨2点备份）
0 2 * * * cd /Users/wsxwj/.config/opencode/skills/backup-skills && python3 scripts/backup_skills.py >> backup.log 2>&1
```

### 恢复技能
```bash
# 查看可恢复的技能
python3 scripts/skill_utils.py --list

# 恢复单个技能
python3 scripts/skill_utils.py --restore <skill-name>

# 从特定备份恢复
python3 scripts/skill_utils.py --restore <skill-name> --backup <backup-path>
```

### 备份报告
每次备份都会生成报告：
```json
{
  "timestamp": "2024-01-27T10:30:00",
  "backup_directory": "/path/to/backup",
  "statistics": {
    "total_files": 150,
    "added_files": 10,
    "modified_files": 5,
    "unchanged_files": 135
  }
}
```

## 🐛 故障排除

### 常见问题

**1. Git 认证失败**
```bash
# 检查远程仓库设置
cd /Users/wsxwj/.config/opencode/skills/backup-skills/backup-repo
git remote -v

# 更新远程仓库 URL
git remote set-url origin https://<token>@github.com/<username>/opencode-skills-backup.git
```

**2. 权限错误**
```bash
# 检查文件权限
ls -la /Users/wsxwj/.config/opencode/skills

# 修复权限
chmod -R 755 /Users/wsxwj/.config/opencode/skills
```

**3. 网络问题**
```bash
# 测试 GitHub 连接
curl -v https://github.com

# 临时关闭代理
unset http_proxy
unset https_proxy
```

### 调试模式
```bash
# 启用详细日志
python3 scripts/backup_skills.py --debug

# 查看日志文件
tail -f /Users/wsxwj/.config/opencode/skills/backup-skills/backup.log
```

## 📊 监控和维护

### 检查备份状态
```bash
# 查看最近备份
cd /Users/wsxwj/.config/opencode/skills/backup-skills/backup-repo
git log --oneline -5

# 查看文件变更
git status
```

### 清理旧备份
```bash
# 清理临时文件
python3 scripts/backup_skills.py --clean

# 手动清理
rm -rf /Users/wsxwj/.config/opencode/skills/backup-skills/backup-repo/tmp/*
```

### 更新备份脚本
```bash
# 从 GitHub 拉取更新
cd /Users/wsxwj/.config/opencode/skills/backup-skills
git pull origin main
```

## 🔒 安全建议

1. **使用私有仓库**：保护你的 skills 备份
2. **定期轮换令牌**：每90天更新 GitHub 访问令牌
3. **加密敏感数据**：不要备份包含敏感信息的文件
4. **监控备份活动**：定期检查备份日志

## 📞 获取帮助

### 查看文档
```bash
# 查看完整文档
cat references/github_setup.md
cat references/backup_workflow.md
```

### 运行测试
```bash
# 运行完整测试套件
python3 scripts/test_backup.py --all
```

### 报告问题
如果遇到问题：
1. 查看错误日志
2. 运行测试脚本
3. 检查 GitHub 仓库状态
4. 联系维护者

## 🎉 完成！

你的 OpenCode skills 备份系统现在已经设置完成。下次你想备份 skills 时，只需对 AI 说：

**"请备份我的 skills"**

AI 会自动处理所有备份流程！