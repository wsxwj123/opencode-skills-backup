# 故障排除指南

本文档汇总了使用 web-to-app 技能时可能遇到的常见问题和解决方案。

## Pake 相关问题

### 1. 安装 pake-cli 失败

**症状**：
```
npm ERR! code EACCES
npm ERR! Permission denied
```

**解决方案**：
```bash
# macOS/Linux
sudo npm install -g pake-cli

# 或使用 nvm 避免权限问题
nvm use 22
npm install -g pake-cli

# Windows (以管理员身份运行)
npm install -g pake-cli
```

### 2. 构建时 Rust 相关错误

**症状**：
```
error: failed to run custom build command for `tauri`
```

**解决方案**：

检查 Rust 版本：
```bash
rustc --version  # 需要 >= 1.85
```

更新 Rust：
```bash
rustup update
```

安装必要的工具链：
```bash
# macOS
xcode-select --install

# Linux (Ubuntu/Debian)
sudo apt install build-essential libwebkit2gtk-4.0-dev \
  libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

# Windows
# 安装 Visual Studio C++ Build Tools
```

### 3. 应用构建成功但无法启动

**症状**：双击应用没有反应

**检查项**：

1. **URL 可访问性**：
```bash
curl -I https://your-url.com
```

2. **文件权限**（macOS/Linux）：
```bash
chmod +x YourApp.app/Contents/MacOS/your-app
```

3. **macOS 安全设置**：
   - 系统偏好设置 → 安全性与隐私
   - 点击"仍要打开"

4. **Windows SmartScreen**：
   - 点击"更多信息"
   - 点击"仍要运行"

### 4. 图标不显示

**问题**：应用使用默认图标

**解决方案**：

1. 检查图标格式：
   - macOS: .icns (1024x1024)
   - Windows: .ico (256x256)
   - Linux: .png (512x512)

2. 使用在线工具转换：
```bash
# 使用 CloudConvert
https://cloudconvert.com/png-to-icns

# 或使用命令行工具
# macOS
iconutil -c icns icon.iconset

# Windows
convert icon.png -define icon:auto-resize icon.ico
```

3. 指定图标路径：
```bash
pake https://example.com --name MyApp --icon ./path/to/icon.icns
```

### 5. 网页加载白屏

**症状**：应用启动后显示空白页面

**排查步骤**：

1. 检查网络连接
2. 检查 URL 是否正确
3. 打开开发者工具查看错误：
   - macOS: `⌘ + ⌥ + I`
   - Windows: `Ctrl + Shift + I`

4. 检查是否需要登录或特殊权限

5. 尝试设置 User Agent：
```bash
pake https://example.com \
  --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
```

## PWABuilder 相关问题

### 1. PWA 评分低

**症状**：PWABuilder 显示低分数

**改进方法**：

1. **添加 HTTPS**：
   - PWA 必须通过 HTTPS 提供
   - 使用 Let's Encrypt 免费证书

2. **创建 manifest.json**：
```json
{
  "name": "My App",
  "short_name": "App",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#ffffff",
  "background_color": "#ffffff",
  "icons": [
    {
      "src": "/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

3. **注册 Service Worker**：
```javascript
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

4. **优化图标**：
   - 提供 192x192 和 512x512 的图标
   - 使用 `purpose: "any maskable"`

### 2. Android TWA 验证失败

**症状**：
```
Digital Asset Links verification failed
```

**解决方案**：

1. 创建 `.well-known/assetlinks.json`：
```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.example.myapp",
    "sha256_cert_fingerprints": [
      "YOUR_SHA256_FINGERPRINT"
    ]
  }
}]
```

2. 获取 SHA256 指纹：
```bash
keytool -list -v -keystore my-app.keystore
```

3. 确保文件可访问：
```bash
curl https://yourdomain.com/.well-known/assetlinks.json
```

### 3. Service Worker 不更新

**症状**：修改代码后 Service Worker 不生效

**解决方案**：

1. 更改缓存名称：
```javascript
const CACHE_NAME = 'my-pwa-cache-v2'; // 版本号+1
```

2. 强制更新：
```javascript
self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(clients.claim());
});
```

3. 清除浏览器缓存：
   - Chrome: DevTools → Application → Clear Storage

4. 取消注册旧的 Service Worker：
```javascript
navigator.serviceWorker.getRegistrations()
  .then(registrations => {
    for(let registration of registrations) {
      registration.unregister();
    }
  });
```

### 4. iOS 无法安装 PWA

**症状**：Safari 中没有"添加到主屏幕"选项

**检查项**：

1. 确保使用 Safari（不是 Chrome）
2. 检查 manifest.json：
```html
<link rel="manifest" href="/manifest.json">
```

3. 添加 iOS Meta 标签：
```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="My App">
<link rel="apple-touch-icon" href="/icon-180x180.png">
```

4. 确保图标 URL 正确且可访问

5. 清除 Safari 缓存后重试

### 5. Windows MSIX 安装失败

**症状**：
```
The app package format is not valid
```

**解决方案**：

1. 检查证书签名
2. 确保 Package Identity 唯一
3. 使用正确的发布者证书
4. 检查应用清单 (AppxManifest.xml)

5. 启用开发者模式：
   - 设置 → 更新和安全 → 开发者选项
   - 启用"开发人员模式"

## 通用问题

### 1. 应用体积过大

**原因**：
- 包含不必要的资源
- 图标文件过大
- 注入的文件过多

**优化方法**：

1. 压缩图标：
```bash
# 使用 ImageMagick
convert icon.png -quality 85 -resize 512x512 icon-optimized.png
```

2. 移除不必要的注入文件

3. 使用 URL 引用而非嵌入资源

### 2. 跨平台编译问题

**症状**：在 macOS 上无法构建 Windows 应用

**解决方案**：

使用 GitHub Actions 在线构建：

```yaml
# .github/workflows/build.yml
name: Build Apps

on:
  push:
    branches: [ main ]

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v2
      - run: pake https://example.com --name MyApp

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - run: pake https://example.com --name MyApp

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: pake https://example.com --name MyApp
```

### 3. 网络请求失败

**症状**：应用内无法加载某些资源

**原因**：
- CORS 限制
- CSP (Content Security Policy)
- 需要认证

**解决方案**：

1. 设置安全域名：
```bash
pake https://example.com \
  --safe-domain api.example.com,cdn.example.com
```

2. 修改 CSP 头（服务器端）

3. 使用代理绕过 CORS

### 4. 性能问题

**症状**：应用运行缓慢、卡顿

**优化方法**：

1. 启用硬件加速（Pake 默认启用）

2. 优化网页性能：
   - 压缩图片
   - 启用懒加载
   - 使用 CDN

3. 使用缓存策略（PWA）

4. 减少 DOM 操作

### 5. 更新和分发问题

**Pake 应用更新**：
- 手动：用户下载新版本
- 自动：使用 Squirrel（需配置）

**PWA 应用更新**：
- 自动：基于 Service Worker
- 提示用户刷新：
```javascript
if (navigator.serviceWorker.controller) {
  navigator.serviceWorker.controller.postMessage({type: 'SKIP_WAITING'});
}
```

## 调试技巧

### 启用开发者工具

**Pake 应用**：
- macOS: `⌘ + ⌥ + I`
- Windows: `Ctrl + Shift + I`
- Linux: `Ctrl + Shift + I`

**PWA**：
- Chrome: F12 或右键 → 检查
- 应用标签：Application 面板查看 PWA 状态

### 查看日志

**macOS**：
```bash
# Console.app 查看应用日志
open /Applications/Utilities/Console.app
```

**Windows**：
```
事件查看器 → Windows 日志 → 应用程序
```

**Linux**：
```bash
journalctl -f
```

### 网络调试

使用 Charles 或 Fiddler 抓包查看请求：

1. 设置代理
2. 安装证书
3. 过滤应用流量

## 寻求帮助

如果问题仍未解决：

### Pake
- GitHub Issues: https://github.com/tw93/Pake/issues
- Discussions: https://github.com/tw93/Pake/discussions
- Telegram: https://t.me/+GclQS9ZnxyI2ODQ1

### PWABuilder
- GitHub Issues: https://github.com/pwa-builder/PWABuilder/issues
- Docs: https://docs.pwabuilder.com
- Community: https://github.com/pwa-builder/PWABuilder/discussions

### 提问最佳实践

1. 描述清楚问题症状
2. 提供复现步骤
3. 附上错误日志
4. 说明系统版本和工具版本
5. 如果可能，提供最小复现示例

## 预防措施

1. **版本管理**：使用 Git 跟踪配置变化
2. **测试**：在目标平台上充分测试
3. **文档**：记录特殊配置和已知问题
4. **备份**：保留工作配置的备份
5. **更新**：定期更新工具到最新版本
