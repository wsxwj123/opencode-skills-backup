# OpenCode 完整备份 - 快速开始指南

## 🚀 一分钟快速开始

### 1. 创建 GitHub 仓库
1. 访问 https://github.com/new
2. 创建新仓库，例如：`opencode-full-backup`
3. 不要初始化 README、.gitignore 或 license
4. 复制仓库 URL：`https://github.com/你的用户名/opencode-full-backup.git`

### 2. 初始化备份
```bash
cd /Users/wsxwj/.config/opencode/skills/opencode-backup
python scripts/backup_opencode.py init --repo-url https://github.com/你的用户名/opencode-full-backup.git
```

### 3. 执行首次完整备份
```bash
python scripts/backup_opencode.py backup
```

### 4. 检查备份状态
```bash
python scripts/backup_opencode.py status
```

## 📋 完整使用流程

### 初始化阶段
```bash
# 1. 初始化备份（首次使用）
python scripts/backup_opencode.py init --repo-url <你的仓库URL>

# 2. 执行完整备份
python scripts/backup_opencode.py backup

# 3. 验证备份
python scripts/backup_opencode.py status
```

### 日常使用
```bash
# 每日增量备份（推荐）
python scripts/backup_opencode.py incremental

# 每周完整备份（推荐）
python scripts/backup_opencode.py backup

# 检查备份状态
python scripts/backup_opencode.py status
```

## 🔄 在新 Mac 上恢复

### 方法 1: 自动恢复脚本（推荐）
```bash
# 下载并运行恢复脚本
curl -O https://raw.githubusercontent.com/你的用户名/opencode-backup-macmini/master/scripts/restore_opencode.sh
chmod +x restore_opencode.sh
./restore_opencode.sh
```

### 方法 2: 手动恢复
```bash
# 1. 克隆备份仓库
git clone https://github.com/你的用户名/opencode-backup-macmini.git ~/.config/opencode

# 2. 安装依赖
cd ~/.config/opencode
npm install  # 或 bun install

# 3. 验证
ls -la skills/
```

**重要**: `node_modules` 不需要备份，会通过 `npm install` 自动重建。

详细说明请参考 [RESTORE_GUIDE.md](./RESTORE_GUIDE.md)
```

### 恢复阶段
```bash
# 从备份恢复（会要求确认）
python scripts/backup_opencode.py restore

# 跳过确认直接恢复
python scripts/backup_opencode.py restore --no-confirm
```

## 🔧 高级功能

### 试运行模式
```bash
# 检查哪些文件会被备份（不实际执行）
python scripts/backup_opencode.py backup --dry-run
python scripts/backup_opencode.py incremental --dry-run
```

### 强制重新初始化
```bash
# 如果仓库URL变更或需要重新初始化
python scripts/backup_opencode.py init --repo-url <新URL> --force
```

## 📊 备份内容说明

### 一定会备份的内容
- ✅ 所有技能（skills/ 目录）
- ✅ 插件配置（plugins/ 目录）
- ✅ 代理配置（agents/ 目录）
- ✅ 命令定义（commands/ 目录）
- ✅ 核心库文件（lib/ 目录）
- ✅ 所有配置文件（*.json）
- ✅ 工具脚本（*.py）

### 不会备份的内容
- ❌ node_modules/（依赖包）
- ❌ .git/（Git 数据）
- ❌ .DS_Store（系统文件）
- ❌ 临时文件（*.tmp, *.log）
- ❌ 编译文件（*.pyc）

## 🚨 重要注意事项

### 1. Git 要求
- 必须安装 Git
- 必须有 GitHub 账户
- 必须有网络连接

### 2. 权限要求
- 需要有 OpenCode 目录的读写权限
- 需要有备份目录的读写权限

### 3. 恢复警告
- 恢复会覆盖当前配置
- 恢复前会自动备份当前配置
- 恢复文件在：`~/.config/opencode/backup_before_restore_时间戳/`

### 4. 网络要求
- 推送到 GitHub 需要网络连接
- 可以使用代理：`git config --global http.proxy http://127.0.0.1:7897`

## 🔍 故障排除

### 常见问题 1：Git 命令未找到
```
错误：git: command not found
```
**解决**：安装 Git
```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt-get install git

# Windows
# 下载并安装 Git for Windows
```

### 常见问题 2：权限被拒绝
```
错误：Permission denied
```
**解决**：检查文件权限
```bash
ls -la ~/.config/opencode/
chmod -R 755 ~/.config/opencode/skills/opencode-backup/
```

### 常见问题 3：网络连接失败
```
错误：Failed to connect to GitHub
```
**解决**：检查网络和代理
```bash
# 测试 GitHub 连接
curl -I https://github.com

# 如果使用代理，设置 Git 代理
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897

# 测试代理连接
curl -x http://127.0.0.1:7897 -I https://github.com
```

### 常见问题 4：仓库未初始化
```
错误：请先初始化备份仓库
```
**解决**：运行初始化命令
```bash
python scripts/backup_opencode.py init --repo-url <你的仓库URL>
```

## 📅 推荐备份计划

### 每日计划（增量备份）
```bash
# 添加到 crontab（Linux/macOS）
0 2 * * * cd /Users/wsxwj/.config/opencode/skills/opencode-backup && python scripts/backup_opencode.py incremental
```

### 每周计划（完整备份）
```bash
# 每周日凌晨3点执行完整备份
0 3 * * 0 cd /Users/wsxwj/.config/opencode/skills/opencode-backup && python scripts/backup_opencode.py backup
```

### 每月检查
```bash
# 每月1号检查备份状态
0 4 1 * * cd /Users/wsxwj/.config/opencode/skills/opencode-backup && python scripts/backup_opencode.py status
```

## 🎯 最佳实践

1. **定期备份**：至少每周一次完整备份
2. **测试恢复**：每季度测试一次恢复流程
3. **监控状态**：每月检查备份状态
4. **更新配置**：OpenCode 更新后重新备份
5. **多地备份**：考虑多个备份位置（GitHub + 本地 + 云存储）

## 📞 获取帮助

如果遇到问题：
1. 检查 `QUICK_START.md`（本文档）
2. 查看 `SKILL.md` 中的详细说明
3. 运行 `python scripts/backup_opencode.py status` 检查状态
4. 查看脚本输出中的错误信息

## 🎉 完成！

现在你的 OpenCode 配置已经安全备份到 GitHub。记得定期执行备份，并测试恢复流程以确保备份有效。

**记住**：备份只有在能够恢复时才有效！