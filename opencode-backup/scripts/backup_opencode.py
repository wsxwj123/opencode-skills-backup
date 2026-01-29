#!/usr/bin/env python3
"""
OpenCode 完整备份脚本
备份完整的 OpenCode 配置到 GitHub 仓库
支持完整备份、增量备份、状态检查和恢复功能
"""

import os
import sys
import json
import shutil
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional

class OpenCodeBackup:
    def __init__(self, opencode_path: str = "~/.config/opencode"):
        """
        初始化 OpenCode 备份工具
        
        Args:
            opencode_path: OpenCode 配置路径
        """
        self.opencode_path = Path(opencode_path).expanduser()
        self.skill_dir = self.opencode_path / "skills" / "opencode-backup"
        self.backup_dir = self.skill_dir / "backup-repo"
        self.config_file = self.skill_dir / "backup-config.json"
        self.hash_file = self.skill_dir / "file-hashes.json"
        
        # 确保目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def load_config(self) -> Dict:
        """加载备份配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"警告：配置文件损坏，使用默认配置")
        
        # 默认配置
        return {
            "repo_url": "",
            "last_backup": None,
            "backup_count": 0,
            "backup_items": self.get_default_backup_items(),
            "git_config": {
                "user_name": "OpenCode Backup",
                "user_email": "backup@opencode.local"
            }
        }
    
    def save_config(self, config: Dict) -> None:
        """保存备份配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def get_default_backup_items(self) -> Dict:
        """获取默认的备份项目配置"""
        return {
            "config_files": [
                "opencode.json",
                "oh-my-opencode.json",
                "oh-my-opencode-slim.json",
                "package.json",
                "bun.lock",
                ".gitignore"
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
                "backup-repo",
                "*.pyc",
                "__pycache__",
                "*.log",
                "*.tmp",
                "*.temp"
            ]
        }
    
    def calculate_file_hash(self, filepath: Path) -> str:
        """计算文件哈希值"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def load_file_hashes(self) -> Dict:
        """加载文件哈希记录"""
        if self.hash_file.exists():
            try:
                with open(self.hash_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def save_file_hashes(self, hashes: Dict) -> None:
        """保存文件哈希记录"""
        with open(self.hash_file, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2, ensure_ascii=False)
    
    def init_backup(self, repo_url: str, force: bool = False) -> bool:
        """
        初始化备份仓库
        
        Args:
            repo_url: GitHub 仓库 URL
            force: 是否强制重新初始化
            
        Returns:
            是否成功
        """
        print(f"🚀 初始化 OpenCode 备份到 {repo_url}")
        
        config = self.load_config()
        
        # 检查是否已初始化
        if config["repo_url"] and not force:
            print(f"⚠️  备份已初始化到: {config['repo_url']}")
            response = input("是否重新初始化？(yes/no): ")
            if response.lower() != "yes":
                print("取消初始化")
                return False
        
        # 配置 Git
        try:
            if not (self.backup_dir / ".git").exists():
                subprocess.run(["git", "init"], cwd=self.backup_dir, check=True, 
                             capture_output=True)
                print("✓ Git 仓库初始化完成")
            
            # 设置 Git 用户信息
            git_config = config["git_config"]
            subprocess.run(["git", "config", "user.name", git_config["user_name"]], 
                         cwd=self.backup_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", git_config["user_email"]], 
                         cwd=self.backup_dir, check=True, capture_output=True)
            
            # 添加远程仓库
            subprocess.run(["git", "remote", "remove", "origin"], 
                         cwd=self.backup_dir, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], 
                         cwd=self.backup_dir, check=True, capture_output=True)
            
            # 更新配置
            config["repo_url"] = repo_url
            self.save_config(config)
            
            print("✅ 备份初始化完成")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git 操作失败: {e}")
            if e.stderr:
                print(f"错误信息: {e.stderr.decode()}")
            return False
    
    def get_changed_files(self) -> List[Path]:
        """
        获取变更的文件列表（用于增量备份）
        
        Returns:
            变更的文件路径列表
        """
        changed_files = []
        old_hashes = self.load_file_hashes()
        new_hashes = {}
        
        config = self.load_config()
        backup_items = config["backup_items"]
        
        # 检查配置文件
        for filename in backup_items["config_files"]:
            src = self.opencode_path / filename
            if src.exists():
                file_hash = self.calculate_file_hash(src)
                new_hashes[str(src)] = file_hash
                
                old_hash = old_hashes.get(str(src), "")
                if old_hash != file_hash:
                    changed_files.append(src)
        
        # 检查工具脚本
        for filename in backup_items["tool_scripts"]:
            src = self.opencode_path / filename
            if src.exists():
                file_hash = self.calculate_file_hash(src)
                new_hashes[str(src)] = file_hash
                
                old_hash = old_hashes.get(str(src), "")
                if old_hash != file_hash:
                    changed_files.append(src)
        
        # 检查文档
        for filename in backup_items["documentation"]:
            src = self.opencode_path / filename
            if src.exists():
                file_hash = self.calculate_file_hash(src)
                new_hashes[str(src)] = file_hash
                
                old_hash = old_hashes.get(str(src), "")
                if old_hash != file_hash:
                    changed_files.append(src)
        
        # 检查目录（简化检查，只检查目录是否存在变化）
        for dirname in backup_items["directories"]:
            src = self.opencode_path / dirname
            if src.exists():
                # 记录目录哈希（使用最后修改时间）
                dir_mtime = src.stat().st_mtime
                new_hashes[str(src)] = str(dir_mtime)
                
                old_hash = old_hashes.get(str(src), "")
                if old_hash != str(dir_mtime):
                    changed_files.append(src)
        
        # 保存新的哈希值
        self.save_file_hashes(new_hashes)
        
        return changed_files
    
    def perform_backup(self, incremental: bool = False, dry_run: bool = False) -> bool:
        """
        执行备份操作
        
        Args:
            incremental: 是否增量备份
            dry_run: 是否试运行（不实际执行）
            
        Returns:
            是否成功
        """
        config = self.load_config()
        
        if not config["repo_url"]:
            print("❌ 错误：请先初始化备份仓库")
            print("使用: python backup_opencode.py init --repo-url <URL>")
            return False
        
        print(f"📦 开始{'增量' if incremental else '完整'}备份 OpenCode 配置...")
        
        if incremental:
            changed_files = self.get_changed_files()
            if not changed_files:
                print("✅ 没有检测到变更，跳过备份")
                return True
            
            print(f"检测到 {len(changed_files)} 个文件变更")
            if dry_run:
                print("试运行模式，不会实际备份")
                for file in changed_files:
                    print(f"  - {file.relative_to(self.opencode_path)}")
                return True
        
        backup_items = config["backup_items"]
        success_count = 0
        total_count = 0
        
        # 备份配置文件
        for filename in backup_items["config_files"]:
            total_count += 1
            if self.backup_file(filename, dry_run):
                success_count += 1
        
        # 备份目录
        for dirname in backup_items["directories"]:
            total_count += 1
            if self.backup_directory(dirname, backup_items["exclude_patterns"], dry_run):
                success_count += 1
        
        # 备份工具脚本
        for filename in backup_items["tool_scripts"]:
            total_count += 1
            if self.backup_file(filename, dry_run):
                success_count += 1
        
        # 备份文档
        for filename in backup_items["documentation"]:
            total_count += 1
            if self.backup_file(filename, dry_run):
                success_count += 1
        
        if dry_run:
            print(f"试运行完成：{success_count}/{total_count} 个项目检查通过")
            return success_count == total_count
        
        if success_count == total_count:
            # 提交到 Git
            if self.commit_backup(incremental):
                config["last_backup"] = datetime.now().isoformat()
                config["backup_count"] = config.get("backup_count", 0) + 1
                self.save_config(config)
                print(f"✅ 备份完成！已提交到 Git（第 {config['backup_count']} 次备份）")
                return True
            else:
                print("❌ 备份完成但 Git 提交失败")
                return False
        else:
            print(f"❌ 备份失败：{success_count}/{total_count} 个项目成功")
            return False
    
    def backup_file(self, filename: str, dry_run: bool = False) -> bool:
        """备份单个文件"""
        src = self.opencode_path / filename
        dst = self.backup_dir / filename
        
        if not src.exists():
            if dry_run:
                print(f"⚠️  文件不存在（跳过）: {filename}")
            return True  # 不是错误，只是跳过
        
        try:
            if dry_run:
                print(f"✓ 检查文件: {filename}")
                return True
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"✓ 备份文件: {filename}")
            return True
        except Exception as e:
            print(f"❌ 备份文件失败 {filename}: {e}")
            return False
    
    def backup_directory(self, dirname: str, exclude_patterns: List[str], dry_run: bool = False) -> bool:
        """备份整个目录"""
        src = self.opencode_path / dirname
        dst = self.backup_dir / dirname
        
        if not src.exists():
            if dry_run:
                print(f"⚠️  目录不存在（跳过）: {dirname}")
            return True  # 不是错误，只是跳过
        
        try:
            if dry_run:
                print(f"✓ 检查目录: {dirname}")
                return True
            
            # 删除旧备份
            if dst.exists():
                shutil.rmtree(dst)
            
            # 复制目录，排除不需要的文件
            def ignore_func(dirpath, names):
                ignored = []
                for pattern in exclude_patterns:
                    for name in names:
                        if pattern in name or fnmatch.fnmatch(name, pattern):
                            ignored.append(name)
                return set(ignored)
            
            # 使用 shutil.ignore_patterns
            import fnmatch
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*exclude_patterns))
            print(f"✓ 备份目录: {dirname}")
            return True
        except Exception as e:
            print(f"❌ 备份目录失败 {dirname}: {e}")
            return False
    
    def commit_backup(self, incremental: bool = False) -> bool:
        """提交备份到 Git"""
        try:
            # 添加所有文件
            subprocess.run(["git", "add", "."], cwd=self.backup_dir, 
                         check=True, capture_output=True)
            
            # 创建提交信息
            commit_type = "incremental" if incremental else "full"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            commit_msg = f"OpenCode {commit_type} backup - {timestamp}"
            
            subprocess.run(["git", "commit", "-m", commit_msg], 
                         cwd=self.backup_dir, check=True, capture_output=True)
            
            # 推送到远程仓库
            print("正在推送到远程仓库...")
            result = subprocess.run(["git", "push", "origin", "main"], 
                                  cwd=self.backup_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 已推送到远程仓库")
                return True
            else:
                # 尝试创建并推送 main 分支
                print("尝试创建 main 分支...")
                subprocess.run(["git", "branch", "-M", "main"], 
                             cwd=self.backup_dir, check=True, capture_output=True)
                subprocess.run(["git", "push", "-u", "origin", "main"], 
                             cwd=self.backup_dir, check=True, capture_output=True)
                print("✅ 已创建并推送到 main 分支")
                return True
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Git 操作失败: {e}")
            if e.stderr:
                print(f"错误信息: {e.stderr.decode()}")
            return False
    
    def check_status(self) -> None:
        """检查备份状态"""
        config = self.load_config()
        
        print("=" * 50)
        print("📊 OpenCode 备份状态")
        print("=" * 50)
        
        print(f"📁 备份目录: {self.backup_dir}")
        print(f"🔗 仓库URL: {config.get('repo_url', '未设置')}")
        print(f"🕒 最后备份: {config.get('last_backup', '从未备份')}")
        print(f"🔢 备份次数: {config.get('backup_count', 0)}")
        
        if (self.backup_dir / ".git").exists():
            try:
                # 检查 Git 状态
                result = subprocess.run(["git", "status", "--short"], 
                                      cwd=self.backup_dir, capture_output=True, text=True)
                
                if result.stdout.strip():
                    print("\n📝 有未提交的变更:")
                    print(result.stdout)
                else:
                    print("\n✅ 备份是最新的")
                
                # 检查远程状态
                result = subprocess.run(["git", "remote", "-v"], 
                                      cwd=self.backup_dir, capture_output=True, text=True)
                print(f"\n🌐 远程仓库:\n{result.stdout}")
                
                # 检查提交历史
                result = subprocess.run(["git", "log", "--oneline", "-5"], 
                                      cwd=self.backup_dir, capture_output=True, text=True)
                print(f"📜 最近提交:\n{result.stdout}")
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Git 状态检查失败: {e}")
        else:
            print("\n❌ 备份仓库未初始化")
        
        # 检查备份完整性
        print("\n🔍 备份完整性检查:")
        backup_items = config["backup_items"]
        missing_items = []
        
        for filename in backup_items["config_files"]:
            src = self.opencode_path / filename
            dst = self.backup_dir / filename
            if src.exists() and not dst.exists():
                missing_items.append(f"配置文件: {filename}")
        
        for dirname in backup_items["directories"]:
            src = self.opencode_path / dirname
            dst = self.backup_dir / dirname
            if src.exists() and not dst.exists():
                missing_items.append(f"目录: {dirname}")
        
        if missing_items:
            print("❌ 缺失的备份项目:")
            for item in missing_items:
                print(f"  - {item}")
        else:
            print("✅ 备份完整性检查通过")
        
        print("=" * 50)
    
    def restore_backup(self, confirm: bool = True) -> bool:
        """
        从备份恢复
        
        Args:
            confirm: 是否要求确认
            
        Returns:
            是否成功
        """
        if confirm:
            print("⚠️  警告：这将覆盖当前的 OpenCode 配置")
            print("当前配置将被备份文件替换")
            response = input("确定要恢复备份吗？(yes/no): ")
            
            if response.lower() != "yes":
                print("恢复已取消")
                return False
        
        print("🔄 开始恢复 OpenCode 配置...")
        
        # 首先备份当前配置（安全措施）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_of_current = self.opencode_path / f"backup_before_restore_{timestamp}"
        
        try:
            print(f"📋 备份当前配置到: {backup_of_current}")
            shutil.copytree(self.opencode_path, backup_of_current, 
                          ignore=shutil.ignore_patterns("node_modules", ".git", "*.pyc"))
        except Exception as e:
            print(f"⚠️  当前配置备份失败: {e}")
            response = input("继续恢复吗？(yes/no): ")
            if response.lower() != "yes":
                print("恢复已取消")
                return False
        
        restored_count = 0
        error_count = 0
        
        # 从备份目录恢复文件
        for item in self.backup_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(self.backup_dir)
                dst_path = self.opencode_path / rel_path
                
                # 跳过备份目录本身
                if "opencode-backup" in str(rel_path):
                    continue
                
                try:
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dst_path)
                    restored_count += 1
                    if restored_count % 50 == 0:
                        print(f"✓ 已恢复 {restored_count} 个文件...")
                except Exception as e:
                    error_count += 1
                    print(f"❌ 恢复失败 {rel_path}: {e}")
        
        print(f"\n✅ 恢复完成！")
        print(f"  恢复文件: {restored_count}")
        print(f"  失败文件: {error_count}")
        
        if error_count == 0:
            print("🎉 所有文件恢复成功！")
        else:
            print(f"⚠️  有 {error_count} 个文件恢复失败，请检查日志")
        
        print(f"\n📁 恢复前的配置备份在: {backup_of_current}")
        print("💡 如果需要回滚，可以手动复制回去")
        
        return error_count == 0

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OpenCode 完整备份工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s init --repo-url https://github.com/username/opencode-backup.git
  %(prog)s backup
  %(prog)s incremental
  %(prog)s status
  %(prog)s restore --no-confirm
  %(prog)s backup --dry-run
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化备份仓库")
    init_parser.add_argument("--repo-url", required=True, help="GitHub 仓库 URL")
    init_parser.add_argument("--force", action="store_true", help="强制重新初始化")
    
    # backup 命令
    backup_parser = subparsers.add_parser("backup", help="执行完整备份")
    backup_parser.add_argument("--dry-run", action="store_true", help="试运行，不实际备份")
    
    # incremental 命令
    inc_parser = subparsers.add_parser("incremental", help="执行增量备份")
    inc_parser.add_argument("--dry-run", action="store_true", help="试运行，不实际备份")
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="检查备份状态")
    
    # restore 命令
    restore_parser = subparsers.add_parser("restore", help="从备份恢复")
    restore_parser.add_argument("--no-confirm", action="store_true", help="跳过确认提示")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    backup = OpenCodeBackup()
    
    try:
        if args.command == "init":
            success = backup.init_backup(args.repo_url, args.force)
            sys.exit(0 if success else 1)
            
        elif args.command == "backup":
            success = backup.perform_backup(incremental=False, dry_run=args.dry_run)
            sys.exit(0 if success else 1)
            
        elif args.command == "incremental":
            success = backup.perform_backup(incremental=True, dry_run=args.dry_run)
            sys.exit(0 if success else 1)
            
        elif args.command == "status":
            backup.check_status()
            sys.exit(0)
            
        elif args.command == "restore":
            success = backup.restore_backup(confirm=not args.no_confirm)
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()