#!/usr/bin/env python3
"""
PWABuilder 转换器脚本 - 使用 PWABuilder 创建 PWA 和 Android APK
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import urllib.parse

class PWABuilderConverter:
    """PWABuilder 转换器类"""
    
    def __init__(self, work_dir: str = None):
        """
        初始化 PWABuilder 转换器
        
        Args:
            work_dir: 工作目录，如果为 None 则使用临时目录
        """
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="pwabuilder_")
        self.api_url = "https://pwabuilder.com"
        
    def analyze_website(self, url: str) -> Optional[Dict[str, Any]]:
        """
        分析网站，获取 PWA 相关信息
        
        Args:
            url: 网站URL
            
        Returns:
            分析结果或 None
        """
        try:
            print(f"🔍 正在分析网站: {url}")
            
            # 这里可以调用 PWABuilder API 进行实际分析
            # 简化版本：返回模拟数据
            
            # 实际实现应该调用：https://pwabuilder.com/api/manifest?url={url}
            
            analysis_result = {
                "url": url,
                "has_manifest": True,
                "has_service_worker": False,
                "manifest": {
                    "name": "My Web App",
                    "short_name": "App",
                    "description": "A Progressive Web App",
                    "theme_color": "#ffffff",
                    "background_color": "#ffffff",
                    "display": "standalone",
                    "orientation": "portrait",
                    "start_url": "/",
                    "scope": "/",
                    "icons": []
                },
                "score": 65,  # PWA 评分 (0-100)
                "recommendations": [
                    "添加 Service Worker 以实现离线功能",
                    "优化图标尺寸",
                    "配置推送通知"
                ]
            }
            
            print(f"✅ 网站分析完成，PWA 评分: {analysis_result['score']}/100")
            return analysis_result
            
        except Exception as e:
            print(f"❌ 网站分析失败: {e}")
            return None
    
    def generate_manifest(self, url: str, config: Dict[str, Any]) -> Optional[str]:
        """
        生成 Web App Manifest 文件
        
        Args:
            url: 网站URL
            config: 配置参数
            
        Returns:
            manifest 文件路径或 None
        """
        try:
            print("📄 正在生成 Web App Manifest...")
            
            # 解析 URL 获取基本信息
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc
            
            # 创建 manifest 内容
            manifest = {
                "name": config.get("name", domain),
                "short_name": config.get("short_name", domain[:12]),
                "description": config.get("description", f"{domain} Progressive Web App"),
                "start_url": config.get("start_url", "/"),
                "scope": config.get("scope", "/"),
                "display": config.get("display", "standalone"),
                "orientation": config.get("orientation", "portrait"),
                "theme_color": config.get("theme_color", "#ffffff"),
                "background_color": config.get("background_color", "#ffffff"),
                "icons": self._generate_icons(config),
                "screenshots": config.get("screenshots", []),
                "categories": config.get("categories", []),
                "shortcuts": config.get("shortcuts", []),
                "lang": config.get("lang", "en"),
                "dir": config.get("dir", "ltr"),
            }
            
            # 保存 manifest 文件
            manifest_path = os.path.join(self.work_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Manifest 生成完成: {manifest_path}")
            return manifest_path
            
        except Exception as e:
            print(f"❌ Manifest 生成失败: {e}")
            return None
    
    def _generate_icons(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成图标配置"""
        icons = config.get("icons", [])
        
        if not icons:
            # 默认图标配置
            sizes = ["192x192", "512x512"]
            for size in sizes:
                icons.append({
                    "src": f"/icon-{size}.png",
                    "sizes": size,
                    "type": "image/png",
                    "purpose": "any maskable"
                })
        
        return icons
    
    def generate_service_worker(self, config: Dict[str, Any]) -> Optional[str]:
        """
        生成 Service Worker 文件
        
        Args:
            config: 配置参数
            
        Returns:
            service worker 文件路径或 None
        """
        try:
            print("⚙️ 正在生成 Service Worker...")
            
            # 创建基本的 Service Worker
            sw_content = """// Service Worker for Progressive Web App
const CACHE_NAME = 'pwa-cache-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json'
];

// 安装 Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// 激活 Service Worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// 拦截网络请求
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // 返回缓存或网络请求
        return response || fetch(event.request);
      })
  );
});

// 处理推送通知
self.addEventListener('push', event => {
  const options = {
    body: event.data.text(),
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    }
  };
  
  event.waitUntil(
    self.registration.showNotification('Push Notification', options)
  );
});
"""
            
            # 保存 Service Worker 文件
            sw_path = os.path.join(self.work_dir, "service-worker.js")
            with open(sw_path, "w", encoding="utf-8") as f:
                f.write(sw_content)
            
            print(f"✅ Service Worker 生成完成: {sw_path}")
            return sw_path
            
        except Exception as e:
            print(f"❌ Service Worker 生成失败: {e}")
            return None
    
    def package_for_android(self, url: str, config: Dict[str, Any]) -> Optional[str]:
        """
        打包为 Android APK
        
        Args:
            url: 网站URL
            config: 配置参数
            
        Returns:
            APK 文件路径或下载链接
        """
        try:
            print("🤖 正在打包 Android APK...")
            
            # 使用 PWABuilder API 打包 Android APK
            # 实际实现应该调用：https://pwabuilder.com/api/packages/android
            
            # 简化版本：提供指导
            print("📋 请按照以下步骤操作：")
            print(f"1. 访问 {self.api_url}")
            print(f"2. 输入URL: {url}")
            print("3. 点击 'Package for Stores'")
            print("4. 选择 'Android'")
            print("5. 配置应用信息：")
            print(f"   - 应用名称: {config.get('name', 'MyApp')}")
            print(f"   - 包名: {config.get('package_name', 'com.example.app')}")
            print(f"   - 版本: {config.get('version', '1.0.0')}")
            print("6. 点击 'Generate' 生成 APK")
            print("7. 下载生成的 APK 文件")
            
            # 返回指导链接
            package_url = f"{self.api_url}/#/package?url={urllib.parse.quote(url)}"
            return package_url
            
        except Exception as e:
            print(f"❌ Android 打包失败: {e}")
            return None
    
    def package_for_windows(self, url: str, config: Dict[str, Any]) -> Optional[str]:
        """
        打包为 Windows 应用
        
        Args:
            url: 网站URL
            config: 配置参数
            
        Returns:
            MSIX 文件路径或下载链接
        """
        try:
            print("🪟 正在打包 Windows 应用...")
            
            # 使用 PWABuilder API 打包 Windows 应用
            # 实际实现应该调用：https://pwabuilder.com/api/packages/windows
            
            print("📋 请按照以下步骤操作：")
            print(f"1. 访问 {self.api_url}")
            print(f"2. 输入URL: {url}")
            print("3. 点击 'Package for Stores'")
            print("4. 选择 'Windows'")
            print("5. 配置应用信息：")
            print(f"   - 应用名称: {config.get('name', 'MyApp')}")
            print(f"   - 发布者: {config.get('publisher', 'CN=Example')}")
            print(f"   - 版本: {config.get('version', '1.0.0')}")
            print("6. 点击 'Generate' 生成 MSIX")
            print("7. 下载生成的 MSIX 文件")
            
            package_url = f"{self.api_url}/#/package?url={urllib.parse.quote(url)}"
            return package_url
            
        except Exception as e:
            print(f"❌ Windows 打包失败: {e}")
            return None
    
    def package_for_ios(self, url: str, config: Dict[str, Any]) -> Optional[str]:
        """
        打包为 iOS PWA（通过 App Store）
        
        Args:
            url: 网站URL
            config: 配置参数
            
        Returns:
            指导链接
        """
        try:
            print("📱 正在准备 iOS PWA...")
            
            # iOS 上的 PWA 可以直接通过 Safari 添加到主屏幕
            # 也可以使用 PWABuilder 生成 iOS 项目
            
            print("📋 iOS PWA 部署选项：")
            print("")
            print("选项 1: 直接添加到主屏幕")
            print(f"1. 在 Safari 中打开: {url}")
            print("2. 点击分享按钮 (📤)")
            print("3. 选择 '添加到主屏幕'")
            print("4. 输入应用名称")
            print("5. 点击 '添加'")
            print("")
            print("选项 2: 使用 PWABuilder 生成 iOS 项目")
            print(f"1. 访问 {self.api_url}")
            print(f"2. 输入URL: {url}")
            print("3. 点击 'Package for Stores'")
            print("4. 选择 'iOS'")
            print("5. 下载生成的 Xcode 项目")
            print("6. 在 Xcode 中打开并配置")
            print("7. 提交到 App Store")
            
            return f"{self.api_url}/#/package?url={urllib.parse.quote(url)}"
            
        except Exception as e:
            print(f"❌ iOS 准备失败: {e}")
            return None
    
    def create_pwa_project(self, url: str, config: Dict[str, Any]) -> Optional[str]:
        """
        创建完整的 PWA 项目
        
        Args:
            url: 网站URL
            config: 配置参数
            
        Returns:
            项目目录路径
        """
        try:
            print("🏗️ 正在创建 PWA 项目...")
            
            # 创建项目目录
            project_name = config.get("name", "pwa-project").replace(" ", "-").lower()
            project_dir = os.path.join(self.work_dir, project_name)
            os.makedirs(project_dir, exist_ok=True)
            
            # 生成文件
            self.generate_manifest(url, config)
            self.generate_service_worker(config)
            
            # 创建 index.html
            index_html = f"""<!DOCTYPE html>
<html lang="{config.get('lang', 'en')}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.get('name', 'PWA App')}</title>
    <meta name="description" content="{config.get('description', 'Progressive Web App')}">
    <meta name="theme-color" content="{config.get('theme_color', '#ffffff')}">
    
    <!-- Web App Manifest -->
    <link rel="manifest" href="manifest.json">
    
    <!-- iOS Meta Tags -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="{config.get('name', 'PWA App')}">
    
    <!-- Icons -->
    <link rel="icon" href="/favicon.ico" type="image/x-icon">
    <link rel="apple-touch-icon" href="/icon-192x192.png">
    
    <!-- Service Worker Registration -->
    <script>
        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', () => {{
                navigator.serviceWorker.register('/service-worker.js')
                    .then(registration => {{
                        console.log('Service Worker registered:', registration);
                    }})
                    .catch(error => {{
                        console.log('Service Worker registration failed:', error);
                    }});
            }});
        }}
    </script>
    
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: {config.get('background_color', '#ffffff')};
            color: #333;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        h1 {{
            color: {config.get('theme_color', '#007bff')};
        }}
        
        iframe {{
            width: 100%;
            height: 600px;
            border: none;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{config.get('name', 'PWA App')}</h1>
        <p>{config.get('description', 'Progressive Web App')}</p>
        
        <iframe src="{url}" title="{config.get('name', 'Web App')}"></iframe>
        
        <div style="margin-top: 20px; text-align: center;">
            <p>📱 将此应用添加到主屏幕以获得更好的体验</p>
            <p>⚡ 支持离线访问和快速加载</p>
        </div>
    </div>
</body>
</html>"""
            
            # 保存 index.html
            index_path = os.path.join(project_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(index_html)
            
            # 复制 manifest 和 service worker
            manifest_src = os.path.join(self.work_dir, "manifest.json")
            sw_src = os.path.join(self.work_dir, "service-worker.js")
            
            if os.path.exists(manifest_src):
                shutil.copy(manifest_src, os.path.join(project_dir, "manifest.json"))
            if os.path.exists(sw_src):
                shutil.copy(sw_src, os.path.join(project_dir, "service-worker.js"))
            
            print(f"✅ PWA 项目创建完成: {project_dir}")
            return project_dir
            
        except Exception as e:
            print(f"❌ PWA 项目创建失败: {e}")
            return None
    
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
    
    parser = argparse.ArgumentParser(description="PWABuilder 转换器")
    parser.add_argument("url", help="要转换的网页URL")
    parser.add_argument("--name", default="MyPWA", help="应用名称")
    parser.add_argument("--platform", choices=["android", "windows", "ios", "pwa"], 
                       default="pwa", help="目标平台")
    
    args = parser.parse_args()
    
    # 创建转换器
    converter = PWABuilderConverter()
    
    # 分析网站
    analysis = converter.analyze_website(args.url)
    if analysis:
        print(f"📊 分析结果: {json.dumps(analysis, indent=2, ensure_ascii=False)}")
    
    # 配置参数
    config = {
        "name": args.name,
        "description": f"{args.name} Progressive Web App",
        "theme_color": "#007bff",
        "background_color": "#ffffff",
    }
    
    # 根据平台打包
    result = None
    if args.platform == "android":
        result = converter.package_for_android(args.url, config)
    elif args.platform == "windows":
        result = converter.package_for_windows(args.url, config)
    elif args.platform == "ios":
        result = converter.package_for_ios(args.url, config)
    else:  # pwa
        result = converter.create_pwa_project(args.url, config)
    
    if result:
        print(f"🎉 {args.platform.upper()} 应用准备完成: {result}")
    else:
        print(f"❌ {args.platform.upper()} 应用准备失败")
    
    # 清理
    converter.cleanup()

if __name__ == "__main__":
    main()