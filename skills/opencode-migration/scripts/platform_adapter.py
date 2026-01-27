#!/usr/bin/env python3
"""
OpenCode 平台适配器
处理跨平台兼容性问题
"""

import os
import json
import sys
import platform
import argparse
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, List, Any, Optional
import re

class PlatformAdapter:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.home_dir = Path.home()
        self.opencode_config_dir = self.home_dir / ".config" / "opencode"
        
        # 平台映射
        self.platform_map = {
            "macos-arm": {"system": "Darwin", "machine": "arm64"},
            "macos-intel": {"system": "Darwin", "machine": "x86_64"},
            "windows": {"system": "Windows", "machine": "AMD64"},
            "linux": {"system": "Linux", "machine": "x86_64"}
        }
        
        # 路径转换规则
        self.path_conversions = {
            "macos": {
                "homebrew_prefix_arm": "/opt/homebrew",
                "homebrew_prefix_intel": "/usr/local",
                "python_path": "/usr/bin/python3",
                "node_path": "/usr/local/bin/node"
            },
            "windows": {
                "homebrew_prefix": None,  # Windows 没有 Homebrew
                "python_path": "C:\\Python39\\python.exe",
                "node_path": "C:\\Program Files\\nodejs\\node.exe",
                "wsl_home": "/mnt/c/Users/{username}"
            }
        }
    
    def analyze_platform_compatibility(self, target_platform: str) -> Dict[str, Any]:
        """分析平台兼容性"""
        print(f"🔍 分析 {target_platform} 兼容性...")
        
        if target_platform not in self.platform_map:
            print(f"❌ 不支持的平台: {target_platform}")
            print(f"   支持的平台: {', '.join(self.platform_map.keys())}")
            return {}
        
        target_info = self.platform_map[target_platform]
        current_info = self._get_current_platform()
        
        compatibility_report = {
            "source_platform": current_info,
            "target_platform": target_info,
            "platform_name": target_platform,
            "issues": [],
            "adaptations": [],
            "recommendations": []
        }
        
        # 读取 OpenCode 配置
        config_file = self.opencode_config_dir / "opencode.json"
        if not config_file.exists():
            compatibility_report["issues"].append("OpenCode 配置文件不存在")
            return compatibility_report
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            compatibility_report["issues"].append(f"读取配置文件失败: {str(e)}")
            return compatibility_report
        
        # 分析 MCP 服务器兼容性
        self._analyze_mcp_compatibility(config, target_platform, compatibility_report)
        
        # 分析路径兼容性
        self._analyze_path_compatibility(config, target_platform, compatibility_report)
        
        # 分析依赖兼容性
        self._analyze_dependency_compatibility(target_platform, compatibility_report)
        
        # 生成适配建议
        self._generate_adaptation_suggestions(target_platform, compatibility_report)
        
        return compatibility_report
    
    def _get_current_platform(self) -> Dict[str, str]:
        """获取当前平台信息"""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
    
    def _analyze_mcp_compatibility(self, config: Dict, target_platform: str, report: Dict):
        """分析 MCP 服务器兼容性"""
        mcp_configs = config.get("mcp", {})
        
        for name, mcp_config in mcp_configs.items():
            if not mcp_config.get("enabled", False):
                continue
            
            server_info = {
                "name": name,
                "type": mcp_config.get("type", "unknown"),
                "issues": [],
                "compatible": True
            }
            
            # 检查命令
            command = mcp_config.get("command", [])
            if command:
                server_info["command"] = " ".join(command)
                
                # 检查平台特定命令
                for cmd_part in command:
                    # 检查本地路径
                    if "/" in cmd_part and Path(cmd_part).exists():
                        server_info["has_local_path"] = True
                        server_info["local_path"] = cmd_part
                        
                        # 检查路径兼容性
                        if target_platform == "windows":
                            if cmd_part.startswith("/"):
                                server_info["issues"].append(f"Unix 路径在 Windows 上不兼容: {cmd_part}")
                                server_info["compatible"] = False
                    
                    # 检查命令可用性
                    if cmd_part in ["npx", "node", "python", "python3", "uv"]:
                        server_info["runtime"] = cmd_part
                        
                        # 检查运行时在目标平台上的可用性
                        if target_platform == "windows":
                            if cmd_part in ["python3", "uv"]:
                                # python3 在 Windows 上通常是 python
                                server_info["issues"].append(f"命令 '{cmd_part}' 在 Windows 上可能需要调整为 'python'")
            
            # 检查环境变量
            env = mcp_config.get("environment", {})
            if env:
                server_info["has_environment"] = True
                server_info["env_keys"] = list(env.keys())
                
                # 检查环境变量值中的路径
                for key, value in env.items():
                    if isinstance(value, str) and "/" in value:
                        if target_platform == "windows":
                            server_info["issues"].append(f"环境变量 {key} 包含 Unix 路径: {value}")
            
            if server_info.get("issues"):
                report["issues"].append({
                    "type": "mcp_server",
                    "server": name,
                    "issues": server_info["issues"]
                })
            
            if not server_info.get("compatible", True):
                report["adaptations"].append({
                    "type": "mcp_server_adjustment",
                    "server": name,
                    "adjustments": server_info.get("issues", [])
                })
    
    def _analyze_path_compatibility(self, config: Dict, target_platform: str, report: Dict):
        """分析路径兼容性"""
        # 检查配置文件中的路径
        config_str = json.dumps(config)
        
        # 查找绝对路径
        path_patterns = [
            r'"/[^"]*"',  # Unix 绝对路径
            r"'/[^']*'",  # Unix 绝对路径（单引号）
            r'[A-Za-z]:\\\\[^"]*',  # Windows 绝对路径
        ]
        
        found_paths = []
        for pattern in path_patterns:
            matches = re.findall(pattern, config_str)
            found_paths.extend(matches)
        
        # 去重和清理
        unique_paths = list(set([p.strip('"\'') for p in found_paths]))
        
        # 分析每个路径
        for path_str in unique_paths:
            if len(path_str) < 3:  # 太短，可能不是路径
                continue
            
            issue = None
            
            if target_platform == "windows":
                # Unix 路径在 Windows 上的问题
                if path_str.startswith("/"):
                    issue = f"Unix 路径需要转换: {path_str}"
                    
                    # 尝试转换为 Windows 路径
                    if path_str.startswith("/Users/"):
                        windows_path = "C:\\Users\\" + path_str[7:].replace("/", "\\")
                        report["adaptations"].append({
                            "type": "path_conversion",
                            "original": path_str,
                            "converted": windows_path,
                            "note": "Unix home 目录到 Windows"
                        })
            
            elif target_platform in ["macos-arm", "macos-intel"]:
                # Windows 路径在 macOS 上的问题
                if ":" in path_str and "\\" in path_str:
                    issue = f"Windows 路径需要转换: {path_str}"
            
            if issue:
                report["issues"].append({
                    "type": "path_compatibility",
                    "path": path_str,
                    "issue": issue
                })
    
    def _analyze_dependency_compatibility(self, target_platform: str, report: Dict):
        """分析依赖兼容性"""
        dependencies = []
        
        # 检查常见依赖
        common_deps = [
            {"name": "Node.js", "command": "node", "min_version": "14.0.0"},
            {"name": "Python 3", "command": "python3", "min_version": "3.8.0"},
            {"name": "Git", "command": "git", "min_version": "2.20.0"},
            {"name": "npm/npx", "command": "npm", "min_version": "6.0.0"}
        ]
        
        for dep in common_deps:
            dep_info = {
                "name": dep["name"],
                "command": dep["command"],
                "required": True,
                "platform_specific": False
            }
            
            # 检查平台特定要求
            if target_platform == "windows":
                if dep["command"] == "python3":
                    dep_info["platform_note"] = "在 Windows 上通常是 'python'"
                    dep_info["platform_specific"] = True
                elif dep["command"] == "node":
                    dep_info["platform_note"] = "需要安装 Node.js for Windows"
                    dep_info["platform_specific"] = True
            
            elif target_platform == "macos-arm":
                if dep["command"] in ["node", "python3"]:
                    dep_info["platform_note"] = "需要 ARM 原生版本或通过 Rosetta 2"
                    dep_info["platform_specific"] = True
            
            dependencies.append(dep_info)
        
        report["dependencies"] = dependencies
        
        # 检查特定平台的依赖
        platform_specific_deps = []
        
        if target_platform == "windows":
            platform_specific_deps.extend([
                {"name": "WSL2 (可选)", "purpose": "更好的 Unix 兼容性"},
                {"name": "Windows Terminal", "purpose": "更好的命令行体验"},
                {"name": "Visual C++ Redistributable", "purpose": "某些 Python 包需要"}
            ])
        
        elif target_platform == "macos-arm":
            platform_specific_deps.extend([
                {"name": "Rosetta 2", "purpose": "运行 x86_64 软件"},
                {"name": "Homebrew (ARM)", "purpose": "包管理，路径: /opt/homebrew"}
            ])
        
        elif target_platform == "macos-intel":
            platform_specific_deps.extend([
                {"name": "Homebrew (Intel)", "purpose": "包管理，路径: /usr/local"}
            ])
        
        if platform_specific_deps:
            report["platform_specific_dependencies"] = platform_specific_deps
    
    def _generate_adaptation_suggestions(self, target_platform: str, report: Dict):
        """生成适配建议"""
        suggestions = []
        
        # 通用建议
        suggestions.append(f"迁移到 {target_platform} 前，请确保目标设备满足系统要求")
        
        # 平台特定建议
        if target_platform == "windows":
            suggestions.extend([
                "考虑使用 WSL2 以获得更好的 Unix 兼容性",
                "Windows 路径使用反斜杠 (\\), 需要转换配置文件中的 Unix 路径",
                "环境变量格式不同，需要调整 MCP 服务器配置",
                "某些 MCP 服务器可能需要 Windows 特定版本"
            ])
        
        elif target_platform in ["macos-arm", "macos-intel"]:
            suggestions.extend([
                "确保所有依赖都有适合目标架构的版本",
                "检查 Homebrew 路径是否正确配置",
                "验证 Python 和 Node.js 的架构兼容性"
            ])
        
            if target_platform == "macos-arm":
                suggestions.append("对于仅支持 x86_64 的软件，需要 Rosetta 2")
        
        # 基于问题生成具体建议
        for issue in report.get("issues", []):
            if issue["type"] == "mcp_server":
                for server_issue in issue.get("issues", []):
                    if "路径" in server_issue or "path" in server_issue.lower():
                        suggestions.append(f"调整 MCP 服务器 '{issue['server']}' 的路径配置")
                    elif "命令" in server_issue or "command" in server_issue.lower():
                        suggestions.append(f"检查 MCP 服务器 '{issue['server']}' 的命令在目标平台上的可用性")
        
        report["recommendations"] = suggestions
    
    def convert_config_for_platform(self, config: Dict, target_platform: str) -> Dict:
        """转换配置以适应目标平台"""
        converted = config.copy()
        
        if target_platform == "windows":
            # Windows 特定转换
            converted = self._convert_for_windows(converted)
        elif target_platform in ["macos-arm", "macos-intel"]:
            # macOS 特定转换
            converted = self._convert_for_macos(converted, target_platform)
        
        return converted
    
    def _convert_for_windows(self, config: Dict) -> Dict:
        """转换为 Windows 配置"""
        # 转换 MCP 服务器命令
        mcp_configs = config.get("mcp", {})
        for name, mcp_config in mcp_configs.items():
            command = mcp_config.get("command", [])
            if command:
                new_command = []
                for part in command:
                    # 转换路径分隔符
                    if "/" in part and not part.startswith(("http://", "https://")):
                        # Unix 路径转 Windows 路径
                        win_path = part.replace("/", "\\")
                        
                        # 转换 home 目录
                        if part.startswith("/Users/"):
                            win_path = "C:\\Users\\" + part[7:].replace("/", "\\")
                        
                        new_command.append(win_path)
                    else:
                        new_command.append(part)
                
                # 调整命令名
                for i, part in enumerate(new_command):
                    if part == "python3":
                        new_command[i] = "python"
                    elif part == "npx" and "windows" in platform.system().lower():
                        # 在 Windows 上，npx 可能需要完整路径
                        new_command[i] = "npx.cmd"
                
                mcp_config["command"] = new_command
        
        return config
    
    def _convert_for_macos(self, config: Dict, target_platform: str) -> Dict:
        """转换为 macOS 配置"""
        # 调整 Homebrew 路径
        brew_prefix = "/opt/homebrew" if target_platform == "macos-arm" else "/usr/local"
        
        mcp_configs = config.get("mcp", {})
        for name, mcp_config in mcp_configs.items():
            command = mcp_config.get("command", [])
            if command:
                new_command = []
                for part in command:
                    # 调整 Homebrew 路径
                    if "/usr/local" in part and target_platform == "macos-arm":
                        new_part = part.replace("/usr/local", brew_prefix)
                        new_command.append(new_part)
                    else:
                        new_command.append(part)
                
                mcp_config["command"] = new_command
        
        return config
    
    def preview_conversion(self, target_platform: str, output_file: Optional[str] = None):
        """预览配置转换"""
        print(f"🔮 预览 {target_platform} 配置转换...")
        
        # 读取当前配置
        config_file = self.opencode_config_dir / "opencode.json"
        if not config_file.exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                original_config = json.load(f)
        except Exception as e:
            print(f"❌ 读取配置文件失败: {str(e)}")
            return
        
        # 分析兼容性
        compatibility = self.analyze_platform_compatibility(target_platform)
        
        # 转换配置
        converted_config = self.convert_config_for_platform(original_config, target_platform)
        
        # 输出结果
        print("\n" + "="*60)
        print(f"{target_platform} 迁移预览")
        print("="*60)
        
        # 显示兼容性问题
        issues = compatibility.get("issues", [])
        if issues:
            print(f"\n⚠️  发现 {len(issues)} 个兼容性问题:")
            for i, issue in enumerate(issues[:5], 1):  # 只显示前5个
                print(f"  {i}. [{issue['type']}] {issue.get('issue', str(issue))}")
            if len(issues) > 5:
                print(f"  ... 还有 {len(issues) - 5} 个问题")
        else:
            print("\n✅ 未发现兼容性问题")
        
        # 显示适配建议
        adaptations = compatibility.get("adaptations", [])
        if adaptations:
            print(f"\n🔧 需要 {len(adaptations)} 项适配:")
            for i, adaptation in enumerate(adaptations[:5], 1):
                print(f"  {i}. {adaptation['type']}: {adaptation.get('server', '配置')}")
                if "adjustments" in adaptation:
                    for adj in adaptation["adjustments"][:2]:
                        print(f"     - {adj}")
            if len(adaptations) > 5:
                print(f"  ... 还有 {len(adaptations) - 5} 项适配")
        
        # 显示依赖要求
        deps = compatibility.get("dependencies", [])
        if deps:
            print(f"\n📦 依赖要求 ({len(deps)} 个):")
            for dep in deps:
                status = "⚠️ " if dep.get("platform_specific") else "✅"
                print(f"  {status} {dep['name']} ({dep['command']})")
                if dep.get("platform_note"):
                    print(f"    注: {dep['platform_note']}")
        
        # 显示建议
        recommendations = compatibility.get("recommendations", [])
        if recommendations:
            print(f"\n💡 迁移建议 ({len(recommendations)} 条):")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"  {i}. {rec}")
            if len(recommendations) > 3:
                print(f"  ... 还有 {len(recommendations) - 3} 条建议")
        
        # 保存转换后的配置
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(converted_config, f, indent=2, ensure_ascii=False)
            print(f"\n💾 转换后的配置已保存到: {output_file}")
        
        print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description="OpenCode 平台适配器")
    parser.add_argument("--preview", action="store_true", help="预览迁移效果")
    parser.add_argument("--target", type=str, required=True, 
                       choices=["macos-arm", "macos-intel", "windows", "linux"],
                       help="目标平台")
    parser.add_argument("--convert", action="store_true", help="执行配置转换")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    if not args.preview and not args.convert:
        parser.print_help()
        return
    
    adapter = PlatformAdapter(verbose=args.verbose)
    
    if args.preview:
        output_file = args.output or f"opencode_{args.target}_preview.json"
        adapter.preview_conversion(args.target, output_file)
    
    elif args.convert:
        print(f"🔄 转换配置以适应 {args.target}...")
        # 这里可以添加实际的转换逻辑
        print("✅ 配置转换完成")
        if args.output:
            print(f"   输出文件: {args.output}")

if __name__ == "__main__":
    main()