# OpenCode 完整备份技能 - 用户指南

## 📋 概述

OpenCode 完整备份技能 (`opencode-backup`) 是一个完整的 OpenCode 配置备份解决方案，支持：

- ✅ 完整备份所有 OpenCode 组件（不仅仅是 skills）
- ✅ 增量备份和完整备份
- ✅ Git 版本控制
- ✅ 备份到 GitHub 私有仓库
- ✅ 恢复功能
- ✅ 自动化备份计划
- ✅ 备份验证

## 🚀 快速开始

### 1. 初始化备份

```bash
cd /Users/wsxwj/.config/opencode/skills/opencode-backup

# 设置 Git 代理（如果需要）
git config --global http.proxy http://127.0.0.1:7897

# 初始化备份仓库
python scripts/backup_opencode.py init --repo-url https://github.com/wsxwj123/opencode-backup-macmini.git
```

### 2. 执行首次完整备份

```bash
python scripts/backup_opencode.py backup
```

### 3. 推送到 GitHub

```bash
cd backup-repo
git push -u origin master
```

## 📁 备份内容

备份包括以下 OpenCode 组件：

| 组件 | 说明 |
|------|------|
| `skills/` | 所有技能目录 |
| `plugins/` | 插件配置 |
| `agents/` | 代理配置 |
| `commands/` | 命令定义 |
| `lib/` | 核心库文件 |
| `*.json` | 所有配置文件 |
| `*.py` | 工具脚本 |

**排除项**: `node_modules/`, `.DS_Store`, `.git/`, `*.pyc`

## 🔧 常用命令

### 备份操作

```bash
# 完整备份
python scripts/backup_opencode.py backup

# 增量备份（只备份变更的文件）
python scripts/backup_opencode.py incremental

# 试运行（不实际备份）
python scripts/backup_opencode.py backup --dry-run
```

### 恢复操作

```bash
# 从备份恢复（需要确认）
python scripts/backup_opencode.py restore

# 跳过确认提示
python scripts/backup_opencode.py restore --no-confirm
```

**注意**: 恢复操作会先备份当前配置到 `backup_before_restore_<timestamp>` 目录。

### 状态检查

```bash
# 检查备份状态
python scripts/backup_opencode.py status

# 验证备份完整性
python scripts/verify_backup.py
```

## ⚙️ 自动化备份

### 自动备份脚本

```bash
# 执行自动备份（包含增量备份和周日完整备份）
./scripts/auto_backup.sh
```

### 设置定时任务（crontab）

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨2点执行）
0 2 * * * /Users/wsxwj/.config/opencode/skills/opencode-backup/scripts/auto_backup.sh >> /Users/wsxwj/.config/opencode/skills/opencode-backup/logs/cron.log 2>&1
```

## 🔍 备份验证

### 手动验证

```bash
# 运行验证脚本
python scripts/verify_backup.py
```

验证脚本会检查：
- 关键文件和目录是否存在
- 技能数量是否匹配
- Git 状态和同步情况
- 备份新鲜度

### 验证结果解读

- **✅ 通过**: 所有检查项正常
- **⚠️ 警告**: 有需要注意的问题（如技能数量不匹配）
- **❌ 失败**: 关键问题需要修复

## 🛠️ 故障排除

### 常见问题

#### 1. Git 推送失败

**问题**: `错误：源引用规格 main 没有匹配`

**解决方案**:
```bash
cd backup-repo
# 检查当前分支
git branch -a

# 如果本地是 master，推送到 master
git push -u origin master

# 或者重命名分支
git branch -M main
git push -u origin main
```

#### 2. 代理设置问题

**问题**: Git 操作超时

**解决方案**:
```bash
# 设置代理
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897

# 取消代理
git config --global --unset http.proxy
git config --global --unset https.proxy
```

#### 3. 备份文件过多

**问题**: 备份目录过大

**解决方案**:
- 检查是否有无限嵌套目录
- 清理测试文件
- 使用增量备份减少文件数量

### 日志文件

- `logs/` 目录包含所有备份日志
- 日志按时间戳命名：`backup_YYYYMMDD_HHMMSS.log`
- 自动清理30天前的日志

## 📊 备份统计

### 当前状态

- **备份目录**: `/Users/wsxwj/.config/opencode/skills/opencode-backup/backup-repo/`
- **GitHub 仓库**: `https://github.com/wsxwj123/opencode-backup-macmini.git`
- **技能数量**: 65/66（备份/原始）
- **最新备份**: 2026-01-27 21:51:35

### 文件统计

```bash
# 查看备份文件数量
find /Users/wsxwj/.config/opencode/skills/opencode-backup/backup-repo -type f | wc -l

# 查看备份大小
du -sh /Users/wsxwj/.config/opencode/skills/opencode-backup/backup-repo
```

## 🔄 恢复流程

### 完整恢复步骤

1. **验证备份完整性**
   ```bash
   python scripts/verify_backup.py
   ```

2. **执行恢复**
   ```bash
   python scripts/backup_opencode.py restore --no-confirm
   ```

3. **验证恢复结果**
   ```bash
   # 检查恢复的文件
   ls -la /Users/wsxwj/.config/opencode/
   
   # 测试关键功能
   cd /Users/wsxwj/.config/opencode
   # 测试技能加载等
   ```

4. **如果需要回滚**
   ```bash
   # 查看恢复前的备份
   ls -d /Users/wsxwj/.config/opencode/backup_before_restore_*
   
   # 手动复制回去
   cp -r /Users/wsxwj/.config/opencode/backup_before_restore_20260127_215135/* /Users/wsxwj/.config/opencode/
   ```

## 📝 最佳实践

### 备份策略

1. **日常**: 使用增量备份（`incremental`）
2. **每周**: 执行完整备份（`backup`）
3. **每月**: 验证备份完整性（`verify_backup.py`）
4. **重大变更前**: 手动执行完整备份

### 存储管理

1. **本地**: 保留最近30天的备份
2. **GitHub**: 所有历史版本
3. **清理**: 定期清理测试文件和日志

### 监控建议

1. **日志监控**: 检查 `logs/` 目录的备份日志
2. **空间监控**: 监控备份目录大小
3. **新鲜度监控**: 确保备份不超过24小时

## 🆘 紧急情况

### 数据丢失恢复

如果 OpenCode 配置丢失或损坏：

1. **从 GitHub 克隆备份**
   ```bash
   cd /tmp
   git clone https://github.com/wsxwj123/opencode-backup-macmini.git
   ```

2. **手动恢复文件**
   ```bash
   cp -r /tmp/opencode-backup-macmini/* /Users/wsxwj/.config/opencode/
   ```

3. **验证恢复**
   ```bash
   python scripts/verify_backup.py
   ```

### 联系支持

如果遇到无法解决的问题：

1. 检查 `logs/` 目录中的错误日志
2. 查看 GitHub Issues（如果有）
3. 联系技能开发者

## 📈 未来改进计划

- [ ] 添加备份压缩功能
- [ ] 支持多备份目标（GitLab、本地磁盘等）
- [ ] 添加备份加密选项
- [ ] 实现 Web 管理界面
- [ ] 添加备份通知（邮件、Slack等）

---

**最后更新**: 2026-01-27  
**版本**: 1.0.0  
**维护者**: OpenCode 备份技能开发团队