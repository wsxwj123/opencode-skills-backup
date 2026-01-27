---
name: opencode-migration
description: 一键打包和迁移 OpenCode 完整配置到不同电脑的技能。支持从 Mac mini M4 Pro 迁移到 M1 MacBook Air、Intel Mac 和 Windows 电脑。自动处理配置打包、跨平台适配、依赖检查和安装部署。当用户需要迁移 OpenCode 环境或备份完整配置时使用此技能。
---

# OpenCode 迁移技能

## 概述

这个技能用于一键打包和迁移 OpenCode 的完整配置到不同的电脑平台。支持从 macOS（M4 Pro）迁移到：
- M1 MacBook Air
- Intel Mac
- Windows 电脑

## 功能特性

### 1. 配置分析
- 自动扫描 OpenCode 配置目录
- 识别所有 MCP 服务器配置
- 检测技能库和插件
- 分析环境依赖

### 2. 智能打包
- 选择性打包必要文件
- 排除敏感信息（API 密钥等）
- 生成迁移清单
- 创建跨平台兼容包

### 3. 跨平台适配
- macOS ARM (M1/M4) 适配
- macOS Intel 适配
- Windows 适配
- 路径转换和兼容性处理

### 4. 一键部署
- 自动安装脚本
- 依赖检查和安装
- 配置验证
- 迁移状态报告

## 使用方式

### 基本迁移流程

**1. 分析当前配置：**
```bash
python3 scripts/migration_analyzer.py --analyze
```

**2. 打包配置：**
```bash
python3 scripts/config_packager.py --package --output migration-package.zip
```

**3. 在新设备上安装：**
```bash
python3 scripts/migration_installer.py --install migration-package.zip
```

### 高级选项

**跨平台预览：**
```bash
python3 scripts/platform_adapter.py --preview --target windows
```

**增量迁移：**
```bash
python3 scripts/config_packager.py --incremental --since 2025-01-01
```

**验证迁移包：**
```bash
python3 scripts/migration_installer.py --verify migration-package.zip
```

## 脚本说明

### scripts/migration_analyzer.py
分析当前 OpenCode 配置，生成迁移报告。

**功能：**
- 扫描配置目录结构
- 识别 MCP 服务器和依赖
- 检测平台特定配置
- 生成迁移可行性报告

**参数：**
- `--analyze`：执行分析
- `--detailed`：详细报告
- `--output <file>`：输出报告文件

### scripts/config_packager.py
打包 OpenCode 配置为可迁移的压缩包。

**功能：**
- 选择性文件打包
- 敏感信息过滤
- 跨平台路径转换
- 生成安装脚本

**参数：**
- `--package`：创建迁移包
- `--incremental`：增量打包
- `--since <date>`：从指定日期开始
- `--output <file>`：输出文件

### scripts/platform_adapter.py
处理跨平台兼容性问题。

**功能：**
- 路径格式转换
- 平台特定配置调整
- 依赖映射
- 兼容性检查

**参数：**
- `--preview`：预览迁移效果
- `--target <platform>`：目标平台（macos-arm, macos-intel, windows）
- `--convert`：执行转换

### scripts/migration_installer.py
在新设备上安装迁移包。

**功能：**
- 解压和验证包
- 安装依赖
- 配置环境
- 验证安装

**参数：**
- `--install <package>`：安装迁移包
- `--verify <package>`：验证包完整性
- `--dry-run`：模拟安装

## 迁移内容

### 核心配置
- `~/.config/opencode/opencode.json` - 主配置文件
- `~/.config/opencode/skills/` - 技能库
- `~/.config/opencode/plugins/` - 插件配置
- `~/.config/opencode/agents/` - 代理配置

### MCP 服务器
- 本地 MCP 服务器配置
- 环境变量和路径
- 依赖项清单
- 启动脚本

### 环境设置
- Node.js/Python 依赖
- 系统路径配置
- 权限设置
- 平台特定调整

## 平台适配指南

### macOS ARM (M1/M4)
- 原生 ARM 二进制支持
- Rosetta 2 兼容性
- Homebrew 路径适配
- Python/Node 版本管理

### macOS Intel
- 传统 x86_64 架构
- Homebrew 标准路径
- 通用二进制支持
- 依赖库兼容性

### Windows
- WSL2 或原生 Windows
- 路径分隔符转换
- 环境变量调整
- 启动脚本适配

## 使用示例

### 示例 1：完整迁移到 M1 MacBook Air
```
用户：请帮我迁移 OpenCode 到新的 M1 MacBook Air
AI：正在分析当前配置...
AI：创建迁移包...
AI：迁移包已保存为 opencode-m1-migration.zip
AI：请在新电脑上运行：python3 migration_installer.py --install opencode-m1-migration.zip
```

### 示例 2：Windows 迁移预览
```
用户：我想看看迁移到 Windows 需要哪些调整
AI：正在分析跨平台兼容性...
AI：生成 Windows 迁移预览报告...
AI：需要调整：路径格式、MCP 服务器启动方式、环境变量
```

### 示例 3：增量备份
```
用户：只备份最近一周的变更
AI：正在执行增量分析...
AI：创建增量迁移包...
AI：增量包已保存，包含 15 个变更文件
```

## 故障排除

### 常见问题

**1. 权限问题**
```bash
# 检查文件权限
ls -la ~/.config/opencode/
# 修复权限
chmod -R 755 ~/.config/opencode/
```

**2. 依赖缺失**
```bash
# 检查 Node.js
node --version
# 检查 Python
python3 --version
# 检查 Git
git --version
```

**3. 路径问题**
```bash
# 检查路径配置
echo $PATH
# 检查 OpenCode 路径
which opencode
```

**4. MCP 服务器启动失败**
```bash
# 检查 MCP 配置
cat ~/.config/opencode/opencode.json | grep -A5 "mcp"
# 测试 MCP 服务器
npx @modelcontextprotocol/server-filesystem --version
```

### 调试模式
```bash
# 启用详细日志
python3 scripts/migration_analyzer.py --analyze --verbose
python3 scripts/config_packager.py --package --debug
```

## 参考文档

详细指南请查看：
- [macOS 迁移指南](references/macos_migration.md)
- [Windows 迁移指南](references/windows_migration.md)
- [MCP 服务器配置](references/mcp_servers.md)
- [故障排除指南](references/troubleshooting.md)

## 检查清单

迁移前请确认：
- [ ] 备份重要数据
- [ ] 检查磁盘空间
- [ ] 验证网络连接
- [ ] 准备目标设备信息
- [ ] 了解目标平台限制

## 注意事项

1. **敏感信息**：迁移包会自动过滤 API 密钥等敏感信息
2. **平台限制**：某些 MCP 服务器可能不支持所有平台
3. **依赖版本**：确保目标设备有兼容的依赖版本
4. **测试验证**：迁移后务必测试所有功能
5. **回滚计划**：保留原始配置以便回滚

## 更新日志

- **v1.0**：初始版本，支持基本迁移功能
- **v1.1**：增加跨平台适配和增量备份
- **v1.2**：优化 Windows 支持和故障排除