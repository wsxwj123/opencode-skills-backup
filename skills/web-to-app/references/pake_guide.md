# Pake 使用指南

Pake 是一个基于 Rust Tauri 的轻量级工具，可以用一条命令将任何网页转换为桌面应用。

## 主要特点

- **轻量级**：比 Electron 小约 20 倍，通常只有 5MB 左右
- **高性能**：基于 Rust 构建，速度快，内存占用低
- **易用性**：一条命令即可打包，无需复杂配置
- **跨平台**：支持 macOS、Windows 和 Linux
- **功能丰富**：支持快捷键、沉浸式窗口、拖放、样式自定义、广告移除等

## 安装 Pake CLI

### 使用 npm/pnpm

```bash
# 使用 pnpm（推荐）
pnpm install -g pake-cli

# 或使用 npm
npm install -g pake-cli
```

### 环境要求

- **Node.js**: >= 22
- **Rust**: >= 1.85（可选，仅本地开发需要）

## 基本用法

### 快速打包

最简单的用法，自动获取网站图标：

```bash
pake https://example.com --name MyApp
```

### 带参数打包

```bash
pake https://example.com \
  --name MyApp \
  --icon https://example.com/icon.icns \
  --width 1200 \
  --height 800 \
  --hide-title-bar
```

## 常用参数

### 必需参数

- `url`: 要打包的网页 URL（第一个参数）
- `--name`: 应用名称

### 窗口配置

- `--width <number>`: 窗口宽度（默认：1200）
- `--height <number>`: 窗口高度（默认：800）
- `--fullscreen`: 启动时全屏
- `--transparent`: 窗口透明
- `--hide-title-bar`: 隐藏标题栏
- `--resizable <bool>`: 是否可调整大小（默认：true）

### 图标和主题

- `--icon <path>`: 应用图标路径（.icns for macOS, .ico for Windows, .png for Linux）
- `--theme-color <color>`: 主题颜色

### 输出配置

- `--output <path>`: 输出目录
- `--identifier <string>`: macOS bundle identifier

### 高级选项

- `--user-agent <string>`: 自定义 User Agent
- `--inject <path>`: 注入 CSS/JS 文件
- `--safe-domain <domain>`: 安全域名（允许导航）
- `--multi-arch`: 构建通用二进制（macOS）

## 实用示例

### 打包 ChatGPT

```bash
pake https://chat.openai.com \
  --name ChatGPT \
  --width 1200 \
  --height 900
```

### 打包 Twitter

```bash
pake https://twitter.com \
  --name Twitter \
  --icon https://abs.twimg.com/icons/apple-touch-icon-192x192.png \
  --width 1400 \
  --height 900
```

### 打包微信读书

```bash
pake https://weread.qq.com \
  --name WeRead \
  --width 1200 \
  --height 800 \
  --hide-title-bar
```

### 打包 YouTube Music

```bash
pake https://music.youtube.com \
  --name "YouTube Music" \
  --width 1400 \
  --height 900
```

## 自定义功能

### 注入自定义样式

创建 CSS 文件 `custom.css`：

```css
/* 隐藏广告 */
.ad-container { display: none !important; }

/* 自定义背景 */
body { background: #1a1a1a; }

/* 调整字体 */
* { font-family: 'SF Pro', sans-serif; }
```

使用注入：

```bash
pake https://example.com \
  --name MyApp \
  --inject custom.css
```

### 注入自定义脚本

创建 JS 文件 `custom.js`：

```javascript
// 移除元素
document.querySelectorAll('.ads').forEach(el => el.remove());

// 添加功能
window.addEventListener('load', () => {
  console.log('App loaded!');
});
```

使用注入：

```bash
pake https://example.com \
  --name MyApp \
  --inject custom.js
```

## 使用 GitHub Actions 在线构建

如果不想配置本地环境，可以使用 GitHub Actions 进行在线构建。

### 步骤

1. Fork Pake 仓库：https://github.com/tw93/Pake
2. 在你的仓库中，进入 Actions 标签
3. 找到 "Build App" workflow
4. 点击 "Run workflow"
5. 填写参数：
   - URL: 网页地址
   - Name: 应用名称
   - Icon: 图标 URL（可选）
   - Width/Height: 窗口尺寸
6. 等待构建完成
7. 在 Artifacts 中下载生成的应用

### 优点

- 无需本地环境
- 支持所有平台（macOS、Windows、Linux）
- 构建快速（约 5-10 分钟）
- 自动打包和分发

## 配置文件方式

创建 `pake.config.json`：

```json
{
  "url": "https://example.com",
  "name": "MyApp",
  "icon": "./icon.icns",
  "width": 1200,
  "height": 800,
  "transparent": false,
  "resizable": true,
  "fullscreen": false,
  "hideToolbar": true,
  "userAgent": "",
  "inject": ["custom.css", "custom.js"]
}
```

使用配置文件：

```bash
pake --config pake.config.json
```

## 快捷键

### macOS

- `⌘ + [`: 返回上一页
- `⌘ + ]`: 前进下一页
- `⌘ + ↑`: 滚动到顶部
- `⌘ + ↓`: 滚动到底部
- `⌘ + r`: 刷新页面
- `⌘ + w`: 隐藏窗口
- `⌘ + -`: 缩小
- `⌘ + =`: 放大
- `⌘ + 0`: 重置缩放
- `⌘ + L`: 复制当前 URL
- `⌘ + ⇧ + H`: 返回主页

### Windows/Linux

将 `⌘` 替换为 `Ctrl` 即可。

## 高级技巧

### 自动获取图标

如果不指定 `--icon`，Pake 会自动尝试从网站获取图标。

### 多架构支持（macOS）

构建通用二进制（支持 Intel 和 Apple Silicon）：

```bash
pake https://example.com --name MyApp --multi-arch
```

### 签名和公证（macOS）

需要 Apple Developer 账号：

```bash
# 设置环境变量
export APPLE_CERT_ID="Developer ID Application: Your Name"
export APPLE_ID="your@email.com"
export APPLE_PASSWORD="app-specific-password"

# 构建并签名
pake https://example.com --name MyApp
```

### 自定义 User Agent

模拟不同设备：

```bash
# 模拟 iPad
pake https://example.com \
  --name MyApp \
  --user-agent "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X)"

# 模拟移动设备
pake https://example.com \
  --name MyApp \
  --user-agent "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)"
```

## 故障排除

### 构建失败

1. **检查 Node.js 版本**：确保 >= 22
2. **检查网络**：某些依赖需要从 GitHub 下载
3. **清理缓存**：`pnpm store prune` 或 `npm cache clean --force`
4. **重新安装**：`pnpm uninstall -g pake-cli && pnpm install -g pake-cli`

### 应用无法启动

1. **检查 URL**：确保网页可以正常访问
2. **检查权限**：在 macOS 上，首次运行可能需要在"安全性与隐私"中允许
3. **查看日志**：启用开发者工具（`⌘ + ⌥ + I`）查看控制台

### 图标问题

1. **macOS**：使用 .icns 格式（1024x1024）
2. **Windows**：使用 .ico 格式（256x256）
3. **Linux**：使用 .png 格式（512x512）

在线转换工具：
- https://cloudconvert.com/icns-converter
- https://convertio.co/icns-converter/

## 性能优化

### 减小包体积

1. 移除不必要的注入文件
2. 优化图标大小
3. 使用 `--transparent` 减少渲染开销

### 提升加载速度

1. 使用 `--user-agent` 获取移动版（通常更轻量）
2. 注入脚本移除不必要的元素
3. 使用 Service Worker 缓存

## 最佳实践

1. **命名规范**：使用有意义的应用名称
2. **图标质量**：使用高分辨率图标
3. **窗口尺寸**：根据网页内容设置合适的默认尺寸
4. **测试**：在目标平台上测试应用
5. **文档**：为用户提供使用说明
6. **更新**：定期检查 Pake 更新

## 常见应用场景

- **AI 工具**：ChatGPT、Claude、Gemini
- **音乐应用**：YouTube Music、Spotify Web
- **阅读应用**：微信读书、豆瓣读书
- **社交媒体**：Twitter、小红书
- **开发工具**：Excalidraw、Figma
- **办公工具**：Notion、Slack Web

## 相关资源

- 官方仓库：https://github.com/tw93/Pake
- 文档：https://github.com/tw93/Pake/blob/main/README_CN.md
- 示例应用：https://github.com/tw93/Pake/releases
- 社区讨论：https://github.com/tw93/Pake/discussions
