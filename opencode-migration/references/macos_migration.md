# macOS 迁移指南

## 概述

本文档提供从其他平台迁移到 macOS（包括 Apple Silicon 和 Intel）的详细指南。

## 平台差异

### Apple Silicon (M1/M2/M3/M4)
- **架构**: ARM64
- **Homebrew 路径**: `/opt/homebrew`
- **Rosetta 2**: 用于运行 x86_64 软件
- **原生支持**: 大多数现代软件都有 ARM 原生版本

### Intel Mac
- **架构**: x86_64
- **Homebrew 路径**: `/usr/local`
- **兼容性**: 更好的传统软件支持
- **性能**: 在某些工作负载上可能较慢

## 迁移步骤

### 1. 环境准备

#### 1.1 安装 Homebrew
```bash
# Apple Silicon
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc

# Intel
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 1.2 安装基础依赖
```bash
# 通用依赖
brew install git node python@3.11

# OpenCode 特定依赖
brew install uv  # Python 包管理
npm install -g npx  # Node.js 包执行器
```

#### 1.3 配置 Shell 环境
```bash
# 检查当前 shell
echo $SHELL

# 如果是 zsh（默认）
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 如果是 bash
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.bash_profile
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile
```

### 2. OpenCode 配置迁移

#### 2.1 路径调整

**Apple Silicon 特定调整:**
```json
{
  "mcp": {
    "example-server": {
      "command": [
        "/opt/homebrew/bin/python3",
        "-m",
        "mcp_server"
      ]
    }
  }
}
```

**Intel Mac 调整:**
```json
{
  "mcp": {
    "example-server": {
      "command": [
        "/usr/local/bin/python3",
        "-m",
        "mcp_server"
      ]
    }
  }
}
```

#### 2.2 环境变量设置
```bash
# 设置 Python 路径
export PYTHONPATH="/opt/homebrew/lib/python3.11/site-packages:$PYTHONPATH"

# 设置 Node.js 路径
export NODE_PATH="/opt/homebrew/lib/node_modules:$NODE_PATH"
```

### 3. MCP 服务器配置

#### 3.1 常见 MCP 服务器安装

**文件系统服务器:**
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**内存服务器:**
```bash
npm install -g @modelcontextprotocol/server-memory
```

**Python 基础服务器:**
```bash
pip3 install mcp
```

#### 3.2 平台特定问题解决

**问题 1: Python 模块找不到**
```bash
# 重新安装 Python 包
pip3 install --upgrade pip
pip3 install mcp openai anthropic

# 或者使用 uv
uv pip install mcp
```

**问题 2: Node.js 模块权限问题**
```bash
# 修复 npm 权限
sudo chown -R $(whoami) ~/.npm
sudo chown -R $(whoami) /opt/homebrew/lib/node_modules
```

**问题 3: Rosetta 2 兼容性**
```bash
# 检查软件架构
file $(which python3)

# 如果需要 Rosetta 2
softwareupdate --install-rosetta
arch -x86_64 /usr/local/bin/python3 --version
```

### 4. 技能库迁移

#### 4.1 技能目录结构
```
~/.config/opencode/skills/
├── skill-name/
│   ├── SKILL.md
│   ├── scripts/
│   ├── references/
│   └── assets/
```

#### 4.2 技能依赖安装
```bash
# 进入技能目录
cd ~/.config/opencode/skills/specific-skill

# 安装 Python 依赖
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt
fi

# 安装 Node.js 依赖
if [ -f package.json ]; then
    npm install
fi
```

#### 4.3 技能权限设置
```bash
# 设置执行权限
find ~/.config/opencode/skills -name "*.sh" -exec chmod +x {} \;
find ~/.config/opencode/skills -name "*.py" -exec chmod +x {} \;
```

### 5. 性能优化

#### 5.1 Apple Silicon 优化
```bash
# 使用 ARM 原生版本
brew install --cask google-chrome  # ARM 原生
brew install --cask visual-studio-code  # ARM 原生

# 检查软件架构
lipo -info $(which python3)
```

#### 5.2 内存优化
```bash
# 增加 Node.js 内存限制
export NODE_OPTIONS="--max-old-space-size=4096"

# 监控内存使用
top -o mem
```

#### 5.3 启动优化
```bash
# 减少启动时间
export OPENCODE_SKIP_PLUGINS="slow-plugin,another-slow-plugin"

# 使用缓存
export OPENCODE_CACHE_DIR="$HOME/Library/Caches/OpenCode"
```

### 6. 故障排除

#### 6.1 常见问题

**问题: "command not found: python3"**
```bash
# 解决方案
brew install python@3.11
ln -s /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3
```

**问题: "Permission denied"**
```bash
# 解决方案
sudo chown -R $(whoami) ~/.config/opencode
chmod -R 755 ~/.config/opencode
```

**问题: MCP 服务器启动失败**
```bash
# 检查日志
tail -f ~/.config/opencode/opencode.log

# 重新安装 MCP 服务器
npm uninstall -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-filesystem
```

#### 6.2 调试技巧
```bash
# 启用详细日志
export OPENCODE_DEBUG=1

# 检查环境变量
env | grep -i opencode
env | grep -i path

# 检查进程
ps aux | grep opencode
lsof -i :3000  # 检查端口占用
```

#### 6.3 性能诊断
```bash
# CPU 使用
htop

# 磁盘 I/O
iotop

# 网络连接
netstat -an | grep LISTEN

# 内存分析
vm_stat
```

### 7. 备份和恢复

#### 7.1 定期备份
```bash
# 创建备份脚本
cat > ~/backup_opencode.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="$HOME/opencode_backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r ~/.config/opencode "$BACKUP_DIR/"
echo "Backup created: $BACKUP_DIR"
EOF

chmod +x ~/backup_opencode.sh
```

#### 7.2 恢复备份
```bash
# 从备份恢复
BACKUP_DIR="$HOME/opencode_backups/20250127_143022"
rm -rf ~/.config/opencode
cp -r "$BACKUP_DIR/opencode" ~/.config/
```

### 8. 最佳实践

#### 8.1 目录组织
```
~/.config/opencode/
├── opencode.json          # 主配置
├── skills/               # 技能库
├── plugins/              # 插件
├── agents/               # 代理配置
├── logs/                 # 日志文件
└── cache/                # 缓存目录
```

#### 8.2 版本控制
```bash
# 初始化 Git 仓库
cd ~/.config/opencode
git init
git add .
git commit -m "Initial OpenCode configuration"

# 连接到远程仓库
git remote add origin https://github.com/username/opencode-config.git
git push -u origin main
```

#### 8.3 自动化脚本
```bash
# 创建安装脚本
cat > ~/setup_opencode.sh << 'EOF'
#!/bin/bash
echo "Setting up OpenCode on macOS..."

# 安装依赖
brew install git node python@3.11 uv

# 创建配置目录
mkdir -p ~/.config/opencode/{skills,plugins,agents,logs,cache}

# 设置权限
chmod -R 755 ~/.config/opencode

echo "OpenCode setup complete!"
EOF

chmod +x ~/setup_opencode.sh
```

### 9. 资源链接

- [Homebrew 官网](https://brew.sh/)
- [Node.js macOS 安装](https://nodejs.org/en/download/package-manager#macos)
- [Python macOS 安装](https://www.python.org/downloads/macos/)
- [OpenCode 文档](https://opencode.ai/docs)
- [MCP 服务器列表](https://github.com/modelcontextprotocol/servers)

### 10. 更新日志

- **2025-01-27**: 初始版本，包含 Apple Silicon 和 Intel Mac 指南
- **2025-01-28**: 添加故障排除和性能优化章节
- **2025-01-29**: 完善备份恢复和最佳实践