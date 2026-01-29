# MCP 服务器迁移指南

## 概述

MCP (Model Context Protocol) 服务器是 OpenCode 的核心组件，负责扩展 AI 的能力。本指南详细说明如何在不同平台间迁移 MCP 服务器配置。

## MCP 服务器架构

### 配置文件位置

**macOS/Linux:**
```
~/.config/opencode/mcp_config.json
```

**Windows:**
```
%APPDATA%\opencode\mcp_config.json
```

### 典型配置结构

```json
{
  "mcpServers": {
    "server-name": {
      "command": "node",
      "args": ["/path/to/server/index.js"],
      "env": {
        "API_KEY": "your-api-key"
      },
      "disabled": false
    }
  }
}
```

## 通用迁移步骤

### 1. 备份当前配置

```bash
# macOS/Linux
cp ~/.config/opencode/mcp_config.json ~/backup/mcp_config.json

# Windows
copy %APPDATA%\opencode\mcp_config.json %USERPROFILE%\backup\
```

### 2. 导出服务器列表

使用迁移工具自动导出：

```bash
python3 scripts/migration_analyzer.py --export-mcp-servers
```

生成的报告包含：
- 服务器名称和类型
- 依赖项版本
- 配置参数
- 平台兼容性状态

### 3. 检查平台兼容性

```bash
python3 scripts/platform_adapter.py --check-mcp-compatibility --target windows
```

## 常见 MCP 服务器迁移

### 1. Filesystem MCP Server

**跨平台兼容性:** ✅ 完全兼容

**配置调整:**

macOS 配置：
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/username/allowed-dir"],
    "env": {}
  }
}
```

Windows 配置：
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\Users\\username\\allowed-dir"],
    "env": {}
  }
}
```

**迁移脚本:**
```bash
# 自动转换路径
python3 scripts/platform_adapter.py --convert-paths \
  --from macos \
  --to windows \
  --server filesystem
```

### 2. Memory MCP Server

**跨平台兼容性:** ✅ 完全兼容

**无需特殊配置**

迁移后验证：
```bash
# 测试内存服务器
echo "create_entities([{'name': 'test', 'type': 'test'}])" | opencode-mcp-test memory
```

### 3. Brave Search MCP Server

**跨平台兼容性:** ✅ 完全兼容

**环境变量配置:**

macOS/Linux:
```json
{
  "brave-search": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "your-api-key"
    }
  }
}
```

Windows (相同配置):
```json
{
  "brave-search": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "your-api-key"
    }
  }
}
```

### 4. Puppeteer MCP Server

**跨平台兼容性:** ⚠️ 需要额外配置

**macOS:**
```json
{
  "puppeteer": {
    "command": "node",
    "args": ["/usr/local/lib/node_modules/@modelcontextprotocol/server-puppeteer/dist/index.js"],
    "env": {}
  }
}
```

**Windows:**
```json
{
  "puppeteer": {
    "command": "node",
    "args": ["C:\\Program Files\\nodejs\\node_modules\\@modelcontextprotocol\\server-puppeteer\\dist\\index.js"],
    "env": {
      "PUPPETEER_EXECUTABLE_PATH": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    }
  }
}
```

**额外依赖:**
- 需要安装 Chrome/Chromium
- Windows 需要指定可执行文件路径

### 5. SQLite MCP Server

**跨平台兼容性:** ✅ 完全兼容

**数据库路径调整:**

macOS:
```json
{
  "sqlite": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-sqlite",
      "/Users/username/databases/mydb.sqlite"
    ]
  }
}
```

Windows:
```json
{
  "sqlite": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-sqlite",
      "C:\\Users\\username\\databases\\mydb.sqlite"
    ]
  }
}
```

**迁移数据库文件:**
```bash
# 复制数据库文件
cp ~/databases/mydb.sqlite /path/to/backup/

# 在新设备上恢复
cp /path/to/backup/mydb.sqlite ~/databases/
```

### 6. GitHub MCP Server

**跨平台兼容性:** ✅ 完全兼容

**GitHub Token 配置:**

```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
    }
  }
}
```

**迁移注意事项:**
- GitHub Token 需要手动配置
- 不要在迁移包中包含 Token（自动过滤）
- 在新设备上重新设置 Token

### 7. Slack MCP Server

**跨平台兼容性:** ✅ 完全兼容

**配置示例:**

```json
{
  "slack": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"],
    "env": {
      "SLACK_BOT_TOKEN": "xoxb-your-token",
      "SLACK_TEAM_ID": "T01234567"
    }
  }
}
```

### 8. Google Drive MCP Server

**跨平台兼容性:** ⚠️ 需要重新认证

**配置示例:**

```json
{
  "gdrive": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-gdrive"],
    "env": {
      "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/credentials.json"
    }
  }
}
```

**迁移步骤:**
1. 导出 OAuth credentials
2. 在新设备上重新认证
3. 更新配置路径

### 9. PostgreSQL MCP Server

**跨平台兼容性:** ✅ 完全兼容

**配置示例:**

```json
{
  "postgres": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-postgres"],
    "env": {
      "POSTGRES_CONNECTION_STRING": "postgresql://user:password@localhost:5432/dbname"
    }
  }
}
```

**迁移注意事项:**
- 连接字符串需要更新
- 确保目标设备可以访问数据库

### 10. EverArt MCP Server

**跨平台兼容性:** ✅ 完全兼容

**配置示例:**

```json
{
  "everart": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-everart"],
    "env": {
      "EVERART_API_KEY": "your-api-key"
    }
  }
}
```

## 自定义 MCP 服务器迁移

### 本地开发服务器

**迁移步骤:**

1. **打包服务器代码**
```bash
# 压缩服务器目录
tar -czf my-mcp-server.tar.gz ~/mcp-servers/my-server/
```

2. **传输到目标设备**

3. **解压并安装依赖**
```bash
tar -xzf my-mcp-server.tar.gz
cd my-server
npm install
```

4. **更新配置路径**
```json
{
  "my-server": {
    "command": "node",
    "args": ["/new/path/to/my-server/index.js"],
    "env": {}
  }
}
```

### NPM 包服务器

**更简单的迁移方式:**

1. 记录包名和版本
2. 在新设备上重新安装：
```bash
npm install -g @scope/mcp-server-name@version
```

## 批量迁移

### 使用迁移工具

```bash
# 1. 导出所有 MCP 服务器配置
python3 scripts/migration_analyzer.py --export-mcp-servers --output mcp_backup.json

# 2. 适配到目标平台
python3 scripts/platform_adapter.py \
  --convert-mcp-servers \
  --input mcp_backup.json \
  --target windows \
  --output mcp_windows.json

# 3. 在目标设备上导入
python3 scripts/migration_installer.py \
  --import-mcp-servers mcp_windows.json
```

### 手动批量更新路径

使用 `jq` 工具：

```bash
# macOS → Windows 路径转换
jq '
  walk(
    if type == "string" and startswith("/Users/") then
      gsub("/Users/"; "C:/Users/") | gsub("/"; "\\")
    else
      .
    end
  )
' mcp_config.json > mcp_config_windows.json
```

## 验证和测试

### 1. 验证配置文件

```bash
# 检查 JSON 语法
python3 -m json.tool ~/.config/opencode/mcp_config.json

# 验证配置完整性
python3 scripts/migration_installer.py --verify-mcp-config
```

### 2. 测试单个服务器

```bash
# 测试文件系统服务器
opencode-cli test-mcp filesystem

# 测试内存服务器
opencode-cli test-mcp memory
```

### 3. 查看服务器日志

**macOS/Linux:**
```bash
tail -f ~/.config/opencode/logs/mcp-*.log
```

**Windows:**
```powershell
Get-Content "$env:APPDATA\opencode\logs\mcp-*.log" -Wait
```

### 4. 检查服务器状态

在 OpenCode 中运行：
```
"显示所有 MCP 服务器的状态"
```

## 常见问题

### 问题 1: 服务器无法启动

**症状:**
```
Error: Cannot find module '/path/to/server/index.js'
```

**解决方案:**
```bash
# 1. 检查路径是否正确
ls /path/to/server/index.js

# 2. 重新安装服务器
npm install -g @modelcontextprotocol/server-name

# 3. 更新配置文件路径
python3 scripts/platform_adapter.py --fix-mcp-paths
```

### 问题 2: 环境变量未生效

**症状:**
```
Error: API key not found
```

**解决方案:**
```bash
# 1. 检查环境变量配置
cat ~/.config/opencode/mcp_config.json | grep -A 5 env

# 2. 手动设置环境变量
export API_KEY="your-key"

# 3. 在配置中添加环境变量
# 编辑 mcp_config.json
```

### 问题 3: 权限错误

**症状:**
```
Error: EACCES: permission denied
```

**解决方案:**
```bash
# macOS/Linux
chmod +x /path/to/server/index.js
chmod -R u+rw ~/.config/opencode/

# Windows (以管理员身份运行)
icacls "%APPDATA%\opencode" /grant %USERNAME%:F /T
```

### 问题 4: Node.js 版本不兼容

**症状:**
```
Error: The engine "node" is incompatible with this module
```

**解决方案:**
```bash
# 检查 Node.js 版本
node --version

# 更新到所需版本
# macOS (使用 nvm)
nvm install 18
nvm use 18

# Windows (使用 nvm-windows)
nvm install 18
nvm use 18
```

### 问题 5: npx 命令找不到

**症状:**
```
Error: 'npx' is not recognized
```

**解决方案:**
```bash
# 确保 npm 已正确安装
npm --version

# 重新安装 Node.js
# macOS
brew install node

# Windows
# 从 nodejs.org 下载安装器
```

## 安全最佳实践

### 1. 保护 API 密钥

**不要做:**
- ❌ 在 Git 中提交包含密钥的配置文件
- ❌ 在公共云存储上分享配置文件
- ❌ 在迁移包中包含明文密钥

**应该做:**
- ✅ 使用环境变量存储密钥
- ✅ 使用密钥管理工具（如 1Password、LastPass）
- ✅ 在新设备上手动配置密钥

### 2. 使用 .env 文件

创建 `.env` 文件：
```bash
# .env
BRAVE_API_KEY=your-api-key
GITHUB_TOKEN=your-token
SLACK_BOT_TOKEN=your-slack-token
```

更新 MCP 配置引用：
```json
{
  "brave-search": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "${BRAVE_API_KEY}"
    }
  }
}
```

### 3. 加密迁移包

```bash
# 使用 GPG 加密
gpg -c opencode_backup.zip

# 解密
gpg -d opencode_backup.zip.gpg > opencode_backup.zip
```

## 性能优化

### 1. 禁用不需要的服务器

```json
{
  "server-name": {
    "disabled": true
  }
}
```

### 2. 配置服务器超时

```json
{
  "server-name": {
    "command": "node",
    "args": ["server.js"],
    "timeout": 30000
  }
}
```

### 3. 限制并发连接

在配置文件中添加：
```json
{
  "mcpSettings": {
    "maxConcurrentServers": 5,
    "serverStartupTimeout": 10000
  }
}
```

## 高级配置

### 1. 多环境配置

**开发环境:**
```json
// mcp_config.dev.json
{
  "mcpServers": {
    "filesystem": {
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/dev/workspace"]
    }
  }
}
```

**生产环境:**
```json
// mcp_config.prod.json
{
  "mcpServers": {
    "filesystem": {
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/prod/data"]
    }
  }
}
```

### 2. 条件配置

```json
{
  "mcpServers": {
    "server-name": {
      "command": "node",
      "args": ["server.js"],
      "env": {
        "NODE_ENV": "production"
      },
      "platforms": ["macos", "linux"]
    }
  }
}
```

### 3. 自定义启动脚本

创建启动脚本：
```bash
#!/bin/bash
# start-mcp-server.sh

# 设置环境变量
export API_KEY=$(security find-generic-password -w -s "mcp-api-key")

# 启动服务器
node /path/to/server/index.js
```

更新配置：
```json
{
  "server-name": {
    "command": "/path/to/start-mcp-server.sh"
  }
}
```

## 监控和日志

### 1. 启用详细日志

```json
{
  "mcpSettings": {
    "logLevel": "debug",
    "logFile": "~/.config/opencode/logs/mcp.log"
  }
}
```

### 2. 监控服务器健康

```bash
# 创建健康检查脚本
cat > check-mcp-health.sh <<'EOF'
#!/bin/bash
for server in $(jq -r '.mcpServers | keys[]' ~/.config/opencode/mcp_config.json); do
  echo "Checking $server..."
  opencode-cli test-mcp "$server" || echo "❌ $server is down"
done
EOF

chmod +x check-mcp-health.sh
```

### 3. 设置告警

```bash
# 使用 cron 定期检查
*/5 * * * * /path/to/check-mcp-health.sh | grep "❌" && notify-send "MCP Server Alert"
```

## 总结

MCP 服务器迁移的关键点：

1. **备份配置** - 始终先备份当前配置
2. **检查兼容性** - 使用工具检查平台兼容性
3. **转换路径** - 自动或手动转换文件路径
4. **保护密钥** - 不要在迁移包中包含敏感信息
5. **验证安装** - 迁移后测试所有服务器
6. **查看日志** - 遇到问题时查看详细日志

使用提供的迁移工具可以自动化大部分过程，确保安全、可靠的迁移。

## 参考资源

- [MCP 官方文档](https://modelcontextprotocol.io)
- [OpenCode MCP 指南](https://opencode.dev/mcp)
- [常见 MCP 服务器列表](https://github.com/modelcontextprotocol/servers)

---

**需要帮助?** 在 OpenCode 中说："帮我迁移 MCP 服务器配置"
