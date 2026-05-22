# Web-to-App Skill 实战演示

## 🎬 实际使用演示

### 演示 1：将 ChatGPT 转为 Mac 应用

#### 用户请求
```
请使用 web-to-app 技能将 https://chat.openai.com 转换为 macOS 应用
```

#### AI 执行步骤

1. **加载技能**
```
✅ 已加载 web-to-app 技能
```

2. **询问需求**
```
我将为你把 ChatGPT 转换为 macOS 应用。请选择：

1. 快速构建（使用默认配置）
2. 自定义配置（指定图标、窗口尺寸等）

你选择哪一个？
```

3. **用户选择 "1. 快速构建"**

4. **执行构建**
```python
# AI 内部执行
from scripts.pake_builder import PakeBuilder
from scripts.platform_detector import PlatformDetector

# 检测平台
detector = PlatformDetector()
info = detector.detect_current_platform()
print(f"当前平台: {info['platform']} ({info['architecture']})")

# 推荐工具
recommendation = detector.recommend_tool("macos", {})
print(f"推荐工具: {recommendation['recommended_tool']}")

# 构建应用
builder = PakeBuilder()
builder.check_environment()

config = {
    "name": "ChatGPT",
    "width": 1200,
    "height": 900,
    "output_dir": "./dist"
}

app_path = builder.build_with_cli("https://chat.openai.com", config)
```

5. **验证应用**
```python
from scripts.app_validator import AppValidator

validator = AppValidator()
result = validator.validate_desktop_app(app_path)
report = validator.generate_report(result)
print(report)
```

6. **交付结果**
```
🎉 ChatGPT.dmg 已成功创建！

📊 应用信息：
- 文件路径: ./dist/ChatGPT.dmg
- 文件大小: 5.2 MB
- 平台: macOS (Universal)
- 验证状态: ✅ 通过

📝 安装方法：
1. 双击 ChatGPT.dmg
2. 将 ChatGPT 拖到应用程序文件夹
3. 首次打开可能需要在"安全性与隐私"中允许

⌨️ 快捷键：
- ⌘ + [: 返回上一页
- ⌘ + ]: 前进下一页
- ⌘ + R: 刷新页面
- ⌘ + L: 复制当前 URL
```

---

### 演示 2：创建多平台应用

#### 用户请求
```
帮我把 https://notion.so 做成全平台应用
需要 Mac、Windows、Android 版本
```

#### AI 执行步骤

1. **制定策略**
```python
from scripts.platform_detector import PlatformDetector

detector = PlatformDetector()
strategy = detector.get_build_strategy(["macos", "windows", "android"])

print("构建策略：")
print(f"预计时间: {strategy['estimated_time']}")
print(f"所需工具: {', '.join(strategy['tools_needed'])}")
```

2. **并行构建桌面版**

注意：不同平台需要在对应系统上构建，建议使用 GitHub Actions。

创建 `.github/workflows/build-all.yml`：
```yaml
name: Build Notion Apps

on:
  workflow_dispatch:

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - run: npm install -g pake-cli
      - run: pake https://notion.so --name Notion --width 1400 --height 900
      - uses: actions/upload-artifact@v3
        with:
          name: Notion-macOS
          path: "*.dmg"

  build-windows:
    runs-on: windows-latest
    steps:
      - run: npm install -g pake-cli
      - run: pake https://notion.so --name Notion --width 1400 --height 900
      - uses: actions/upload-artifact@v3
        with:
          name: Notion-Windows
          path: "*.msi"

  build-android:
    runs-on: ubuntu-latest
    steps:
      - name: Generate PWA
        run: |
          # 创建 PWA 配置
          # 使用 PWABuilder 生成 APK
      - uses: actions/upload-artifact@v3
        with:
          name: Notion-Android
          path: "*.apk"
```

3. **提供指导**
```
📋 全平台构建方案：

由于你需要多个平台，我建议使用 GitHub Actions 自动化构建：

1️⃣ 创建 GitHub 仓库
2️⃣ 上传我为你生成的 workflow 文件
3️⃣ 在 Actions 中手动触发构建
4️⃣ 等待 15-20 分钟
5️⃣ 下载所有平台的应用

或者，我可以先在当前系统（macOS）上构建 Mac 版本，
然后为你提供其他平台的构建脚本。

你希望怎么做？
```

---

### 演示 3：PWA 项目创建

#### 用户请求
```
为 https://example.com 创建一个 PWA 项目
需要支持离线和推送通知
```

#### AI 执行步骤

1. **分析网站**
```python
from scripts.pwabuilder_converter import PWABuilderConverter

converter = PWABuilderConverter()
analysis = converter.analyze_website("https://example.com")

print(f"PWA 就绪程度: {analysis['score']}/100")
print(f"改进建议: {analysis['recommendations']}")
```

2. **创建项目**
```python
config = {
    "name": "Example App",
    "short_name": "Example",
    "description": "Example Progressive Web App",
    "theme_color": "#007bff",
    "background_color": "#ffffff",
    "lang": "zh-CN"
}

project_dir = converter.create_pwa_project("https://example.com", config)
```

3. **生成文件结构**
```
pwa-project/
├── index.html          # 主页面
├── manifest.json       # Web App Manifest
├── service-worker.js   # Service Worker（含离线和推送）
├── icon-192x192.png    # 图标（需用户提供）
└── icon-512x512.png    # 图标（需用户提供）
```

4. **部署指南**
```
✅ PWA 项目已创建！

📁 项目位置: ./pwa-project/

🚀 部署步骤：
1. 上传到支持 HTTPS 的服务器
2. 确保 manifest.json 和 service-worker.js 可访问
3. 访问你的网站
4. 浏览器会自动提示"安装应用"

📱 移动设备：
- Android: Chrome 浏览器会显示"添加到主屏幕"
- iOS: Safari 中选择"添加到主屏幕"

🔧 测试：
1. 本地测试: python3 -m http.server 8000
2. 访问: http://localhost:8000
3. 使用 Chrome DevTools 的 Lighthouse 检查 PWA 质量
```

---

### 演示 4：Android APK 生成

#### 用户请求
```
把我的网站 https://mywebsite.com 做成 Android APK
需要能上传到 Google Play
```

#### AI 执行步骤

1. **检查 PWA 就绪**
```python
converter = PWABuilderConverter()
analysis = converter.analyze_website("https://mywebsite.com")

if analysis['score'] < 80:
    print("⚠️ 网站的 PWA 评分较低，建议先优化：")
    for rec in analysis['recommendations']:
        print(f"  • {rec}")
```

2. **配置 TWA**
```python
config = {
    "name": "My Website",
    "package_name": "com.mywebsite.app",
    "version": "1.0.0",
    "version_code": 1,
    "host": "mywebsite.com",
    "start_url": "/",
    "theme_color": "#007bff",
    "background_color": "#ffffff",
    "orientation": "portrait",
    "display": "standalone"
}

apk_url = converter.package_for_android("https://mywebsite.com", config)
```

3. **生成 APK**
```
📦 正在生成 Android APK...

方式 1: 使用 PWABuilder 在线生成（推荐）
1. 访问: https://www.pwabuilder.com
2. 输入 URL: https://mywebsite.com
3. 点击 "Package for Stores" → "Android"
4. 配置应用信息
5. 下载生成的 APK

方式 2: 使用 Bubblewrap CLI（高级）
npm install -g @bubblewrap/cli
bubblewrap init --manifest https://mywebsite.com/manifest.json
bubblewrap build
```

4. **签名和发布**
```
🔐 签名 APK（用于 Google Play）:

1. 生成密钥库:
keytool -genkey -v -keystore my-app.keystore \
  -alias my-app -keyalg RSA -keysize 2048 -validity 10000

2. 签名 APK:
jarsigner -verbose -sigalg SHA256withRSA \
  -digestalg SHA-256 -keystore my-app.keystore \
  app-release-unsigned.apk my-app

3. 对齐 APK:
zipalign -v 4 app-release-unsigned.apk app-release.apk

4. 上传到 Google Play Console

📝 Digital Asset Links:
在你的网站根目录添加:
/.well-known/assetlinks.json

内容参考 references/pwabuilder_guide.md
```

---

### 演示 5：自定义样式和功能

#### 用户请求
```
把 YouTube Music 做成桌面应用
要求：
- 深色主题
- 去除广告
- 全局快捷键控制播放
```

#### AI 执行步骤

1. **创建自定义 CSS**
```css
/* custom-youtube-music.css */

/* 深色主题 */
body {
  background: #0f0f0f !important;
  color: #ffffff !important;
}

/* 隐藏广告 */
.ytmusic-ad,
.ad-container,
ytd-display-ad-renderer {
  display: none !important;
}

/* 优化布局 */
ytmusic-app {
  --ytmusic-color-black: #0f0f0f;
  --ytmusic-color-white: #ffffff;
}

/* 自定义滚动条 */
::-webkit-scrollbar {
  width: 10px;
  background: #1a1a1a;
}

::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 5px;
}
```

2. **创建功能脚本**
```javascript
// custom-youtube-music.js

// 全局快捷键
document.addEventListener('keydown', (e) => {
  // 空格键：播放/暂停
  if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
    e.preventDefault();
    const playButton = document.querySelector('[aria-label="播放"]') || 
                      document.querySelector('[aria-label="暂停"]');
    if (playButton) playButton.click();
  }
  
  // Cmd/Ctrl + 右箭头：下一首
  if ((e.metaKey || e.ctrlKey) && e.code === 'ArrowRight') {
    e.preventDefault();
    const nextButton = document.querySelector('[aria-label="下一首"]');
    if (nextButton) nextButton.click();
  }
  
  // Cmd/Ctrl + 左箭头：上一首
  if ((e.metaKey || e.ctrlKey) && e.code === 'ArrowLeft') {
    e.preventDefault();
    const prevButton = document.querySelector('[aria-label="上一首"]');
    if (prevButton) prevButton.click();
  }
});

// 移除广告元素（持续监听）
const removeAds = () => {
  document.querySelectorAll('.ytmusic-ad, .ad-container').forEach(ad => {
    ad.remove();
  });
};

setInterval(removeAds, 1000);

// 优化性能
window.addEventListener('load', () => {
  // 禁用不必要的动画
  document.documentElement.style.setProperty('--animation-duration', '0s');
});

console.log('✅ YouTube Music 自定义脚本已加载');
```

3. **构建应用**
```bash
pake https://music.youtube.com \
  --name "YouTube Music" \
  --width 1400 \
  --height 900 \
  --hide-title-bar \
  --inject custom-youtube-music.css \
  --inject custom-youtube-music.js
```

4. **验证和交付**
```
✅ YouTube Music 桌面应用已创建！

📦 应用信息：
- 文件: YouTube Music.dmg
- 大小: 5.8 MB
- 特性: 深色主题 | 无广告 | 快捷键控制

⌨️ 快捷键：
- 空格: 播放/暂停
- ⌘ + →: 下一首
- ⌘ + ←: 上一首
- ⌘ + R: 刷新
- ⌘ + L: 复制当前URL

🎵 享受你的音乐！
```

---

### 演示 6：企业内网应用

#### 用户请求
```
我们公司的 OA 系统 https://oa.company.com 需要做成桌面应用
要求：
- 支持 Windows 员工使用
- 窗口大小 1200x800
- 使用公司 Logo 作为图标
- 登录状态要能保持
```

#### AI 执行步骤

1. **准备图标**
```
我注意到你需要使用公司 Logo。请提供：
1. Logo 文件路径
2. 或者 Logo 的 URL

如果暂时没有，我可以先用默认图标，之后再替换。
```

2. **用户提供**: `./company-logo.png`

3. **转换图标格式**
```bash
# macOS/Linux
convert company-logo.png -resize 256x256 company-logo.ico

# 或使用在线工具
# https://cloudconvert.com/png-to-ico
```

4. **构建 Windows 应用**
```bash
pake https://oa.company.com \
  --name "Company OA" \
  --icon ./company-logo.ico \
  --width 1200 \
  --height 800
```

5. **配置会话保持**
```
💡 关于登录状态保持：

Pake 应用会自动保存 cookies 和 localStorage，
因此登录状态会在重启后保持。

如果遇到频繁登出的问题，可能是网站的安全策略导致。
建议：
1. 使用 SSO（单点登录）
2. 设置更长的会话超时时间（服务器端配置）
3. 使用"记住我"功能
```

6. **创建安装包**
```
✅ Company OA.msi 已创建！

📦 分发方案：

方案 1: 内网共享
- 将 .msi 文件放到公司内网共享文件夹
- 员工下载后双击安装

方案 2: 自动部署
- 使用 SCCM 或 Intune 推送
- 统一安装到所有员工电脑

方案 3: 自建下载页面
- 创建内网下载页面
- 提供安装说明和版本更新

📝 IT 管理员注意：
- 可能需要在组策略中添加信任
- 首次安装可能需要管理员权限
```

---

### 演示 7：开发者工具本地化

#### 用户请求
```
我经常用 Excalidraw 画图，但在线版有时候卡
能不能做成本地应用？
```

#### AI 执行步骤

1. **分析需求**
```
Excalidraw 是很好的选择！本地应用的优势：
✅ 响应更快（无网络延迟）
✅ 离线可用
✅ 数据更安全（本地存储）
✅ 系统集成更好

我来为你构建...
```

2. **优化配置**
```python
config = {
    "name": "Excalidraw",
    "width": 1600,  # 画图需要更大的画布
    "height": 1000,
    "hide_title_bar": True,  # 更大的工作区域
    "transparent": False,
    "resizable": True,
    "fullscreen": False
}
```

3. **构建**
```bash
pake https://excalidraw.com \
  --name Excalidraw \
  --width 1600 \
  --height 1000 \
  --hide-title-bar
```

4. **添加快捷键说明**
```
✅ Excalidraw.dmg 已创建！

🎨 使用提示：

窗口操作：
- ⌘ + F: 全屏模式（更大画布）
- ⌘ + =/-: 缩放画布
- ⌘ + S: 导出为 PNG（如果网站支持）

数据保存：
- 应用会自动保存你的绘图到本地存储
- 数据位置: ~/Library/Application Support/Excalidraw/

备份建议：
- 定期导出你的绘图文件
- 或使用 Excalidraw 的云同步功能
```

---

## 🎓 学习要点

通过这些演示，你应该了解：

1. **技能触发**：明确说明要使用 web-to-app 技能
2. **需求沟通**：AI 会询问配置偏好
3. **自动执行**：AI 自动选择工具和参数
4. **验证交付**：确保应用质量
5. **使用指导**：提供安装和使用说明

## 🔑 成功关键

1. **清晰表达需求**：说明目标平台和特殊要求
2. **提供必要资源**：如自定义图标、样式文件
3. **理解限制**：了解不同平台的限制
4. **充分测试**：在实际设备上测试应用
5. **考虑更新**：计划应用的更新和维护

## 📚 进阶阅读

- 查看 `references/pake_guide.md` 了解 Pake 的所有参数
- 查看 `references/pwabuilder_guide.md` 了解 PWA 最佳实践
- 查看 `references/platform_comparison.md` 选择最适合的方案
- 查看 `references/troubleshooting.md` 解决常见问题

## 🤝 反馈和改进

如果你有建议或发现问题，欢迎反馈！

---

**演示版本**: v1.0.0  
**最后更新**: 2026-01-27  
**适用于**: Claude Code & OpenCode

现在就试试吧！🚀
