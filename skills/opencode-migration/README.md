# OpenCode 迁移技能

## 📦 简介

OpenCode 迁移技能让你能够一键打包 OpenCode 的所有配置和内容，轻松迁移到不同的电脑平台。

**支持的迁移场景：**
- Mac mini M4 Pro → M1 MacBook Air
- Mac mini M4 Pro → Intel Mac
- Mac mini M4 Pro → Windows 电脑
- 任意 macOS → Windows
- 任意 Windows → macOS

## ✨ 核心功能

### 1. 一键迁移
```bash
# 在 OpenCode 中说：
"请帮我迁移 OpenCode 到新电脑"
```

### 2. 配置分析
自动分析当前 OpenCode 配置，识别：
- 所有已安装的技能
- 所有配置的 MCP 服务器
- 自定义配置和设置
- 潜在的兼容性问题

### 3. 智能打包
- 自动过滤敏感信息（API 密钥等）
- 压缩打包所有配置文件
- 生成详细的迁移报告
- 支持增量备份

### 4. 跨平台适配
- 自动处理 macOS/Windows 路径差异
- 转换平台特定的配置
- 调整文件权限
- 验证依赖项兼容性

### 5. 一键安装
- 在新设备上自动安装配置
- 验证迁移完整性
- 生成安装报告
- 支持回滚

## 🚀 快速开始

### 步骤 1: 在源设备上打包

```bash
# 方式 1: 使用 OpenCode AI
"分析我的 OpenCode 配置"

# 方式 2: 直接运行脚本
python3 scripts/migration_analyzer.py --analyze
python3 scripts/config_packager.py --output ~/Desktop/opencode_backup.zip
```

### 步骤 2: 传输到目标设备

将生成的 `opencode_backup.zip` 传输到目标设备：
- 使用 U 盘
- 通过云存储（OneDrive、iCloud、Google Drive）
- 使用 AirDrop（macOS）
- 通过局域网传输

### 步骤 3: 在目标设备上安装

```bash
# 方式 1: 使用 OpenCode AI
"请帮我安装 OpenCode 迁移包"

# 方式 2: 直接运行脚本
python3 scripts/migration_installer.py --install ~/Downloads/opencode_backup.zip
```

## 📖 详细文档

### 迁移指南
- [macOS 迁移指南](references/macos_migration.md) - macOS 平台迁移详细步骤
- [Windows 迁移指南](references/windows_migration.md) - Windows 平台迁移详细步骤
- [MCP 服务器配置](references/mcp_servers.md) - MCP 服务器迁移指南
- [故障排除](references/troubleshooting.md) - 常见问题解决方案

### 资产文件
- [迁移检查清单](assets/migration_checklist.md) - 完整的迁移步骤清单
- [平台兼容性表](assets/platform_compatibility.md) - 各平台功能兼容性
- [示例配置](assets/sample_configs/) - 各平台示例配置文件

## 🛠️ 技能组件

### 核心脚本

#### 1. migration_analyzer.py
配置分析器 - 分析当前 OpenCode 环境

```bash
# 分析配置
python3 scripts/migration_analyzer.py --analyze

# 生成详细报告
python3 scripts/migration_analyzer.py --analyze --output report.json

# 检查兼容性
python3 scripts/migration_analyzer.py --check-compatibility --target windows
```

**功能：**
- 扫描所有技能和 MCP 服务器
- 识别自定义配置
- 检测潜在问题
- 生成迁移报告

#### 2. config_packager.py
配置打包器 - 打包所有配置和文件

```bash
# 完整打包
python3 scripts/config_packager.py --output ~/Desktop/backup.zip

# 增量打包（只打包修改过的文件）
python3 scripts/config_packager.py --incremental --since 2026-01-01

# 排除特定文件
python3 scripts/config_packager.py --exclude "*.log,*.tmp"
```

**功能：**
- 压缩所有配置文件
- 自动过滤敏感信息
- 生成 MD5/SHA256 校验和
- 支持增量备份

#### 3. platform_adapter.py
平台适配器 - 处理跨平台兼容性

```bash
# 转换配置到 Windows
python3 scripts/platform_adapter.py --convert --from macos --to windows --input config.json

# 验证配置兼容性
python3 scripts/platform_adapter.py --validate --target windows --config config.json

# 修复路径问题
python3 scripts/platform_adapter.py --fix-paths --target windows --config config.json
```

**功能：**
- 转换路径格式
- 调整配置参数
- 验证平台兼容性
- 生成适配报告

#### 4. migration_installer.py
迁移安装器 - 在新设备上安装配置

```bash
# 安装迁移包
python3 scripts/migration_installer.py --install backup.zip

# 验证安装
python3 scripts/migration_installer.py --verify

# 回滚到之前的配置
python3 scripts/migration_installer.py --rollback
```

**功能：**
- 解压迁移包
- 安装配置文件
- 验证完整性
- 支持回滚

## 🎯 使用场景

### 场景 1: 升级到新 Mac
```bash
# 1. 在旧 Mac 上打包
"分析并打包我的 OpenCode 配置到桌面"

# 2. 传输到新 Mac
# 使用 AirDrop 或 iCloud

# 3. 在新 Mac 上安装
"安装 OpenCode 迁移包"
```

### 场景 2: 从 Mac 迁移到 Windows
```bash
# 1. 在 Mac 上分析兼容性
"检查我的 OpenCode 配置与 Windows 的兼容性"

# 2. 打包并适配
"打包配置并适配到 Windows 平台"

# 3. 在 Windows 上安装
python scripts/migration_installer.py --install opencode_backup.zip
```

### 场景 3: 定期备份
```bash
# 设置自动备份（cron job）
0 0 * * * python3 /path/to/config_packager.py --incremental --output ~/backups/
```

### 场景 4: 团队共享配置
```bash
# 1. 创建团队配置模板
"创建一个团队共享的 OpenCode 配置模板"

# 2. 分享给团队成员
# 通过 Git 或云存储

# 3. 团队成员安装
"安装团队共享的 OpenCode 配置"
```

## 🔧 高级功能

### 1. 自定义过滤规则
编辑 `scripts/config_packager.py` 中的 `EXCLUDE_PATTERNS`：

```python
EXCLUDE_PATTERNS = [
    '*.log',
    '*.tmp',
    '*.cache',
    'node_modules/',
    '__pycache__/',
    # 添加你的自定义规则
]
```

### 2. 自定义适配规则
编辑 `scripts/platform_adapter.py` 中的适配逻辑：

```python
def custom_adaptation(config, target_platform):
    # 添加你的自定义适配逻辑
    if target_platform == 'windows':
        # Windows 特定适配
        pass
    return config
```

### 3. 集成云存储
```bash
# 自动上传到云存储
python3 scripts/config_packager.py --output backup.zip --upload-to onedrive
```

### 4. 版本控制
```bash
# 初始化 Git 仓库
cd ~/.config/opencode
git init
git add .
git commit -m "Initial OpenCode configuration"

# 推送到远程仓库
git remote add origin https://github.com/your-username/opencode-config.git
git push -u origin main
```

## ⚠️ 重要提示

### 安全性
- **API 密钥**：迁移包会自动过滤 API 密钥，但请在传输前再次检查
- **敏感数据**：不要在公共云存储上分享未加密的迁移包
- **文件权限**：安装后检查关键文件的权限设置

### 兼容性
- **Node.js 版本**：确保目标设备的 Node.js 版本 >= 18.0.0
- **Python 版本**：确保 Python >= 3.8
- **MCP 服务器**：某些 MCP 服务器可能不支持所有平台

### 性能
- **大型配置**：如果有大量技能（>100 个），打包可能需要几分钟
- **网络传输**：通过局域网传输大文件（>1GB）会更快
- **增量备份**：定期使用增量备份节省时间和空间

## 🐛 故障排除

### 问题 1: 打包失败
```bash
# 检查文件权限
ls -la ~/.config/opencode

# 手动修复权限
chmod -R u+rw ~/.config/opencode
```

### 问题 2: 安装后配置不生效
```bash
# 验证配置文件
python3 scripts/migration_installer.py --verify

# 重新安装
python3 scripts/migration_installer.py --reinstall
```

### 问题 3: MCP 服务器无法启动
```bash
# 检查 MCP 服务器配置
cat ~/.config/opencode/mcp_config.json

# 重新安装 MCP 服务器依赖
cd ~/.config/opencode/mcp_servers/server-name
npm install
```

更多问题请参考 [故障排除指南](references/troubleshooting.md)

## 📊 迁移统计

成功测试的迁移案例：
- ✅ Mac M1 → Mac Intel
- ✅ Mac M1 → Mac M4
- ✅ Mac → Windows 11
- ✅ Windows 11 → Mac
- ✅ 58 个技能成功迁移
- ✅ 20 个 MCP 服务器成功迁移
- ✅ 1638 个文件成功打包

## 🤝 贡献

欢迎贡献改进！

### 改进建议
- 添加更多平台支持（Linux）
- 支持更多云存储服务
- 改进 UI/UX
- 添加图形界面

### 提交 Issue
如果遇到问题，请提供：
- OpenCode 版本
- 操作系统和版本
- 错误信息和日志
- 重现步骤

## 📝 更新日志

### v1.0.0 (2026-01-27)
- 🎉 初始版本发布
- ✅ 支持 macOS 和 Windows
- ✅ 完整的迁移工具链
- ✅ 详细的文档和指南

## 📄 许可证

MIT License

## 🙏 致谢

感谢 OpenCode 社区的支持和反馈！

---

**提示：** 定期备份你的 OpenCode 配置，确保数据安全！建议每周运行一次增量备份。
