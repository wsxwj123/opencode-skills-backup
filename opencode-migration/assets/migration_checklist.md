# OpenCode 迁移检查清单

使用此检查清单确保完整、安全的 OpenCode 迁移。在每个步骤旁打勾 (✓) 以跟踪进度。

## 迁移前准备

### 源设备检查

- [ ] 确认 OpenCode 版本
  ```bash
  opencode --version
  ```

- [ ] 检查磁盘空间（至少需要 2GB 空闲空间）
  ```bash
  df -h ~
  ```

- [ ] 更新所有技能和 MCP 服务器到最新版本
  ```bash
  opencode update --all
  ```

- [ ] 记录当前配置
  ```bash
  python3 scripts/migration_analyzer.py --analyze --output config_snapshot.json
  ```

- [ ] 备份重要数据
  ```bash
  cp -r ~/.config/opencode ~/opencode_backup_$(date +%Y%m%d)
  ```

### 环境准备

- [ ] 安装 Python 3.8+
  ```bash
  python3 --version
  ```

- [ ] 安装 Node.js 18+
  ```bash
  node --version
  ```

- [ ] 准备传输介质（USB、云存储等）

- [ ] 记录所有 API 密钥和环境变量
  - [ ] GitHub Token: `__________`
  - [ ] Brave API Key: `__________`
  - [ ] Slack Bot Token: `__________`
  - [ ] 其他: `__________`

## 配置分析阶段

### 技能分析

- [ ] 列出所有已安装的技能
  ```bash
  ls ~/.config/opencode/skills/
  ```

- [ ] 记录技能数量: `__________` 个

- [ ] 识别自定义技能
  - [ ] `__________`
  - [ ] `__________`
  - [ ] `__________`

- [ ] 检查技能依赖
  ```bash
  python3 scripts/migration_analyzer.py --list-skill-dependencies
  ```

### MCP 服务器分析

- [ ] 列出所有 MCP 服务器
  ```bash
  cat ~/.config/opencode/mcp_config.json | jq '.mcpServers | keys'
  ```

- [ ] 记录 MCP 服务器数量: `__________` 个

- [ ] 识别需要特殊配置的服务器
  - [ ] `__________`
  - [ ] `__________`

- [ ] 检查平台兼容性
  ```bash
  python3 scripts/platform_adapter.py --check-mcp-compatibility --target [目标平台]
  ```

### 配置文件检查

- [ ] 验证主配置文件
  ```bash
  python3 -m json.tool ~/.config/opencode/config.json
  ```

- [ ] 检查自定义配置
  - [ ] `__________`
  - [ ] `__________`

- [ ] 记录特殊路径配置
  - [ ] `__________`
  - [ ] `__________`

## 打包阶段

### 创建迁移包

- [ ] 运行配置分析
  ```bash
  python3 scripts/migration_analyzer.py --analyze --output analysis_report.json
  ```

- [ ] 审查分析报告
  - [ ] 检查警告和错误
  - [ ] 确认所有关键配置已识别

- [ ] 执行打包
  ```bash
  python3 scripts/config_packager.py --output ~/Desktop/opencode_backup_$(date +%Y%m%d).zip
  ```

- [ ] 记录打包文件信息
  - 文件名: `__________`
  - 大小: `__________` MB
  - SHA256: `__________`

### 验证打包完整性

- [ ] 生成校验和
  ```bash
  sha256sum opencode_backup.zip > opencode_backup.zip.sha256
  ```

- [ ] 测试解压
  ```bash
  unzip -t opencode_backup.zip
  ```

- [ ] 检查打包内容
  ```bash
  unzip -l opencode_backup.zip | head -50
  ```

- [ ] 确认敏感信息已过滤
  ```bash
  unzip -c opencode_backup.zip | grep -i "api_key\|password\|token" || echo "No sensitive data found"
  ```

### 备份验证

- [ ] 创建备份副本
  ```bash
  cp opencode_backup.zip opencode_backup_copy.zip
  ```

- [ ] 验证两个文件完全相同
  ```bash
  diff opencode_backup.zip opencode_backup_copy.zip
  ```

- [ ] 上传到安全的云存储（可选）

## 传输阶段

### 选择传输方式

- [ ] 选择传输方法：
  - [ ] USB 驱动器
  - [ ] 云存储 (OneDrive/iCloud/Google Drive)
  - [ ] 网络传输 (rsync/scp)
  - [ ] AirDrop (macOS)
  - [ ] 其他: `__________`

### 传输执行

#### 如果使用 USB

- [ ] 复制到 USB
  ```bash
  cp opencode_backup.zip /Volumes/USB/
  cp opencode_backup.zip.sha256 /Volumes/USB/
  ```

- [ ] 安全弹出 USB

- [ ] 在目标设备插入 USB

- [ ] 复制到目标设备
  ```bash
  cp /Volumes/USB/opencode_backup.zip ~/Downloads/
  cp /Volumes/USB/opencode_backup.zip.sha256 ~/Downloads/
  ```

#### 如果使用云存储

- [ ] 上传到云存储
  - OneDrive: `__________`
  - iCloud: `__________`
  - Google Drive: `__________`

- [ ] 等待同步完成

- [ ] 在目标设备下载文件

#### 如果使用网络传输

- [ ] 使用 rsync 传输
  ```bash
  rsync -avz --progress opencode_backup.zip user@target:/path/
  ```

### 传输验证

- [ ] 在目标设备验证文件完整性
  ```bash
  sha256sum -c opencode_backup.zip.sha256
  ```

- [ ] 确认文件大小匹配
  ```bash
  ls -lh opencode_backup.zip
  ```

## 目标设备准备

### 系统检查

- [ ] 确认目标操作系统
  - [ ] macOS (版本: `__________`)
  - [ ] Windows (版本: `__________`)
  - [ ] Linux (发行版: `__________`)

- [ ] 检查磁盘空间
  ```bash
  df -h ~
  ```
  至少需要: `__________` GB

- [ ] 安装必要工具
  - [ ] Python 3.8+
  - [ ] Node.js 18+
  - [ ] npm
  - [ ] Git (可选)

### OpenCode 安装

- [ ] 安装 OpenCode（如果尚未安装）
  - [ ] 从官方网站下载
  - [ ] 完成初始设置
  - [ ] 验证安装

- [ ] 记录 OpenCode 安装路径
  - macOS: `__________`
  - Windows: `__________`

### 环境配置

- [ ] 创建配置目录
  ```bash
  mkdir -p ~/.config/opencode
  ```

- [ ] 设置权限
  ```bash
  chmod 755 ~/.config/opencode
  ```

## 安装阶段

### 平台适配

- [ ] 检查平台兼容性
  ```bash
  python3 scripts/platform_adapter.py --validate --target [当前平台] --config config.json
  ```

- [ ] 转换配置（如需要）
  ```bash
  python3 scripts/platform_adapter.py --convert --from [源平台] --to [目标平台]
  ```

- [ ] 审查适配报告
  - [ ] 路径更改: `__________` 处
  - [ ] 配置调整: `__________` 处
  - [ ] 警告: `__________` 个

### 执行安装

- [ ] 运行安装脚本
  ```bash
  python3 scripts/migration_installer.py --install ~/Downloads/opencode_backup.zip
  ```

- [ ] 处理安装提示
  - [ ] 确认覆盖现有配置（如适用）
  - [ ] 选择合并策略

- [ ] 监控安装进度
  - [ ] 技能安装: `__________/%`
  - [ ] MCP 服务器安装: `__________/%`
  - [ ] 配置导入: `__________/%`

### 依赖安装

- [ ] 安装 Python 依赖
  ```bash
  pip3 install -r ~/.config/opencode/requirements.txt
  ```

- [ ] 安装 Node.js 依赖
  ```bash
  cd ~/.config/opencode/mcp_servers && npm install
  ```

- [ ] 安装系统依赖（根据需要）
  - [ ] `__________`
  - [ ] `__________`

## 配置阶段

### 环境变量配置

- [ ] 创建 .env 文件
  ```bash
  cat > ~/.config/opencode/.env <<EOF
  API_KEY=your-api-key
  GITHUB_TOKEN=your-token
  EOF
  ```

- [ ] 配置环境变量
  - [ ] GitHub Token
  - [ ] Brave API Key
  - [ ] Slack Bot Token
  - [ ] 其他: `__________`

### 路径调整

- [ ] 更新绝对路径
  ```bash
  python3 scripts/platform_adapter.py --fix-paths --old-home [旧路径] --new-home [新路径]
  ```

- [ ] 验证所有路径
  ```bash
  grep -r "/Users/\|C:\\" ~/.config/opencode/ | head -20
  ```

- [ ] 手动修复特殊路径（如需要）

### MCP 服务器配置

- [ ] 验证 MCP 配置
  ```bash
  python3 -m json.tool ~/.config/opencode/mcp_config.json
  ```

- [ ] 更新平台特定配置
  - [ ] 文件路径
  - [ ] 可执行文件位置
  - [ ] 环境变量

- [ ] 测试每个 MCP 服务器
  - [ ] filesystem: `__________`
  - [ ] memory: `__________`
  - [ ] brave-search: `__________`
  - [ ] 其他: `__________`

## 验证阶段

### 配置验证

- [ ] 运行完整性检查
  ```bash
  python3 scripts/migration_installer.py --verify
  ```

- [ ] 检查配置文件
  - [ ] config.json: ✓ / ✗
  - [ ] mcp_config.json: ✓ / ✗
  - [ ] .env: ✓ / ✗

- [ ] 验证文件权限
  ```bash
  ls -la ~/.config/opencode/
  ```

### 技能验证

- [ ] 列出所有技能
  ```bash
  opencode skills list
  ```

- [ ] 测试关键技能
  - [ ] `__________`: ✓ / ✗
  - [ ] `__________`: ✓ / ✗
  - [ ] `__________`: ✓ / ✗

- [ ] 检查技能依赖
  ```bash
  python3 scripts/migration_installer.py --verify-skills
  ```

### MCP 服务器验证

- [ ] 启动 OpenCode

- [ ] 查看 MCP 服务器状态
  ```
  "显示所有 MCP 服务器的状态"
  ```

- [ ] 测试每个服务器功能
  - [ ] filesystem - 列出文件: ✓ / ✗
  - [ ] memory - 创建实体: ✓ / ✗
  - [ ] brave-search - 搜索: ✓ / ✗
  - [ ] 其他: `__________`

- [ ] 检查服务器日志
  ```bash
  tail -f ~/.config/opencode/logs/mcp-*.log
  ```

### 功能测试

- [ ] 测试基本功能
  - [ ] 创建新对话: ✓ / ✗
  - [ ] 使用技能: ✓ / ✗
  - [ ] 读取文件: ✓ / ✗
  - [ ] 执行命令: ✓ / ✗

- [ ] 测试高级功能
  - [ ] 多模态支持: ✓ / ✗
  - [ ] 代码执行: ✓ / ✗
  - [ ] 网络搜索: ✓ / ✗
  - [ ] 其他: `__________`

- [ ] 性能测试
  - [ ] 启动时间: `__________` 秒
  - [ ] 响应速度: 快 / 中 / 慢
  - [ ] 内存使用: `__________` MB

## 清理阶段

### 源设备清理（可选）

- [ ] 确认目标设备一切正常

- [ ] 在源设备创建最终备份
  ```bash
  cp -r ~/.config/opencode ~/opencode_final_backup
  ```

- [ ] 可选：在源设备删除配置
  ```bash
  rm -rf ~/.config/opencode
  ```

### 目标设备清理

- [ ] 删除迁移包
  ```bash
  rm ~/Downloads/opencode_backup.zip
  ```

- [ ] 清理临时文件
  ```bash
  rm -rf /tmp/opencode_*
  ```

- [ ] 整理文档
  - [ ] 保存迁移报告
  - [ ] 记录自定义配置
  - [ ] 更新文档

## 后续步骤

### 优化配置

- [ ] 审查并优化性能设置

- [ ] 禁用不需要的 MCP 服务器
  ```bash
  # 在 mcp_config.json 中设置 disabled: true
  ```

- [ ] 清理不需要的技能

- [ ] 配置自动备份
  ```bash
  # 设置 cron job 或计划任务
  ```

### 定期维护

- [ ] 设置定期备份计划
  - 频率: 每周 / 每月
  - 备份位置: `__________`

- [ ] 记录定制化内容
  ```bash
  cat > ~/.config/opencode/CUSTOMIZATIONS.md <<EOF
  # 自定义内容
  - ...
  EOF
  ```

- [ ] 订阅 OpenCode 更新通知

### 文档记录

- [ ] 记录迁移日期: `__________`

- [ ] 记录源设备信息
  - 型号: `__________`
  - 操作系统: `__________`

- [ ] 记录目标设备信息
  - 型号: `__________`
  - 操作系统: `__________`

- [ ] 记录遇到的问题和解决方案
  - `__________`
  - `__________`

- [ ] 评估迁移时间
  - 准备: `__________` 小时
  - 打包: `__________` 小时
  - 传输: `__________` 小时
  - 安装: `__________` 小时
  - 验证: `__________` 小时
  - 总计: `__________` 小时

## 成功标准

迁移被认为成功，当：

- [x] ✅ 所有配置文件正确加载
- [x] ✅ 所有技能可用且功能正常
- [x] ✅ 所有 MCP 服务器启动并响应
- [x] ✅ 环境变量正确配置
- [x] ✅ 基本功能测试通过
- [x] ✅ 高级功能测试通过
- [x] ✅ 性能符合预期
- [x] ✅ 无严重错误或警告

## 如果遇到问题

参考以下资源：

1. **故障排除指南**: `references/troubleshooting.md`
2. **MCP 服务器指南**: `references/mcp_servers.md`
3. **平台迁移指南**:
   - `references/macos_migration.md`
   - `references/windows_migration.md`

4. **在 OpenCode 中寻求帮助**:
   ```
   "帮我解决 OpenCode 迁移问题"
   ```

5. **社区支持**:
   - OpenCode 官方论坛
   - GitHub Issues
   - Discord/Slack 社区

---

## 迁移完成

恭喜！你已成功完成 OpenCode 迁移。

**最终确认：**

- [ ] 我已验证所有关键功能正常工作
- [ ] 我已保存了迁移文档和备份
- [ ] 我了解如何在需要时回滚
- [ ] 我已设置定期备份计划

**迁移完成日期**: `__________`

**签名**: `__________`

---

**提示:** 保存此清单以供将来参考。定期备份可以让下次迁移更加轻松！
