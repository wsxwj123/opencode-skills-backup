# Web-to-App Skill 使用指南

## 简介

这是一个强大的 Claude/OpenCode 技能，可以将任意网页快速转换为完整的桌面或移动应用程序。

## 主要特性

✨ **一键转换**：只需提供网页 URL，自动生成应用  
🚀 **多平台支持**：macOS、Windows、Linux、iOS PWA、Android APK  
⚡ **轻量高效**：基于 Pake (Rust Tauri)，应用体积仅 ~5MB  
🎯 **智能推荐**：自动选择最适合的构建工具和方法  
✅ **完整验证**：自动验证生成的应用，确保质量  
📚 **丰富文档**：包含详细指南、示例和故障排除  

## 支持的工具

### Pake (桌面应用)
- 基于 Rust Tauri
- 体积小（~5MB）
- 性能优异
- 支持 macOS/Windows/Linux

### PWABuilder (PWA/移动)
- Progressive Web Apps
- 支持 Android APK
- 支持 iOS PWA
- 跨平台兼容

## 安装使用

### 1. 安装技能

将 `web-to-app.skill` 文件复制到你的技能目录：

**Claude Code**:
```bash
cp web-to-app.skill ~/.claude/skills/
```

**OpenCode**:
```bash
cp web-to-app.skill ~/.config/opencode/skills/personal/
```

### 2. 使用技能

在 Claude Code 或 OpenCode 中：

```
请使用 web-to-app 技能将 https://chat.openai.com 转换为 macOS 应用
```

或

```
帮我把 https://example.com 变成 Android APK
```

## 快速示例

### 示例 1：ChatGPT 桌面版

```
用户：把 ChatGPT 网页版做成 Mac 应用

AI：我来帮你将 ChatGPT 转换为 macOS 应用...
执行：pake https://chat.openai.com --name ChatGPT --width 1200 --height 900
结果：✅ 生成 ChatGPT.dmg（约 5MB）
```

### 示例 2：多平台应用

```
用户：给我这个网站 https://example.com 做全平台应用

AI：我将为你创建所有平台的应用...
- macOS/Windows/Linux：使用 Pake 构建桌面应用
- Android：使用 PWABuilder 生成 APK
- iOS：生成 PWA 配置
- Web：创建完整的 PWA 项目
```

### 示例 3：自定义配置

```
用户：帮我把 https://music.youtube.com 做成桌面应用，要大一点的窗口，隐藏标题栏

AI：好的，我来为你自定义构建...
执行：pake https://music.youtube.com \
  --name "YouTube Music" \
  --width 1400 \
  --height 900 \
  --hide-title-bar
```

## 包含的资源

### 脚本 (scripts/)
- `pake_builder.py` - Pake 构建自动化
- `pwabuilder_converter.py` - PWA 转换器
- `app_validator.py` - 应用验证器
- `platform_detector.py` - 平台检测和推荐

### 参考文档 (references/)
- `pake_guide.md` - Pake 详细使用指南
- `pwabuilder_guide.md` - PWABuilder 使用指南
- `platform_comparison.md` - 平台和工具对比
- `troubleshooting.md` - 故障排除手册

## 环境要求

### 桌面应用 (Pake)
- Node.js >= 22
- pnpm 或 npm
- Rust >= 1.85（可选）

### PWA/移动应用 (PWABuilder)
- 现代浏览器
- HTTPS（生产环境）
- Node.js >= 18（使用 CLI 时）

## 支持的应用类型

### AI 工具
✅ ChatGPT  
✅ Claude  
✅ Gemini  
✅ DeepSeek  
✅ Grok  

### SaaS 工具
✅ Notion  
✅ Figma  
✅ Linear  
✅ Excalidraw  

### 媒体应用
✅ YouTube Music  
✅ Spotify Web  
✅ 微信读书  

### 社交媒体
✅ Twitter  
✅ 小红书  
✅ Instagram Web  

### 自定义网站
✅ 任意网页都可以转换！

## 常见问题

### Q: 可以转换任何网站吗？
A: 几乎所有网站都可以，但需要注意版权和使用条款。某些需要特殊权限或复杂登录的网站可能需要额外配置。

### Q: 生成的应用能离线使用吗？
A: 桌面应用（Pake）本身可以离线运行，但网页内容取决于网站是否支持离线。PWA 可以通过 Service Worker 实现离线功能。

### Q: 应用会自动更新吗？
A: PWA 基于网页，自动更新。桌面应用（Pake）需要重新构建和分发新版本。

### Q: 可以自定义应用外观吗？
A: 可以！通过注入 CSS 文件自定义样式，或修改窗口尺寸、颜色等配置。

### Q: 需要编程知识吗？
A: 不需要！使用默认配置一条命令即可完成。高级自定义可以参考文档。

### Q: 可以发布到应用商店吗？
A: 可以！Android APK 可以上传到 Google Play，PWA 可以发布到 Microsoft Store。macOS 和 iOS 应用需要 Apple Developer 账号签名。

## 最佳实践

1. **应用命名**：使用简短、有意义的名称
2. **图标准备**：提供高质量图标（1024x1024）
3. **窗口尺寸**：根据网页内容选择合适尺寸
4. **性能优化**：使用 CDN、启用缓存
5. **充分测试**：在目标平台上测试应用

## 示例用例

### 用例 1：团队协作工具

将公司内网的 OA 系统转换为桌面应用，提供更好的工作体验。

```
pake https://oa.company.com --name "Company OA" --width 1400 --height 900
```

### 用例 2：学习应用

将在线学习平台转换为专注的学习应用。

```
pake https://coursera.org --name "Coursera" --hide-title-bar
```

### 用例 3：开发工具

将常用的 Web 开发工具转换为桌面应用。

```
pake https://codesandbox.io --name "CodeSandbox" --width 1600 --height 1000
```

## 获取帮助

### 文档
- 查看技能内的 `references/` 目录
- 参考 SKILL.md 中的详细说明

### 社区
- **Pake**: https://github.com/tw93/Pake
- **PWABuilder**: https://www.pwabuilder.com
- **Telegram**: https://t.me/+GclQS9ZnxyI2ODQ1

### 报告问题
如果遇到问题：
1. 查看 `references/troubleshooting.md`
2. 在 GitHub 上提 Issue
3. 在社区论坛求助

## 更新日志

### v1.0.0 (2026-01-27)
- ✨ 初始版本发布
- ✅ 支持 Pake 桌面应用构建
- ✅ 支持 PWABuilder PWA/移动应用
- ✅ 完整的验证和故障排除
- ✅ 详细的文档和示例
- ✅ 平台检测和智能推荐

## 许可证

MIT License

## 贡献

欢迎贡献代码、文档或报告问题！

---

**技能版本**: v1.0.0  
**创建日期**: 2026-01-27  
**兼容性**: Claude Code & OpenCode  
**维护者**: AI Assistant

## 开始使用

现在就试试吧！

```
请使用 web-to-app 技能将 https://你喜欢的网站.com 转换为应用
```

享受便捷的网页转应用体验！🚀
