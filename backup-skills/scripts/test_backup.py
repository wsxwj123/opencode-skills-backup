#!/usr/bin/env python3
"""
测试备份脚本
"""

import sys
import os
from pathlib import Path

# 添加脚本目录到路径
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from skill_utils import SkillUtils

def test_skill_utils():
    """测试技能工具"""
    print("测试 SkillUtils 类...")
    
    # 初始化
    skills_dir = Path("/Users/wsxwj/.config/opencode/skills")
    utils = SkillUtils(skills_dir)
    
    # 测试获取技能列表
    print("1. 获取技能列表...")
    skills = utils.get_skill_list()
    print(f"   找到 {len(skills)} 个技能")
    
    for skill in skills[:3]:  # 只显示前3个
        print(f"   - {skill['name']} ({utils.format_size(skill['size'])})")
    
    if len(skills) > 3:
        print(f"   ... 和 {len(skills)-3} 个其他技能")
    
    # 测试技能摘要
    print("\n2. 生成技能摘要...")
    summary = utils.create_skill_summary()
    print(f"   总技能数: {summary['total_skills']}")
    print(f"   有 SKILL.md 的技能: {summary['skills_with_md']}")
    print(f"   总大小: {summary['formatted_total_size']}")
    
    # 测试技能验证
    print("\n3. 验证技能结构...")
    if skills:
        test_skill = skills[0]['name']
        print(f"   验证技能: {test_skill}")
        valid, messages = utils.validate_skill_structure(test_skill)
        if valid:
            print(f"   ✓ 技能结构有效")
            if messages:
                print(f"   提示: {', '.join(messages)}")
        else:
            print(f"   ✗ 技能结构无效")
            print(f"   错误: {', '.join(messages)}")
    
    print("\n✅ SkillUtils 测试完成")

def test_backup_script():
    """测试备份脚本"""
    print("\n测试备份脚本...")
    
    # 检查备份脚本是否存在
    backup_script = scripts_dir / "backup_skills.py"
    if backup_script.exists():
        print("1. 备份脚本存在")
        
        # 测试帮助信息
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, str(backup_script), "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("2. 备份脚本帮助信息正常")
            else:
                print("2. 备份脚本帮助信息异常")
        except Exception as e:
            print(f"2. 运行备份脚本时出错: {e}")
    else:
        print("1. 备份脚本不存在")
    
    print("\n✅ 备份脚本测试完成")

def test_git_operations():
    """测试 Git 操作"""
    print("\n测试 GitOperations 类...")
    
    try:
        from git_operations import GitOperations
        import shutil
        
        # 初始化
        test_dir = Path("/tmp/test_git_repo")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        test_dir.mkdir(parents=True)
        
        git = GitOperations(test_dir)
        
        # 测试初始化
        if git.init_repo():
            print("1. Git 仓库初始化成功")
        else:
            print("1. Git 仓库初始化失败")
        
        # 测试状态检查
        status = git.status()
        print(f"2. Git 状态: {'有变更' if status else '无变更'}")
        
        # 清理
        shutil.rmtree(test_dir)
        
    except ImportError as e:
        print(f"导入 GitOperations 失败: {e}")
    except Exception as e:
        print(f"测试 GitOperations 时出错: {e}")
    
    print("\n✅ GitOperations 测试完成")

def main():
    """主测试函数"""
    print("=" * 60)
    print("OpenCode Skills Backup 测试套件")
    print("=" * 60)
    
    try:
        test_skill_utils()
        test_backup_script()
        test_git_operations()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
        # 提供使用建议
        print("\n📋 使用建议:")
        print("1. 首次使用前，请先设置 GitHub 仓库")
        print("2. 运行备份: python3 scripts/backup_skills.py")
        print("3. 查看状态: python3 scripts/backup_skills.py --status")
        print("4. 测试备份: python3 scripts/backup_skills.py --test")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())