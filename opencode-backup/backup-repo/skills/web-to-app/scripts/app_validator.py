#!/usr/bin/env python3
"""
应用验证器脚本 - 验证生成的应用程序是否完整、可用、无误
"""

import os
import sys
import json
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import zipfile
import tarfile

class AppValidator:
    """应用验证器类"""
    
    def __init__(self):
        """初始化应用验证器"""
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        
    def validate_desktop_app(self, app_path: str) -> Dict[str, Any]:
        """
        验证桌面应用程序
        
        Args:
            app_path: 应用文件路径
            
        Returns:
            验证结果
        """
        result = {
            "valid": False,
            "type": "unknown",
            "platform": self.system,
            "issues": [],
            "warnings": [],
            "suggestions": []
        }
        
        try:
            if not os.path.exists(app_path):
                result["issues"].append(f"文件不存在: {app_path}")
                return result
            
            # 获取文件信息
            file_size = os.path.getsize(app_path)
            result["file_size"] = f"{file_size / 1024 / 1024:.2f} MB"
            
            # 根据文件扩展名确定类型
            ext = os.path.splitext(app_path)[1].lower()
            
            if ext == ".dmg":
                result["type"] = "macos_dmg"
                result.update(self._validate_macos_dmg(app_path))
            elif ext == ".app":
                result["type"] = "macos_app"
                result.update(self._validate_macos_app(app_path))
            elif ext in [".exe", ".msi"]:
                result["type"] = "windows_exe"
                result.update(self._validate_windows_exe(app_path))
            elif ext in [".deb", ".rpm"]:
                result["type"] = "linux_package"
                result.update(self._validate_linux_package(app_path))
            elif ext == ".appimage":
                result["type"] = "linux_appimage"
                result.update(self._validate_appimage(app_path))
            else:
                result["issues"].append(f"不支持的文件类型: {ext}")
            
            # 检查文件权限
            if os.access(app_path, os.X_OK):
                result["executable"] = True
            else:
                result["warnings"].append("文件不可执行，可能需要设置执行权限")
            
            # 总体验证
            if not result["issues"]:
                result["valid"] = True
                result["message"] = "✅ 应用程序验证通过"
            else:
                result["message"] = "❌ 应用程序存在一些问题"
                
        except Exception as e:
            result["issues"].append(f"验证过程中出错: {str(e)}")
            result["message"] = "❌ 验证失败"
        
        return result
    
    def _validate_macos_dmg(self, dmg_path: str) -> Dict[str, Any]:
        """验证 macOS DMG 文件"""
        result = {"issues": [], "warnings": [], "suggestions": []}
        
        try:
            # 检查 DMG 文件结构
            if not dmg_path.endswith(".dmg"):
                result["issues"].append("文件扩展名不是 .dmg")
            
            # 检查文件大小（合理的 DMG 大小）
            file_size = os.path.getsize(dmg_path)
            if file_size < 1024 * 1024:  # 小于 1MB
                result["warnings"].append("DMG 文件可能过小")
            elif file_size > 1024 * 1024 * 500:  # 大于 500MB
                result["warnings"].append("DMG 文件可能过大")
            
            # 尝试挂载 DMG（在 macOS 上）
            if self.system == "darwin":
                try:
                    mount_cmd = f"hdiutil attach -nobrowse -noverify -noautoopen '{dmg_path}'"
                    mount_result = subprocess.run(mount_cmd, shell=True, 
                                                capture_output=True, text=True)
                    
                    if mount_result.returncode == 0:
                        # 获取挂载点
                        for line in mount_result.stdout.split('\n'):
                            if "/Volumes/" in line:
                                mount_point = line.split("\t")[-1].strip()
                                result["mount_point"] = mount_point
                                
                                # 检查 .app 目录
                                app_found = False
                                for item in os.listdir(mount_point):
                                    if item.endswith(".app"):
                                        app_found = True
                                        app_path = os.path.join(mount_point, item)
                                        
                                        # 验证 .app 结构
                                        if os.path.isdir(app_path):
                                            contents_path = os.path.join(app_path, "Contents")
                                            if os.path.exists(contents_path):
                                                result["app_structure"] = "完整"
                                            else:
                                                result["issues"].append(".app 目录结构不完整")
                                        break
                                
                                if not app_found:
                                    result["issues"].append("DMG 中未找到 .app 应用程序")
                                
                                # 卸载 DMG
                                unmount_cmd = f"hdiutil detach '{mount_point}'"
                                subprocess.run(unmount_cmd, shell=True, 
                                            capture_output=True, text=True)
                                break
                    else:
                        result["warnings"].append("无法挂载 DMG 文件进行验证")
                        
                except Exception as e:
                    result["warnings"].append(f"DMG 挂载验证失败: {str(e)}")
            
        except Exception as e:
            result["issues"].append(f"DMG 验证出错: {str(e)}")
        
        return result
    
    def _validate_macos_app(self, app_path: str) -> Dict[str, Any]:
        """验证 macOS .app 应用程序"""
        result = {"issues": [], "warnings": [], "suggestions": []}
        
        try:
            # 检查是否为目录
            if not os.path.isdir(app_path):
                result["issues"].append(".app 应该是一个目录")
                return result
            
            # 检查 Contents 目录
            contents_path = os.path.join(app_path, "Contents")
            if not os.path.exists(contents_path):
                result["issues"].append("缺少 Contents 目录")
                return result
            
            # 检查 Info.plist
            info_plist = os.path.join(contents_path, "Info.plist")
            if not os.path.exists(info_plist):
                result["issues"].append("缺少 Info.plist 文件")
            else:
                # 尝试读取 Info.plist
                try:
                    plist_cmd = f"plutil -p '{info_plist}'"
                    plist_result = subprocess.run(plist_cmd, shell=True,
                                                capture_output=True, text=True)
                    if plist_result.returncode == 0:
                        result["info_plist"] = "有效"
                    else:
                        result["issues"].append("Info.plist 格式错误")
                except:
                    result["warnings"].append("无法验证 Info.plist")
            
            # 检查 MacOS 目录和可执行文件
            macos_dir = os.path.join(contents_path, "MacOS")
            if os.path.exists(macos_dir):
                executables = [f for f in os.listdir(macos_dir) 
                             if os.path.isfile(os.path.join(macos_dir, f))]
                if executables:
                    result["executable_found"] = True
                    # 检查执行权限
                    exe_path = os.path.join(macos_dir, executables[0])
                    if os.access(exe_path, os.X_OK):
                        result["executable_permission"] = "可执行"
                    else:
                        result["issues"].append("可执行文件没有执行权限")
                else:
                    result["issues"].append("MacOS 目录中没有可执行文件")
            else:
                result["issues"].append("缺少 MacOS 目录")
            
            # 检查 Resources 目录
            resources_dir = os.path.join(contents_path, "Resources")
            if not os.path.exists(resources_dir):
                result["warnings"].append("缺少 Resources 目录")
            
            # 检查图标
            if os.path.exists(resources_dir):
                icons = [f for f in os.listdir(resources_dir) 
                        if f.endswith(".icns")]
                if icons:
                    result["icons_found"] = True
                else:
                    result["warnings"].append("未找到 .icns 图标文件")
            
        except Exception as e:
            result["issues"].append(f".app 验证出错: {str(e)}")
        
        return result
    
    def _validate_windows_exe(self, exe_path: str) -> Dict[str, Any]:
        """验证 Windows 可执行文件"""
        result = {"issues": [], "warnings": [], "suggestions": []}
        
        try:
            # 检查 PE 文件头（Windows 可执行文件）
            with open(exe_path, 'rb') as f:
                header = f.read(2)
                if header != b'MZ':
                    result["issues"].append("不是有效的 Windows 可执行文件 (缺少 MZ 头)")
                else:
                    result["pe_header"] = "有效"
            
            # 检查文件大小
            file_size = os.path.getsize(exe_path)
            if file_size < 1024 * 10:  # 小于 10KB
                result["warnings"].append("可执行文件可能过小")
            elif file_size > 1024 * 1024 * 100:  # 大于 100MB
                result["warnings"].append("可执行文件可能过大")
            
            # 检查是否为安装程序
            if exe_path.endswith(".msi"):
                result["installer_type"] = "MSI 安装程序"
                # MSI 文件应该有特定的结构
                try:
                    import msilib  # Windows only
                    result["msi_valid"] = "需要 Windows 系统验证"
                except:
                    result["warnings"].append("无法验证 MSI 文件结构")
            
        except Exception as e:
            result["issues"].append(f"Windows 可执行文件验证出错: {str(e)}")
        
        return result
    
    def _validate_linux_package(self, pkg_path: str) -> Dict[str, Any]:
        """验证 Linux 包文件"""
        result = {"issues": [], "warnings": [], "suggestions": []}
        
        try:
            if pkg_path.endswith(".deb"):
                result["package_type"] = "Debian 包"
                # 检查 deb 文件结构
                try:
                    with tarfile.open(pkg_path, 'r:gz') as tar:
                        members = tar.getmembers()
                        control_found = any('control.tar' in m.name for m in members)
                        data_found = any('data.tar' in m.name for m in members)
                        
                        if control_found and data_found:
                            result["deb_structure"] = "完整"
                        else:
                            result["issues"].append("DEB 包结构不完整")
                except:
                    result["issues"].append("不是有效的 DEB 包文件")
                    
            elif pkg_path.endswith(".rpm"):
                result["package_type"] = "RPM 包"
                result["warnings"].append("RPM 包验证需要 rpm 工具")
            
        except Exception as e:
            result["issues"].append(f"Linux 包验证出错: {str(e)}")
        
        return result
    
    def _validate_appimage(self, appimage_path: str) -> Dict[str, Any]:
        """验证 AppImage 文件"""
        result = {"issues": [], "warnings": [], "suggestions": []}
        
        try:
            # 检查是否为可执行文件
            if not os.access(appimage_path, os.X_OK):
                result["issues"].append("AppImage 文件不可执行")
            
            # 检查文件头
            with open(appimage_path, 'rb') as f:
                header = f.read(8)
                if header != b'\x7fELF':
                    result["issues"].append("不是有效的 ELF 文件")
                else:
                    result["elf_header"] = "有效"
            
            # 检查文件大小
            file_size = os.path.getsize(appimage_path)
            if file_size < 1024 * 1024:  # 小于 1MB
                result["warnings"].append("AppImage 文件可能过小")
            
            # 检查是否包含 AppImage 魔法字节
            try:
                with open(appimage_path, 'rb') as f:
                    f.seek(-8, 2)  # 文件末尾
                    magic = f.read(8)
                    if magic == b'AI\x02' or magic == b'AI\x01':
                        result["appimage_magic"] = "有效"
                    else:
                        result["warnings"].append("未找到 AppImage 魔法字节")
            except:
                result["warnings"].append("无法验证 AppImage 魔法字节")
            
        except Exception as e:
            result["issues"].append(f"AppImage 验证出错: {str(e)}")
        
        return result
    
    def validate_pwa(self, project_dir: str) -> Dict[str, Any]:
        """
        验证 PWA 项目
        
        Args:
            project_dir: PWA 项目目录
            
        Returns:
            验证结果
        """
        result = {
            "valid": False,
            "type": "pwa",
            "issues": [],
            "warnings": [],
            "suggestions": []
        }
        
        try:
            if not os.path.exists(project_dir):
                result["issues"].append(f"项目目录不存在: {project_dir}")
                return result
            
            # 检查必要文件
            required_files = ["index.html", "manifest.json", "service-worker.js"]
            for file in required_files:
                file_path = os.path.join(project_dir, file)
                if os.path.exists(file_path):
                    result[f"{file}_exists"] = True
                else:
                    result["issues"].append(f"缺少必要文件: {file}")
            
            # 验证 manifest.json
            manifest_path = os.path.join(project_dir, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    
                    # 检查必要字段
                    required_fields = ["name", "short_name", "start_url", "display"]
                    for field in required_fields:
                        if field not in manifest:
                            result["issues"].append(f"manifest 缺少必要字段: {field}")
                        else:
                            result[f"manifest_{field}"] = "存在"
                    
                    # 检查图标
                    if "icons" in manifest and manifest["icons"]:
                        result["icons"] = f"找到 {len(manifest['icons'])} 个图标"
                    else:
                        result["warnings"].append("manifest 中没有图标配置")
                    
                    result["manifest_valid"] = True
                    
                except json.JSONDecodeError:
                    result["issues"].append("manifest.json 不是有效的 JSON 文件")
                except Exception as e:
                    result["issues"].append(f"manifest 验证出错: {str(e)}")
            
            # 验证 service-worker.js
            sw_path = os.path.join(project_dir, "service-worker.js")
            if os.path.exists(sw_path):
                try:
                    with open(sw_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 检查基本内容
                    if "addEventListener" in content and "ServiceWorker" in content:
                        result["service_worker_basic"] = "有效"
                    else:
                        result["warnings"].append("service-worker.js 可能不完整")
                    
                    result["service_worker_exists"] = True
                    
                except Exception as e:
                    result["issues"].append(f"service-worker 验证出错: {str(e)}")
            
            # 验证 index.html
            index_path = os.path.join(project_dir, "index.html")
            if os.path.exists(index_path):
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 检查必要的 meta 标签
                    checks = {
                        "viewport": "viewport" in content,
                        "manifest": "manifest" in content,
                        "theme-color": "theme-color" in content,
                        "service-worker": "serviceWorker" in content,
                    }
                    
                    for check_name, check_result in checks.items():
                        if check_result:
                            result[f"html_{check_name}"] = "存在"
                        else:
                            result["warnings"].append(f"index.html 缺少 {check_name}")
                    
                    result["html_valid"] = True
                    
                except Exception as e:
                    result["issues"].append(f"index.html 验证出错: {str(e)}")
            
            # 总体验证
            if not result["issues"]:
                result["valid"] = True
                result["message"] = "✅ PWA 项目验证通过"
            else:
                result["message"] = "❌ PWA 项目存在一些问题"
                
        except Exception as e:
            result["issues"].append(f"PWA 验证过程中出错: {str(e)}")
            result["message"] = "❌ PWA 验证失败"
        
        return result
    
    def validate_apk(self, apk_path: str) -> Dict[str, Any]:
        """
        验证 Android APK 文件
        
        Args:
            apk_path: APK 文件路径
            
        Returns:
            验证结果
        """
        result = {
            "valid": False,
            "type": "android_apk",
            "issues": [],
            "warnings": [],
            "suggestions": []
        }
        
        try:
            if not os.path.exists(apk_path):
                result["issues"].append(f"APK 文件不存在: {apk_path}")
                return result
            
            # 检查文件扩展名
            if not apk_path.endswith(".apk"):
                result["issues"].append("文件扩展名不是 .apk")
            
            # 检查文件大小
            file_size = os.path.getsize(apk_path)
            result["file_size"] = f"{file_size / 1024 / 1024:.2f} MB"
            
            if file_size < 1024 * 100:  # 小于 100KB
                result["warnings"].append("APK 文件可能过小")
            elif file_size > 1024 * 1024 * 100:  # 大于 100MB
                result["warnings"].append("APK 文件可能过大")
            
            # 检查是否为 ZIP 文件（APK 本质上是 ZIP）
            try:
                with zipfile.ZipFile(apk_path, 'r') as zip_ref:
                    # 检查必要文件
                    required_files = ["AndroidManifest.xml", "classes.dex", "resources.arsc"]
                    apk_files = zip_ref.namelist()
                    
                    for file in required_files:
                        if any(file in f for f in apk_files):
                            result[f"{file}_exists"] = True
                        else:
                            result["issues"].append(f"APK 缺少必要文件: {file}")
                    
                    result["apk_structure"] = "基本完整"
                    result["file_count"] = len(apk_files)
                    
            except zipfile.BadZipFile:
                result["issues"].append("不是有效的 ZIP/APK 文件")
            except Exception as e:
                result["issues"].append(f"APK 结构验证出错: {str(e)}")
            
            # 总体验证
            if not result["issues"]:
                result["valid"] = True
                result["message"] = "✅ APK 文件验证通过"
            else:
                result["message"] = "❌ APK 文件存在一些问题"
                
        except Exception as e:
            result["issues"].append(f"APK 验证过程中出错: {str(e)}")
            result["message"] = "❌ APK 验证失败"
        
        return result
    
    def generate_report(self, validation_result: Dict[str, Any]) -> str:
        """
        生成验证报告
        
        Args:
            validation_result: 验证结果
            
        Returns:
            格式化报告
        """
        report = []
        report.append("=" * 60)
        report.append("应用验证报告")
        report.append("=" * 60)
        
        # 基本信息
        report.append(f"应用类型: {validation_result.get('type', '未知')}")
        report.append(f"平台: {validation_result.get('platform', '未知')}")
        report.append(f"验证状态: {validation_result.get('message', '未知')}")
        
        if 'file_size' in validation_result:
            report.append(f"文件大小: {validation_result['file_size']}")
        
        # 问题列表
        if validation_result.get('issues'):
            report.append("\n❌ 发现的问题:")
            for issue in validation_result['issues']:
                report.append(f"  • {issue}")
        
        # 警告列表
        if validation_result.get('warnings'):
            report.append("\n⚠️ 警告:")
            for warning in validation_result['warnings']:
                report.append(f"  • {warning}")
        
        # 建议列表
        if validation_result.get('suggestions'):
            report.append("\n💡 建议:")
            for suggestion in validation_result['suggestions']:
                report.append(f"  • {suggestion}")
        
        # 详细信息
        report.append("\n📊 详细信息:")
        for key, value in validation_result.items():
            if key not in ['issues', 'warnings', 'suggestions', 'message', 
                          'type', 'platform', 'file_size', 'valid']:
                if isinstance(value, (str, int, float, bool)):
                    report.append(f"  {key}: {value}")
        
        report.append("=" * 60)
        
        return "\n".join(report)

def main():
    """主函数 - 测试用"""
    import argparse
    
    parser = argparse.ArgumentParser(description="应用验证器")
    parser.add_argument("path", help="要验证的应用文件或目录路径")
    parser.add_argument("--type", choices=["auto", "desktop", "pwa", "apk"], 
                       default="auto", help="应用类型")
    
    args = parser.parse_args()
    
    # 创建验证器
    validator = AppValidator()
    
    # 自动检测类型
    if args.type == "auto":
        if args.path.endswith((".dmg", ".app", ".exe", ".msi", ".deb", ".rpm", ".appimage")):
            app_type = "desktop"
        elif args.path.endswith(".apk"):
            app_type = "apk"
        elif os.path.isdir(args.path):
            app_type = "pwa"
        else:
            app_type = "desktop"  # 默认
    else:
        app_type = args.type
    
    # 执行验证
    if app_type == "desktop":
        result = validator.validate_desktop_app(args.path)
    elif app_type == "pwa":
        result = validator.validate_pwa(args.path)
    elif app_type == "apk":
        result = validator.validate_apk(args.path)
    else:
        print(f"❌ 不支持的应用类型: {app_type}")
        return
    
    # 生成报告
    report = validator.generate_report(result)
    print(report)
    
    # 输出 JSON 格式结果（用于程序处理）
    print("\n📋 JSON 格式结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()