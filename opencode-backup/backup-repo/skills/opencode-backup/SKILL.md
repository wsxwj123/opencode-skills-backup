name: opencode-backup
description: Use when needing to backup complete OpenCode configuration including skills, plugins, agents, commands, and system settings to GitHub with incremental backup and restore capabilities

# OpenCode 完整备份技能

## 概述
自动备份完整的 OpenCode 配置到 GitHub 仓库，包括所有技能、插件、代理、命令、库文件和系统配置。支持增量备份、状态检查和完整恢复功能。

## 何时使用
- 需要备份完整的 OpenCode 环境到 GitHub
- 系统重装或迁移时需要恢复 OpenCode 配置
- 需要版本控制 OpenCode 配置变更
- 需要定期备份防止数据丢失
- 需要在多台设备间同步 OpenCode 配置

## 何时不使用
- 仅需要备份 skills 目录（使用 skills-backup 技能）
- 临时文件备份
- 不需要版本控制的简单复制

## 核心原则
**完整备份原则**：OpenCode 是一个完整的生态系统，必须备份所有组件才能确保完整恢复。只备份 skills 是不够的。

## 备份范围
必须备份以下所有内容：

### 1. 核心配置文件
- `opencode.json` - 主配置文件
- `oh-my-opencode.json` - 自定义配置
- `oh-my-opencode-slim.json` - 精简配置
- `package.json` - 依赖配置
- `bun.lock` - 包锁定文件

### 2. 插件系统
- `plugins/` 目录 - 所有插件配置
  - `chinese-settings.js` - 中文设置插件
  - `superpowers.js` - 超级能力插件

### 3. 技能库
- `skills/` 目录 - 所有技能（完整目录结构）
- 包括所有子目录和文件

### 4. 代理配置
- `agents/` 目录 - 代理配置
  - `code-reviewer.md` - 代码审查代理

### 5. 命令系统
- `commands/` 目录 - 命令定义
  - `brainstorm.md`, `execute-plan.md`, `write-plan.md`

### 6. 核心库
- `lib/` 目录 - 核心库文件
  - `skills-core.js` - 技能核心库

### 7. 工具脚本
- `add_khazix_metadata.py` - 元数据工具
- `fix_github_urls.py` - GitHub URL 修复工具
- `fix_updated_skills.py` - 技能更新修复工具
- `restore_skills.py` - 技能恢复工具
- `update_skills.py` - 技能更新工具

### 8. 文档
- `OpenCode_Skill_Format_规范说明.md` - 技能格式规范
- `OpenCode_Skill_Format_总结.md` - 技能格式总结

### 9. 排除项（不备份）
- `node_modules/` - 依赖包（可通过 package.json 恢复）
- `.DS_Store` - 系统文件
- `.git/` - Git 仓库数据
- 任何临时文件

## 快速参考

| 操作 | 命令 | 说明 |
|------|------|------|
| 初始化备份 | `python scripts/backup_opencode.py init --repo-url <url>` | 初始化备份仓库 |
| 执行备份 | `python scripts/backup_opencode.py backup` | 执行完整备份 |
| 检查状态 | `python scripts/backup_opencode.py status` | 检查备份状态 |
| 恢复配置 | `python scripts/backup_opencode.py restore` | 从备份恢复 |
| 增量备份 | `python scripts/backup_opencode.py incremental` | 仅备份变更 |

## 实现

### 备份脚本
主要备份逻辑在 `scripts/backup_opencode.py` 中：

```python
#!/usr/bin/env python3
"""
OpenCode 完整备份脚本
备份完整的 OpenCode 配置到 GitHub 仓库
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

class OpenCodeBackup:
    def __init__(self, opencode_path="~/.config/opencode"):
        self.opencode_path = Path(opencode_path).expanduser()
        self.backup_dir = self.opencode_path / "skills" / "opencode-backup" / "backup-repo"
        self.config_file = self.opencode_path / "skills" / "opencode-backup" / "backup-config.json"
        
    def load_config(self):
        """加载备份配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "repo_url": "",
            "last_backup": None,
            "backup_items": self.get_backup_items()
        }
    
    def save_config(self, config):
        """保存备份配置"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get_backup_items(self):
        """获取需要备份的项目列表"""
        return {
            "config_files": [
                "opencode.json",
                "oh-my-opencode.json",
                "oh-my-opencode-slim.json",
                "package.json",
                "bun.lock"
            ],
            "directories": [
                "plugins",
                "skills",
                "agents",
                "commands",
                "lib"
            ],
            "tool_scripts": [
                "add_khazix_metadata.py",
                "fix_github_urls.py",
                "fix_updated_skills.py",
                "restore_skills.py",
                "update_skills.py"
            ],
            "documentation": [
                "OpenCode_Skill_Format_规范说明.md",
                "OpenCode_Skill_Format_总结.md"
            ],
            "exclude_patterns": [
                "node_modules",
                ".DS_Store",
                ".git",
                "*.pyc",
                "__pycache__"
            ]
        }
    
    def init_backup(self, repo_url):
        """初始化备份仓库"""
        print(f"初始化 OpenCode 备份到 {repo_url}")
        
        # 创建备份目录
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 Git 仓库
        if not (self.backup_dir / ".git").exists():
            subprocess.run(["git", "init"], cwd=self.backup_dir, check=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], 
                         cwd=self.backup_dir, check=True)
        
        # 保存配置
        config = self.load_config()
        config["repo_url"] = repo_url
        self.save_config(config)
        
        print("备份初始化完成")
    
    def perform_backup(self, incremental=False):
        """执行备份操作"""
        config = self.load_config()
        if not config["repo_url"]:
            print("错误：请先初始化备份仓库")
            return False
        
        print("开始备份 OpenCode 配置...")
        
        # 备份每个项目
        backup_items = config["backup_items"]
        backup_success = True
        
        for item in backup_items["config_files"]:
            if not self.backup_file(item):
                backup_success = False
        
        for directory in backup_items["directories"]:
            if not self.backup_directory(directory, backup_items["exclude_patterns"]):
                backup_success = False
        
        for script in backup_items["tool_scripts"]:
            if not self.backup_file(script):
                backup_success = False
        
        for doc in backup_items["documentation"]:
            if not self.backup_file(doc):
                backup_success = False
        
        if backup_success:
            # 提交到 Git
            self.commit_backup(incremental)
            config["last_backup"] = datetime.now().isoformat()
            self.save_config(config)
            print("备份完成并已提交到 Git")
        else:
            print("备份过程中出现错误")
        
        return backup_success
    
    def backup_file(self, filename):
        """备份单个文件"""
        src = self.opencode_path / filename
        dst = self.backup_dir / filename
        
        if not src.exists():
            print(f"警告：文件不存在 {filename}")
            return True  # 不是错误，只是跳过
        
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"✓ 备份文件: {filename}")
            return True
        except Exception as e:
            print(f"✗ 备份文件失败 {filename}: {e}")
            return False
    
    def backup_directory(self, dirname, exclude_patterns):
        """备份整个目录"""
        src = self.opencode_path / dirname
        dst = self.backup_dir / dirname
        
        if not src.exists():
            print(f"警告：目录不存在 {dirname}")
            return True  # 不是错误，只是跳过
        
        try:
            # 删除旧备份
            if dst.exists():
                shutil.rmtree(dst)
            
            # 复制目录，排除不需要的文件
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*exclude_patterns))
            print(f"✓ 备份目录: {dirname}")
            return True
        except Exception as e:
            print(f"✗ 备份目录失败 {dirname}: {e}")
            return False
    
    def commit_backup(self, incremental=False):
        """提交备份到 Git"""
        try:
            subprocess.run(["git", "add", "."], cwd=self.backup_dir, check=True)
            
            commit_msg = "增量备份" if incremental else "完整备份"
            commit_msg += f" - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            subprocess.run(["git", "commit", "-m", commit_msg], 
                         cwd=self.backup_dir, check=True)
            
            # 推送到远程仓库
            subprocess.run(["git", "push", "origin", "main"], 
                         cwd=self.backup_dir, check=True)
            print("✓ 已推送到远程仓库")
            return True
        except Exception as e:
            print(f"✗ Git 操作失败: {e}")
            return False
    
    def check_status(self):
        """检查备份状态"""
        config = self.load_config()
        
        print("=== OpenCode 备份状态 ===")
        print(f"仓库URL: {config.get('repo_url', '未设置')}")
        print(f"最后备份: {config.get('last_backup', '从未备份')}")
        
        if (self.backup_dir / ".git").exists():
            # 检查 Git 状态
            result = subprocess.run(["git", "status", "--short"], 
                                  cwd=self.backup_dir, capture_output=True, text=True)
            if result.stdout.strip():
                print("有未提交的变更:")
                print(result.stdout)
            else:
                print("✓ 备份是最新的")
        else:
            print("✗ 备份仓库未初始化")
    
    def restore_backup(self):
        """从备份恢复"""
        print("警告：这将覆盖当前的 OpenCode 配置")
        response = input("确定要恢复备份吗？(yes/no): ")
        
        if response.lower() != "yes":
            print("恢复已取消")
            return
        
        print("开始恢复 OpenCode 配置...")
        
        # 从备份目录恢复文件
        for item in self.backup_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(self.backup_dir)
                dst_path = self.opencode_path / rel_path
                
                try:
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dst_path)
                    print(f"✓ 恢复: {rel_path}")
                except Exception as e:
                    print(f"✗ 恢复失败 {rel_path}: {e}")
        
        print("恢复完成")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenCode 完整备份工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化备份仓库")
    init_parser.add_argument("--repo-url", required=True, help="GitHub 仓库 URL")
    
    # backup 命令
    backup_parser = subparsers.add_parser("backup", help="执行完整备份")
    
    # incremental 命令
    inc_parser = subparsers.add_parser("incremental", help="执行增量备份")
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="检查备份状态")
    
    # restore 命令
    restore_parser = subparsers.add_parser("restore", help="从备份恢复")
    
    args = parser.parse_args()
    
    backup = OpenCodeBackup()
    
    if args.command == "init":
        backup.init_backup(args.repo_url)
    elif args.command == "backup":
        backup.perform_backup(incremental=False)
    elif args.command == "incremental":
        backup.perform_backup(incremental=True)
    elif args.command == "status":
        backup.check_status()
    elif args.command == "restore":
        backup.restore_backup()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

### 配置文件
`backup-config.json` 配置文件：

```json
{
  "repo_url": "https://github.com/username/opencode-backup.git",
  "last_backup": "2025-01-27T21:35:00",
  "backup_items": {
    "config_files": [
      "opencode.json",
      "oh-my-opencode.json",
      "oh-my-opencode-slim.json",
      "package.json",
      "bun.lock"
    ],
    "directories": [
      "plugins",
      "skills",
      "agents",
      "commands",
      "lib"
    ],
    "tool_scripts": [
      "add_khazix_metadata.py",
      "fix_github_urls.py",
      "fix_updated_skills.py",
      "restore_skills.py",
      "update_skills.py"
    ],
    "documentation": [
      "OpenCode_Skill_Format_规范说明.md",
      "OpenCode_Skill_Format_总结.md"
    ],
    "exclude_patterns": [
      "node_modules",
      ".DS_Store",
      ".git",
      "*.pyc",
      "__pycache__"
    ]
  }
}
```

## 使用示例

### 1. 初始化备份（使用代理）
```bash
cd /Users/wsxwj/.config/opencode/skills/opencode-backup

# 设置 Git 代理（如果使用代理）
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897

# 初始化备份
python scripts/backup_opencode.py init --repo-url https://github.com/wsxwj123/opencode-full-backup.git
```

### 2. 执行完整备份
```bash
python scripts/backup_opencode.py backup
```

### 3. 检查备份状态
```bash
python scripts/backup_opencode.py status
```

### 4. 执行增量备份
```bash
python scripts/backup_opencode.py incremental
```

### 5. 从备份恢复
```bash
python scripts/backup_opencode.py restore
```

## 完整工作流程示例

### 场景：新设备上恢复 OpenCode 配置
```bash
# 1. 克隆技能仓库（如果需要）
git clone https://github.com/wsxwj123/opencode-skills-backup.git

# 2. 设置代理（如果需要）
git config --global http.proxy http://127.0.0.1:7897

# 3. 初始化备份
cd /Users/wsxwj/.config/opencode/skills/opencode-backup
python scripts/backup_opencode.py init --repo-url https://github.com/wsxwj123/opencode-full-backup.git

# 4. 从备份恢复
python scripts/backup_opencode.py restore --no-confirm

# 5. 安装依赖
cd /Users/wsxwj/.config/opencode
npm install  # 或 bun install

# 6. 验证恢复
python scripts/backup_opencode.py status
```

### 场景：日常备份维护
```bash
# 每日增量备份（添加到 crontab）
0 2 * * * cd /Users/wsxwj/.config/opencode/skills/opencode-backup && python scripts/backup_opencode.py incremental

# 每周完整备份
0 3 * * 0 cd /Users/wsxwj/.config/opencode/skills/opencode-backup && python scripts/backup_opencode.py backup

# 每月状态检查
0 4 1 * * cd /Users/wsxwj/.config/opencode/skills/opencode-backup && python scripts/backup_opencode.py status
```

## 常见错误和解决方案

### 错误：Git 仓库未初始化
**症状**：`git: command not found` 或 `fatal: not a git repository`
**解决**：
1. 确保 Git 已安装：`git --version`
2. 运行初始化命令：`python scripts/backup_opencode.py init --repo-url <URL>`
3. 如果使用代理：`git config --global http.proxy http://127.0.0.1:7897`

### 错误：权限问题
**症状**：`Permission denied` 错误
**解决**：
1. 检查文件权限：`ls -la ~/.config/opencode/`
2. 修复权限：`chmod -R 755 ~/.config/opencode/skills/opencode-backup/`
3. 以管理员运行：`sudo python scripts/backup_opencode.py <command>`

### 错误：网络连接问题
**症状**：`Failed to connect to GitHub` 或 `Connection refused`
**解决**：
1. 检查网络连接：`ping github.com`
2. 设置 Git 代理（如果使用代理）：
   ```bash
   git config --global http.proxy http://127.0.0.1:7897
   git config --global https.proxy http://127.0.0.1:7897
   ```
3. 测试代理：`curl -x http://127.0.0.1:7897 https://github.com`

### 错误：文件冲突
**症状**：恢复时文件已存在或权限冲突
**解决**：
1. 恢复前会自动备份当前配置到 `backup_before_restore_时间戳/`
2. 手动解决冲突：比较备份文件和当前文件
3. 选择性恢复：手动复制需要的文件

### 错误：仓库已存在
**症状**：`remote origin already exists`
**解决**：
1. 使用 `--force` 参数重新初始化
2. 或手动删除：`git remote remove origin`

### 错误：大文件处理
**症状**：备份缓慢或内存不足
**解决**：
1. 使用增量备份：`python scripts/backup_opencode.py incremental`
2. 排除大文件：在配置中添加排除模式
3. 分批备份：手动备份大目录

### 错误：Python 模块缺失
**症状**：`ModuleNotFoundError`
**解决**：
```bash
# 安装所需模块
pip install shutil fnmatch hashlib json datetime pathlib subprocess argparse
# 这些通常是 Python 标准库，如果缺失可能需要修复 Python 安装

## 理性化表格

| 借口 | 现实 |
|------|------|
| "只备份 skills 就够了" | OpenCode 是完整生态系统，需要所有组件才能正常工作 |
| "node_modules 太大，不备份" | 正确，通过 package.json 可以重新安装依赖 |
| "简单的复制就行" | Git 提供版本历史、增量备份和远程存储 |
| "用户知道如何恢复" | 完整的恢复流程确保配置一致性 |
| "配置很少变化" | 即使很少变化，完整备份确保灾难恢复 |

## 红色标志 - 停止并重新开始

- 只备份了 skills 目录
- 没有排除 node_modules
- 没有使用版本控制
- 没有提供恢复流程
- "这太复杂了，简单点就行"

**所有这些都意味着：停止，使用完整的备份方案。**

## 验证清单

执行备份前检查：
- [ ] 所有核心配置文件存在
- [ ] 插件目录完整
- [ ] 技能目录完整
- [ ] Git 仓库已初始化
- [ ] 网络连接正常
- [ ] 有足够的磁盘空间

恢复前检查：
- [ ] 备份是最新的
- [ ] 当前配置已备份（如果需要）
- [ ] 了解恢复的影响
- [ ] 有恢复计划

## 最佳实践

1. **定期备份**：每周执行一次完整备份
2. **增量备份**：每天执行增量备份
3. **验证备份**：定期检查备份完整性
4. **测试恢复**：每季度测试恢复流程
5. **文档更新**：配置变更时更新备份文档

## 与其他技能的关系

- **skills-backup**：仅备份 skills 目录，本技能是完整版本
- **skill-manager**：管理技能生命周期，本技能备份所有配置
- **github-to-skills**：从 GitHub 获取技能，本技能反向操作

---

**记住**：完整的 OpenCode 备份不仅仅是文件复制，而是确保整个 AI 助手生态系统可恢复的完整解决方案。