#!/usr/bin/env python3
"""
OpenCode 备份验证脚本
"""

import os
import sys
from pathlib import Path

def verify_backup_integrity():
    """验证备份完整性"""
    print("🔍 验证 OpenCode 备份完整性...")
    
    # 路径配置
    opencode_path = Path("/Users/wsxwj/.config/opencode")
    backup_path = Path("/Users/wsxwj/.config/opencode/skills/opencode-backup/backup-repo")
    
    if not backup_path.exists():
        print("❌ 备份目录不存在")
        return False
    
    # 检查关键目录和文件
    critical_items = [
        "skills",
        "plugins",
        "agents",
        "commands",
        "lib",
        "opencode.json",
        "oh-my-opencode.json",
        "package.json"
    ]
    
    missing_items = []
    for item in critical_items:
        item_path = backup_path / item
        if not item_path.exists():
            missing_items.append(item)
    
    if missing_items:
        print(f"❌ 缺少关键项目: {', '.join(missing_items)}")
        return False
    
    # 检查 skills 数量
    original_skills = len(list((opencode_path / "skills").iterdir()))
    backup_skills = len(list((backup_path / "skills").iterdir()))
    
    print(f"📊 技能数量统计:")
    print(f"  原始目录: {original_skills} 个技能")
    print(f"  备份目录: {backup_skills} 个技能")
    
    if original_skills != backup_skills:
        print(f"⚠️  技能数量不匹配 (差异: {abs(original_skills - backup_skills)})")
        # 找出缺失的技能
        original_skill_names = {p.name for p in (opencode_path / "skills").iterdir() if p.is_dir()}
        backup_skill_names = {p.name for p in (backup_path / "skills").iterdir() if p.is_dir()}
        
        missing_in_backup = original_skill_names - backup_skill_names
        extra_in_backup = backup_skill_names - original_skill_names
        
        if missing_in_backup:
            print(f"  备份中缺少的技能: {', '.join(sorted(missing_in_backup)[:5])}")
            if len(missing_in_backup) > 5:
                print(f"  还有 {len(missing_in_backup) - 5} 个...")
        
        if extra_in_backup:
            print(f"  备份中多余的技能: {', '.join(sorted(extra_in_backup)[:5])}")
            if len(extra_in_backup) > 5:
                print(f"  还有 {len(extra_in_backup) - 5} 个...")
    
    # 检查 Git 状态
    print("\n📦 Git 状态检查:")
    try:
        import subprocess
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=backup_path,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print("⚠️  有未提交的变更:")
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"  {line}")
        else:
            print("✅ 工作区干净")
        
        # 检查远程同步状态
        result = subprocess.run(
            ["git", "log", "--oneline", "origin/master..HEAD"],
            cwd=backup_path,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print("⚠️  有未推送到远程的提交")
        else:
            print("✅ 与远程仓库同步")
            
    except Exception as e:
        print(f"⚠️  Git 检查失败: {e}")
    
    print("\n✅ 备份验证完成")
    return True

def check_backup_freshness():
    """检查备份新鲜度"""
    print("\n📅 检查备份新鲜度...")
    
    backup_path = Path("/Users/wsxwj/.config/opencode/skills/opencode-backup/backup-repo")
    
    try:
        import subprocess
        from datetime import datetime
        
        # 获取最新提交时间
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=iso"],
            cwd=backup_path,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            last_commit_str = result.stdout.strip()
            last_commit_time = datetime.fromisoformat(last_commit_str.replace(' +', '+'))
            now = datetime.now()
            age_hours = (now - last_commit_time).total_seconds() / 3600
            
            print(f"  最新备份时间: {last_commit_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  备份年龄: {age_hours:.1f} 小时")
            
            if age_hours > 24:
                print("⚠️  备份超过24小时，建议更新")
            else:
                print("✅ 备份新鲜度良好")
        else:
            print("⚠️  无法获取提交时间")
            
    except Exception as e:
        print(f"⚠️  新鲜度检查失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("OpenCode 备份完整性验证")
    print("=" * 60)
    
    success = verify_backup_integrity()
    check_backup_freshness()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 备份验证通过！")
    else:
        print("❌ 备份验证发现问题，请检查")
        sys.exit(1)