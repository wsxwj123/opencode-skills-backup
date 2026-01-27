# 跨平台迁移指南

本文档说明如何将 OpenCode 配置从一台设备迁移到另一台设备。

---

## 🎯 迁移目标

将当前 macOS 设备的 OpenCode 配置完整迁移到：
- 另一台 Mac
- Windows 设备
- Linux 设备

---

## 📋 迁移前准备

### 1. 确认当前设备备份完整

在当前设备上运行：
```bash
cd ~/.config/opencode/skills/opencode-backup
python3 scripts/backup_opencode.py status
```

如果需要备份，运行：
```bash
python3 scripts/backup_opencode.py backup
```

### 2. 记录当前配置信息

**API Keys**（已包含在备份中）：
- ✅ Tavily API Key（在 `opencode.json` 中）
- ✅ LinkAPI API Key（在 `opencode.json` 中）
- ✅ KuaiAPI API Key（在 `opencode.json` 中）
- ✅ MMW API Keys（在 `opencode.json` 中）

**MCP 服务器 Git 仓库**（见 `MCP_SERVERS.md`）

---

## 🚀 新设备迁移步骤

### 步骤 1: 克隆备份仓库

在新设备上：

```bash
# 在新设备上克隆备份仓库
git clone https://github.com/wsxwj123/opencode-backup-macmini.git ~/opencode-backup-temp

# 创建 OpenCode 配置目录
mkdir -p ~/.config/opencode

# 复制备份内容到 OpenCode 配置目录
cp -r ~/opencode-backup-temp/* ~/.config/opencode/
```

### 步骤 2: 更新配置文件中的路径

**需要更新的文件**: `~/.config/opencode/opencode.json`

#### 2.1 更新用户主目录路径

使用文本编辑器打开 `opencode.json`，查找并替换：

- **macOS**: `/Users/wsxwj` → `/Users/<你的用户名>`
- **Windows**: `/Users/wsxwj` → `C:\Users\<你的用户名>`
- **Linux**: `/Users/wsxwj` → `/home/<你的用户名>`

#### 2.2 更新 Python 虚拟环境路径

**macOS/Linux**:
- `venv/bin/python` 或 `.venv/bin/python`

**Windows**:
- `venv\Scripts\python.exe` 或 `.venv\Scripts\python.exe`

在 `opencode.json` 中查找所有 Python MCP 服务器配置并更新路径格式。

#### 2.3 更新文件系统访问路径

找到 `filesystem` MCP 服务器配置，更新访问路径：

```json
"filesystem": {
  "type": "local",
  "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/Users/<用户名>/Desktop", "/Users/<用户名>"],
  "enabled": true
}
```

### 步骤 3: 重新部署本地 MCP 服务器

参考 `MCP_SERVERS.md` 文档，重新克隆并部署需要的 MCP 服务器。

#### 3.1 创建 MCP 目录

```bash
# macOS/Linux
mkdir -p ~/Documents/Cline/MCP
cd ~/Documents/Cline/MCP

# Windows
mkdir %USERPROFILE%\Documents\Cline\MCP
cd %USERPROFILE%\Documents\Cline\MCP
```

#### 3.2 克隆 MCP 服务器

按照 `MCP_SERVERS.md` 中的 GitHub 地址，逐个克隆并安装：

**Python MCP 服务器**:
```bash
# 示例: file-to-pdf
git clone https://github.com/wowyuarm/file-converter-mcp.git file-to-pdf/file-converter-mcp
cd file-to-pdf/file-converter-mcp
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..
```

**Node.js MCP 服务器**:
```bash
# 示例: quickchart
git clone https://github.com/GongRzhe/quickchart-mcp-server.git
cd quickchart-mcp-server
npm install
npm run build
cd ..
```

### 步骤 4: 安装依赖工具

#### macOS
```bash
# Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Node.js 和 Python
brew install node python3

# UV 工具
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows
```powershell
# Node.js: 从 https://nodejs.org/ 下载安装
# Python: 从 https://www.python.org/downloads/ 下载安装

# UV 工具
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Linux (Ubuntu/Debian)
```bash
# Node.js 和 Python
sudo apt update
sudo apt install nodejs npm python3 python3-venv python3-pip

# UV 工具
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 步骤 5: 验证配置

安装 OpenCode 并启动，检查：

1. ✅ 所有 MCP 服务器是否正常加载
2. ✅ API Keys 是否工作
3. ✅ Skills 是否可用
4. ✅ 文件系统访问是否正常

---

## 🔧 常见问题解决

### 问题 1: MCP 服务器无法启动

**症状**: OpenCode 启动时提示 MCP 服务器连接失败

**解决方案**:
1. 检查 `opencode.json` 中的路径是否正确
2. 确认 Python 虚拟环境已正确创建
3. 检查 Node.js 服务器是否已运行 `npm run build`
4. 查看 OpenCode 日志获取详细错误信息

### 问题 2: Python 虚拟环境路径错误

**症状**: Python MCP 服务器无法启动

**解决方案**:
```bash
# 检查虚拟环境是否存在
ls -la ~/Documents/Cline/MCP/<服务器名>/.venv

# 重新创建虚拟环境
cd ~/Documents/Cline/MCP/<服务器名>
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 问题 3: Git 代理配置

如果在中国大陆，可能需要配置 Git 代理：

```bash
# 设置全局代理
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897

# 取消代理
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### 问题 4: API Keys 无效

**症状**: API 调用失败

**解决方案**:
1. 检查 `opencode.json` 中的 API Keys 是否完整
2. 确认 API Keys 未过期
3. 检查 API 服务提供商的账户状态

---

## 📊 迁移检查清单

使用此清单确保迁移完整：

- [ ] 备份仓库已克隆到新设备
- [ ] OpenCode 配置目录已创建
- [ ] `opencode.json` 路径已更新
- [ ] Python 虚拟环境路径已更新（Windows）
- [ ] 文件系统访问路径已更新
- [ ] 所有依赖工具已安装（Node.js, Python, UV）
- [ ] MCP 服务器已重新部署
- [ ] Python MCP 服务器虚拟环境已创建
- [ ] Node.js MCP 服务器已构建
- [ ] OpenCode 可以正常启动
- [ ] 所有 MCP 服务器已连接
- [ ] API Keys 工作正常
- [ ] Skills 可用
- [ ] 文件系统访问正常

---

## 🎉 迁移完成

恭喜！您已成功将 OpenCode 配置迁移到新设备。

**下一步**:
1. 在新设备上初始化备份：
   ```bash
   cd ~/.config/opencode/skills/opencode-backup
   python3 scripts/backup_opencode.py init --repo-url https://github.com/wsxwj123/opencode-backup-<新设备名>.git
   ```

2. 定期备份新设备的配置：
   ```bash
   python3 scripts/backup_opencode.py backup
   ```

---

**最后更新**: 2026-01-27
**维护者**: wsxwj
