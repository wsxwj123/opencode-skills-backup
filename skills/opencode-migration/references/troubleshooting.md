# OpenCode 迁移故障排除指南

## 概述

本指南涵盖 OpenCode 迁移过程中可能遇到的常见问题及其解决方案。

## 目录

1. [打包阶段问题](#打包阶段问题)
2. [传输阶段问题](#传输阶段问题)
3. [安装阶段问题](#安装阶段问题)
4. [配置问题](#配置问题)
5. [MCP 服务器问题](#mcp-服务器问题)
6. [技能问题](#技能问题)
7. [权限问题](#权限问题)
8. [性能问题](#性能问题)

---

## 打包阶段问题

### 问题 1: 打包脚本执行失败

**症状:**
```bash
bash: ./package_skill.sh: Permission denied
```

**原因:** 脚本没有执行权限

**解决方案:**
```bash
# 添加执行权限
chmod +x scripts/*.py
chmod +x package_skill.sh

# 重新执行
./package_skill.sh
```

---

### 问题 2: Python 脚本导入错误

**症状:**
```
ModuleNotFoundError: No module named 'json'
```

**原因:** Python 环境问题

**解决方案:**
```bash
# 检查 Python 版本
python3 --version  # 应该 >= 3.8

# 如果版本过旧，更新 Python
# macOS
brew install python@3.11

# Windows
# 从 python.org 下载最新版本

# 验证安装
python3 -c "import json, pathlib, hashlib; print('OK')"
```

---

### 问题 3: 打包文件过大

**症状:**
```
Warning: Package size exceeds 100MB
```

**原因:** 包含了不必要的文件（如 node_modules）

**解决方案:**
```bash
# 1. 检查大文件
du -sh ~/.config/opencode/* | sort -hr | head -20

# 2. 清理不必要的文件
rm -rf ~/.config/opencode/node_modules/
rm -rf ~/.config/opencode/*/node_modules/
rm -rf ~/.config/opencode/.cache/

# 3. 使用排除参数
python3 scripts/config_packager.py \
  --output backup.zip \
  --exclude "node_modules/,*.log,*.tmp,.cache/"
```

---

### 问题 4: 打包过程中断

**症状:**
```
Error: Connection reset by peer
Killed: 9
```

**原因:** 内存不足或磁盘空间不足

**解决方案:**
```bash
# 1. 检查磁盘空间
df -h

# 2. 检查内存使用
free -h  # Linux
vm_stat  # macOS

# 3. 分批打包
python3 scripts/config_packager.py --skills-only --output skills.zip
python3 scripts/config_packager.py --mcp-only --output mcp.zip
python3 scripts/config_packager.py --config-only --output config.zip

# 4. 使用压缩级别
python3 scripts/config_packager.py --compression-level 9 --output backup.zip
```

---

## 传输阶段问题

### 问题 5: 文件传输失败

**症状:**
```
Error: File transfer interrupted
CRC32 checksum mismatch
```

**原因:** 网络不稳定或传输错误

**解决方案:**
```bash
# 1. 验证文件完整性
# 源设备
sha256sum opencode_backup.zip > backup.sha256

# 目标设备
sha256sum -c backup.sha256

# 2. 使用可靠的传输方式
# 通过 rsync (Linux/macOS)
rsync -avz --progress opencode_backup.zip user@target:/path/

# 通过 USB 直接复制
cp opencode_backup.zip /Volumes/USB/

# 3. 分段传输大文件
split -b 100M opencode_backup.zip backup_part_

# 在目标设备合并
cat backup_part_* > opencode_backup.zip
```

---

### 问题 6: 云存储同步失败

**症状:**
```
Error: Upload failed - network timeout
```

**原因:** 网络限制或文件过大

**解决方案:**
```bash
# 1. 使用断点续传工具
# OneDrive
onedrive --sync --upload-only

# Google Drive (使用 rclone)
rclone copy opencode_backup.zip gdrive:backups/ --progress

# 2. 压缩并加密
tar -czf - ~/.config/opencode | gpg -c > backup.tar.gz.gpg

# 3. 分卷上传
split -b 500M backup.tar.gz.gpg backup_
# 上传每个分卷
for file in backup_*; do
  rclone copy "$file" gdrive:backups/
done
```

---

## 安装阶段问题

### 问题 7: 安装脚本找不到文件

**症状:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'opencode_backup.zip'
```

**原因:** 工作目录不正确或文件路径错误

**解决方案:**
```bash
# 1. 使用绝对路径
python3 scripts/migration_installer.py \
  --install /Users/username/Downloads/opencode_backup.zip

# 2. 检查当前目录
pwd
ls -la opencode_backup.zip

# 3. 移动到正确位置
mv ~/Downloads/opencode_backup.zip .
```

---

### 问题 8: 解压失败

**症状:**
```
Error: Archive is corrupted
gzip: stdin: not in gzip format
```

**原因:** 文件损坏或格式错误

**解决方案:**
```bash
# 1. 验证文件完整性
file opencode_backup.zip
sha256sum opencode_backup.zip

# 2. 尝试修复压缩文件
zip -FF opencode_backup.zip --out fixed.zip

# 3. 使用不同的解压工具
# macOS
ditto -x -k opencode_backup.zip destination/

# Linux
unzip opencode_backup.zip -d destination/

# Windows
Expand-Archive opencode_backup.zip -DestinationPath destination\

# 4. 如果无法修复，重新下载/传输
```

---

### 问题 9: 权限拒绝

**症状:**
```
PermissionError: [Errno 13] Permission denied: '/Users/username/.config/opencode'
```

**原因:** 没有写入权限

**解决方案:**
```bash
# macOS/Linux
# 1. 检查目录权限
ls -la ~/.config/opencode

# 2. 修复权限
chmod -R u+rwX ~/.config/opencode/

# 3. 如果目录不存在，创建它
mkdir -p ~/.config/opencode
chmod 755 ~/.config/opencode

# Windows (PowerShell 管理员)
# 1. 检查权限
Get-Acl "$env:APPDATA\opencode"

# 2. 修复权限
icacls "$env:APPDATA\opencode" /grant "${env:USERNAME}:(OI)(CI)F" /T

# 3. 创建目录
New-Item -ItemType Directory -Force -Path "$env:APPDATA\opencode"
```

---

### 问题 10: 配置文件冲突

**症状:**
```
Warning: Existing configuration found
Do you want to overwrite? [y/N]
```

**原因:** 目标设备已有 OpenCode 配置

**解决方案:**
```bash
# 选项 1: 备份现有配置
mv ~/.config/opencode ~/.config/opencode.backup.$(date +%Y%m%d)

# 选项 2: 合并配置
python3 scripts/migration_installer.py \
  --install backup.zip \
  --merge-config

# 选项 3: 只导入特定部分
python3 scripts/migration_installer.py \
  --install backup.zip \
  --import-skills-only

# 选项 4: 交互式选择
python3 scripts/migration_installer.py \
  --install backup.zip \
  --interactive
```

---

## 配置问题

### 问题 11: 配置文件解析错误

**症状:**
```
JSONDecodeError: Expecting property name enclosed in double quotes
```

**原因:** JSON 格式错误

**解决方案:**
```bash
# 1. 验证 JSON 格式
python3 -m json.tool ~/.config/opencode/config.json

# 2. 使用 jq 修复常见问题
jq '.' ~/.config/opencode/config.json > fixed.json
mv fixed.json ~/.config/opencode/config.json

# 3. 手动修复
# 常见错误：
# - 尾随逗号：{"key": "value",}
# - 单引号：{'key': 'value'}
# - 注释：{"key": "value" // comment}

# 4. 使用备份恢复
cp ~/.config/opencode/config.json.backup ~/.config/opencode/config.json
```

---

### 问题 12: 路径不存在

**症状:**
```
Error: Path '/Users/olduser/project' does not exist
```

**原因:** 路径在新设备上不存在

**解决方案:**
```bash
# 1. 自动修复路径
python3 scripts/platform_adapter.py \
  --fix-paths \
  --old-home /Users/olduser \
  --new-home /Users/newuser

# 2. 手动编辑配置
# 查找所有需要更新的路径
grep -r "/Users/olduser" ~/.config/opencode/

# 批量替换
find ~/.config/opencode -type f -exec sed -i '' 's|/Users/olduser|/Users/newuser|g' {} \;

# 3. 使用环境变量
# 在配置中使用 ${HOME} 代替绝对路径
sed -i '' 's|/Users/[^/]*|${HOME}|g' ~/.config/opencode/config.json
```

---

### 问题 13: 环境变量未设置

**症状:**
```
Error: Environment variable 'API_KEY' is not set
```

**原因:** 新设备缺少必要的环境变量

**解决方案:**
```bash
# 1. 列出所有需要的环境变量
python3 scripts/migration_analyzer.py --list-required-env

# 2. 创建 .env 文件
cat > ~/.config/opencode/.env <<EOF
API_KEY=your-api-key
GITHUB_TOKEN=your-github-token
SLACK_BOT_TOKEN=your-slack-token
EOF

# 3. 加载环境变量
# macOS/Linux (~/.zshrc 或 ~/.bashrc)
export $(cat ~/.config/opencode/.env | xargs)

# Windows (PowerShell profile)
Get-Content "$env:APPDATA\opencode\.env" | ForEach-Object {
  $name, $value = $_.Split('=')
  [Environment]::SetEnvironmentVariable($name, $value, 'User')
}

# 4. 验证
python3 scripts/migration_installer.py --verify-env
```

---

## MCP 服务器问题

### 问题 14: MCP 服务器无法启动

**症状:**
```
Error: spawn npx ENOENT
Failed to start MCP server: filesystem
```

**原因:** Node.js 或 npx 未安装

**解决方案:**
```bash
# 1. 检查 Node.js 安装
node --version
npm --version

# 2. 安装 Node.js
# macOS
brew install node

# Windows
winget install OpenJS.NodeJS

# Linux
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 3. 验证 npx
npx --version

# 4. 测试 MCP 服务器
npx -y @modelcontextprotocol/server-filesystem --help

# 5. 重启 OpenCode
```

---

### 问题 15: MCP 服务器版本不兼容

**症状:**
```
Warning: MCP server version mismatch
Expected: 1.2.0, Found: 1.0.0
```

**原因:** 服务器版本过旧

**解决方案:**
```bash
# 1. 更新所有 MCP 服务器
npm update -g @modelcontextprotocol/*

# 2. 更新特定服务器
npm update -g @modelcontextprotocol/server-filesystem

# 3. 查看已安装版本
npm list -g @modelcontextprotocol/

# 4. 强制重新安装
npm uninstall -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-filesystem@latest

# 5. 清除 npm 缓存
npm cache clean --force
```

---

### 问题 16: MCP 服务器超时

**症状:**
```
Error: MCP server startup timeout (30000ms exceeded)
```

**原因:** 服务器启动慢或网络问题

**解决方案:**
```bash
# 1. 增加超时时间
# 编辑 ~/.config/opencode/mcp_config.json
{
  "mcpSettings": {
    "serverStartupTimeout": 60000
  }
}

# 2. 手动测试服务器启动
npx -y @modelcontextprotocol/server-filesystem /path/to/dir

# 3. 检查服务器日志
tail -f ~/.config/opencode/logs/mcp-*.log

# 4. 禁用慢速服务器
{
  "slow-server": {
    "disabled": true
  }
}

# 5. 检查网络连接
ping registry.npmjs.org
```

---

## 技能问题

### 问题 17: 技能无法加载

**症状:**
```
Error: Skill 'my-skill' not found
Failed to load skill manifest
```

**原因:** 技能文件损坏或路径错误

**解决方案:**
```bash
# 1. 验证技能目录结构
ls -la ~/.config/opencode/skills/my-skill/

# 应该有：
# - SKILL.md
# - manifest.json (可选)
# - 其他资源文件

# 2. 检查 SKILL.md 格式
head -20 ~/.config/opencode/skills/my-skill/SKILL.md

# 3. 重新安装技能
rm -rf ~/.config/opencode/skills/my-skill
# 从备份或原始源重新安装

# 4. 验证技能加载
python3 scripts/migration_installer.py --verify-skills

# 5. 查看详细错误
opencode --debug --load-skill my-skill
```

---

### 问题 18: 技能依赖缺失

**症状:**
```
Error: Required dependency 'python-package' not found
Skill requires: pandas >= 1.0.0
```

**原因:** 技能所需的外部依赖未安装

**解决方案:**
```bash
# 1. 列出所有技能依赖
python3 scripts/migration_analyzer.py --list-skill-dependencies

# 2. 安装 Python 依赖
pip3 install -r ~/.config/opencode/skills/requirements.txt

# 3. 安装 Node.js 依赖
cd ~/.config/opencode/skills/my-skill
npm install

# 4. 系统依赖
# macOS
brew install required-tool

# Linux
sudo apt-get install required-tool

# Windows
winget install required-tool

# 5. 创建虚拟环境（推荐）
python3 -m venv ~/.config/opencode/venv
source ~/.config/opencode/venv/bin/activate
pip install -r requirements.txt
```

---

### 问题 19: 技能版本冲突

**症状:**
```
Warning: Skill version conflict
Existing: 1.0.0, Importing: 2.0.0
```

**原因:** 新旧版本技能冲突

**解决方案:**
```bash
# 1. 备份现有版本
mv ~/.config/opencode/skills/my-skill \
   ~/.config/opencode/skills/my-skill.v1.0.0

# 2. 安装新版本
# 迁移工具会自动处理

# 3. 比较版本差异
diff -r ~/.config/opencode/skills/my-skill.v1.0.0 \
        ~/.config/opencode/skills/my-skill

# 4. 手动合并配置
# 如果有自定义配置，需要手动迁移

# 5. 测试新版本
opencode --test-skill my-skill
```

---

## 权限问题

### 问题 20: 文件权限错误

**症状:**
```
PermissionError: [Errno 13] Permission denied: 'config.json'
Operation not permitted
```

**解决方案:**

**macOS:**
```bash
# 1. 检查文件权限
ls -la ~/.config/opencode/config.json

# 2. 修复权限
chmod 644 ~/.config/opencode/config.json
chmod 755 ~/.config/opencode/scripts/*.py

# 3. 修复所有权
chown -R $USER ~/.config/opencode/

# 4. 如果涉及系统保护目录
# 系统偏好设置 > 安全性与隐私 > 完全磁盘访问权限
# 添加终端或 OpenCode
```

**Windows:**
```powershell
# 1. 检查权限
Get-Acl "$env:APPDATA\opencode\config.json" | Format-List

# 2. 修复权限
icacls "$env:APPDATA\opencode" /grant "${env:USERNAME}:(OI)(CI)F" /T

# 3. 取消只读属性
Get-ChildItem "$env:APPDATA\opencode" -Recurse | 
  ForEach-Object { $_.Attributes = $_.Attributes -band -bnot [System.IO.FileAttributes]::ReadOnly }

# 4. 以管理员身份运行
# 右键点击 PowerShell > 以管理员身份运行
```

---

### 问题 21: 执行权限被拒绝

**症状:**
```bash
zsh: permission denied: ./script.py
```

**解决方案:**
```bash
# 1. 添加执行权限
chmod +x ~/.config/opencode/scripts/*.py
chmod +x ~/.config/opencode/skills/*/scripts/*.sh

# 2. 使用 Python 解释器
python3 ./script.py

# 3. 批量修复
find ~/.config/opencode -name "*.py" -exec chmod +x {} \;
find ~/.config/opencode -name "*.sh" -exec chmod +x {} \;

# 4. 检查 shebang
head -1 script.py
# 应该是: #!/usr/bin/env python3

# 5. 验证
ls -la script.py
./script.py --help
```

---

## 性能问题

### 问题 22: 迁移速度慢

**症状:**
```
Progress: 5% - Estimated time remaining: 2 hours
Packaging very slow...
```

**原因:** 大文件或网络问题

**解决方案:**
```bash
# 1. 排除大文件和不必要的内容
python3 scripts/config_packager.py \
  --exclude "node_modules/,*.log,*.cache,__pycache__/" \
  --output backup.zip

# 2. 使用更快的压缩算法
python3 scripts/config_packager.py \
  --compression-level 1 \
  --output backup.zip

# 3. 分批打包
# 先打包小文件
python3 scripts/config_packager.py --skills-only
# 再打包大文件
python3 scripts/config_packager.py --mcp-only

# 4. 使用 SSD 存储目标
# 确保输出到 SSD 而不是 HDD

# 5. 增量备份
python3 scripts/config_packager.py \
  --incremental \
  --since 2026-01-01 \
  --output incremental.zip
```

---

### 问题 23: 内存不足

**症状:**
```
MemoryError: Unable to allocate array
Process killed: Out of memory
```

**原因:** 打包大量文件时内存不足

**解决方案:**
```bash
# 1. 增加交换空间
# Linux
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 2. 分批处理
python3 scripts/config_packager.py --batch-size 100

# 3. 使用流式压缩
tar -czf backup.tar.gz -C ~/.config opencode

# 4. 清理内存
# macOS
sudo purge

# Linux
sync; echo 3 > /proc/sys/vm/drop_caches

# 5. 关闭其他应用
# 确保有足够的可用内存
```

---

### 问题 24: OpenCode 启动慢

**症状:**
```
OpenCode startup time: 45 seconds
Loading skills...
```

**原因:** 过多的技能或 MCP 服务器

**解决方案:**
```bash
# 1. 禁用不需要的 MCP 服务器
# 编辑 ~/.config/opencode/mcp_config.json
{
  "unused-server": {
    "disabled": true
  }
}

# 2. 延迟加载技能
# 编辑 ~/.config/opencode/config.json
{
  "skillsConfig": {
    "lazyLoad": true,
    "loadOnDemand": true
  }
}

# 3. 清理缓存
rm -rf ~/.config/opencode/.cache/*
rm -rf ~/.config/opencode/logs/*.log

# 4. 优化配置
python3 scripts/migration_analyzer.py --optimize-config

# 5. 检查系统资源
# 确保没有其他进程占用资源
top  # Linux/macOS
tasklist  # Windows
```

---

## 高级故障排除

### 调试模式

启用详细日志：
```bash
# 1. 环境变量
export DEBUG=opencode:*
export OPENCODE_LOG_LEVEL=debug

# 2. 命令行参数
opencode --debug --verbose

# 3. 配置文件
# ~/.config/opencode/config.json
{
  "debug": true,
  "logLevel": "debug",
  "logFile": "~/.config/opencode/logs/debug.log"
}

# 4. 查看日志
tail -f ~/.config/opencode/logs/debug.log
```

### 完全重置

如果所有方法都失败：
```bash
# ⚠️ 警告：这会删除所有配置！

# 1. 备份当前配置
cp -r ~/.config/opencode ~/opencode.backup.$(date +%Y%m%d)

# 2. 完全删除
rm -rf ~/.config/opencode

# 3. 重新安装
python3 scripts/migration_installer.py --clean-install backup.zip

# 4. 如果还有问题，从头开始
# 不使用备份，手动重新配置
```

### 获取帮助

如果问题仍未解决：

1. **收集诊断信息:**
```bash
python3 scripts/migration_analyzer.py --diagnose > diagnostic.txt
```

2. **查看系统信息:**
```bash
# macOS
system_profiler SPSoftwareDataType
sw_vers

# Linux
uname -a
lsb_release -a

# Windows
systeminfo
```

3. **导出配置快照:**
```bash
python3 scripts/migration_analyzer.py --export-snapshot --output snapshot.json
```

4. **在 OpenCode 中请求帮助:**
```
"帮我诊断 OpenCode 迁移问题，这是我的错误信息：[粘贴错误]"
```

5. **查看社区资源:**
- OpenCode 官方文档
- GitHub Issues
- Discord/Slack 社区
- Stack Overflow

---

## 预防措施

### 最佳实践

1. **定期备份:**
```bash
# 设置自动备份 (cron)
0 2 * * 0 python3 ~/scripts/config_packager.py --incremental --output ~/backups/
```

2. **版本控制:**
```bash
cd ~/.config/opencode
git init
git add .
git commit -m "Initial config"
```

3. **测试迁移:**
```bash
# 在虚拟机中测试迁移流程
# 确保一切正常后再在生产环境操作
```

4. **文档化定制:**
```bash
# 记录所有自定义配置
cat > ~/.config/opencode/CUSTOMIZATIONS.md <<EOF
# 自定义配置说明
- MCP 服务器 X 使用自定义路径
- 技能 Y 需要额外依赖 Z
- 环境变量 A 设置为 B
EOF
```

5. **保持更新:**
```bash
# 定期更新工具和依赖
pip3 install --upgrade opencode-migration-tools
npm update -g @modelcontextprotocol/*
```

---

## 总结

大多数迁移问题可以通过以下方式避免：

1. ✅ **仔细规划** - 提前检查兼容性
2. ✅ **完整备份** - 始终保留原始配置
3. ✅ **逐步验证** - 每个阶段都进行测试
4. ✅ **查看日志** - 详细日志是最好的诊断工具
5. ✅ **寻求帮助** - 不要犹豫向社区求助

记住：迁移是一个可逆的过程。如果遇到问题，你总是可以回滚到之前的状态。

---

**需要即时帮助?** 在 OpenCode 中说："帮我解决迁移问题"
