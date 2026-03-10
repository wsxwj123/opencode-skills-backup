# Windows 迁移指南

## 概述

本文档提供从 macOS 或 Linux 迁移到 Windows 的详细指南。Windows 环境与 Unix 系统有显著差异，需要特别注意路径、权限和工具链的调整。

## 环境选择

### 选项 1: 原生 Windows
- **优点**: 性能最佳，无需额外层
- **缺点**: Unix 工具兼容性差
- **推荐**: 对于纯 Windows 工作流

### 选项 2: WSL2 (Windows Subsystem for Linux)
- **优点**: 完整的 Linux 兼容性
- **缺点**: 额外的资源开销
- **推荐**: 对于需要 Unix 工具的工作流

### 选项 3: Git Bash / MSYS2
- **优点**: 轻量级 Unix 环境
- **缺点**: 功能有限
- **推荐**: 简单脚本和 Git 操作

## WSL2 设置（推荐）

### 1. 安装 WSL2

#### 1.1 系统要求
- Windows 10 版本 2004 或更高
- Windows 11
- 启用虚拟化（BIOS/UEFI）

#### 1.2 安装步骤
```powershell
# 以管理员身份打开 PowerShell
wsl --install

# 或手动安装
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 重启后设置 WSL2 为默认
wsl --set-default-version 2

# 安装 Ubuntu
wsl --install -d Ubuntu
```

#### 1.3 配置 WSL2
```bash
# 在 WSL2 中
sudo apt update
sudo apt upgrade -y

# 安装基础工具
sudo apt install -y git curl wget build-essential
```

### 2. 安装 OpenCode 依赖

#### 2.1 Node.js 安装
```bash
# 方法 1: 使用 NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 方法 2: 使用 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
```

#### 2.2 Python 安装
```bash
# 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 安装 pip
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# 安装 uv (现代 Python 包管理)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.cargo/env
```

#### 2.3 其他工具
```bash
# Git
sudo apt install -y git

# 压缩工具
sudo apt install -y zip unzip

# 开发工具
sudo apt install -y pkg-config libssl-dev
```

## 原生 Windows 设置

### 1. 安装必要软件

#### 1.1 Chocolatey (包管理器)
```powershell
# 以管理员身份运行 PowerShell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

#### 1.2 安装基础软件
```powershell
# Git
choco install git -y

# Node.js
choco install nodejs -y

# Python
choco install python -y

# 7-Zip
choco install 7zip -y

# VS Code
choco install vscode -y
```

#### 1.3 配置环境变量
```powershell
# 刷新环境变量
refreshenv

# 检查安装
node --version
python --version
git --version
```

### 2. OpenCode 配置调整

#### 2.1 路径转换

**Unix 路径到 Windows 路径映射:**
```
Unix: /Users/username/.config/opencode
Windows: C:\Users\username\.config\opencode

Unix: /opt/homebrew/bin/python3
Windows: C:\Python39\python.exe 或 python
```

#### 2.2 配置文件调整

**修改 opencode.json:**
```json
{
  "mcp": {
    "filesystem": {
      "command": [
        "npx",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\username",
        "C:\\Users\\username\\Desktop"
      ]
    },
    "example-server": {
      "command": [
        "python",
        "-m",
        "mcp_server"
      ]
    }
  }
}
```

#### 2.3 环境变量设置
```powershell
# 设置 OpenCode 路径
[Environment]::SetEnvironmentVariable("OPENCODE_CONFIG_DIR", "C:\Users\username\.config\opencode", "User")

# 设置 Python 路径
[Environment]::SetEnvironmentVariable("PYTHONPATH", "C:\Python39\Lib\site-packages", "User")

# 刷新当前会话
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

## 迁移步骤

### 步骤 1: 分析源配置
```bash
# 在源设备上运行
python3 migration_analyzer.py --analyze --output migration_report.json
```

### 步骤 2: 创建迁移包
```bash
# 在源设备上运行
python3 config_packager.py --package --output opencode_windows_migration.zip
```

### 步骤 3: 传输文件
```powershell
# 方法 1: 使用网络共享
# 在 Windows 上创建共享文件夹
New-Item -Path "C:\Shared" -ItemType Directory
# 从 macOS 复制文件

# 方法 2: 使用云存储
# 上传到 Google Drive、Dropbox 等

# 方法 3: 使用 SCP (WSL2)
# 在 WSL2 中
scp user@macos:/path/to/opencode_windows_migration.zip .
```

### 步骤 4: 安装迁移包

#### WSL2 安装:
```bash
# 在 WSL2 中
python3 migration_installer.py --install opencode_windows_migration.zip
```

#### 原生 Windows 安装:
```powershell
# 可能需要调整 Python 命令
python migration_installer.py --install opencode_windows_migration.zip
```

## 平台特定问题解决

### 问题 1: 路径分隔符
**症状**: `SyntaxError: invalid syntax` 或 `FileNotFoundError`

**解决方案:**
```python
# 在 Python 脚本中使用 os.path
import os
config_path = os.path.join(os.path.expanduser("~"), ".config", "opencode")

# 或使用 pathlib
from pathlib import Path, PureWindowsPath
config_path = Path.home() / ".config" / "opencode"
```

### 问题 2: 行结束符
**症状**: `bash: $'\r': command not found`

**解决方案:**
```bash
# 转换行结束符
dos2unix script.sh

# 或在 Git 中配置
git config --global core.autocrlf input
```

### 问题 3: 权限问题
**症状**: `Permission denied` 或 `Access is denied`

**解决方案:**
```powershell
# 以管理员身份运行
Start-Process PowerShell -Verb RunAs

# 修改权限
icacls "C:\Users\username\.config\opencode" /grant username:F /T
```

### 问题 4: 环境变量
**症状**: 命令找不到或配置不生效

**解决方案:**
```powershell
# 检查环境变量
Get-ChildItem Env: | Where-Object Name -like "*PATH*"

# 添加到 PATH
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Python39", "User")
```

## WSL2 与 Windows 集成

### 1. 文件系统访问
```bash
# 从 WSL2 访问 Windows 文件
cd /mnt/c/Users/username

# 从 Windows 访问 WSL2 文件
# 在文件资源管理器中输入: \\wsl$\Ubuntu\home\username
```

### 2. 网络集成
```bash
# 从 WSL2 访问 Windows 服务
curl http://host.docker.internal:3000

# 从 Windows 访问 WSL2 服务
# 使用 localhost (WSL2 自动端口转发)
```

### 3. 环境变量共享
```bash
# 在 WSL2 中访问 Windows 环境变量
echo $WSLENV
export WINDOWS_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')
```

## 性能优化

### 1. WSL2 性能优化
```bash
# 创建 .wslconfig 文件
cat > /mnt/c/Users/username/.wslconfig << EOF
[wsl2]
memory=8GB
processors=4
localhostForwarding=true
EOF

# 重启 WSL2
wsl --shutdown
```

### 2. 磁盘性能
```bash
# 将项目文件放在 WSL2 文件系统中
# 而不是 /mnt/c/ 中，以获得更好的性能
mkdir -p ~/projects/opencode
```

### 3. 内存管理
```powershell
# 限制 WSL2 内存使用
# 在 .wslconfig 中设置
memory=4GB
swap=2GB
```

## 安全考虑

### 1. 文件权限
```powershell
# 设置适当的权限
icacls "C:\Users\username\.config\opencode" /inheritance:r
icacls "C:\Users\username\.config\opencode" /grant:r username:(OI)(CI)F
```

### 2. 敏感信息保护
```bash
# 不要在配置文件中硬编码密钥
# 使用环境变量
export OPENAI_API_KEY="your-key-here"

# 或在 Windows 中
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-key-here", "User")
```

### 3. 防火墙配置
```powershell
# 允许 OpenCode 相关端口
New-NetFirewallRule -DisplayName "OpenCode" -Direction Inbound -Protocol TCP -LocalPort 3000-3010 -Action Allow
```

## 备份和恢复

### 1. Windows 备份
```powershell
# 创建备份脚本
$backupDir = "C:\Backups\OpenCode\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force
Copy-Item -Path "C:\Users\username\.config\opencode" -Destination $backupDir -Recurse
```

### 2. WSL2 备份
```powershell
# 导出 WSL2 发行版
wsl --export Ubuntu ubuntu_backup.tar

# 导入恢复
wsl --import UbuntuNew C:\WSL\UbuntuNew ubuntu_backup.tar
```

## 故障排除

### 常见错误

**错误: "python3: command not found"**
```powershell
# 解决方案
# 确保 Python 已安装并添加到 PATH
python --version
# 如果只有 python 没有 python3，创建符号链接
mklink C:\Python39\python3.exe C:\Python39\python.exe
```

**错误: "npm: command not found"**
```powershell
# 解决方案
# 重新安装 Node.js 或修复 PATH
refreshenv
npm --version
```

**错误: "Access denied"**
```powershell
# 解决方案
# 以管理员身份运行
Start-Process PowerShell -Verb RunAs
```

### 调试工具
```powershell
# 检查系统信息
systeminfo

# 检查磁盘空间
Get-PSDrive C | Select-Object Used,Free

# 检查网络
Test-NetConnection -ComputerName google.com -Port 443

# 检查进程
Get-Process | Where-Object {$_.ProcessName -like "*node*" -or $_.ProcessName -like "*python*"}
```

## 最佳实践

### 1. 使用版本控制
```bash
# 在 WSL2 中初始化 Git
cd ~/.config/opencode
git init
git add .
git commit -m "Initial Windows migration"

# 或使用 Git for Windows
cd C:\Users\username\.config\opencode
git init
```

### 2. 文档化配置
```markdown
# 创建 README.md
记录所有自定义配置和调整
```

### 3. 定期测试
```powershell
# 创建测试脚本
Test-OpenCode.ps1:
- 检查所有 MCP 服务器
- 验证技能功能
- 测试性能
```

### 4. 监控和日志
```powershell
# 启用日志
$env:OPENCODE_LOG_LEVEL="debug"

# 监控资源使用
Get-Counter '\Process(*)\% Processor Time' | Select-Object -ExpandProperty CounterSamples | Where-Object {$_.InstanceName -like "*opencode*"}
```

## 资源链接

- [WSL2 官方文档](https://docs.microsoft.com/en-us/windows/wsl/)
- [Chocolatey 包管理器](https://chocolatey.org/)
- [Windows Terminal](https://github.com/microsoft/terminal)
- [PowerShell 文档](https://docs.microsoft.com/en-us/powershell/)
- [OpenCode Windows 支持](https://opencode.ai/docs/windows)

## 更新日志

- **2025-01-27**: 初始版本，包含 WSL2 和原生 Windows 指南
- **2025-01-28**: 添加故障排除和性能优化
- **2025-01-29**: 完善安全考虑和最佳实践