#!/usr/bin/env python3
"""
智能批量更新 skills：只更新元数据，保留现有内容
"""

import os
import sys
import json
import subprocess
import re
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

def get_latest_commit_hash(github_url):
    """从 GitHub 获取最新的 commit hash"""
    try:
        result = subprocess.run(
            ['git', 'ls-remote', github_url, 'HEAD'],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        # Output format: <hash>\tHEAD
        latest_hash = result.stdout.split()[0]
        return latest_hash
    except Exception as e:
        print(f"    ⚠️  Failed to fetch hash: {e}")
        return None

def update_skill_metadata(skill_info):
    """更新单个 skill 的元数据"""
    name = skill_info['name']
    skill_dir = skill_info['dir']
    github_url = skill_info['github_url']
    old_hash = skill_info['local_hash']
    new_hash = skill_info['remote_hash']
    
    print(f"\n{'='*60}")
    print(f"📦 Updating: {name}")
    print(f"📂 Directory: {skill_dir}")
    print(f"🔗 GitHub: {github_url}")
    print(f"📝 Old hash: {old_hash[:8]}...")
    print(f"✨ New hash: {new_hash[:8]}...")
    print(f"{'='*60}")
    
    # 检查目录是否存在
    if not os.path.exists(skill_dir):
        print(f"❌ Directory not found")
        return False
    
    # 查找 SKILL.md
    skill_md = os.path.join(skill_dir, 'SKILL.md')
    if not os.path.exists(skill_md):
        print(f"⚠️  SKILL.md not found, skipping...")
        return False
    
    # 读取文件内容
    print("📖 Reading SKILL.md...")
    try:
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Failed to read SKILL.md: {e}")
        return False
    
    # 更新 github_hash
    if 'github_hash:' in content:
        print("✍️  Updating github_hash...")
        # 使用正则表达式替换 github_hash
        new_content = re.sub(
            r'github_hash:\s*[a-f0-9]+',
            f'github_hash: {new_hash}',
            content
        )
        
        # 写回文件
        try:
            with open(skill_md, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Successfully updated {name}")
            return True
        except Exception as e:
            print(f"❌ Failed to write SKILL.md: {e}")
            return False
    else:
        print(f"⚠️  No github_hash field found in SKILL.md")
        # 尝试在 frontmatter 结束前添加
        if '---' in content:
            parts = content.split('---', 2)
            if len(parts) >= 3:
                # 在 frontmatter 中添加 github_hash
                frontmatter = parts[1].rstrip()
                frontmatter += f"\ngithub_hash: {new_hash}\n"
                new_content = f"---{frontmatter}---{parts[2]}"
                
                try:
                    with open(skill_md, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"✅ Added github_hash and updated {name}")
                    return True
                except Exception as e:
                    print(f"❌ Failed to write SKILL.md: {e}")
                    return False
        
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python smart_batch_update.py <skills_dir>")
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
    for skill in outdated_skills[:10]:  # 只显示前 10 个
        print(f"  - {skill['name']}")
    if len(outdated_skills) > 10:
        print(f"  ... and {len(outdated_skills) - 10} more")
    
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
        if update_skill_metadata(skill):
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
        for name in failed_skills[:10]:  # 只显示前 10 个
            print(f"   - {name}")
        if len(failed_skills) > 10:
            print(f"   ... and {len(failed_skills) - 10} more")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
