# OpenCode Skills Backup - 使用示例

## 🤖 AI 对话示例

### 示例 1: 基本备份
```
用户: 请备份我的 skills

AI: 正在备份 OpenCode skills 到 GitHub...

[执行备份流程]
1. 检查环境... ✓
2. 初始化 Git 仓库... ✓
3. 复制 skills 文件... ✓ (备份了 54 个技能，总计 8.80 MB)
4. 创建 Git 提交... ✓ (提交信息: "备份 OpenCode skills - 2024-01-27 10:30:00")
5. 推送到 GitHub... ✓

备份完成！所有 skills 已成功备份到 GitHub 仓库。
```

### 示例 2: 查看备份状态
```
用户: skills 备份状态如何？

AI: 正在检查备份状态...

备份状态报告:
- 远程仓库: https://github.com/username/opencode-skills-backup.git
- 当前分支: main
- 最新提交: a1b2c3d - 备份 OpenCode skills - 2024-01-27 10:30:00 (2小时前)
- 未提交变更: 无
- 备份目录: /Users/wsxwj/.config/opencode/skills/backup-skills/backup-repo

所有备份状态正常，上次备份于 2 小时前完成。
```

### 示例 3: 强制重新备份
```
用户: 强制重新备份所有 skills

AI: 正在执行强制备份...

警告: 这将重新备份所有文件，忽略增量检测。
是否继续？(y/N): y

[执行强制备份]
1. 清理旧备份... ✓
2. 重新复制所有文件... ✓
3. 创建新提交... ✓
4. 强制推送到 GitHub... ✓

强制备份完成！所有 skills 已重新备份。
```

### 示例 4: 备份特定技能
```
用户: 只备份 frontend-design 技能

AI: 正在备份特定技能: frontend-design

[执行单个技能备份]
1. 检查 frontend-design 技能... ✓
2. 备份技能文件... ✓ (备份了 42 个文件，总计 1.2 MB)
3. 创建提交... ✓ (提交信息: "备份 frontend-design 技能")
4. 推送到 GitHub... ✓

frontend-design 技能备份完成！
```

### 示例 5: 恢复技能
```
用户: 我不小心删除了 frontend-design 技能，能从备份恢复吗？

AI: 正在从备份恢复 frontend-design 技能...

[执行恢复流程]
1. 查找最新备份... ✓ (找到备份于 2024-01-27 10:30:00)
2. 验证备份完整性... ✓
3. 恢复技能文件... ✓
4. 验证恢复结果... ✓

恢复完成！frontend-design 技能已成功恢复到原位置。
```

## 💻 命令行使用示例

### 基本命令
```bash
# 查看帮助
python3 scripts/backup_skills.py --help

# 执行备份
python3 scripts/backup_skills.py

# 查看状态
python3 scripts/backup_skills.py --status

# 调试模式
python3 scripts/backup_skills.py --debug
```

### 高级命令
```bash
# 强制备份（忽略增量检测）
python3 scripts/backup_skills.py --force

# 只备份特定技能
python3 scripts/skill_utils.py --backup frontend-design

# 列出所有技能
python3 scripts/skill_utils.py --list

# 验证技能结构
python3 scripts/skill_utils.py --validate frontend-design

# 生成备份报告
python3 scripts/backup_skills.py --report
```

### 恢复命令
```bash
# 查看可恢复的备份
python3 scripts/skill_utils.py --list-backups

# 恢复单个技能
python3 scripts/skill_utils.py --restore frontend-design

# 恢复到特定版本
python3 scripts/skill_utils.py --restore frontend-design --version a1b2c3d

# 恢复所有技能
python3 scripts/backup_skills.py --restore-all
```

## 📊 备份报告示例

### JSON 报告
```json
{
  "backup_report": {
    "timestamp": "2024-01-27T10:30:00",
    "status": "success",
    "duration_seconds": 45.2,
    "statistics": {
      "total_skills": 54,
      "skills_backed_up": 54,
      "total_files": 1247,
      "total_size_bytes": 8801234,
      "total_size_human": "8.80 MB",
      "new_files": 12,
      "modified_files": 8,
      "unchanged_files": 1227
    },
    "git_info": {
      "commit_hash": "a1b2c3d",
      "commit_message": "备份 OpenCode skills - 2024-01-27 10:30:00",
      "branch": "main",
      "remote": "origin"
    },
    "errors": [],
    "warnings": [
      "技能 'test-skill' 缺少 SKILL.md 文件"
    ]
  }
}
```

### 文本报告
```
==========================================
OpenCode Skills 备份报告
==========================================
备份时间: 2024-01-27 10:30:00
状态: 成功
耗时: 45.2 秒

📊 统计信息:
- 总技能数: 54
- 已备份技能: 54
- 总文件数: 1,247
- 总大小: 8.80 MB
- 新增文件: 12
- 修改文件: 8
- 未变文件: 1,227

🔧 Git 信息:
- 提交哈希: a1b2c3d
- 提交信息: 备份 OpenCode skills - 2024-01-27 10:30:00
- 分支: main
- 远程仓库: origin

⚠️ 警告:
- 技能 'test-skill' 缺少 SKILL.md 文件

✅ 备份完成！
==========================================
```

## 🎯 实际使用场景

### 场景 1: 日常备份
```
用户: 每天帮我备份一次 skills

AI: 已设置每日自动备份。将在每天凌晨2点自动执行备份。
您也可以随时说"备份 skills"手动触发备份。
```

### 场景 2: 版本回滚
```
用户: 我想恢复到昨天的 skills 版本

AI: 正在查找昨天的备份...

找到以下备份版本:
1. 2024-01-26 10:30:00 (a1b2c3d) - 完整备份
2. 2024-01-26 15:45:00 (b2c3d4e) - 增量备份

请选择要恢复的版本: 1

正在恢复到 2024-01-26 10:30:00 版本...
恢复完成！所有 skills 已恢复到昨天上午的状态。
```

### 场景 3: 技能迁移
```
用户: 我要换电脑，如何迁移我的 skills？

AI: 可以通过以下步骤迁移 skills:

1. 在当前电脑上执行完整备份:
   python3 scripts/backup_skills.py --force

2. 在新电脑上克隆备份仓库:
   git clone https://github.com/username/opencode-skills-backup.git

3. 恢复 skills:
   python3 scripts/backup_skills.py --restore-all

或者，您可以直接说"备份所有 skills 用于迁移"，我会生成一个迁移包。
```

### 场景 4: 备份验证
```
用户: 如何验证备份是否完整？

AI: 正在验证备份完整性...

[执行验证]
1. 检查文件数量... ✓ (1247/1247)
2. 验证文件哈希... ✓ (所有文件哈希匹配)
3. 检查目录结构... ✓
4. 测试恢复流程... ✓

验证完成！备份完整且可恢复。
```

## 🔧 故障排除示例

### 问题 1: 备份失败
```
用户: 备份失败了，怎么办？

AI: 正在诊断备份问题...

发现的问题:
1. GitHub 认证失败
2. 网络连接超时

解决方案:
1. 更新 GitHub 访问令牌
2. 检查网络连接
3. 重试备份

是否尝试自动修复？(y/N): y

[执行修复]
1. 更新 Git 配置... ✓
2. 测试网络连接... ✓
3. 重新执行备份... ✓

修复完成！备份已成功执行。
```

### 问题 2: 存储空间不足
```
用户: 备份时提示存储空间不足

AI: 正在分析存储使用情况...

存储分析:
- 备份目录: 15.2 GB
- 可用空间: 2.1 GB
- 建议清理: 是

清理建议:
1. 删除旧备份版本 (可释放 8.5 GB)
2. 压缩备份文件 (可节省 3.2 GB)
3. 排除大文件 (可减少 2.1 GB)

是否执行自动清理？(y/N): y

[执行清理]
1. 删除30天前的备份... ✓ (释放 5.2 GB)
2. 压缩备份文件... ✓ (节省 2.1 GB)
3. 重新执行备份... ✓

清理完成！现在有 9.4 GB 可用空间，备份成功。
```

## 🎉 成功消息示例

### 备份成功
```
✅ 备份成功完成！

📊 备份摘要:
- 时间: 2024-01-27 10:30:00
- 技能数: 54
- 文件数: 1,247
- 总大小: 8.80 MB
- 提交: a1b2c3d

🔗 GitHub 链接: https://github.com/username/opencode-skills-backup

下次备份建议: 2024-01-28 (24小时后)
```

### 恢复成功
```
✅ 恢复成功完成！

📊 恢复摘要:
- 恢复时间: 2024-01-27 10:35:00
- 恢复版本: 2024-01-26 10:30:00
- 恢复技能: 54
- 恢复文件: 1,235

恢复的技能已就绪，可以正常使用。
```

### 验证成功
```
✅ 验证成功完成！

📊 验证结果:
- 备份完整性: 100%
- 文件一致性: 100%
- 可恢复性: 100%
- 总体健康度: 优秀

您的备份处于完美状态，随时可以恢复。
```

## 📝 提示和技巧

### 高效使用
1. **增量备份**: 默认启用，只备份有变化的文件
2. **定时备份**: 设置自动备份，无需手动操作
3. **选择性备份**: 只备份重要的技能
4. **版本标签**: 为重要版本创建 Git 标签

### 最佳实践
1. **定期验证**: 每月验证一次备份完整性
2. **测试恢复**: 每季度测试恢复流程
3. **监控空间**: 监控备份存储空间使用
4. **更新配置**: 定期更新备份配置

### 高级功能
1. **加密备份**: 对敏感技能进行加密
2. **多位置备份**: 备份到多个位置
3. **版本对比**: 比较不同版本的技能
4. **自动清理**: 自动清理旧备份