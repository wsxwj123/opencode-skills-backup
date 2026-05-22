#!/usr/bin/env python3
"""
平台检测器 - 检测目标平台并选择最佳构建工具
"""

import platform
import sys
from typing import Dict, Any, List, Optional

class PlatformDetector:
    """平台检测器类"""
    
    def __init__(self):
        """初始化平台检测器"""
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.version = platform.version()
        
    def detect_current_platform(self) -> Dict[str, Any]:
        """
        检测当前平台信息
        
        Returns:
            平台信息字典
        """
        info = {
            "system": self.system,
            "machine": self.machine,
            "version": self.version,
            "python_version": sys.version,
            "platform": self._get_platform_name(),
            "architecture": self._get_architecture(),
            "can_build": self._get_buildable_platforms()
        }
        
        return info
    
    def _get_platform_name(self) -> str:
        """获取平台名称"""
        if self.system == "darwin":
            return "macOS"
        elif self.system == "windows":
            return "Windows"
        elif self.system == "linux":
            return "Linux"
        else:
            return "Unknown"
    
    def _get_architecture(self) -> str:
        """获取架构信息"""
        if "x86_64" in self.machine or "amd64" in self.machine:
            return "x86_64"
        elif "arm64" in self.machine or "aarch64" in self.machine:
            return "ARM64"
        elif "arm" in self.machine:
            return "ARM"
        else:
            return self.machine
    
    def _get_buildable_platforms(self) -> List[str]:
        """获取当前平台可以构建的目标平台"""
        buildable = []
        
        if self.system == "darwin":
            # macOS 可以构建 macOS、iOS 和 Web
            buildable.extend(["macos", "ios", "pwa"])
            # 通过交叉编译可以构建其他平台（需要额外配置）
            buildable.extend(["windows", "linux", "android"])
        elif self.system == "windows":
            # Windows 可以构建 Windows、Android 和 Web
            buildable.extend(["windows", "android", "pwa"])
            # 通过交叉编译可以构建其他平台
            buildable.extend(["linux"])
        elif self.system == "linux":
            # Linux 可以构建 Linux、Android 和 Web
            buildable.extend(["linux", "android", "pwa"])
            # 通过交叉编译可以构建其他平台
            buildable.extend(["windows"])
        
        return buildable
    
    def recommend_tool(self, target_platform: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据目标平台和需求推荐最佳工具
        
        Args:
            target_platform: 目标平台 (macos, windows, linux, ios, android, pwa)
            requirements: 需求字典（如性能、离线支持、大小限制等）
            
        Returns:
            推荐结果
        """
        recommendation = {
            "target_platform": target_platform,
            "recommended_tool": None,
            "alternative_tools": [],
            "reasons": [],
            "requirements_met": {},
            "trade_offs": []
        }
        
        # 桌面平台推荐
        if target_platform in ["macos", "windows", "linux"]:
            recommendation["recommended_tool"] = "pake"
            recommendation["reasons"].extend([
                "Pake 基于 Rust Tauri，性能优异",
                "体积小（约 5MB），比 Electron 小 20 倍",
                "内存占用低",
                "支持原生窗口功能",
                "一键命令打包，简单快捷"
            ])
            recommendation["alternative_tools"].append({
                "name": "Electron",
                "pros": ["成熟稳定", "社区庞大", "功能丰富"],
                "cons": ["体积大", "内存占用高"]
            })
            
            # 检查需求是否满足
            recommendation["requirements_met"]["size"] = "优秀（~5MB）"
            recommendation["requirements_met"]["performance"] = "优秀（Rust）"
            recommendation["requirements_met"]["native_features"] = "支持"
            
        # iOS 平台推荐
        elif target_platform == "ios":
            recommendation["recommended_tool"] = "pwabuilder"
            recommendation["reasons"].extend([
                "PWABuilder 支持生成 iOS 项目",
                "可以通过 Safari 直接添加到主屏幕",
                "支持 PWA 标准，无需原生开发",
                "可以提交到 App Store（需要 Xcode 项目）"
            ])
            recommendation["alternative_tools"].append({
                "name": "Native iOS",
                "pros": ["完全原生体验", "所有 iOS API"],
                "cons": ["开发成本高", "需要 Swift/Objective-C"]
            })
            
            recommendation["requirements_met"]["pwa_support"] = "完整"
            recommendation["requirements_met"]["app_store"] = "支持（需配置）"
            
        # Android 平台推荐
        elif target_platform == "android":
            recommendation["recommended_tool"] = "pwabuilder"
            recommendation["reasons"].extend([
                "PWABuilder 可以直接生成 Android APK",
                "基于 TWA (Trusted Web Activity) 技术",
                "无需 Android 开发经验",
                "自动处理图标和配置",
                "可以上传到 Google Play"
            ])
            recommendation["alternative_tools"].append({
                "name": "React Native",
                "pros": ["原生性能", "丰富的组件库"],
                "cons": ["需要学习框架", "开发成本高"]
            })
            
            recommendation["requirements_met"]["apk_generation"] = "直接支持"
            recommendation["requirements_met"]["play_store"] = "支持"
            
        # PWA 推荐
        elif target_platform == "pwa":
            recommendation["recommended_tool"] = "pwabuilder"
            recommendation["reasons"].extend([
                "PWABuilder 专为 PWA 设计",
                "自动生成 manifest 和 service worker",
                "支持离线功能",
                "跨平台兼容",
                "无需应用商店审核"
            ])
            recommendation["alternative_tools"].append({
                "name": "手动开发",
                "pros": ["完全控制", "自定义灵活"],
                "cons": ["开发复杂", "需要 PWA 知识"]
            })
            
            recommendation["requirements_met"]["offline"] = "支持"
            recommendation["requirements_met"]["install"] = "支持"
            recommendation["requirements_met"]["cross_platform"] = "完整"
        
        # 根据特殊需求调整推荐
        if requirements.get("offline_required", False):
            if target_platform in ["macos", "windows", "linux"]:
                recommendation["trade_offs"].append("Pake 自带离线支持")
            elif target_platform in ["ios", "android", "pwa"]:
                recommendation["trade_offs"].append("需要配置 Service Worker 实现离线功能")
        
        if requirements.get("size_limit"):
            limit = requirements["size_limit"]
            if target_platform in ["macos", "windows", "linux"]:
                recommendation["trade_offs"].append(f"Pake 约 5MB，满足 {limit}MB 限制")
            else:
                recommendation["trade_offs"].append(f"PWA 无安装包大小限制")
        
        if requirements.get("native_features"):
            features = requirements["native_features"]
            if target_platform in ["macos", "windows", "linux"]:
                recommendation["trade_offs"].append(f"Pake 支持大部分桌面原生功能")
            else:
                recommendation["trade_offs"].append(f"PWA 功能受浏览器 API 限制")
        
        return recommendation
    
    def get_build_strategy(self, target_platforms: List[str]) -> Dict[str, Any]:
        """
        获取多平台构建策略
        
        Args:
            target_platforms: 目标平台列表
            
        Returns:
            构建策略
        """
        strategy = {
            "platforms": target_platforms,
            "build_order": [],
            "tools_needed": set(),
            "parallel_possible": False,
            "estimated_time": "未知",
            "recommendations": []
        }
        
        # 分组平台
        desktop_platforms = [p for p in target_platforms if p in ["macos", "windows", "linux"]]
        mobile_platforms = [p for p in target_platforms if p in ["ios", "android"]]
        web_platforms = [p for p in target_platforms if p == "pwa"]
        
        # 制定构建顺序
        if web_platforms:
            strategy["build_order"].append({
                "step": 1,
                "platforms": web_platforms,
                "tool": "pwabuilder",
                "reason": "PWA 是基础，其他平台可以复用"
            })
            strategy["tools_needed"].add("pwabuilder")
        
        if desktop_platforms:
            strategy["build_order"].append({
                "step": 2,
                "platforms": desktop_platforms,
                "tool": "pake",
                "reason": "桌面平台可以并行构建"
            })
            strategy["tools_needed"].add("pake")
            if len(desktop_platforms) > 1:
                strategy["parallel_possible"] = True
        
        if mobile_platforms:
            strategy["build_order"].append({
                "step": 3,
                "platforms": mobile_platforms,
                "tool": "pwabuilder",
                "reason": "移动平台基于 PWA"
            })
            strategy["tools_needed"].add("pwabuilder")
        
        # 估算时间
        total_platforms = len(target_platforms)
        if total_platforms == 1:
            strategy["estimated_time"] = "5-15分钟"
        elif total_platforms <= 3:
            strategy["estimated_time"] = "15-30分钟"
        else:
            strategy["estimated_time"] = "30-60分钟"
        
        # 提供建议
        if len(desktop_platforms) > 1:
            strategy["recommendations"].append("桌面平台可以在同一台机器上并行构建")
        
        if mobile_platforms and not web_platforms:
            strategy["recommendations"].append("建议先创建 PWA，然后生成移动应用")
        
        if "macos" in target_platforms and self.system != "darwin":
            strategy["recommendations"].append("macOS 应用最好在 macOS 系统上构建，或使用 GitHub Actions")
        
        if "windows" in target_platforms and self.system != "windows":
            strategy["recommendations"].append("Windows 应用最好在 Windows 系统上构建，或使用 GitHub Actions")
        
        strategy["tools_needed"] = list(strategy["tools_needed"])
        
        return strategy
    
    def print_platform_info(self):
        """打印平台信息"""
        info = self.detect_current_platform()
        
        print("=" * 60)
        print("平台检测结果")
        print("=" * 60)
        print(f"当前系统: {info['platform']}")
        print(f"架构: {info['architecture']}")
        print(f"系统版本: {info['version']}")
        print(f"Python 版本: {info['python_version'].split()[0]}")
        print(f"\n可构建平台: {', '.join(info['can_build'])}")
        print("=" * 60)

def main():
    """主函数 - 测试用"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="平台检测器")
    parser.add_argument("--target", help="目标平台")
    parser.add_argument("--info", action="store_true", help="显示平台信息")
    parser.add_argument("--recommend", action="store_true", help="推荐工具")
    
    args = parser.parse_args()
    
    detector = PlatformDetector()
    
    if args.info:
        detector.print_platform_info()
    
    if args.recommend and args.target:
        requirements = {
            "offline_required": False,
            "size_limit": 50,
            "native_features": []
        }
        
        recommendation = detector.recommend_tool(args.target, requirements)
        
        print("\n" + "=" * 60)
        print(f"针对 {args.target} 平台的推荐")
        print("=" * 60)
        print(f"推荐工具: {recommendation['recommended_tool']}")
        print("\n推荐理由:")
        for reason in recommendation['reasons']:
            print(f"  • {reason}")
        
        if recommendation['alternative_tools']:
            print("\n备选工具:")
            for tool in recommendation['alternative_tools']:
                print(f"  {tool['name']}:")
                print(f"    优点: {', '.join(tool['pros'])}")
                print(f"    缺点: {', '.join(tool['cons'])}")
        
        print("\n需求满足情况:")
        for req, status in recommendation['requirements_met'].items():
            print(f"  {req}: {status}")
        
        print("=" * 60)
    
    if not (args.info or args.recommend):
        parser.print_help()

if __name__ == "__main__":
    main()
