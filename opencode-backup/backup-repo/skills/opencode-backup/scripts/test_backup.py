#!/usr/bin/env python3
"""
OpenCode 备份测试脚本
测试备份功能的各个组件
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import subprocess

def test_backup_script():
    """测试备份脚本的基本功能"""
    print("🧪 开始测试 OpenCode 备份脚本...")
    
    # 创建临时目录模拟 OpenCode 环境
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 创建测试环境: {tmpdir}")
        
        # 创建模拟的 OpenCode 目录结构
        opencode_path = Path(tmpdir) / ".config" / "opencode"
        opencode_path.mkdir(parents=True, exist_ok=True)
        
        # 创建测试文件
        test_files = [
            "opencode.json",
            "oh-my-opencode.json",
            "package.json",
            ".gitignore"
        ]
        
        for filename in test_files:
            filepath = opencode_path / filename
            filepath.write_text(f'{{"test": "{filename}"}}')
            print(f"✓ 创建测试文件: {filename}")
        
        # 创建测试目录
        test_dirs = ["plugins", "skills", "agents", "commands", "lib"]
        for dirname in test_dirs:
            dirpath = opencode_path / dirname
            dirpath.mkdir(exist_ok=True)
            
            # 在目录中创建一些文件
            (dirpath / "test.txt").write_text(f"Test content for {dirname}")
            print(f"✓ 创建测试目录: {dirname}")
        
        # 创建技能备份目录
        skill_backup_dir = opencode_path / "skills" / "opencode-backup"
        skill_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制备份脚本到测试环境
        current_script = Path(__file__).parent / "backup_opencode.py"
        test_script = skill_backup_dir / "backup_opencode.py"
        shutil.copy2(current_script, test_script)
        
        # 创建测试配置文件
        config_content = {
            "repo_url": "https://github.com/test/opencode-backup.git",
            "last_backup": None,
            "backup_count": 0,
            "backup_items": {
                "config_files": ["opencode.json", "oh-my-opencode.json", "package.json"],
                "directories": ["plugins", "skills", "agents"],
                "tool_scripts": [],
                "documentation": [],
                "exclude_patterns": ["node_modules", ".DS_Store"]
            },
            "git_config": {
                "user_name": "Test User",
                "user_email": "test@example.com"
            }
        }
        
        import json
        config_file = skill_backup_dir / "backup-config.json"
        config_file.write_text(json.dumps(config_content, indent=2))
        
        print("✅ 测试环境设置完成")
        
        # 测试脚本导入
        print("\n🔧 测试脚本导入...")
        try:
            # 修改 sys.path 以便导入
            sys.path.insert(0, str(skill_backup_dir.parent))
            
            # 动态导入模块
            import importlib.util
            spec = importlib.util.spec_from_file_location("backup_opencode", test_script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            print("✅ 脚本导入成功")
            
            # 测试类实例化
            backup = module.OpenCodeBackup(str(opencode_path))
            print("✅ 类实例化成功")
            
            # 测试配置加载
            config = backup.load_config()
            assert config["repo_url"] == "https://github.com/test/opencode-backup.git"
            print("✅ 配置加载成功")
            
            # 测试文件备份
            test_file = opencode_path / "opencode.json"
            assert backup.backup_file("opencode.json", dry_run=True)
            print("✅ 文件备份测试通过")
            
            # 测试目录备份
            assert backup.backup_directory("plugins", ["*.tmp"], dry_run=True)
            print("✅ 目录备份测试通过")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n🎉 所有测试通过！")
        return True

def test_cli_commands():
    """测试命令行接口"""
    print("\n🖥️  测试命令行接口...")
    
    # 测试帮助命令
    try:
        result = subprocess.run(
            [sys.executable, "scripts/backup_opencode.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print("✅ 帮助命令测试通过")
            
            # 检查是否包含关键命令
            required_commands = ["init", "backup", "incremental", "status", "restore"]
            for cmd in required_commands:
                if cmd in result.stdout:
                    print(f"  ✓ 包含命令: {cmd}")
                else:
                    print(f"  ❌ 缺失命令: {cmd}")
                    return False
        else:
            print(f"❌ 帮助命令失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ CLI 测试失败: {e}")
        return False
    
    print("✅ CLI 测试通过")
    return True

def test_backup_integrity():
    """测试备份完整性检查"""
    print("\n🔍 测试备份完整性检查...")
    
    try:
        # 导入模块
        sys.path.insert(0, str(Path(__file__).parent))
        
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "backup_opencode", 
            Path(__file__).parent / "backup_opencode.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 创建测试实例
        backup = module.OpenCodeBackup()
        
        # 测试默认备份项目
        items = backup.get_default_backup_items()
        required_keys = ["config_files", "directories", "exclude_patterns"]
        
        for key in required_keys:
            if key in items:
                print(f"✓ 包含配置项: {key}")
            else:
                print(f"❌ 缺失配置项: {key}")
                return False
        
        # 检查必要的配置文件
        required_files = ["opencode.json", "package.json"]
        for file in required_files:
            if file in items["config_files"]:
                print(f"✓ 包含配置文件: {file}")
            else:
                print(f"❌ 缺失配置文件: {file}")
                return False
        
        # 检查必要的目录
        required_dirs = ["plugins", "skills"]
        for dir in required_dirs:
            if dir in items["directories"]:
                print(f"✓ 包含目录: {dir}")
            else:
                print(f"❌ 缺失目录: {dir}")
                return False
        
        print("✅ 备份完整性检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 完整性检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 OpenCode 备份功能测试套件")
    print("=" * 60)
    
    tests = [
        ("备份脚本功能", test_backup_script),
        ("命令行接口", test_cli_commands),
        ("备份完整性", test_backup_integrity)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 测试: {test_name}")
        print("-" * 40)
        
        try:
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
                
        except Exception as e:
            print(f"💥 {test_name} - 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n🎯 通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有测试通过！备份功能正常。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())