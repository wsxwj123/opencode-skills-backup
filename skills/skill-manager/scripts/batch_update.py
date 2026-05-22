#!/usr/bin/env python3
"""批量更新所有过期的 skills"""

import os
import sys
import json
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """执行命令并返回输出"""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr

def update_skill(skill_info):
    """更新单个 skill"""
    name = skill_info['name']
    skill_dir = skill_info['dir']
    github_url = skill_info['github_url']
    remote_hash = skill_info['remote_hash']
    
    print(f"\n{'='*60}")
    print(f"📦 Updating: {name}")
    print(f"📂 Directory: {skill_dir}")
    print(f"🔗 GitHub: {github_url}")
    print(f"{'='*60}")
    
    # 检查目录是否存在
    if not os.path.exists(skill_dir):
        print(f"❌ Directory not found: {skill_dir}")
        return False
    
    # 检查是否是 git 仓库
    git_dir = os.path.join(skill_dir, '.git')
    if not os.path.exists(git_dir):
        print(f"⚠️  Not a git repository, skipping...")
        return False
    
    # 保存当前状态
    print("💾 Saving current state...")
    code, _, _ = run_command("git stash", cwd=skill_dir)
    
    # 拉取最新更改
    print("⬇️  Pulling latest changes...")
    code, stdout, stderr = run_command("git pull --rebase", cwd=skill_dir)
    
    if code != 0:
        print(f"❌ Pull failed: {stderr}")
        # 尝试恢复
        run_command("git stash pop", cwd=skill_dir)
        return False
    
    # 恢复本地修改
    print("📦 Restoring local changes...")
    run_command("git stash pop", cwd=skill_dir)
    
    # 更新 SKILL.md 中的 github_hash
    skill_md = os.path.join(skill_dir, 'SKILL.md')
    if os.path.exists(skill_md):
        print("📝 Updating SKILL.md metadata...")
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 简单的替换 github_hash
        if 'github_hash:' in content:
            import re
            content = re.sub(
                r'github_hash:\s*[a-f0-9]+',
                f'github_hash: {remote_hash}',
                content
            )
            with open(skill_md, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Updated github_hash in SKILL.md")
    
    print(f"✅ Successfully updated: {name}")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_update.py <skills_dir>")
        sys.exit(1)
    
    skills_dir = sys.argv[1]
    
    # 先运行扫描
    print("🔍 Scanning for outdated skills...")
    scan_script = os.path.join(skills_dir, 'skill-manager', 'scripts', 'scan_and_check.py')
    code, stdout, stderr = run_command(f"python3 {scan_script} {skills_dir}")
    
    if code != 0:
        print(f"❌ Scan failed: {stderr}")
        sys.exit(1)
    
    # 解析结果
    skills_status = json.loads(stdout)
    outdated_skills = [s for s in skills_status if s['status'] == 'outdated']
    
    print(f"\n📊 Found {len(outdated_skills)} outdated skills")
    print(f"✅ {len([s for s in skills_status if s['status'] == 'current'])} skills are up to date")
    
    if not outdated_skills:
        print("\n🎉 All skills are up to date!")
        return
    
    # 显示将要更新的 skills
    print("\n📋 Skills to update:")
    for skill in outdated_skills:
        print(f"  - {skill['name']}")
    
    # 确认
    response = input(f"\n❓ Update all {len(outdated_skills)} skills? (y/n): ")
    if response.lower() != 'y':
        print("❌ Update cancelled")
        return
    
    # 批量更新
    success_count = 0
    failed_skills = []
    
    for i, skill in enumerate(outdated_skills, 1):
        print(f"\n[{i}/{len(outdated_skills)}]", end=" ")
        if update_skill(skill):
            success_count += 1
        else:
            failed_skills.append(skill['name'])
    
    # 总结
    print(f"\n{'='*60}")
    print(f"📊 Update Summary")
    print(f"{'='*60}")
    print(f"✅ Successfully updated: {success_count}/{len(outdated_skills)}")
    if failed_skills:
        print(f"❌ Failed to update: {len(failed_skills)}")
        for name in failed_skills:
            print(f"   - {name}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
