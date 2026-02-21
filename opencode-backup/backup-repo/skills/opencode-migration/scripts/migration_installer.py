#!/usr/bin/env python3
"""
OpenCode 迁移安装器
在新设备上安装迁移包
"""

import os
import json
import sys
import zipfile
import hashlib
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import platform

class MigrationInstaller:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.home_dir = Path.home()
        self.opencode_config_dir = self.home_dir / ".config" / "opencode"
        self.installation_log = {
            "installation_time": datetime.now().isoformat(),
            "platform": self._get_platform_info(),
            "steps": [],
            "files_installed": [],
            "issues": [],
            "success": False
        }
    
    def _get_platform_info(self) -> Dict[str, str]:
        """获取平台信息"""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version()
        }
        
        # macOS 特定信息
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(["sw_vers"], capture_output=True, text=True)
                for line in result.stdout.split("\n"):
                    if "ProductName:" in line:
                        info["macos_name"] = line.split(":")[1].strip()
                    elif "ProductVersion:" in line:
                        info["macos_version"] = line.split(":")[1].strip()
            except:
                pass
        
        return info
    
    def verify_package(self, package_path: str) -> Dict[str, Any]:
        """验证迁移包完整性"""
        print(f"🔍 验证迁移包: {package_path}")
        
        verification = {
            "package_path": package_path,
            "exists": False,
            "valid_zip": False,
            "has_manifest": False,
            "checksum_match": False,
            "issues": []
        }
        
        # 检查文件是否存在
        if not os.path.exists(package_path):
            verification["issues"].append("迁移包文件不存在")
            return verification
        
        verification["exists"] = True
        file_size = os.path.getsize(package_path)
        verification["file_size"] = file_size
        verification["file_size_mb"] = file_size / 1024 / 1024
        
        # 检查 ZIP 文件有效性
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                file_list = zipf.namelist()
                verification["file_count"] = len(file_list)
                verification["valid_zip"] = True
                
                # 检查清单文件
                if "MIGRATION_MANIFEST.json" in file_list:
                    verification["has_manifest"] = True
                    
                    # 读取清单
                    manifest_data = zipf.read("MIGRATION_MANIFEST.json")
                    try:
                        manifest = json.loads(manifest_data.decode('utf-8'))
                        verification["manifest"] = manifest.get("package_info", {})
                        
                        # 验证校验和
                        expected_checksums = manifest.get("package_info", {}).get("checksums", {})
                        if expected_checksums:
                            with open(package_path, 'rb') as f:
                                content = f.read()
                            
                            actual_md5 = hashlib.md5(content).hexdigest()
                            actual_sha256 = hashlib.sha256(content).hexdigest()
                            
                            verification["checksums"] = {
                                "expected_md5": expected_checksums.get("md5"),
                                "actual_md5": actual_md5,
                                "expected_sha256": expected_checksums.get("sha256"),
                                "actual_sha256": actual_sha256,
                                "match_md5": actual_md5 == expected_checksums.get("md5"),
                                "match_sha256": actual_sha256 == expected_checksums.get("sha256")
                            }
                            
                            verification["checksum_match"] = (
                                actual_md5 == expected_checksums.get("md5") and
                                actual_sha256 == expected_checksums.get("sha256")
                            )
                            
                            if not verification["checksum_match"]:
                                verification["issues"].append("校验和不匹配，文件可能已损坏")
                    
                    except json.JSONDecodeError as e:
                        verification["issues"].append(f"清单文件 JSON 解析失败: {str(e)}")
                else:
                    verification["issues"].append("迁移包缺少清单文件")
        
        except zipfile.BadZipFile:
            verification["issues"].append("无效的 ZIP 文件")
        except Exception as e:
            verification["issues"].append(f"验证 ZIP 文件时出错: {str(e)}")
        
        # 输出验证结果
        print(f"  文件大小: {verification['file_size_mb']:.2f} MB")
        print(f"  文件数量: {verification.get('file_count', 0)}")
        print(f"  ZIP 有效性: {'✅' if verification['valid_zip'] else '❌'}")
        print(f"  清单文件: {'✅' if verification['has_manifest'] else '❌'}")
        
        if verification.get("checksums"):
            checksums = verification["checksums"]
            print(f"  校验和匹配: {'✅' if verification['checksum_match'] else '❌'}")
            if not verification["checksum_match"] and self.verbose:
                print(f"    MD5 期望: {checksums.get('expected_md5')}")
                print(f"    MD5 实际: {checksums.get('actual_md5')}")
                print(f"    SHA256 期望: {checksums.get('expected_sha256')}")
                print(f"    SHA256 实际: {checksums.get('actual_sha256')}")
        
        if verification["issues"]:
            print(f"⚠️  发现问题 ({len(verification['issues'])} 个):")
            for issue in verification["issues"]:
                print(f"   • {issue}")
        
        return verification
    
    def check_dependencies(self) -> Dict[str, Any]:
        """检查系统依赖"""
        print("📦 检查系统依赖...")
        
        dependencies = {
            "required": [],
            "optional": [],
            "missing": [],
            "platform_issues": []
        }
        
        # 必需依赖
        required_deps = [
            {"name": "Python 3", "command": "python3", "min_version": "3.8.0"},
            {"name": "Node.js", "command": "node", "min_version": "14.0.0"},
            {"name": "npm/npx", "command": "npm", "min_version": "6.0.0"}
        ]
        
        # 可选依赖
        optional_deps = [
            {"name": "Git", "command": "git", "min_version": "2.20.0"},
            {"name": "Homebrew", "command": "brew", "min_version": "3.0.0"},
            {"name": "UV", "command": "uv", "min_version": "0.1.0"}
        ]
        
        # 检查必需依赖
        for dep in required_deps:
            status = self._check_dependency(dep)
            dependencies["required"].append(status)
            if not status["installed"]:
                dependencies["missing"].append(dep["name"])
        
        # 检查可选依赖
        for dep in optional_deps:
            status = self._check_dependency(dep)
            dependencies["optional"].append(status)
        
        # 平台特定检查
        current_platform = self.installation_log["platform"]
        if current_platform["system"] == "Darwin":
            if "arm" in current_platform["machine"].lower():
                # Apple Silicon
                dependencies["platform_issues"].append("Apple Silicon 设备，检查 Rosetta 2 和 ARM 原生支持")
            else:
                # Intel Mac
                dependencies["platform_issues"].append("Intel Mac，检查 Universal Binary 支持")
        
        elif current_platform["system"] == "Windows":
            dependencies["platform_issues"].append("Windows 设备，检查 WSL2 和路径兼容性")
        
        # 输出结果
        print(f"  必需依赖: {len([d for d in dependencies['required'] if d['installed']])}/{len(dependencies['required'])} 已安装")
        print(f"  可选依赖: {len([d for d in dependencies['optional'] if d['installed']])}/{len(dependencies['optional'])} 已安装")
        
        if dependencies["missing"]:
            print(f"⚠️  缺少必需依赖: {', '.join(dependencies['missing'])}")
        
        if dependencies["platform_issues"] and self.verbose:
            print(f"  平台问题: {', '.join(dependencies['platform_issues'])}")
        
        return dependencies
    
    def _check_dependency(self, dep: Dict) -> Dict[str, Any]:
        """检查单个依赖"""
        status = {
            "name": dep["name"],
            "command": dep["command"],
            "installed": False,
            "version": "unknown",
            "meets_minimum": False
        }
        
        try:
            # 尝试运行命令获取版本
            if dep["command"] == "python3" and platform.system() == "Windows":
                # Windows 上可能是 python 而不是 python3
                cmd = ["python", "--version"]
            else:
                cmd = [dep["command"], "--version"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                status["installed"] = True
                version_output = result.stdout.strip()
                
                # 提取版本号
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+)', version_output)
                if version_match:
                    status["version"] = version_match.group(1)
                    
                    # 检查是否满足最低版本要求
                    if "min_version" in dep:
                        from packaging import version
                        try:
                            current_ver = version.parse(status["version"])
                            min_ver = version.parse(dep["min_version"])
                            status["meets_minimum"] = current_ver >= min_ver
                        except:
                            status["meets_minimum"] = True  # 如果解析失败，假设满足
        
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass  # 依赖未安装
        
        return status
    
    def install_package(self, package_path: str, backup: bool = True, dry_run: bool = False) -> bool:
        """安装迁移包"""
        print(f"🚀 安装迁移包: {package_path}")
        
        # 验证包
        verification = self.verify_package(package_path)
        if not verification["valid_zip"] or not verification["has_manifest"]:
            print("❌ 迁移包验证失败，无法安装")
            return False
        
        # 检查依赖
        dependencies = self.check_dependencies()
        if dependencies["missing"]:
            print("❌ 缺少必需依赖，无法继续安装")
            print(f"   请先安装: {', '.join(dependencies['missing'])}")
            return False
        
        # 备份现有配置
        if backup and not dry_run:
            backup_success = self._backup_existing_config()
            if not backup_success:
                print("⚠️  备份现有配置失败，继续安装...")
        
        try:
            # 提取迁移包
            print("📂 提取迁移包...")
            
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # 读取清单
                manifest_data = zipf.read("MIGRATION_MANIFEST.json")
                manifest = json.loads(manifest_data.decode('utf-8'))
                
                # 创建 OpenCode 配置目录
                if not dry_run:
                    self.opencode_config_dir.mkdir(parents=True, exist_ok=True)
                
                # 提取文件
                file_count = 0
                for file_info in zipf.infolist():
                    # 跳过目录条目和清单文件（已经处理）
                    if file_info.filename.endswith('/') or file_info.filename == "MIGRATION_MANIFEST.json":
                        continue
                    
                    # 确定目标路径
                    if file_info.filename.startswith("external/"):
                        # 外部文件，需要特殊处理
                        rel_path = Path(file_info.filename[9:])  # 去掉 "external/"
                        target_path = self.home_dir / rel_path
                    else:
                        # OpenCode 配置文件
                        target_path = self.opencode_config_dir / file_info.filename
                    
                    # 创建父目录
                    if not dry_run:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 提取文件
                    if not dry_run:
                        with zipf.open(file_info) as source, open(target_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                    
                    file_count += 1
                    self.installation_log["files_installed"].append(str(target_path))
                    
                    if self.verbose and file_count % 50 == 0:
                        print(f"    已提取 {file_count} 个文件...")
                
                print(f"✅ 提取完成: {file_count} 个文件")
                
                # 记录安装信息
                self.installation_log["manifest"] = manifest.get("package_info", {})
                self.installation_log["source_platform"] = manifest.get("package_info", {}).get("platform_info", {})
                self.installation_log["file_count"] = file_count
                self.installation_log["dependencies"] = dependencies
        
        except Exception as e:
            print(f"❌ 安装失败: {str(e)}")
            self.installation_log["issues"].append(f"安装失败: {str(e)}")
            return False
        
        # 后安装配置
        if not dry_run:
            post_install_success = self._post_install_configuration()
            if not post_install_success:
                print("⚠️  后安装配置遇到问题，但安装已完成")
        
        # 保存安装日志
        if not dry_run:
            log_file = self.opencode_config_dir / "migration_installation_log.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.installation_log, f, indent=2, ensure_ascii=False)
            print(f"📝 安装日志已保存: {log_file}")
        
        self.installation_log["success"] = True
        return True
    
    def _backup_existing_config(self) -> bool:
        """备份现有配置"""
        print("💾 备份现有配置...")
        
        if not self.opencode_config_dir.exists():
            print("  没有现有配置需要备份")
            return True
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.home_dir / "opencode_backups" / f"pre_migration_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制配置文件
            shutil.copytree(self.opencode_config_dir, backup_dir / ".config" / "opencode")
            
            print(f"✅ 配置已备份到: {backup_dir}")
            self.installation_log["backup_location"] = str(backup_dir)
            return True
            
        except Exception as e:
            print(f"❌ 备份失败: {str(e)}")
            self.installation_log["issues"].append(f"备份失败: {str(e)}")
            return False
    
    def _post_install_configuration(self) -> bool:
        """后安装配置"""
        print("⚙️  执行后安装配置...")
        
        issues = []
        
        try:
            # 检查主配置文件
            config_file = self.opencode_config_dir / "opencode.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 验证配置
                if not config.get("model"):
                    issues.append("配置文件中缺少模型设置")
                
                # 检查 MCP 服务器
                mcp_servers = config.get("mcp", {})
                for name, server_config in mcp_servers.items():
                    if server_config.get("enabled", False):
                        # 检查命令是否存在
                        command = server_config.get("command", [])
                        if command and command[0] not in ["npx", "node", "python", "python3", "uv"]:
                            # 检查本地命令
                            cmd_path = Path(command[0])
                            if not cmd_path.exists():
                                issues.append(f"MCP 服务器 '{name}' 的命令不存在: {command[0]}")
            
            else:
                issues.append("主配置文件不存在")
        
        except Exception as e:
            issues.append(f"后安装配置检查失败: {str(e)}")
        
        # 设置文件权限
        try:
            for root, dirs, files in os.walk(self.opencode_config_dir):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    os.chmod(dir_path, 0o755)
                for file_name in files:
                    file_path = Path(root) / file_name
                    if file_path.suffix in ['.sh', '.py']:
                        os.chmod(file_path, 0o755)
                    else:
                        os.chmod(file_path, 0o644)
        except Exception as e:
            issues.append(f"设置文件权限失败: {str(e)}")
        
        # 记录问题
        if issues:
            self.installation_log["post_install_issues"] = issues
            print(f"⚠️  后安装配置发现问题 ({len(issues)} 个):")
            for issue in issues[:3]:
                print(f"   • {issue}")
            if len(issues) > 3:
                print(f"   ... 还有 {len(issues) - 3} 个问题")
            return False
        
        print("✅ 后安装配置完成")
        return True
    
    def print_installation_summary(self):
        """打印安装摘要"""
        if not self.installation_log.get("success"):
            print("❌ 安装未完成或失败")
            return
        
        print("\n" + "="*60)
        print("🎉 OpenCode 迁移安装完成!")
        print("="*60)
        
        print(f"\n📅 安装时间: {self.installation_log.get('installation_time', '未知')}")
        
        # 平台信息
        target_platform = self.installation_log.get("platform", {})
        source_platform = self.installation_log.get("source_platform", {})
        
        print(f"\n💻 平台信息:")
        print(f"   目标平台: {target_platform.get('system', 'Unknown')} {target_platform.get('machine', '')}")
        if source_platform:
            print(f"   源平台: {source_platform.get('system', 'Unknown')} {source_platform.get('machine', '')}")
        
        # 文件统计
        file_count = self.installation_log.get("file_count", 0)
        print(f"\n📁 安装统计:")
        print(f"   文件数量: {file_count}")
        
        # 依赖状态
        dependencies = self.installation_log.get("dependencies", {})
        if dependencies:
            required_installed = len([d for d in dependencies.get("required", []) if d.get("installed", False)])
            required_total = len(dependencies.get("required", []))
            print(f"   依赖状态: {required_installed}/{required_total} 必需依赖已安装")
        
        # 备份信息
        backup_location = self.installation_log.get("backup_location")
        if backup_location:
            print(f"\n💾 备份位置: {backup_location}")
        
        # 问题
        issues = self.installation_log.get("issues", [])
        post_install_issues = self.installation_log.get("post_install_issues", [])
        all_issues = issues + post_install_issues
        
        if all_issues:
            print(f"\n⚠️  安装过程中发现问题 ({len(all_issues)} 个):")
            for i, issue in enumerate(all_issues[:3], 1):
                print(f"   {i}. {issue}")
            if len(all_issues) > 3:
                print(f"   ... 还有 {len(all_issues) - 3} 个问题")
        
        # 后续步骤
        print(f"\n🚀 后续步骤:")
        print("   1. 验证 OpenCode 配置:")
        print(f"      cd {self.opencode_config_dir}")
        print("      cat opencode.json | head -20")
        print("   2. 测试 MCP 服务器:")
        print("      检查各个 MCP 服务器是否能正常启动")
        print("   3. 测试技能:")
        print("      运行几个技能确保功能正常")
        print("   4. 如有问题，查看安装日志:")
        print(f"      {self.opencode_config_dir}/migration_installation_log.json")
        
        print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description="OpenCode 迁移安装器")
    parser.add_argument("--install", type=str, help="安装迁移包")
    parser.add_argument("--verify", type=str, help="验证迁移包")
    parser.add_argument("--dry-run", action="store_true", help="模拟安装，不实际修改文件")
    parser.add_argument("--no-backup", action="store_true", help="不备份现有配置")
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    if not args.install and not args.verify:
        parser.print_help()
        return
    
    installer = MigrationInstaller(verbose=args.verbose)
    
    if args.verify:
        print("🔍 验证迁移包...")
        verification = installer.verify_package(args.verify)
        
        if verification["valid_zip"] and verification["has_manifest"]:
            print("\n✅ 迁移包验证通过")
            if verification.get("checksum_match"):
                print("   校验和匹配，文件完整")
        else:
            print("\n❌ 迁移包验证失败")
            sys.exit(1)
    
    elif args.install:
        print("🚀 开始安装迁移包...")
        
        success = installer.install_package(
            package_path=args.install,
            backup=not args.no_backup,
            dry_run=args.dry_run
        )
        
        if success:
            installer.print_installation_summary()
        else:
            print("\n❌ 安装失败")
            sys.exit(1)

if __name__ == "__main__":
    main()