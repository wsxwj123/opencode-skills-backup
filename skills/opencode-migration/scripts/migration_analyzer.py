#!/usr/bin/env python3
"""
OpenCode 迁移分析器
分析当前 OpenCode 配置，生成迁移报告
"""

import os
import json
import sys
import platform
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

class MigrationAnalyzer:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.home_dir = Path.home()
        self.opencode_config_dir = self.home_dir / ".config" / "opencode"
        self.report = {
            "analysis_time": datetime.now().isoformat(),
            "source_platform": self._get_platform_info(),
            "opencode_config": {},
            "mcp_servers": [],
            "skills": [],
            "dependencies": [],
            "issues": [],
            "recommendations": []
        }
    
    def _get_platform_info(self) -> Dict[str, str]:
        """获取平台信息"""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
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
                    elif "BuildVersion:" in line:
                        info["macos_build"] = line.split(":")[1].strip()
            except:
                pass
        
        return info
    
    def analyze_opencode_config(self) -> bool:
        """分析 OpenCode 配置"""
        try:
            # 检查配置目录
            if not self.opencode_config_dir.exists():
                self.report["issues"].append(f"OpenCode 配置目录不存在: {self.opencode_config_dir}")
                return False
            
            # 读取主配置文件
            config_file = self.opencode_config_dir / "opencode.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.report["opencode_config"] = {
                    "file": str(config_file),
                    "model": config.get("model", "unknown"),
                    "plugins": config.get("plugin", []),
                    "mcp_count": len(config.get("mcp", {})),
                    "provider_count": len(config.get("provider", {}))
                }
            else:
                self.report["issues"].append(f"主配置文件不存在: {config_file}")
            
            # 分析技能目录
            skills_dir = self.opencode_config_dir / "skills"
            if skills_dir.exists():
                skills = []
                for item in skills_dir.iterdir():
                    if item.is_dir():
                        skill_info = {
                            "name": item.name,
                            "has_skill_md": (item / "SKILL.md").exists(),
                            "file_count": len(list(item.glob("**/*")))
                        }
                        skills.append(skill_info)
                
                self.report["skills"] = {
                    "directory": str(skills_dir),
                    "count": len(skills),
                    "skills": skills[:10]  # 只显示前10个
                }
            
            # 分析 MCP 服务器
            self._analyze_mcp_servers()
            
            # 分析依赖
            self._analyze_dependencies()
            
            return True
            
        except Exception as e:
            self.report["issues"].append(f"分析配置时出错: {str(e)}")
            return False
    
    def _analyze_mcp_servers(self):
        """分析 MCP 服务器配置"""
        try:
            config_file = self.opencode_config_dir / "opencode.json"
            if not config_file.exists():
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            mcp_configs = config.get("mcp", {})
            mcp_servers = []
            
            for name, mcp_config in mcp_configs.items():
                server_info = {
                    "name": name,
                    "enabled": mcp_config.get("enabled", False),
                    "type": mcp_config.get("type", "unknown")
                }
                
                # 分析命令
                command = mcp_config.get("command", [])
                if command:
                    server_info["command"] = " ".join(command)
                    
                    # 检查命令可执行性
                    if command[0] in ["npx", "node", "python", "python3", "uv"]:
                        server_info["runtime"] = command[0]
                    
                    # 检查路径
                    for part in command:
                        if "/" in part and Path(part).exists():
                            server_info["has_local_path"] = True
                            server_info["local_path"] = part
                
                # 检查环境变量
                env = mcp_config.get("environment", {})
                if env:
                    server_info["has_environment"] = True
                    server_info["env_keys"] = list(env.keys())
                
                mcp_servers.append(server_info)
            
            self.report["mcp_servers"] = mcp_servers
            
        except Exception as e:
            self.report["issues"].append(f"分析 MCP 服务器时出错: {str(e)}")
    
    def _analyze_dependencies(self):
        """分析系统依赖"""
        dependencies = []
        
        # 检查 Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                dependencies.append({
                    "name": "Node.js",
                    "version": result.stdout.strip(),
                    "status": "installed"
                })
        except:
            dependencies.append({
                "name": "Node.js",
                "version": "unknown",
                "status": "not_installed"
            })
        
        # 检查 Python
        try:
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                dependencies.append({
                    "name": "Python 3",
                    "version": result.stdout.strip(),
                    "status": "installed"
                })
        except:
            dependencies.append({
                "name": "Python 3",
                "version": "unknown",
                "status": "not_installed"
            })
        
        # 检查 Git
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                dependencies.append({
                    "name": "Git",
                    "version": result.stdout.strip(),
                    "status": "installed"
                })
        except:
            dependencies.append({
                "name": "Git",
                "version": "unknown",
                "status": "not_installed"
            })
        
        # 检查 npm/npx
        try:
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                dependencies.append({
                    "name": "npm",
                    "version": result.stdout.strip(),
                    "status": "installed"
                })
        except:
            dependencies.append({
                "name": "npm",
                "version": "unknown",
                "status": "not_installed"
            })
        
        self.report["dependencies"] = dependencies
    
    def generate_recommendations(self):
        """生成迁移建议"""
        recommendations = []
        
        # 平台相关建议
        source_platform = self.report["source_platform"]
        if source_platform["system"] == "Darwin":
            if "arm" in source_platform["machine"].lower():
                recommendations.append("源设备为 Apple Silicon (ARM)，迁移到 Intel Mac 需要 Rosetta 2")
                recommendations.append("迁移到 Windows 需要 WSL2 或原生 Windows 适配")
            else:
                recommendations.append("源设备为 Intel Mac，迁移到 Apple Silicon 需要 Universal Binary 支持")
        
        # MCP 服务器建议
        for server in self.report["mcp_servers"]:
            if server.get("has_local_path"):
                recommendations.append(f"MCP 服务器 '{server['name']}' 使用本地路径，需要确保目标设备有相同路径")
            if server.get("has_environment"):
                recommendations.append(f"MCP 服务器 '{server['name']}' 需要环境变量，需要在目标设备上设置")
        
        # 依赖建议
        missing_deps = [d for d in self.report["dependencies"] if d["status"] == "not_installed"]
        if missing_deps:
            recommendations.append(f"缺少依赖: {', '.join([d['name'] for d in missing_deps])}")
        
        self.report["recommendations"] = recommendations
    
    def save_report(self, output_file: Optional[str] = None):
        """保存分析报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"migration_analysis_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        print(f"分析报告已保存到: {output_file}")
        return output_file
    
    def print_summary(self):
        """打印分析摘要"""
        print("\n" + "="*60)
        print("OpenCode 迁移分析报告")
        print("="*60)
        
        print(f"\n📊 分析时间: {self.report['analysis_time']}")
        
        # 平台信息
        platform_info = self.report["source_platform"]
        print(f"\n💻 源平台: {platform_info.get('system', 'Unknown')} {platform_info.get('release', '')}")
        if "macos_name" in platform_info:
            print(f"   macOS: {platform_info['macos_name']} {platform_info['macos_version']}")
        print(f"   架构: {platform_info.get('machine', 'Unknown')}")
        
        # OpenCode 配置
        config = self.report.get("opencode_config", {})
        if config:
            print(f"\n⚙️  OpenCode 配置:")
            print(f"   配置文件: {config.get('file', 'Unknown')}")
            print(f"   模型: {config.get('model', 'Unknown')}")
            print(f"   插件: {len(config.get('plugins', []))} 个")
            print(f"   MCP 服务器: {config.get('mcp_count', 0)} 个")
            print(f"   提供商: {config.get('provider_count', 0)} 个")
        
        # 技能
        skills = self.report.get("skills", {})
        if skills:
            print(f"\n📚 技能库:")
            print(f"   目录: {skills.get('directory', 'Unknown')}")
            print(f"   技能数量: {skills.get('count', 0)}")
        
        # MCP 服务器
        mcp_servers = self.report.get("mcp_servers", [])
        if mcp_servers:
            print(f"\n🔌 MCP 服务器 ({len(mcp_servers)} 个):")
            for server in mcp_servers[:5]:  # 只显示前5个
                status = "✅ 启用" if server.get("enabled") else "❌ 禁用"
                print(f"   • {server['name']} - {status}")
            if len(mcp_servers) > 5:
                print(f"   ... 还有 {len(mcp_servers) - 5} 个服务器")
        
        # 依赖
        dependencies = self.report.get("dependencies", [])
        if dependencies:
            print(f"\n📦 系统依赖:")
            for dep in dependencies:
                status = "✅" if dep["status"] == "installed" else "❌"
                print(f"   {status} {dep['name']}: {dep['version']}")
        
        # 问题
        issues = self.report.get("issues", [])
        if issues:
            print(f"\n⚠️  发现问题 ({len(issues)} 个):")
            for issue in issues[:3]:  # 只显示前3个
                print(f"   • {issue}")
            if len(issues) > 3:
                print(f"   ... 还有 {len(issues) - 3} 个问题")
        
        # 建议
        recommendations = self.report.get("recommendations", [])
        if recommendations:
            print(f"\n💡 迁移建议 ({len(recommendations)} 条):")
            for rec in recommendations[:3]:  # 只显示前3个
                print(f"   • {rec}")
            if len(recommendations) > 3:
                print(f"   ... 还有 {len(recommendations) - 3} 条建议")
        
        print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description="OpenCode 迁移分析器")
    parser.add_argument("--analyze", action="store_true", help="执行迁移分析")
    parser.add_argument("--detailed", action="store_true", help="生成详细报告")
    parser.add_argument("--output", type=str, help="输出报告文件路径")
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    if not args.analyze and not args.detailed:
        parser.print_help()
        return
    
    print("🔍 开始分析 OpenCode 配置...")
    
    analyzer = MigrationAnalyzer(verbose=args.verbose)
    
    if analyzer.analyze_opencode_config():
        analyzer.generate_recommendations()
        analyzer.print_summary()
        
        if args.output or args.detailed:
            output_file = analyzer.save_report(args.output)
            print(f"\n📄 详细报告已保存到: {output_file}")
    else:
        print("❌ 分析失败，请检查错误信息")
        for issue in analyzer.report.get("issues", []):
            print(f"   • {issue}")
        sys.exit(1)

if __name__ == "__main__":
    main()