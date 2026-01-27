# OpenCode MCP 服务器清单

本文档列出了当前 OpenCode 配置中使用的所有 MCP 服务器及其安装方式。

---

## 🔗 GitHub 仓库速查表

| 服务器名称 | GitHub 仓库 | 状态 |
|-----------|------------|------|
| file-to-pdf | https://github.com/wowyuarm/file-converter-mcp | ✅ |
| ppt-mcp | https://github.com/GongRzhe/Office-PowerPoint-MCP-Server | ✅ |
| word-mcp | https://github.com/GongRzhe/Office-Word-MCP-Server | ✅ |
| claude-document | https://github.com/alejandroBallesterosC/document-edit-mcp | ✅ |
| paper-search | https://github.com/openags/paper-search-mcp | ✅ |
| quickchart | https://github.com/GongRzhe/quickchart-mcp-server | ✅ |
| drawio | https://github.com/lgazo/drawio-mcp-server | ✅ |
| markdownify | https://github.com/zcaceres/markdownify-mcp | ✅ |
| arxiv | https://github.com/blazickjp/arxiv-mcp-server | ✅ |
| desktop-commander | https://github.com/wonderwhy-er/DesktopCommanderMCP | ✅ |
| tavily | https://github.com/tavily-ai/tavily-mcp | ✅ |
| filesystem | https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem | ✅ |
| memory | https://github.com/modelcontextprotocol/servers/tree/main/src/memory | ✅ |
| playwright | https://github.com/executeautomation/playwright-mcp-server | ✅ |
| sequential-thinking | https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking | ✅ |
| office-editor | ⚠️ 未找到（私有或本地） | ❌ |
| reddit | ⚠️ 未找到（私有或本地） | ❌ |

---

## 📦 NPM 包管理的 MCP 服务器

这些服务器通过 `npx` 自动安装，**无需手动部署**：

| 服务器名称 | NPM 包名 | 用途 | 配置状态 |
|-----------|---------|------|---------|
| memory | `@modelcontextprotocol/server-memory` | 会话记忆管理 | ✅ 启用 |
| desktop-commander | `@wonderwhy-er/desktop-commander` | 桌面自动化 | ✅ 启用 |

**NPM 包 GitHub 仓库**：
- memory: https://github.com/modelcontextprotocol/servers/tree/main/src/memory
- desktop-commander: https://github.com/wonderwhy-er/DesktopCommanderMCP
- sequential-thinking: https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking
- playwright: https://github.com/executeautomation/playwright-mcp-server
- tavily: https://github.com/tavily-ai/tavily-mcp
- filesystem: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
| sequential-thinking | `@modelcontextprotocol/server-sequential-thinking` | 思维链 | ❌ 禁用 |
| context7 | `@upstash/context7-mcp` | 上下文管理 | ❌ 禁用 |
| playwright | `@executeautomation/playwright-mcp-server` | 浏览器自动化 | ✅ 启用 |
| tavily | `tavily-mcp@0.1.4` | 网页搜索 | ✅ 启用 |
| filesystem | `@modelcontextprotocol/server-filesystem` | 文件系统访问 | ✅ 启用 |

**安装方式**：这些服务器会在 OpenCode 启动时自动通过 `npx -y` 安装，无需额外操作。

---

## 🐍 Python 虚拟环境的 MCP 服务器

这些服务器需要从 GitHub 下载并手动部署：

### 1. **file-to-pdf** - 文件格式转换
- **GitHub**: https://github.com/wowyuarm/file-converter-mcp.git
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/file-to-pdf/file-converter-mcp`
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP/file-to-pdf
  git clone https://github.com/wowyuarm/file-converter-mcp.git file-converter-mcp
  cd file-converter-mcp
  python3 -m venv venv
  source venv/bin/activate  # Windows: venv\Scripts\activate
  pip install -r requirements.txt
  ```

### 2. **office-editor** - Office 文档编辑
- **GitHub**: ⚠️ 本地部署，未找到 Git 仓库（可能是私有仓库或本地开发）
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/ms-edit-mcp/office-editor-mcp-main`
- **备注**: 如需重新部署，请联系原作者或使用本地备份
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP/ms-edit-mcp
  git clone <REPOSITORY_URL> office-editor-mcp-main
  cd office-editor-mcp-main
  python3 -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  ```

### 3. **ppt-mcp** - PowerPoint 操作
- **GitHub**: https://github.com/GongRzhe/Office-PowerPoint-MCP-Server.git
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/ppt-mcp`
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP/ppt-mcp
  git clone https://github.com/GongRzhe/Office-PowerPoint-MCP-Server.git .
  python3 -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  ```

### 4. **word-mcp** - Word 文档操作
- **GitHub**: https://github.com/GongRzhe/Office-Word-MCP-Server
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/word-mcp/Office-Word-MCP-Server`
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP/word-mcp
  git clone <REPOSITORY_URL> Office-Word-MCP-Server
  cd Office-Word-MCP-Server
  python3 -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  ```

### 5. **claude-document** - Claude 文档处理
- **GitHub**: https://github.com/alejandroBallesterosC/document-edit-mcp
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/document`
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP/document
  git clone <REPOSITORY_URL> .
  python3 -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install -e .
  ```

### 6. **reddit** - Reddit 数据访问
- **GitHub**: ⚠️ 本地部署，未找到 Git 仓库（可能是私有仓库或本地开发）
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/mcp-server-reddit`
- **备注**: 如需重新部署，请联系原作者或使用本地备份
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP/mcp-server-reddit
  git clone <REPOSITORY_URL> .
  python3 -m venv mcp_reddit_venv
  source mcp_reddit_venv/bin/activate  # Windows: mcp_reddit_venv\Scripts\activate
  pip install -r requirements.txt
  ```

### 7. **paper-search** - 学术论文搜索
- **GitHub**: https://github.com/openags/paper-search-mcp
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/paper-search-mcp/paper-search-mcp`
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP/paper-search-mcp
  git clone <REPOSITORY_URL> paper-search-mcp
  cd paper-search-mcp
  # 使用 uv 工具运行，无需手动创建虚拟环境
  ```

---

## 🌐 UV 工具管理的 MCP 服务器

这些服务器使用 `uv` 或 `uvx` 工具管理：

### 8. **arxiv** - arXiv 论文访问
- **GitHub**: https://github.com/blazickjp/arxiv-mcp-server
- **安装方式**: `uv tool install arxiv-mcp-server`
- **配置**: 存储路径为 `/Users/wsxwj/Downloads/reference`
- **无需 GitHub 仓库**

### 9. **pandoc** - Pandoc 文档转换
- **安装方式**: `uvx mcp-pandoc`
- **无需 GitHub 仓库**

### 10. **fetch** - 网页内容获取
- **安装方式**: `uvx mcp-server-fetch`
- **无需 GitHub 仓库**

---

## 📝 Node.js 本地部署的 MCP 服务器

这些服务器需要从 GitHub 下载并使用 Node.js 运行：

### 11. **quickchart** - 图表生成
- **GitHub**: https://github.com/GongRzhe/quickchart-mcp-server.git
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/quickchart-mcp-server`
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP
  git clone <REPOSITORY_URL> quickchart-mcp-server
  cd quickchart-mcp-server
  npm install
  npm run build
  ```

### 12. **drawio** - Draw.io 图表编辑
- **GitHub**: https://github.com/lgazo/drawio-mcp-server.git
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/drawio-mcp-server/drawio-mcp-server`
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP/drawio-mcp-server
  git clone <REPOSITORY_URL> drawio-mcp-server
  cd drawio-mcp-server
  npm install
  npm run build
  ```

### 13. **markdownify** - 格式转换为 Markdown
- **GitHub**: https://github.com/zcaceres/markdownify-mcp
- **当前路径**: `/Users/wsxwj/Documents/Cline/MCP/markdownify`
- **部署步骤**:
  ```bash
  cd ~/Documents/Cline/MCP
  git clone <REPOSITORY_URL> markdownify
  cd markdownify
  npm install
  npm run build
  ```

---

## 🔧 依赖工具安装

### UV 工具（Python 包管理器）
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Node.js 和 NPM
- 访问 https://nodejs.org/ 下载安装
- 或使用包管理器：
  - macOS: `brew install node`
  - Windows: `choco install nodejs`
  - Linux: `sudo apt install nodejs npm`

### Python 3
- macOS: 系统自带或 `brew install python3`
- Windows: https://www.python.org/downloads/
- Linux: `sudo apt install python3 python3-venv python3-pip`

---

## 📋 快速部署检查清单

在新设备上部署 OpenCode MCP 服务器时，请按以下步骤：

### 1. 安装依赖工具
- [ ] Node.js (≥16.x)
- [ ] Python 3 (≥3.8)
- [ ] UV 工具

### 2. 创建 MCP 目录
```bash
mkdir -p ~/Documents/Cline/MCP
cd ~/Documents/Cline/MCP
```

### 3. 克隆并部署本地 MCP 服务器
按照上面的部署步骤，逐个部署需要的服务器。

### 4. 更新 opencode.json 配置
将配置中的路径替换为新设备的对应路径：
- macOS/Linux: `/Users/<USERNAME>/Documents/Cline/MCP/...`
- Windows: `C:\Users\<USERNAME>\Documents\Cline\MCP\...`

### 5. 验证部署
启动 OpenCode 并检查所有 MCP 服务器是否正常工作。

---

## ⚠️ 注意事项

1. **Python 虚拟环境路径差异**：
   - macOS/Linux: `venv/bin/python` 或 `.venv/bin/python`
   - Windows: `venv\Scripts\python.exe` 或 `.venv\Scripts\python.exe`

2. **绝对路径需要更新**：
   所有 MCP 服务器的路径配置需要根据新设备的用户名和操作系统更新。

3. **API Keys**：
   Tavily API Key 已包含在配置中，备份时会一并保存。

4. **文件系统访问路径**：
   `filesystem` MCP 服务器的访问路径需要根据新设备更新：
   - 当前配置: `/Users/wsxwj/Desktop`, `/Users/wsxwj`
   - 新设备需要更新为对应的用户目录

---

**最后更新**: 2026-01-27
**维护者**: wsxwj
**自动查找工具**: scripts/find_mcp_repos.py
