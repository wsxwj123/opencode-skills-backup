# PWABuilder 使用指南

PWABuilder 是创建 Progressive Web Apps 的最简单方式，支持跨平台和设备。

## 主要特点

- **跨平台**：一次构建，多平台部署（Web、Android、Windows、iOS）
- **简单易用**：在线工具，无需复杂配置
- **PWA 标准**：完全符合 PWA 标准
- **应用商店**：可以发布到 Google Play、Microsoft Store、App Store
- **离线支持**：自动生成 Service Worker
- **安装体验**：提供原生应用般的安装体验

## 使用方式

### 1. 在线使用（推荐）

访问 https://www.pwabuilder.com

#### 步骤

1. **输入 URL**：在首页输入你的网站 URL
2. **分析网站**：PWABuilder 会分析你的网站 PWA 就绪程度
3. **查看报告**：查看 PWA 评分和改进建议
4. **打包应用**：点击 "Package for Stores" 选择目标平台
5. **下载应用**：下载生成的应用包

### 2. 命令行使用

PWABuilder 也提供 CLI 工具（仅限高级用户）。

```bash
npm install -g @pwabuilder/cli

# 分析网站
pwabuilder analyze https://example.com

# 生成 manifest
pwabuilder manifest https://example.com

# 打包应用
pwabuilder package https://example.com --platform android
```

## Web App Manifest

Manifest 是 PWA 的核心配置文件。

### 基本结构

```json
{
  "name": "My Progressive Web App",
  "short_name": "MyPWA",
  "description": "A description of my PWA",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "theme_color": "#ffffff",
  "background_color": "#ffffff",
  "icons": [
    {
      "src": "/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/screenshot1.png",
      "sizes": "540x720",
      "type": "image/png"
    }
  ],
  "categories": ["productivity"],
  "shortcuts": [
    {
      "name": "New Task",
      "url": "/new",
      "icons": [{ "src": "/icon-96x96.png", "sizes": "96x96" }]
    }
  ]
}
```

### 重要字段

- **name**: 应用完整名称（最多 45 字符）
- **short_name**: 应用简称（最多 12 字符）
- **start_url**: 启动 URL
- **display**: 显示模式（fullscreen/standalone/minimal-ui/browser）
- **theme_color**: 主题颜色
- **icons**: 应用图标（至少 192x192 和 512x512）

### Display 模式

- `fullscreen`: 全屏，隐藏所有浏览器 UI
- `standalone`: 独立应用，隐藏浏览器 UI，保留系统状态栏
- `minimal-ui`: 最小 UI，保留基本导航控件
- `browser`: 普通浏览器标签

## Service Worker

Service Worker 提供离线功能和性能优化。

### 基本 Service Worker

```javascript
const CACHE_NAME = 'my-pwa-cache-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json'
];

// 安装
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// 激活
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
});

// 拦截请求
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
```

### 缓存策略

#### 1. Cache First（缓存优先）

```javascript
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        return response || fetch(event.request).then(fetchResponse => {
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, fetchResponse.clone());
            return fetchResponse;
          });
        });
      })
  );
});
```

适用于：静态资源、不经常变化的内容

#### 2. Network First（网络优先）

```javascript
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request)
      .then(response => {
        return caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, response.clone());
          return response;
        });
      })
      .catch(() => caches.match(event.request))
  );
});
```

适用于：动态内容、需要最新数据的场景

#### 3. Stale While Revalidate（使用缓存的同时更新）

```javascript
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      const fetchPromise = fetch(event.request).then(networkResponse => {
        caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, networkResponse.clone());
        });
        return networkResponse;
      });
      return cachedResponse || fetchPromise;
    })
  );
});
```

适用于：需要快速响应同时保持更新的内容

## 打包 Android APK

### 使用 PWABuilder 在线打包

1. 访问 https://www.pwabuilder.com
2. 输入你的 PWA URL
3. 点击 "Package for Stores"
4. 选择 "Android"
5. 配置选项：
   - **Package ID**: com.example.myapp
   - **App Name**: My App
   - **Version**: 1.0.0
   - **Host**: your-domain.com
   - **Icons**: 自动从 manifest 获取
6. 点击 "Generate"
7. 下载 APK 文件

### TWA (Trusted Web Activity)

PWABuilder 使用 TWA 技术，优点：

- 无需编写原生代码
- 自动更新（基于网页）
- 完整的 Web API 支持
- 可以上传到 Google Play

### 签名 APK

上传到 Google Play 需要签名：

```bash
# 生成密钥库
keytool -genkey -v -keystore my-app.keystore \
  -alias my-app -keyalg RSA -keysize 2048 -validity 10000

# 签名 APK
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore my-app.keystore app-release-unsigned.apk my-app

# 对齐 APK
zipalign -v 4 app-release-unsigned.apk app-release.apk
```

## 打包 Windows 应用

### 使用 PWABuilder 打包

1. 访问 https://www.pwabuilder.com
2. 输入你的 PWA URL
3. 选择 "Windows"
4. 配置选项：
   - **Package Name**: MyApp
   - **Publisher**: CN=Publisher
   - **Version**: 1.0.0.0
5. 下载 MSIX 包

### 安装到 Windows

双击 MSIX 文件即可安装，或使用命令：

```powershell
Add-AppxPackage -Path MyApp.msix
```

### 上传到 Microsoft Store

1. 注册 Microsoft 开发者账号
2. 创建应用提交
3. 上传 MSIX 包
4. 填写应用信息
5. 提交审核

## 打包 iOS 应用

### 方式 1：直接添加到主屏幕

iOS 原生支持 PWA，用户可以：

1. 在 Safari 中打开网站
2. 点击分享按钮
3. 选择"添加到主屏幕"

### 方式 2：使用 PWABuilder 生成 Xcode 项目

1. 访问 https://www.pwabuilder.com
2. 选择 "iOS"
3. 下载 Xcode 项目
4. 在 Xcode 中打开
5. 配置签名和证书
6. 构建并上传到 App Store

### iOS 特定配置

在 HTML `<head>` 中添加：

```html
<!-- iOS Meta Tags -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="My App">

<!-- iOS Icons -->
<link rel="apple-touch-icon" href="/icon-180x180.png">
<link rel="apple-touch-startup-image" href="/splash.png">
```

## PWA 最佳实践

### 1. HTTPS 必需

PWA 必须通过 HTTPS 提供（localhost 除外）。

### 2. 响应式设计

确保在所有设备上都能良好显示。

```css
@media (max-width: 768px) {
  /* 移动端样式 */
}

@media (min-width: 769px) {
  /* 桌面端样式 */
}
```

### 3. 快速加载

- 优化图片大小
- 使用 Service Worker 缓存
- 启用 GZIP 压缩
- 使用 CDN

### 4. 离线体验

提供有意义的离线页面：

```javascript
// service-worker.js
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match('/offline.html');
    })
  );
});
```

### 5. 推送通知

请求权限：

```javascript
if ('Notification' in window) {
  Notification.requestPermission().then(permission => {
    if (permission === 'granted') {
      new Notification('Hello!', {
        body: 'This is a notification',
        icon: '/icon-192x192.png'
      });
    }
  });
}
```

### 6. 图标要求

提供多种尺寸的图标：

- 192x192（必需）
- 512x512（必需）
- 72x72、96x96、128x128、144x144、152x152、180x180（推荐）

使用 `purpose: "any maskable"` 支持 Android 自适应图标。

### 7. 屏幕截图

为应用商店提供截图（540x720 或 1080x1920）。

## PWA 检查清单

使用 Lighthouse 检查 PWA 质量：

```bash
# 安装 Lighthouse CLI
npm install -g lighthouse

# 运行检查
lighthouse https://example.com --view
```

或在 Chrome DevTools > Lighthouse 中运行。

### 核心要求

- ✅ 通过 HTTPS 提供
- ✅ 注册 Service Worker
- ✅ 包含 Web App Manifest
- ✅ 包含 192x192 和 512x512 图标
- ✅ 响应式设计
- ✅ 快速加载（< 3秒）
- ✅ 可安装

## PWA vs 原生应用

### PWA 优势

- 无需应用商店审核
- 自动更新
- 跨平台
- 开发成本低
- 无需安装即可使用

### PWA 限制

- 某些原生 API 不可用
- iOS 上功能受限
- 离线存储限制
- 性能略逊于原生

## 实用工具

- **Manifest Generator**: https://www.simicart.com/manifest-generator.html/
- **Icon Generator**: https://realfavicongenerator.net/
- **PWA Tester**: https://www.pwabuilder.com/
- **Lighthouse**: Chrome DevTools
- **Workbox**: Google 的 Service Worker 库

## 故障排除

### Service Worker 不更新

```javascript
// 强制更新
self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(clients.claim());
});
```

### iOS 安装按钮不显示

检查：
- manifest.json 是否有效
- 图标是否符合要求
- 是否通过 HTTPS

### Android TWA 验证失败

确保：
- assetlinks.json 文件正确
- 域名匹配
- HTTPS 证书有效

## 相关资源

- 官方网站：https://www.pwabuilder.com
- 文档：https://docs.pwabuilder.com
- GitHub：https://github.com/pwa-builder/PWABuilder
- PWA Starter：https://github.com/pwa-builder/pwa-starter
- Workbox：https://developers.google.com/web/tools/workbox
