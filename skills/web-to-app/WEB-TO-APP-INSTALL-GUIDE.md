# Web-to-App Skill 完整指南

## 🎉 技能已创建完成！

你的 **web-to-app.skill** 已成功打包，位于：
```
/Users/wsxwj/Desktop/app/web-to-app.skill
```

## 📦 技能包含内容

### 核心功能
- ✅ 网页转 macOS 应用（基于 Pake）
- ✅ 网页转 Windows 应用（基于 Pake）
- ✅ 网页转 Linux 应用（基于 Pake）
- ✅ 网页转 Android APK（基于 PWABuilder）
- ✅ 网页转 iOS PWA（基于 PWABuilder）
- ✅ 创建完整 PWA 项目
- ✅ 自动验证应用质量
- ✅ 智能工具推荐

### 脚本工具 (4个)
1. `pake_builder.py` - Pake 构建器，自动化桌面应用打包
2. `pwabuilder_converter.py` - PWA 转换器，创建 PWA 和移动应用
3. `app_validator.py` - 应用验证器，确保应用质量
4. `platform_detector.py` - 平台检测器，智能推荐工具

### 参考文档 (4个)
1. `pake_guide.md` - Pake 详细使用指南（命令、参数、示例）
2. `pwabuilder_guide.md` - PWABuilder 使用指南（PWA、APK、iOS）
3. `platform_comparison.md` - 平台和工具对比分析
4. `troubleshooting.md` - 故障排除和常见问题

## 🚀 快速开始

### 在 Claude Code 中使用

1. **安装技能**：
```bash
# 复制技能文件到 Claude Code 技能目录
cp web-to-app.skill ~/.claude/skills/

# 或者解压到自定义位置
unzip web-to-app.skill -d ~/.claude/skills/web-to-app/
```

2. **使用技能**：
```
请使用 web-to-app 技能将 https://chat.openai.com 转换为 macOS 应用
```

### 在 OpenCode 中使用

1. **安装技能**：
```bash
# 复制到个人技能目录
cp web-to-app.skill ~/.config/opencode/skills/personal/

# 或者解压
unzip web-to-app.skill -d ~/.config/opencode/skills/personal/web-to-app/
```

2. **使用技能**：
```
帮我用 web-to-app 技能把这个网站做成应用：https://example.com
```

## 💡 使用示例

### 示例 1：快速转换（默认配置）

**用户输入**：
```
把 https://twitter.com 做成 Mac 应用
```

**AI 执行**：
- 识别目标平台：macOS
- 选择工具：Pake
- 执行构建：`pake https://twitter.com --name Twitter`
- 验证应用：检查 .dmg 文件完整性
- 交付结果：Twitter.dmg（约 5MB）

### 示例 2：自定义配置

**用户输入**：
```
帮我把 YouTube Music 做成桌面应用，要求：
- 窗口大一点（1400x900）
- 隐藏标题栏
- 使用自定义图标
```

**AI 执行**：
- 询问图标路径或自动获取
- 配置参数：width=1400, height=900, hide-title-bar=true
- 执行构建
- 验证并交付

### 示例 3：全平台构建

**用户输入**：
```
给我这个企业应用做全平台版本：https://oa.company.com
需要：桌面版（Mac/Windows/Linux）和移动版（Android/iOS）
```

**AI 执行**：
1. 分析需求，制定构建策略
2. 桌面平台：
   - macOS: Pake → .dmg
   - Windows: Pake → .msi
   - Linux: Pake → .deb/.AppImage
3. 移动平台：
   - Android: PWABuilder → .apk
   - iOS: PWABuilder → PWA 配置
4. 创建 PWA 项目作为 Web 版本
5. 验证所有应用
6. 提供分发指南

### 示例 4：PWA 项目创建

**用户输入**：
```
帮我为 https://example.com 创建一个完整的 PWA 项目
需要支持离线功能和推送通知
```

**AI 执行**：
- 分析网站
- 生成 manifest.json
- 创建 Service Worker（含离线和推送功能）
- 生成 index.html
- 提供部署指南

## 🎯 实际应用场景

### 场景 1：开发者工具本地化

**需求**：将 CodePen、JSFiddle 等在线工具做成桌面应用，方便离线使用。

**方案**：
```bash
pake https://codepen.io --name CodePen --width 1600 --height 1000
```

### 场景 2：企业内网应用

**需求**：将公司 OA、CRM 系统做成桌面应用，提升员工体验。

**方案**：
```bash
pake https://oa.company.com \
  --name "Company OA" \
  --icon ./company-logo.icns \
  --width 1400 \
  --height 900
```

### 场景 3：教育应用

**需求**：将在线课程平台做成应用，支持 Android 学生使用。

**方案**：
使用 PWABuilder 创建 Android APK，学生可以直接安装。

### 场景 4：内容分发

**需求**：将博客、文档网站做成应用，提供更好的阅读体验。

**方案**：
创建 PWA，支持离线阅读，可添加到各平台主屏幕。

## 🔧 高级功能

### 自定义样式

创建 `custom.css` 注入到应用：
```css
/* 隐藏广告 */
.ad-container, .advertisement { display: none !important; }

/* 深色主题 */
body { 
  background: #1a1a1a; 
  color: #e0e0e0; 
}

/* 自定义滚动条 */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-thumb { background: #555; border-radius: 4px; }
```

使用：
```bash
pake https://example.com --name MyApp --inject custom.css
```

### 自定义脚本

创建 `custom.js` 添加功能：
```javascript
// 移除特定元素
document.querySelectorAll('.unwanted').forEach(el => el.remove());

// 添加快捷键
document.addEventListener('keydown', (e) => {
  if (e.metaKey && e.key === 'k') {
    // 自定义功能
  }
});

// 监听页面变化
const observer = new MutationObserver(() => {
  // 响应变化
});
observer.observe(document.body, { childList: true, subtree: true });
```

使用：
```bash
pake https://example.com --name MyApp --inject custom.js
```

### 批量构建

创建配置文件 `apps.json`：
```json
[
  {
    "url": "https://chat.openai.com",
    "name": "ChatGPT",
    "width": 1200,
    "height": 900
  },
  {
    "url": "https://claude.ai",
    "name": "Claude",
    "width": 1200,
    "height": 900
  },
  {
    "url": "https://gemini.google.com",
    "name": "Gemini",
    "width": 1200,
    "height": 900
  }
]
```

批量构建脚本：
```python
import json
from scripts.pake_builder import PakeBuilder

with open('apps.json') as f:
    apps = json.load(f)

builder = PakeBuilder()
for app in apps:
    print(f"构建 {app['name']}...")
    config = {k: v for k, v in app.items() if k != 'url'}
    builder.build_with_cli(app['url'], config)
```

## 🌟 技能优势

### vs 手动使用工具
- ✅ 自动环境检查
- ✅ 智能工具选择
- ✅ 完整的验证流程
- ✅ 详细的错误处理
- ✅ 一站式解决方案

### vs 原生开发
- ✅ 开发时间：小时 vs 周/月
- ✅ 学习成本：零 vs 高
- ✅ 维护成本：低 vs 高
- ✅ 跨平台：原生支持 vs 需多次开发

### vs Electron
- ✅ 体积：5MB vs 100MB+
- ✅ 性能：优秀 vs 中等
- ✅ 内存：50MB vs 150MB+
- ✅ 启动：<1s vs 2-3s

## 📊 性能对比

| 指标 | Pake | PWA | Electron |
|-----|------|-----|----------|
| 应用体积 | ~5MB | ~1MB | ~100MB |
| 内存占用 | ~50MB | ~80MB | ~150MB |
| 启动时间 | <1s | <1s | 2-3s |
| 开发时间 | 1小时 | 2小时 | 1天 |

## 🎓 学习资源

### 官方文档
- Pake: https://github.com/tw93/Pake
- PWABuilder: https://docs.pwabuilder.com
- Tauri: https://tauri.app

### 视频教程
- Pake 快速入门（YouTube）
- PWA 开发教程（Google Developers）

### 社区
- Pake Telegram: https://t.me/+GclQS9ZnxyI2ODQ1
- PWABuilder Discord
- Tauri Discord

## 📝 检查清单

使用技能前，确保：
- [ ] 网页 URL 可正常访问
- [ ] 了解目标平台（macOS/Windows/Linux/iOS/Android）
- [ ] 准备好应用名称
- [ ] （可选）准备好自定义图标
- [ ] （可选）了解特殊配置需求

构建后，验证：
- [ ] 应用文件完整生成
- [ ] 文件大小合理
- [ ] 应用可以正常启动
- [ ] 网页内容正确显示
- [ ] 快捷键正常工作
- [ ] 无明显性能问题

## 🚨 重要提示

1. **版权问题**：确保你有权打包目标网站
2. **使用条款**：遵守网站的服务条款
3. **商业使用**：如果用于商业目的，可能需要额外授权
4. **隐私保护**：不要在应用中收集用户隐私数据
5. **安全性**：只打包可信的网站

## 💬 获取支持

如果你在使用过程中遇到任何问题：

1. **查看文档**：
   - SKILL.md（主要说明）
   - references/ 目录（详细指南）

2. **运行诊断**：
```bash
# 环境检查
python scripts/pake_builder.py --check-env

# 平台信息
python scripts/platform_detector.py --info

# 应用验证
python scripts/app_validator.py <app-path>
```

3. **社区求助**：
   - GitHub Issues
   - Telegram 群组
   - Discord 频道

## 🎊 开始创建你的第一个应用！

现在就在 Claude Code 或 OpenCode 中试试：

```
请使用 web-to-app 技能将 https://你喜欢的网站.com 转换为桌面应用
```

祝你使用愉快！🚀

---

**技能版本**: v1.0.0  
**文件大小**: 37KB  
**包含文件**: 9 个（1个主文件 + 4个脚本 + 4个参考文档）  
**创建日期**: 2026-01-27  
**兼容性**: ✅ Claude Code | ✅ OpenCode  
**许可证**: MIT
