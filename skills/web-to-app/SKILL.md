---
name: web-to-app
description: 将任意网页链接转换为完整、可用的桌面或移动应用。基于 Pake (Rust Tauri) 和 PWABuilder 工具，支持 macOS、Windows、Linux、iOS PWA 和 Android APK。一键命令打包，自动选择最佳工具，包含验证和故障排除。适用于：(1) 将网页/SaaS工具转为桌面应用，(2) 创建跨平台 PWA，(3) 快速生成移动应用，(4) 需要轻量级应用包装时。
---

# Web To App - 网页转应用技能

将任意网页快速转换为完整的桌面应用（macOS/Windows/Linux）或移动应用（iOS PWA/Android APK）。

## 概述

本技能整合了两个强大的开源工具：
- **Pake**：基于 Rust Tauri，将网页打包为轻量级桌面应用（~5MB）
- **PWABuilder**：创建 Progressive Web Apps，支持 Web、iOS 和 Android

## 工作流程

### 1. 理解用户需求

当用户提供网页 URL 时，首先询问目标平台和配置偏好：

**必需信息**：
- 网页 URL
- 目标平台（macOS/Windows/Linux/iOS/Android/PWA）
- 应用名称（可选，默认从网页标题提取）

**可选配置**：
- 自定义图标
- 窗口尺寸
- 主题颜色
- 特殊功能需求

### 2. 选择合适的工具

使用 `scripts/platform_detector.py` 检测当前平台并推荐工具：

```python
python scripts/platform_detector.py --target <platform> --recommend
```

**决策逻辑**：
- **桌面应用**（macOS/Windows/Linux）→ 使用 Pake
- **移动应用**（iOS/Android）→ 使用 PWABuilder
- **PWA** → 使用 PWABuilder
- **全平台** → Pake（桌面）+ PWABuilder（移动/Web）

### 3. 构建应用

#### 方案 A：桌面应用（Pake）

```bash
# 检查环境
python scripts/pake_builder.py --check-env

# 快速构建（推荐）
pake <URL> --name "AppName" --width 1200 --height 800

# 高级构建（自定义图标和样式）
pake <URL> \
  --name "AppName" \
  --icon ./icon.icns \
  --width 1400 \
  --height 900 \
  --hide-title-bar \
  --inject custom.css
```

**使用脚本构建**：
```python
from scripts.pake_builder import PakeBuilder

builder = PakeBuilder()
config = {
    "name": "MyApp",
    "width": 1200,
    "height": 800,
    "output_dir": "./dist"
}
app_path = builder.build_with_cli(url, config)
```

#### 方案 B：PWA/移动应用（PWABuilder）

```python
from scripts.pwabuilder_converter import PWABuilderConverter

converter = PWABuilderConverter()

# 分析网站
analysis = converter.analyze_website(url)

# 创建 PWA 项目
config = {
    "name": "MyPWA",
    "theme_color": "#007bff",
    "background_color": "#ffffff"
}
project_dir = converter.create_pwa_project(url, config)

# 打包为 Android APK
apk_url = converter.package_for_android(url, config)

# 打包为 iOS PWA
ios_url = converter.package_for_ios(url, config)
```

### 4. 验证应用

使用 `scripts/app_validator.py` 验证生成的应用：

```python
from scripts.app_validator import AppValidator

validator = AppValidator()

# 验证桌面应用
result = validator.validate_desktop_app("./MyApp.dmg")

# 验证 PWA 项目
result = validator.validate_pwa("./pwa-project")

# 验证 APK
result = validator.validate_apk("./MyApp.apk")

# 生成验证报告
report = validator.generate_report(result)
print(report)
```

### 5. 处理问题

如果遇到问题，参考 `references/troubleshooting.md`：

**常见问题**：
- 构建失败 → 检查环境和依赖
- 应用无法启动 → 验证 URL 和权限
- 图标不显示 → 检查图标格式和路径
- Service Worker 不更新 → 清除缓存，更改版本号

## 快速示例

### 示例 1：将 ChatGPT 转为 macOS 应用

```bash
# 一条命令完成
pake https://chat.openai.com --name ChatGPT --width 1200 --height 900

# 输出：ChatGPT.dmg（约 5MB）
```

### 示例 2：将网站转为 Android APK

```python
from scripts.pwabuilder_converter import PWABuilderConverter

converter = PWABuilderConverter()
config = {
    "name": "MyApp",
    "package_name": "com.example.myapp",
    "version": "1.0.0"
}

# 获取打包链接
apk_url = converter.package_for_android("https://example.com", config)
print(f"在线打包: {apk_url}")
```

### 示例 3：创建完整的 PWA 项目

```python
from scripts.pwabuilder_converter import PWABuilderConverter

converter = PWABuilderConverter()
config = {
    "name": "My Progressive App",
    "short_name": "MyApp",
    "description": "A Progressive Web App",
    "theme_color": "#007bff",
    "icons": [
        {"src": "/icon-192x192.png", "sizes": "192x192"},
        {"src": "/icon-512x512.png", "sizes": "512x512"}
    ]
}

# 创建项目
project_dir = converter.create_pwa_project("https://example.com", config)
print(f"PWA 项目创建完成: {project_dir}")
```

### 示例 4：全平台构建

```python
from scripts.platform_detector import PlatformDetector
from scripts.pake_builder import PakeBuilder
from scripts.pwabuilder_converter import PWABuilderConverter

# 获取构建策略
detector = PlatformDetector()
strategy = detector.get_build_strategy(["macos", "windows", "linux", "android", "ios"])

print("构建策略:")
for step in strategy["build_order"]:
    print(f"步骤 {step['step']}: {step['platforms']} (使用 {step['tool']})")

# 执行构建
url = "https://example.com"
config = {"name": "MyApp"}

# 桌面平台
pake_builder = PakeBuilder()
for platform in ["macos", "windows", "linux"]:
    print(f"构建 {platform} 应用...")
    # 注意：实际需要在对应平台上构建，或使用 GitHub Actions

# 移动平台
pwa_converter = PWABuilderConverter()
pwa_converter.package_for_android(url, config)
pwa_converter.package_for_ios(url, config)
```

## 参考资源

### 详细指南
- **Pake 使用**: 查看 `references/pake_guide.md`
- **PWABuilder 使用**: 查看 `references/pwabuilder_guide.md`
- **平台对比**: 查看 `references/platform_comparison.md`
- **故障排除**: 查看 `references/troubleshooting.md`

### 脚本工具
- `scripts/pake_builder.py` - Pake 构建器
- `scripts/pwabuilder_converter.py` - PWABuilder 转换器
- `scripts/app_validator.py` - 应用验证器
- `scripts/platform_detector.py` - 平台检测器

## 最佳实践

### 1. 应用命名
- 使用简短、有意义的名称
- 避免特殊字符
- 考虑国际化

### 2. 图标准备
- macOS: 1024x1024 PNG → .icns
- Windows: 256x256 PNG → .ico
- Linux: 512x512 PNG
- PWA: 192x192 和 512x512 PNG

在线转换：https://cloudconvert.com/icns-converter

### 3. 窗口尺寸
- 聊天工具：1200x900
- 音乐应用：1400x900
- 阅读应用：1000x800
- 工具应用：1200x800

### 4. 性能优化
- 使用 CDN 加速资源加载
- 启用 Service Worker 缓存
- 压缩图片和资源
- 移除不必要的元素（注入 CSS）

### 5. 分发和更新
- 桌面：GitHub Releases 或自建服务器
- Android：Google Play 或直接分发 APK
- iOS：App Store 或 PWA 直接使用
- PWA：自动更新（基于 Service Worker）

## 环境要求

### Pake（桌面应用）
- Node.js >= 22
- pnpm 或 npm
- Rust >= 1.85（可选，仅本地开发）
- 平台特定工具：
  - macOS: Xcode Command Line Tools
  - Windows: Visual Studio C++ Build Tools
  - Linux: build-essential, webkit2gtk

### PWABuilder（PWA/移动）
- 现代浏览器
- HTTPS（生产环境必需）
- Node.js >= 18（使用 CLI 时）

### 通用
- Git（版本管理）
- 稳定的网络连接
- 足够的磁盘空间（至少 2GB）

## 支持的平台

### 桌面
- ✅ macOS 10.13+ (Intel 和 Apple Silicon)
- ✅ Windows 10/11 (x64 和 ARM64)
- ✅ Linux (Ubuntu 18.04+, Debian 10+, Fedora 30+)

### 移动
- ✅ Android 5.0+ (API 21+)
- ✅ iOS 11.3+ (通过 PWA)

### Web
- ✅ Chrome 90+
- ✅ Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+

## 使用技巧

### 快速原型
快速验证想法，使用默认配置：
```bash
pake https://example.com --name MyApp
```

### 生产应用
精心配置，提供最佳体验：
```bash
pake https://example.com \
  --name "My Application" \
  --icon ./assets/icon.icns \
  --width 1400 \
  --height 900 \
  --hide-title-bar \
  --inject ./assets/custom.css \
  --user-agent "Custom UA"
```

### 自动化构建
使用脚本批量构建：
```python
# build_all.py
from scripts.pake_builder import PakeBuilder
from scripts.pwabuilder_converter import PWABuilderConverter

apps = [
    {"url": "https://chat.openai.com", "name": "ChatGPT"},
    {"url": "https://claude.ai", "name": "Claude"},
    {"url": "https://gemini.google.com", "name": "Gemini"}
]

builder = PakeBuilder()
for app in apps:
    print(f"构建 {app['name']}...")
    builder.build_with_cli(app["url"], {"name": app["name"]})
```

### GitHub Actions 在线构建
创建 `.github/workflows/build.yml`：
```yaml
name: Build Apps
on: [push]
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v2
      - run: npm install -g pake-cli
      - run: pake https://example.com --name MyApp
```

## 注意事项

1. **版权和授权**：确保有权打包目标网站
2. **网站兼容性**：某些网站可能不适合打包（需要特殊权限、复杂登录等）
3. **更新机制**：桌面应用需要手动更新，PWA 自动更新
4. **平台限制**：iOS PWA 功能受限，建议使用 TestFlight 测试
5. **签名和公证**：分发应用可能需要代码签名（macOS、iOS）

## 常见使用场景

1. **AI 工具桌面化**：ChatGPT、Claude、Gemini
2. **SaaS 工具本地化**：Notion、Figma、Linear
3. **媒体应用**：YouTube Music、Spotify Web
4. **阅读应用**：微信读书、豆瓣读书
5. **社交媒体**：Twitter、Instagram Web
6. **开发工具**：Excalidraw、CodePen
7. **企业内网应用**：OA、CRM 系统

## 获取帮助

- **Pake**: https://github.com/tw93/Pake
- **PWABuilder**: https://www.pwabuilder.com
- **社区**: Telegram、Discord、GitHub Discussions

---

**技能版本**: 1.0.0  
**最后更新**: 2026-01-27  
**维护者**: AI Assistant  
**许可**: MIT
