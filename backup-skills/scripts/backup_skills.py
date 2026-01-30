#!/usr/bin/env python3
"""
Skills Backup Script
自动备份 OpenCode skills 到 GitHub 仓库
"""

import os
import sys
import argparse
import subprocess
import datetime
from pathlib import Path
import shutil

# 配置常量
SKILLS_DIR = Path("/Users/wsxwj/.config/opencode/skills")
BACKUP_DIR = Path("/Users/wsxwj/.config/opencode/skills/backup-skills")
GIT_REPO_PATH = BACKUP_DIR / "backup-repo"
GIT_REMOTE = "origin"
GIT_BRANCH = "main"

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_color(text, color):
    """彩色打印"""
    print(f"{color}{text}{Colors.END}")

def print_header(text):
    """打印标题"""
    print_color(f"\n{'='*60}", Colors.BLUE)
    print_color(f" {text}", Colors.BOLD + Colors.BLUE)
    print_color(f"{'='*60}", Colors.BLUE)

def print_success(text):
    """打印成功信息"""
    print_color(f"✓ {text}", Colors.GREEN)

def print_warning(text):
    """打印警告信息"""
    print_color(f"⚠ {text}", Colors.YELLOW)

def print_error(text):
    """打印错误信息"""
    print_color(f"✗ {text}", Colors.RED)

def run_command(cmd, cwd=None, capture_output=False):
    """运行命令并返回结果"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, cwd=cwd, 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, cwd=cwd, check=True)
            return True
    except subprocess.CalledProcessError as e:
        if capture_output:
            print_error(f"命令执行失败: {cmd}")
            print_error(f"错误输出: {e.stderr}")
        else:
            print_error(f"命令执行失败: {cmd}")
        return None

def check_environment():
    """检查环境"""
    print_header("检查环境")
    
    # 检查 skills 目录
    if not SKILLS_DIR.exists():
        print_error(f"Skills 目录不存在: {SKILLS_DIR}")
        return False
    
    print_success(f"Skills 目录: {SKILLS_DIR}")
    
    # 检查 Git
    git_version = run_command("git --version", capture_output=True)
    if git_version:
        print_success(f"Git 版本: {git_version}")
    else:
        print_error("Git 未安装")
        return False
    
    # 检查备份目录
    if not BACKUP_DIR.exists():
        print_warning("备份目录不存在，正在创建...")
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        print_success(f"创建备份目录: {BACKUP_DIR}")
    
    return True

def init_git_repo():
    """初始化 Git 仓库"""
    print_header("初始化 Git 仓库")
    
    if GIT_REPO_PATH.exists():
        print_success(f"Git 仓库已存在: {GIT_REPO_PATH}")
        return True
    
    # 创建仓库目录
    GIT_REPO_PATH.mkdir(parents=True, exist_ok=True)
    
    # 初始化 Git 仓库
    if run_command("git init", cwd=GIT_REPO_PATH):
        print_success("Git 仓库初始化成功")
        
        # 创建 .gitignore
        gitignore_content = """# 备份忽略文件
.DS_Store
*.pyc
__pycache__/
*.log
temp/
tmp/
*.bak
*.backup
"""
        (GIT_REPO_PATH / ".gitignore").write_text(gitignore_content)
        print_success("创建 .gitignore 文件")
        
        # 创建 README
        readme_content = """# OpenCode Skills Backup

这个仓库用于备份 OpenCode skills。

## 备份内容
- OpenCode skills 目录结构
- 所有技能文件
- 配置和脚本

## 使用说明
备份由自动脚本执行，请勿手动修改。

## 恢复备份
如果需要恢复 skills，请复制本仓库内容到：
`/Users/wsxwj/.config/opencode/skills/`
"""
        (GIT_REPO_PATH / "README.md").write_text(readme_content)
        print_success("创建 README.md 文件")
        
        return True
    
    return False

def setup_git_remote():
    """设置 Git 远程仓库"""
    print_header("设置 Git 远程仓库")
    
    # 检查是否已设置远程仓库
    remote_url = run_command("git remote get-url origin", 
                           cwd=GIT_REPO_PATH, capture_output=True)
    
    if remote_url:
        print_success(f"远程仓库已设置: {remote_url}")
        return True
    
    print_warning("未设置远程仓库，请提供 GitHub 仓库 URL")
    print("格式: https://github.com/<username>/<repo-name>.git")
    
    # 在实际使用中，这里应该从配置文件中读取或提示用户输入
    # 暂时返回 False，让用户手动设置
    print_error("请手动设置远程仓库:")
    print(f"cd {GIT_REPO_PATH}")
    print("git remote add origin <your-repo-url>")
    
    return False

def copy_skills_to_backup():
    """复制 skills 到备份目录"""
    print_header("复制 skills 到备份目录")
    
    # 备份目录中的 skills 子目录
    backup_skills_dir = GIT_REPO_PATH / "skills"
    
    # 如果备份目录已存在，先删除
    if backup_skills_dir.exists():
        shutil.rmtree(backup_skills_dir)
        print_success("清理旧备份")
    
    # 复制 skills 目录
    try:
        shutil.copytree(SKILLS_DIR, backup_skills_dir, 
                       ignore=shutil.ignore_patterns('backup-skills', '__pycache__', '*.pyc'))
        print_success(f"复制 skills 到: {backup_skills_dir}")
        
        # 统计文件数量
        file_count = sum(1 for _ in backup_skills_dir.rglob('*') if _.is_file())
        dir_count = sum(1 for _ in backup_skills_dir.rglob('*') if _.is_dir())
        print_success(f"备份文件统计: {file_count} 个文件, {dir_count} 个目录")
        
        return True
    except Exception as e:
        print_error(f"复制失败: {e}")
        return False

def git_add_and_commit():
    """Git 添加和提交"""
    print_header("Git 添加和提交")
    
    # 添加所有文件
    if run_command("git add .", cwd=GIT_REPO_PATH):
        print_success("添加文件到暂存区")
    else:
        return False
    
    # 检查是否有变更
    status = run_command("git status --porcelain", cwd=GIT_REPO_PATH, capture_output=True)
    if not status:
        print_warning("没有需要提交的变更")
        return True
    
    # 创建提交信息
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"备份 OpenCode skills - {timestamp}"
    
    # 提交
    if run_command(f'git commit -m "{commit_message}"', cwd=GIT_REPO_PATH):
        print_success(f"提交成功: {commit_message}")
        
        # 显示提交详情
        commit_hash = run_command("git log -1 --pretty=format:%h", 
                                cwd=GIT_REPO_PATH, capture_output=True)
        if commit_hash:
            print_success(f"提交哈希: {commit_hash}")
        
        return True
    
    return False

def git_push():
    """推送到远程仓库"""
    print_header("推送到远程仓库")
    
    # 检查远程仓库是否设置
    remote_url = run_command("git remote get-url origin", 
                           cwd=GIT_REPO_PATH, capture_output=True)
    if not remote_url:
        print_error("未设置远程仓库")
        return False
    
    # 推送
    if run_command(f"git push {GIT_REMOTE} {GIT_BRANCH}", cwd=GIT_REPO_PATH):
        print_success(f"推送到 {GIT_REMOTE}/{GIT_BRANCH}")
        return True
    
    return False

def show_status():
    """显示备份状态"""
    print_header("备份状态")
    
    # 检查 Git 仓库状态
    if not GIT_REPO_PATH.exists():
        print_warning("Git 仓库未初始化")
        return
    
    # 显示远程仓库信息
    remote_url = run_command("git remote get-url origin", 
                           cwd=GIT_REPO_PATH, capture_output=True)
    if remote_url:
        print_success(f"远程仓库: {remote_url}")
    else:
        print_warning("未设置远程仓库")
    
    # 显示分支信息
    branch = run_command("git branch --show-current", 
                        cwd=GIT_REPO_PATH, capture_output=True)
    if branch:
        print_success(f"当前分支: {branch}")
    
    # 显示未提交的变更
    status = run_command("git status --porcelain", cwd=GIT_REPO_PATH, capture_output=True)
    if status:
        print_warning("有未提交的变更:")
        print(status)
    else:
        print_success("所有变更已提交")
    
    # 显示最新提交
    last_commit = run_command('git log -1 --pretty=format:"%h - %s (%cr)"', 
                            cwd=GIT_REPO_PATH, capture_output=True)
    if last_commit:
        print_success(f"最新提交: {last_commit}")

def backup_skills(force=False):
    """执行备份"""
    print_header("开始备份 OpenCode Skills")
    
    # 检查环境
    if not check_environment():
        return False
    
    # 初始化 Git 仓库
    if not init_git_repo():
        return False
    
    # 设置远程仓库（如果未设置）
    if not setup_git_remote():
        print_warning("继续本地备份，稍后请设置远程仓库")
    
    # 复制 skills
    if not copy_skills_to_backup():
        return False
    
    # Git 操作
    if not git_add_and_commit():
        return False
    
    # 推送（如果设置了远程仓库）
    remote_url = run_command("git remote get-url origin", 
                           cwd=GIT_REPO_PATH, capture_output=True)
    if remote_url:
        if not git_push():
            print_warning("推送失败，但本地备份已完成")
    else:
        print_warning("未设置远程仓库，仅完成本地备份")
    
    print_header("备份完成")
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="备份 OpenCode skills 到 GitHub")
    parser.add_argument("--status", action="store_true", help="显示备份状态")
    parser.add_argument("--force", action="store_true", help="强制重新备份")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    else:
        if backup_skills(args.force):
            print_success("备份成功完成！")
            sys.exit(0)
        else:
            print_error("备份失败")
            sys.exit(1)

if __name__ == "__main__":
    main()