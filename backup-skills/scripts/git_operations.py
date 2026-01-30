#!/usr/bin/env python3
"""
Git 操作封装
"""

import subprocess
import os
from pathlib import Path

class GitOperations:
    """Git 操作类"""
    
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
    
    def run_git_command(self, cmd, capture_output=False):
        """运行 Git 命令"""
        full_cmd = f"git {cmd}"
        try:
            if capture_output:
                result = subprocess.run(
                    full_cmd, 
                    shell=True, 
                    cwd=self.repo_path,
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                return result.stdout.strip()
            else:
                subprocess.run(
                    full_cmd, 
                    shell=True, 
                    cwd=self.repo_path,
                    check=True
                )
                return True
        except subprocess.CalledProcessError as e:
            print(f"Git 命令失败: {full_cmd}")
            if capture_output:
                print(f"错误: {e.stderr}")
            return False
    
    def init_repo(self):
        """初始化 Git 仓库"""
        if (self.repo_path / ".git").exists():
            return True
        
        return self.run_git_command("init")
    
    def add_remote(self, remote_name, remote_url):
        """添加远程仓库"""
        # 检查是否已存在
        existing = self.run_git_command(f"remote get-url {remote_name}", capture_output=True)
        if existing:
            if existing == remote_url:
                return True
            else:
                # 更新远程仓库
                return self.run_git_command(f"remote set-url {remote_name} {remote_url}")
        else:
            return self.run_git_command(f"remote add {remote_name} {remote_url}")
    
    def add_all(self):
        """添加所有文件到暂存区"""
        return self.run_git_command("add .")
    
    def commit(self, message):
        """提交变更"""
        return self.run_git_command(f'commit -m "{message}"')
    
    def push(self, remote="origin", branch="main"):
        """推送到远程仓库"""
        return self.run_git_command(f"push {remote} {branch}")
    
    def pull(self, remote="origin", branch="main"):
        """从远程仓库拉取"""
        return self.run_git_command(f"pull {remote} {branch}")
    
    def status(self):
        """获取仓库状态"""
        return self.run_git_command("status --porcelain", capture_output=True)
    
    def has_changes(self):
        """检查是否有未提交的变更"""
        status = self.status()
        return bool(status)
    
    def get_last_commit(self):
        """获取最新提交信息"""
        return self.run_git_command('log -1 --pretty=format:"%h - %s (%cr)"', capture_output=True)
    
    def get_current_branch(self):
        """获取当前分支"""
        return self.run_git_command("branch --show-current", capture_output=True)
    
    def get_remote_url(self, remote="origin"):
        """获取远程仓库 URL"""
        return self.run_git_command(f"remote get-url {remote}", capture_output=True)
    
    def create_branch(self, branch_name):
        """创建新分支"""
        return self.run_git_command(f"checkout -b {branch_name}")
    
    def switch_branch(self, branch_name):
        """切换分支"""
        return self.run_git_command(f"checkout {branch_name}")
    
    def list_branches(self):
        """列出所有分支"""
        return self.run_git_command("branch -a", capture_output=True)
    
    def get_file_diff(self, file_path=None):
        """获取文件差异"""
        if file_path:
            return self.run_git_command(f"diff {file_path}", capture_output=True)
        else:
            return self.run_git_command("diff", capture_output=True)
    
    def get_commit_history(self, limit=10):
        """获取提交历史"""
        return self.run_git_command(f'log --oneline -n {limit}', capture_output=True)
    
    def reset_hard(self, commit="HEAD"):
        """硬重置到指定提交"""
        return self.run_git_command(f"reset --hard {commit}")
    
    def clean_untracked(self):
        """清理未跟踪文件"""
        return self.run_git_command("clean -fd")
    
    def stash_changes(self, message=""):
        """暂存变更"""
        if message:
            return self.run_git_command(f'stash push -m "{message}"')
        else:
            return self.run_git_command("stash push")
    
    def pop_stash(self):
        """恢复暂存的变更"""
        return self.run_git_command("stash pop")
    
    def list_stash(self):
        """列出暂存列表"""
        return self.run_git_command("stash list", capture_output=True)
    
    def tag(self, tag_name, message=""):
        """创建标签"""
        if message:
            return self.run_git_command(f'tag -a {tag_name} -m "{message}"')
        else:
            return self.run_git_command(f"tag {tag_name}")
    
    def push_tags(self, remote="origin"):
        """推送标签"""
        return self.run_git_command(f"push {remote} --tags")
    
    def clone(self, repo_url, target_dir=None):
        """克隆仓库"""
        if target_dir:
            cmd = f"clone {repo_url} {target_dir}"
        else:
            cmd = f"clone {repo_url}"
        
        return self.run_git_command(cmd)
    
    def fetch(self, remote="origin"):
        """获取远程更新"""
        return self.run_git_command(f"fetch {remote}")
    
    def merge(self, branch):
        """合并分支"""
        return self.run_git_command(f"merge {branch}")
    
    def rebase(self, branch):
        """变基"""
        return self.run_git_command(f"rebase {branch}")
    
    def cherry_pick(self, commit_hash):
        """拣选提交"""
        return self.run_git_command(f"cherry-pick {commit_hash}")
    
    def show_config(self):
        """显示 Git 配置"""
        return self.run_git_command("config --list", capture_output=True)
    
    def set_config(self, key, value, global_config=False):
        """设置 Git 配置"""
        scope = "--global" if global_config else "--local"
        return self.run_git_command(f"config {scope} {key} {value}")
    
    def get_config(self, key, global_config=False):
        """获取 Git 配置"""
        scope = "--global" if global_config else "--local"
        return self.run_git_command(f"config {scope} {key}", capture_output=True)