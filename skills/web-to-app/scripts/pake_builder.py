#!/usr/bin/env python3
"""
Pake 构建器脚本 - 使用 Pake 将网页转换为桌面应用
支持 macOS、Windows 和 Linux
"""

import os
import sys
import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

class PakeBuilder:
    """Pake 构建器类"""
    
    def __init__(self, work_dir: str = None):
        """
        初始化 Pake 构建器
        
        Args:
            work_dir: 工作目录，如果为 None 则使用临时目录
        """
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="pake_build_")
        self.pake_cli_installed = False
        
    def check_environment(self) -> bool:
        """检查环境是否满足要求"""
        try:
            # 检查 Node.js
            result = subprocess.run(["node", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Node.js 未安装")
                return False
            
            # 检查 pnpm
            result = subprocess.run(["pnpm", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("⚠️ pnpm 未安装，尝试使用 npm")
                # 检查 npm
                result = subprocess.run(["npm", "--version"], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print("❌ npm 也未安装")
                    return False
            
            # 检查 Rust (可选，用于本地开发)
            try:
                subprocess.run(["rustc", "--version"], 
                             capture_output=True, text=True, check=False)
            except:
                print("⚠️ Rust 未安装，将使用在线构建或 CLI 工具")
            
            return True
            
        except Exception as e:
            print(f"❌ 环境检查失败: {e}")
            return False
    
    def install_pake_cli(self) -> bool:
        """安装 Pake CLI 工具"""
        try:
            print("📦 正在安装 Pake CLI...")
            
            # 尝试使用 pnpm 安装
            try:
                subprocess.run(["pnpm", "install", "-g", "pake-cli"], 
                             check=True, capture_output=True, text=True)
                print("✅ Pake CLI 安装成功 (使用 pnpm)")
                self.pake_cli_installed = True
                return True
            except:
                # 尝试使用 npm 安装
                try:
                    subprocess.run(["npm", "install", "-g", "pake-cli"], 
                                 check=True, capture_output=True, text=True)
                    print("✅ Pake CLI 安装成功 (使用 npm)")
                    self.pake_cli_installed = True
                    return True
                except Exception as e:
                    print(f"❌ Pake CLI 安装失败: {e}")
                    return False
                    
        except Exception as e:
            print(f"❌ 安装过程出错: {e}")
            return False
    
    def build_with_cli(self, url: str, config: Dict[str, Any]) -> Optional[str]:
        """
        使用 Pake CLI 构建应用
        
        Args:
            url: 网页URL
            config: 配置参数
            
        Returns:
            构建的应用路径或 None
        """
        try:
            if not self.pake_cli_installed:
                if not self.install_pake_cli():
                    return None
            
            # 构建命令
            cmd = ["pake", url]
            
            # 添加参数
            if "name" in config:
                cmd.extend(["--name", config["name"]])
            
            if "icon" in config:
                cmd.extend(["--icon", config["icon"]])
            
            if "width" in config:
                cmd.extend(["--width", str(config["width"])])
            
            if "height" in config:
                cmd.extend(["--height", str(config["height"])])
            
            if config.get("hide_title_bar", False):
                cmd.append("--hide-title-bar")
            
            if config.get("fullscreen", False):
                cmd.append("--fullscreen")
            
            if config.get("transparent", False):
                cmd.append("--transparent")
            
            # 设置输出目录
            output_dir = config.get("output_dir", self.work_dir)
            cmd.extend(["--output", output_dir])
            
            print(f"🚀 正在构建应用: {' '.join(cmd)}")
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.work_dir)
            
            if result.returncode == 0:
                print("✅ 应用构建成功")
                
                # 查找生成的应用文件
                app_name = config.get("name", "app")
                for ext in [".dmg", ".app", ".exe", ".msi", ".deb", ".AppImage"]:
                    app_path = os.path.join(output_dir, f"{app_name}{ext}")
                    if os.path.exists(app_path):
                        return app_path
                
                # 如果没有找到特定扩展名的文件，查找任何新文件
                for file in os.listdir(output_dir):
                    if file.endswith((".dmg", ".app", ".exe", ".msi", ".deb", ".AppImage")):
                        return os.path.join(output_dir, file)
                
                print("⚠️ 未找到生成的应用文件")
                return None
            else:
                print(f"❌ 构建失败: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ 构建过程出错: {e}")
            return None
    
    def build_with_github_actions(self, url: str, config: Dict[str, Any]) -> Optional[str]:
        """
        使用 GitHub Actions 在线构建（无需本地环境）
        
        Args:
            url: 网页URL
            config: 配置参数
            
        Returns:
            下载链接或 None
        """
        try:
            print("🌐 使用 GitHub Actions 在线构建...")
            
            # 这里可以集成 GitHub Actions API
            # 实际实现需要创建 GitHub workflow 文件并触发 Actions
            
            # 简化版本：提供用户手动操作的指导
            print("📋 请按照以下步骤操作：")
            print("1. 访问 https://github.com/tw93/Pake")
            print("2. 点击 'Use this template' 创建新仓库")
            print("3. 在仓库设置中启用 Actions")
            print("4. 修改 .github/workflows/build.yml 中的配置")
            print(f"5. 将 URL 设置为: {url}")
            print(f"6. 应用名称: {config.get('name', 'MyApp')}")
            print("7. 手动触发 Actions 运行")
            
            return "https://github.com/tw93/Pake/actions"
            
        except Exception as e:
            print(f"❌ 在线构建配置失败: {e}")
            return None
    
    def create_config_file(self, url: str, config: Dict[str, Any]) -> str:
        """
        创建 Pake 配置文件
        
        Args:
            url: 网页URL
            config: 配置参数
            
        Returns:
            配置文件路径
        """
        config_data = {
            "url": url,
            "name": config.get("name", "MyApp"),
            "icon": config.get("icon", ""),
            "width": config.get("width", 1200),
            "height": config.get("height", 800),
            "transparent": config.get("transparent", False),
            "resizable": config.get("resizable", True),
            "fullscreen": config.get("fullscreen", False),
            "user_agent": config.get("user_agent", ""),
            "injections": config.get("injections", []),
        }
        
        config_path = os.path.join(self.work_dir, "pake.config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        return config_path
    
    def cleanup(self):
        """清理临时文件"""
        if os.path.exists(self.work_dir) and self.work_dir.startswith(tempfile.gettempdir()):
            try:
                shutil.rmtree(self.work_dir)
                print(f"🧹 已清理临时目录: {self.work_dir}")
            except:
                pass

def main():
    """主函数 - 测试用"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pake 构建器")
    parser.add_argument("url", help="要转换的网页URL")
    parser.add_argument("--name", default="MyApp", help="应用名称")
    parser.add_argument("--output", default=".", help="输出目录")
    parser.add_argument("--width", type=int, default=1200, help="窗口宽度")
    parser.add_argument("--height", type=int, default=800, help="窗口高度")
    
    args = parser.parse_args()
    
    # 创建构建器
    builder = PakeBuilder()
    
    # 检查环境
    if not builder.check_environment():
        print("❌ 环境检查失败，请安装必要的依赖")
        sys.exit(1)
    
    # 配置参数
    config = {
        "name": args.name,
        "output_dir": args.output,
        "width": args.width,
        "height": args.height,
        "hide_title_bar": False,
        "transparent": False,
    }
    
    # 构建应用
    app_path = builder.build_with_cli(args.url, config)
    
    if app_path:
        print(f"🎉 应用构建完成: {app_path}")
    else:
        print("❌ 应用构建失败")
        # 尝试在线构建
        online_url = builder.build_with_github_actions(args.url, config)
        if online_url:
            print(f"🔗 在线构建链接: {online_url}")
    
    # 清理
    builder.cleanup()

if __name__ == "__main__":
    main()