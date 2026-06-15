# social-clip 升级计划

> 目标(用户 2026-06-15):从"小红书剪藏为主"升级为**通用社交信息聚合器**——
> 主动检索社交平台内容与**评论**,读取图文(下载识图)、视频音频(转写总结)、文案,
> 多重信息获取,不限于小红书/知乎/B站/豆瓣/微博。

## 一、能力矩阵(重构核心)

| 平台 | 主动检索 | 正文/文案 | 图片识图 | 视频/音频 | 评论 |
|------|----------|-----------|----------|-----------|------|
| 小红书 | ✅ MCP `search_feeds` | `get_feed_detail.desc` | `imageList`下载→Read | Playwright拦CDN→ffmpeg→voice-bridge | ✅ `get_feed_detail` `load_all_comments` |
| B站 | 🟡 抓搜索页 | fetch-everything | 抓正文 img | yt-dlp 字幕优先→音频 | 🟡 fetch-everything 抓DOM |
| YouTube/抖音 | ❌ 给链接 | — | — | yt-dlp 字幕优先→音频 | 🟡 fetch-everything |
| 知乎/微博/豆瓣 | 🟡 抓搜索页(脆弱) | fetch-everything(可能需CDP登录态) | 抓正文 img→下载→Read | yt-dlp(若视频) | 🟡 fetch-everything 抓DOM(脆弱) |

**可靠性分级(诚实标注,不假装等同):**
- **T1 满血**:小红书(原生 MCP,检索/详情/图/评论全可靠)
- **T2 较可靠**:B站/YT/抖音视频转写、任意公开网页正文
- **T3 尽力而为**:知乎/微博/豆瓣 的检索与评论——强反爬+登录墙,靠 fetch-everything,可能需本机 Chrome 登录态(CDP);抓不到就 HALT 告知用户,不硬编。

## 二、逐条任务

| # | 任务 | 类型 | 来源 |
|---|------|------|------|
| 1 | 建 `references/summary-standard.md`,下沉总结标准(零遗漏细则+ASR表+模板) | 架构 | 上轮#5 |
| 2 | 建 `references/platform-recipes.md`,各平台检索URL/正文/图片/评论抓取配方 | 架构 | 新增 |
| 3 | **评论提取**:小红书 `load_all_comments`;其他平台 fetch-everything 抓DOM | 功能(核心) | 新增 |
| 4 | **正文泛化**:非XHS非视频走 fetch-everything 抓正文+文案,修"文字帖必失败" | 功能 | 上轮#1 |
| 5 | **图片识图泛化**:非XHS 从正文提 img URL→下载→Read | 功能 | 新增 |
| 6 | **主动检索泛化**:小红书原生;其他平台抓搜索结果页拿候选(标注脆弱) | 功能 | 新增 |
| 7 | voice-bridge `/health` 检查统一前置(yt-dlp 流程当前缺) | 健壮性 | 上轮#2 |
| 8 | 字幕优先:YouTube/B站 `yt-dlp --write-auto-sub`,无字幕再 ASR | 效率 | 上轮#3 |
| 9 | 去装修过拟合:ASR表/示例标注为"示例,按领域自建";保存目录给通用 fallback | 上下文 | 上轮#4 |
| 10 | 重写 SKILL.md(能力矩阵路由+引用references)+ 更新 description + 检查清单 + test-prompts | 整合 | — |

## 三、执行策略

- references 先建(新文件,零风险)→ SKILL.md 整体重写一次(文档,一次重写比10次小改干净)→ test-prompts 更新 → 验证脚本存在性/命令语法。
- 回退手段:全程 git,改前 commit 基线;每条改完不跑真实抓取(会触发风控),只做静态校验(命令语法、脚本路径、引用完整性)。

## 四、风险与缓解

| 失败模式 | 缓解 |
|----------|------|
| 知乎/微博评论藏在动态DOM/需滚动点击"更多",fetch-everything 抓不全 | 标注 T3 尽力而为;抓不到评论时只交付正文+提示"评论需登录态",不假装完整 |
| 非XHS"主动检索"抓搜索页被风控/返回登录墙 | HALT 告知用户改用"直接给链接";不硬刷 |
| SKILL.md 重写丢失原有可用流程(XHS图文/视频/yt-dlp) | 重写前对照原文件逐节保留;重写后 diff 校验关键命令未丢 |
| references 拆分后 SKILL.md 该按需加载的没标清,模型不会去读 | 每个 references 文件在 SKILL.md 标注"何时加载" |
