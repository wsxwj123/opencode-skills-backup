# OpenCode Skills Backup

![Backup Status](https://img.shields.io/badge/backup-active-success)
![Last Backup](https://img.shields.io/badge/last%20backup-{{timestamp}}-blue)
![Skills Count](https://img.shields.io/badge/skills-{{skill_count}}-orange)

这个仓库用于自动备份 OpenCode skills 到 GitHub。

## 📁 目录结构

```
opencode-skills-backup/
├── skills/                    # 备份的 skills 目录
│   ├── skill-creator/        # 技能创建工具
│   ├── frontend-design/      # 前端设计技能
│   ├── ...                   # 其他技能
│   └── backup-skills/        # 备份技能自身（排除）
├── scripts/                  # 备份脚本
├── reports/                  # 备份报告
├── config/                   # 配置文件
├── .gitignore               # Git 忽略规则
└── README.md                # 本文件
```

## 🚀 快速开始

### 初始化备份
```bash
# 克隆本仓库（如果需要）
git clone {{repo_url}}

# 运行备份脚本
cd opencode-skills-backup
python3 scripts/backup_skills.py
```

### 查看备份状态
```bash
python3 scripts/backup_skills.py --status
```

### 恢复备份
```bash
# 恢复单个技能
python3 scripts/skill_utils.py --restore <skill-name>

# 恢复所有技能
python3 scripts/backup_skills.py --restore-all
```

## 🔧 配置

### 环境变量
创建 `.env` 文件：
```bash
GITHUB_TOKEN=your_personal_access_token
GITHUB_USERNAME=your_username
BACKUP_DIR=/Users/wsxwj/.config/opencode/skills
```

### 定时备份
使用 cron 定时任务：
```bash
# 每天凌晨2点执行备份
0 2 * * * cd /path/to/backup && python3 scripts/backup_skills.py >> backup.log 2>&1
```

## 📊 备份统计

| 项目 | 数值 |
|------|------|
| 总技能数 | {{total_skills}} |
| 有 SKILL.md 的技能 | {{skills_with_md}} |
| 总文件大小 | {{total_size}} |
| 最后备份时间 | {{last_backup}} |
| 备份次数 | {{backup_count}} |

## 🔒 安全注意事项

1. **敏感信息**：不要备份包含 API 密钥、密码等敏感信息的文件
2. **访问控制**：使用私有仓库保护备份
3. **加密**：考虑对敏感数据进行加密
4. **权限**：定期审查仓库访问权限

## 🛠️ 维护

### 日常维护
- 检查备份状态
- 验证备份完整性
- 清理临时文件

### 定期任务
- 每周：执行完整备份
- 每月：清理旧备份版本
- 每季度：测试恢复流程

## 🐛 故障排除

### 常见问题

**备份失败**
```bash
# 查看详细错误
python3 scripts/backup_skills.py --debug

# 检查网络连接
curl -v https://github.com
```

**认证错误**
```bash
# 更新 GitHub 令牌
export GITHUB_TOKEN=new_token
python3 scripts/backup_skills.py
```

**存储空间不足**
```bash
# 清理旧备份
python3 scripts/backup_skills.py --clean-old
```

### 获取帮助
1. 查看详细日志：`logs/backup.log`
2. 检查错误报告：`reports/error_report.json`
3. 联系维护者

## 📈 监控

### 健康检查
```bash
# 运行健康检查
python3 scripts/health_check.py

# 查看监控指标
python3 scripts/monitor.py --metrics
```

### 报警设置
配置以下报警条件：
- 备份失败
- 备份超时（> 10分钟）
- 存储空间使用率 > 90%
- 连续备份失败 > 3次

## 🔄 更新日志

### 版本 1.0.0 (初始版本)
- 基础备份功能
- GitHub 集成
- 增量备份支持
- 备份报告生成

### 版本 1.1.0 (计划中)
- 多仓库备份支持
- 加密备份选项
- 自动化调度
- 增强监控

## 🤝 贡献

欢迎贡献代码和提出建议！

### 开发指南
1. Fork 本仓库
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

### 代码规范
- 遵循 PEP 8 (Python)
- 添加适当的注释
- 编写单元测试
- 更新文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

感谢以下项目的启发：
- [GitHub Backup](https://github.com/jeffreywildman/github-backup)
- [Python Git](https://github.com/gitpython-developers/GitPython)
- [OpenCode](https://opencode.dev)

## 📞 联系

如有问题或建议，请：
1. 创建 [Issue]({{repo_url}}/issues)
2. 发送邮件至：{{maintainer_email}}
3. 加入讨论：{{discussion_url}}

---

*最后更新：{{last_updated}}*
*备份由 OpenCode Skills Backup 系统自动维护*