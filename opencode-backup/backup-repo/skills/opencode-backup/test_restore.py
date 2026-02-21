#!/usr/bin/env python3
"""
测试备份恢复功能
"""

import os
import shutil
import tempfile
from pathlib import Path

def test_restore_functionality():
    """测试恢复功能的基本逻辑"""
    print("🧪 测试备份恢复功能...")
    
    # 创建测试目录结构
    test_dir = Path(tempfile.mkdtemp(prefix="opencode_test_"))
    print(f"测试目录: {test_dir}")
    
    # 创建模拟的 OpenCode 结构
    test_opencode = test_dir / "opencode"
    test_backup = test_dir / "backup"
    
    # 创建源目录
    test_opencode.mkdir()
    (test_opencode / "skills").mkdir()
    (test_opencode / "plugins").mkdir()
    (test_opencode / "agents").mkdir()
    
    # 创建一些测试文件
    (test_opencode / "opencode.json").write_text('{"test": "original"}')
    (test_opencode / "skills" / "test-skill").mkdir()
    (test_opencode / "skills" / "test-skill" / "SKILL.md").write_text("# Test Skill")
    
    # 创建备份目录（模拟备份）
    test_backup.mkdir()
    shutil.copytree(test_opencode, test_backup, dirs_exist_ok=True)
    
    # 修改备份中的文件
    (test_backup / "opencode.json").write_text('{"test": "restored"}')
    (test_backup / "skills" / "test-skill" / "SKILL.md").write_text("# Test Skill Restored")
    
    # 模拟恢复操作
    print("模拟恢复操作...")
    
    # 备份当前配置
    backup_before = test_dir / "backup_before_restore"
    shutil.copytree(test_opencode, backup_before)
    
    # 执行恢复（复制备份文件到源目录）
    for item in test_backup.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(test_backup)
            dst_path = test_opencode / rel_path
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst_path)
    
    # 验证恢复结果
    print("\n验证恢复结果:")
    
    # 检查配置文件
    restored_config = (test_opencode / "opencode.json").read_text()
    if '"test": "restored"' in restored_config:
        print("✅ 配置文件恢复成功")
    else:
        print("❌ 配置文件恢复失败")
    
    # 检查技能文件
    restored_skill = (test_opencode / "skills" / "test-skill" / "SKILL.md").read_text()
    if "Restored" in restored_skill:
        print("✅ 技能文件恢复成功")
    else:
        print("❌ 技能文件恢复失败")
    
    # 检查备份文件存在
    if backup_before.exists():
        print("✅ 恢复前备份创建成功")
    else:
        print("❌ 恢复前备份创建失败")
    
    # 清理
    shutil.rmtree(test_dir)
    print(f"\n🧹 清理测试目录: {test_dir}")
    
    print("\n🎉 恢复功能测试完成！")

if __name__ == "__main__":
    test_restore_functionality()