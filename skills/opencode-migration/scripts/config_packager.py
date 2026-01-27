#!/usr/bin/env python3
"""
OpenCode 配置打包器
打包 OpenCode 配置为可迁移的压缩包
"""

import os
import json
import sys
import zipfile
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set
import hashlib

class ConfigPackager:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.home_dir = Path.home()
        self.opencode_config_dir = self.home_dir / ".config" / "opencode"
        self.package_info = {
            "package_time": datetime.now().isoformat(),
            "files": [],
            "excluded": [],
            "platform_info": self._get_platform_info(),
            "checksums": {}
        }
        
        # 需要排除的文件和目录
        self.exclude_patterns = [
            "*.pyc", "*.pyo", "__pycache__", ".git", ".DS_Store",
            "node_modules", "*.log", "*.tmp", "*.temp"
        ]
        
        # 敏感信息模式（需要过滤或替换）
        self.sensitive_patterns = {
            "api_key": r"(?i)(api[_-]?key|secret|token|password|auth)[\s]*[:=][\s]*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            "bearer_token": r"Bearer\s+([a-zA-Z0-9_\-]{20,})",
            "private_key": r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----"
        }
    
    def _get_platform_info(self) -> Dict[str, str]:
        """获取平台信息"""
        import platform
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version()
        }
        return info
    
    def _should_exclude(self, path: Path) -> bool:
        """检查文件是否应该排除"""
        # 检查排除模式
        for pattern in self.exclude_patterns:
            if pattern.startswith("*."):
                # 文件扩展名匹配
                if path.name.endswith(pattern[1:]):
                    return True
            elif pattern in str(path):
                # 目录名匹配
                return True
        
        # 检查文件大小（排除大文件）
        try:
            if path.is_file() and path.stat().st_size > 50 * 1024 * 1024:  # 50MB
                if self.verbose:
                    print(f"  排除大文件: {path} ({path.stat().st_size / 1024 / 1024:.1f}MB)")
                return True
        except:
            pass
        
        return False
    
    def _filter_sensitive_content(self, content: str, filepath: str) -> str:
        """过滤敏感内容"""
        filtered = content
        
        # 过滤 API 密钥等敏感信息
        import re
        
        # 替换 API 密钥
        for key_type, pattern in self.sensitive_patterns.items():
            matches = re.findall(pattern, filtered)
            for match in matches:
                if isinstance(match, tuple):
                    # 模式匹配了多个组
                    for group in match:
                        if len(group) > 10:  # 可能是密钥
                            masked = f"[FILTERED_{key_type.upper()}]"
                            filtered = filtered.replace(group, masked)
                elif len(match) > 10:
                    masked = f"[FILTERED_{key_type.upper()}]"
                    filtered = filtered.replace(match, masked)
        
        # 特定文件处理
        if "opencode.json" in filepath:
            # 在 OpenCode 配置中过滤提供商密钥
            try:
                config = json.loads(filtered)
                if "provider" in config:
                    for provider_name, provider_config in config["provider"].items():
                        if "options" in provider_config and "headers" in provider_config["options"]:
                            headers = provider_config["options"]["headers"]
                            if "Authorization" in headers:
                                # 保留 Bearer 前缀但隐藏实际令牌
                                auth_header = headers["Authorization"]
                                if auth_header.startswith("Bearer "):
                                    headers["Authorization"] = "Bearer [FILTERED_API_KEY]"
                                elif auth_header.startswith("sk-"):
                                    headers["Authorization"] = "[FILTERED_API_KEY]"
                
                filtered = json.dumps(config, indent=2, ensure_ascii=False)
            except:
                pass  # 如果 JSON 解析失败，保持原样
        
        return filtered
    
    def scan_config_files(self) -> List[Path]:
        """扫描 OpenCode 配置文件"""
        print("📁 扫描 OpenCode 配置文件...")
        
        config_files = []
        
        # 核心配置文件
        core_files = [
            self.opencode_config_dir / "opencode.json",
            self.opencode_config_dir / "package.json",
            self.opencode_config_dir / "oh-my-opencode.json",
            self.opencode_config_dir / "oh-my-opencode-slim.json"
        ]
        
        for file in core_files:
            if file.exists():
                config_files.append(file)
                if self.verbose:
                    print(f"  找到: {file}")
        
        # 扫描目录
        directories_to_scan = [
            ("skills", "技能库"),
            ("plugins", "插件"),
            ("agents", "代理配置"),
            ("commands", "命令")
        ]
        
        for dir_name, description in directories_to_scan:
            dir_path = self.opencode_config_dir / dir_name
            if dir_path.exists():
                print(f"  扫描 {description}...")
                for item in dir_path.rglob("*"):
                    if not self._should_exclude(item):
                        config_files.append(item)
                        if self.verbose and len(config_files) % 50 == 0:
                            print(f"    已找到 {len(config_files)} 个文件...")
        
        print(f"✅ 共找到 {len(config_files)} 个配置文件")
        return config_files
    
    def create_migration_package(self, output_file: str, incremental: bool = False, since_date: str = None) -> bool:
        """创建迁移包"""
        print(f"📦 创建迁移包: {output_file}")
        
        try:
            # 扫描文件
            all_files = self.scan_config_files()
            
            # 增量打包处理
            files_to_package = all_files
            if incremental:
                files_to_package = self._filter_incremental_files(all_files, since_date)
                print(f"  增量打包: {len(files_to_package)}/{len(all_files)} 个文件")
            
            # 创建 ZIP 包
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加清单文件
                self._create_manifest(zipf, files_to_package)
                
                # 添加文件
                for file_path in files_to_package:
                    self._add_file_to_zip(zipf, file_path)
            
            # 计算校验和
            self._calculate_checksums(output_file)
            
            # 保存包信息
            self._save_package_info(output_file)
            
            print(f"✅ 迁移包创建成功: {output_file}")
            print(f"   文件数量: {len(files_to_package)}")
            print(f"   包大小: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建迁移包失败: {str(e)}")
            return False
    
    def _filter_incremental_files(self, all_files: List[Path], since_date: str = None) -> List[Path]:
        """过滤增量文件"""
        if not since_date:
            # 默认最近7天
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(days=7)
        else:
            try:
                cutoff_time = datetime.strptime(since_date, "%Y-%m-%d")
            except:
                print(f"⚠️  无效日期格式: {since_date}，使用默认7天")
                cutoff_time = datetime.now() - timedelta(days=7)
        
        incremental_files = []
        for file_path in all_files:
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime >= cutoff_time:
                    incremental_files.append(file_path)
            except:
                # 如果无法获取修改时间，包含文件
                incremental_files.append(file_path)
        
        return incremental_files
    
    def _create_manifest(self, zipf: zipfile.ZipFile, files: List[Path]):
        """创建清单文件"""
        manifest = {
            "package_info": self.package_info,
            "files": []
        }
        
        for file_path in files:
            try:
                rel_path = file_path.relative_to(self.opencode_config_dir)
                file_info = {
                    "path": str(rel_path),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "is_file": file_path.is_file()
                }
                manifest["files"].append(file_info)
            except:
                # 文件不在 OpenCode 目录内
                pass
        
        manifest_str = json.dumps(manifest, indent=2, ensure_ascii=False)
        zipf.writestr("MIGRATION_MANIFEST.json", manifest_str)
        
        if self.verbose:
            print("  创建清单文件: MIGRATION_MANIFEST.json")
    
    def _add_file_to_zip(self, zipf: zipfile.ZipFile, file_path: Path):
        """添加文件到 ZIP 包"""
        try:
            # 计算相对路径
            try:
                rel_path = file_path.relative_to(self.opencode_config_dir)
            except ValueError:
                # 文件不在 OpenCode 目录内，使用绝对路径
                rel_path = Path("external") / file_path.relative_to(self.home_dir)
            
            # 处理敏感信息
            if file_path.is_file():
                # 文本文件：过滤敏感内容
                if file_path.suffix in ['.json', '.md', '.txt', '.js', '.py', '.yaml', '.yml', '.toml']:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 过滤敏感内容
                        filtered_content = self._filter_sensitive_content(content, str(file_path))
                        
                        # 添加到 ZIP
                        zipf.writestr(str(rel_path), filtered_content)
                        
                        # 记录文件信息
                        file_info = {
                            "path": str(rel_path),
                            "original_size": len(content),
                            "filtered_size": len(filtered_content),
                            "sensitive_filtered": content != filtered_content
                        }
                        self.package_info["files"].append(file_info)
                        
                    except UnicodeDecodeError:
                        # 二进制文件，直接复制
                        zipf.write(file_path, str(rel_path))
                        self.package_info["files"].append({
                            "path": str(rel_path),
                            "binary": True
                        })
                else:
                    # 二进制文件，直接复制
                    zipf.write(file_path, str(rel_path))
                    self.package_info["files"].append({
                        "path": str(rel_path),
                        "binary": True
                    })
            else:
                # 目录，创建空目录条目
                zipf.writestr(str(rel_path) + "/", "")
            
            if self.verbose and len(self.package_info["files"]) % 100 == 0:
                print(f"    已添加 {len(self.package_info['files'])} 个文件...")
                
        except Exception as e:
            print(f"⚠️  添加文件失败 {file_path}: {str(e)}")
            self.package_info["excluded"].append({
                "path": str(file_path),
                "error": str(e)
            })
    
    def _calculate_checksums(self, package_file: str):
        """计算包的校验和"""
        print("🔐 计算校验和...")
        
        try:
            with open(package_file, 'rb') as f:
                content = f.read()
            
            self.package_info["checksums"] = {
                "md5": hashlib.md5(content).hexdigest(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content)
            }
            
            if self.verbose:
                print(f"  MD5: {self.package_info['checksums']['md5']}")
                print(f"  SHA256: {self.package_info['checksums']['sha256']}")
                
        except Exception as e:
            print(f"⚠️  计算校验和失败: {str(e)}")
    
    def _save_package_info(self, package_file: str):
        """保存包信息"""
        info_file = package_file.replace(".zip", "_info.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(self.package_info, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"  包信息已保存: {info_file}")

def main():
    parser = argparse.ArgumentParser(description="OpenCode 配置打包器")
    parser.add_argument("--package", action="store_true", help="创建迁移包")
    parser.add_argument("--incremental", action="store_true", help="增量打包")
    parser.add_argument("--since", type=str, help="增量打包起始日期 (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="opencode-migration.zip", 
                       help="输出文件路径 (默认: opencode-migration.zip)")
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    
    args = parser.parse_args()
    
    if not args.package:
        parser.print_help()
        return
    
    print("🚀 OpenCode 配置打包器")
    print("="*50)
    
    packager = ConfigPackager(verbose=args.verbose or args.debug)
    
    # 设置输出文件名
    if args.output:
        output_file = args.output
        if not output_file.endswith(".zip"):
            output_file += ".zip"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"opencode_migration_{timestamp}.zip"
    
    # 创建迁移包
    success = packager.create_migration_package(
        output_file=output_file,
        incremental=args.incremental,
        since_date=args.since
    )
    
    if success:
        print("\n🎉 打包完成!")
        print(f"   迁移包: {output_file}")
        print(f"   信息文件: {output_file.replace('.zip', '_info.json')}")
        print(f"   文件数量: {len(packager.package_info['files'])}")
        print(f"   排除文件: {len(packager.package_info.get('excluded', []))}")
        
        # 显示校验和
        checksums = packager.package_info.get("checksums", {})
        if checksums:
            print(f"\n🔐 校验和:")
            print(f"   SHA256: {checksums.get('sha256', 'N/A')}")
            print(f"   文件大小: {checksums.get('size', 0) / 1024 / 1024:.2f} MB")
    else:
        print("\n❌ 打包失败")
        sys.exit(1)

if __name__ == "__main__":
    main()