---
name: social-clip
description: >
  从社交平台主动检索/提取完整内容并保存到 Obsidian 知识库,做多重信息聚合。
  能力:主动检索内容与评论、读图文(下载图片识图)、转视频音频为文字并总结、提取文案。
  支持平台:小红书(原生检索+评论最完整)、B站、知乎、微博、豆瓣、抖音、YouTube、Twitter 等。
  只要用户分享社交/视频链接、粘贴短链(xhslink.com、b23.tv 等),或要求"搜/找某主题的内容、评论",都自动触发。
  除非用户明确说"看看就好""不用"等否定词,否则不需要确认。
  核心承诺:不跳过任何图片、不压缩转写、每个要点/例子/数据/高赞评论都完整保留。
---

# social-clip:社交内容聚合技能

## 核心原则

内容提取的最大敌人是"偷懒"——跳过图片、压缩转写、遗漏评论里的增量信息。
本技能强制**完整提取**:图文逐张读图,视频完整转写,评论抓取增量观点,总结不省略任何有意义的要点、数字、例子、反面案例。

---

## 能力矩阵(决定每个平台用什么后端)

| 平台 | 主动检索 | 正文/文案 | 图片识图 | 视频/音频 | 评论 |
|------|----------|-----------|----------|-----------|------|
| 小红书 | ✅ MCP search | ✅ `desc` | ✅ `imageList` | ✅ Playwright+ffmpeg | ✅ MCP 满血 |
| B站 | ✅ autocli search | ✅ autocli read | read 提图 | ✅ autocli subtitle→yt-dlp | 🟡 尽力(read/fetch) |
| 知乎/微博/豆瓣 | ✅ autocli search(登录态) | ✅ autocli read | read 提图 | yt-dlp(若视频) | 🟡 尽力(脆弱) |
| YouTube/抖音/其他 | autocli search / 给链接 | autocli read | read 提图 | yt-dlp 字幕优先 | 🟡 尽力 |

- **后端原则**:非小红书平台一律先试 `autocli`(复用本机 Chrome 登录态,对登录墙站点远比隐身抓取可靠),无对应命令/抓空再降级 `fetch-everything`,再不行 🛑 HALT 告知用户。
- ✅ 满血可靠 · 🟡 尽力而为(尤其评论:autocli 无通用读评论命令,非小红书评论靠 read/fetch 部分抓取,抓不到不硬刷)
- **评论 MCP 可选增强**:为某平台装了评论 MCP(B站/知乎/抖音/豆瓣,见 platform-recipes.md)则自动用它满血读评论;不装也能跑,纯 opt-in、不进硬依赖。
- **非小红书平台的所有抓取配方在 `references/platform-recipes.md`**——处理它们时先读那个文件。

---

## 依赖与配置(分享/移植必读)

本技能依赖若干外部工具与本机服务,**缺失则降级,不硬假设存在**:

| 依赖 | 用途 | 缺失时 |
|------|------|--------|
| `xiaohongshu` MCP | 小红书检索/详情/评论 | 降级 fetch-everything 抓单页 |
| `autocli`(PATH 中) | 非XHS 检索/正文/B站字幕(登录态) | 降级 fetch-everything;`command -v autocli` 找不到提示装:`curl -fsSL https://raw.githubusercontent.com/nashsu/AutoCLI/main/scripts/install.sh \| sh` |
| `~/.claude/skills/fetch-everything` | 通用抓取兜底 | 提示该技能未装 |
| `~/.claude/skills/yt-dlp-downloader` + `yt-dlp`/`ffmpeg` | 视频音频提取 | 视频流程不可用,提示 |
| voice-bridge 服务 | 音频转文字 | 跳过 ASR,改用字幕或提示 |

**可配置项(环境变量,均有默认,别人不配也能跑):**
- `OBSIDIAN_VAULT`:保存目标 vault 根目录。未设则运行时自动探测(见「保存到 Obsidian」)
- `VOICE_BRIDGE_URL`:转写服务地址,默认 `http://127.0.0.1:7788`
- 网络代理:默认直连;本机需代理时 `export http_proxy=...` 即可,技能不写死端口

> **跨技能路径按当前 runtime 的 skills 根解析**:Claude Code=`~/.claude/skills`、Codex=`~/.codex/skills`、OpenCode=`~/.config/opencode/skills`。本技能与 fetch-everything/yt-dlp-downloader 同级,**取本技能所在目录的父目录**即可定位它们;下文示例按 Claude Code 路径书写,换 runtime 时相应替换根目录。不出现任何特定用户名的绝对路径。

---

## 快速路由

先判断用户给的是**链接**、**关键词**,还是要**评论**:

```
输入
 ├── 只有关键词/主题(要"搜/找…的内容或评论")
 │     ├── 小红书 → [小红书关键词检索] → 选笔记 → 详情流程
 │     └── 其他平台 → references/platform-recipes.md「主动检索」抓搜索页 → 选条目 → 详情流程
 └── 有链接 → 判断平台
        ├── 小红书(xhslink / xiaohongshu) → 展开短链 → get_feed_detail
        │     ├── type=normal → [2A 图文帖]   ├── type=video → [2B 视频帖]
        │     └── 都要 → [2C 评论提取]
        └── 非小红书(B站/知乎/微博/豆瓣/YT/抖音/Twitter 等) → references/platform-recipes.md
              (autocli 优先:search 检索 / read 取正文 / bilibili subtitle 取字幕;
               视频无字幕→yt-dlp 音频转写;图文→正文+图片识图;评论尽力而为)
```

---

## 第一步:平台识别和 URL 解析

| URL 特征 | 平台 |
|----------|------|
| `xhslink.com` / `xiaohongshu.com` | 小红书 |
| `bilibili.com` / `b23.tv` | B站 |
| `zhihu.com` | 知乎 |
| `weibo.com` / `t.cn` | 微博 |
| `douban.com` | 豆瓣 |
| `douyin.com` / `iesdouyin.com` | 抖音 |
| `youtube.com` / `youtu.be` | YouTube |
| `twitter.com` / `x.com` | Twitter/X |

**短链展开**(xhslink.com、b23.tv 等):
```bash
curl -sL --max-redirs 5 -o /dev/null -w "%{url_effective}" "SHORT_URL"
```

---

## 临时文件管理(防残留)

下载的图片/视频/音频统一用前缀 `/tmp/social_clip_*`。**会下载的流程(图文配图/视频/音频)开始第一步先清上次残留、全部完成后再清一次**——幂等 self-healing:某次中途跳步残留,下次入口也兜底清掉,不累积。统一清理命令:
```bash
find /tmp -maxdepth 1 -name 'social_clip_*' -exec rm -rf {} + 2>/dev/null
```
> 🔴 **清理必须用 `find`,禁止 `rm -rf /tmp/social_clip_*`**:zsh 下通配无匹配会报错中断,且一条命令含多个通配只要一个无匹配就连累整条(该删的也删不掉)。`find` 无匹配静默、bash/zsh/Linux 一致。
> 技能跨多次独立 Bash 调用执行,单进程 `trap` 覆盖不了全程,故用"入口+出口双清"而非 trap。

---

## 小红书(XHS)完整流程

### 关键词检索(无链接时)

```
mcp__xiaohongshu__search_feeds(keyword="关键词", filters={...})
```
`filters` 可选:`sort_by`(综合/最新/最多点赞/最多评论/最多收藏)、`note_type`(不限/视频/图文)、`publish_time`(不限/一天内/一周内/半年内)、`search_scope`、`location`。

过滤候选:
- **丢弃 `modelType == "hot_query"`**(热搜词,非笔记)
- 只保留 `modelType == "note"`,从 `noteCard` 取 `displayTitle`、`user.nickname`、`type`、`interactInfo`
- 按互动数排序列给用户选,或按要求取 top-N
- 对选中笔记,用其 `id`(=feed_id)和 `xsecToken`(=xsec_token)**直接进详情(跳过短链展开)**

### 1. 获取帖子信息

从展开后 URL 提取 `feed_id`(path 最后一段)和 `xsec_token`(query 参数)。
```
mcp__xiaohongshu__get_feed_detail(feed_id=..., xsec_token=...)
```
`note.type`:`"normal"`→图文帖,`"video"`→视频帖。**返回里已含前10条评论**(见 2C)。

**MCP 调用失败时**:
1. 检查 `feed_id`/`xsec_token` 是否提取正确(`/discovery/item/{feed_id}?xsec_token={token}`)
2. 仍失败 → fetch-everything 隐身降级(它把小红书识别为动态站,走 Scrapling,比 WebFetch 更能突破风控):
   ```bash
   python3 ~/.claude/skills/fetch-everything/scripts/fetch_everything.py "完整XHS链接" --json
   ```
   能提取多少算多少;**不要用 WebFetch**(对小红书基本只拿到登录墙)
3. 告知用户"MCP 失败,已用 fetch-everything 隐身降级"

### 2A. 图文帖

- **文字**:读 `note.desc`,保留全文
- **图片**(关键):从 `note.imageList` 拿所有 URL,**逐张下载 + Read**,不跳过任何一张
```bash
curl -s "imageList[0].urlDefault" -o /tmp/social_clip_img_1.jpg   # → Read
curl -s "imageList[1].urlDefault" -o /tmp/social_clip_img_2.jpg   # → Read
# ...共 N 次,每张都下载+Read。下载失败(报错或 <1KB)→ 记"第X张失败",继续后续
find /tmp -maxdepth 1 -name 'social_clip_img_*' -exec rm -f {} + 2>/dev/null   # 读完清图(zsh 安全)
```
图里的文字、表格、对比图全部提取。

### 2B. 视频帖

**Step 1** Playwright 拦截 CDN 视频 URL:
```bash
python3 ~/.claude/skills/yt-dlp-downloader/xhs_get_video.py "XHS_URL"   # 多行CDN URL,取第一行
```
**Step 2** ffmpeg 直接从 CDN 提音频(不下整个视频):
```bash
ffmpeg -i "CDN_URL" -vn -acodec mp3 -ar 16000 -ac 1 -y /tmp/social_clip_audio.mp3 2>/dev/null
# 直连失败且本机已 export http_proxy → 加 -http_proxy "$http_proxy" 重试
```
ffmpeg 仍失败(鉴权过期/网络) → curl 下整个视频再提:
```bash
curl -L ${http_proxy:+--proxy "$http_proxy"} -o /tmp/social_clip_video.mp4 "CDN_URL"   # 仅当已 export http_proxy 才走代理
ffmpeg -i /tmp/social_clip_video.mp4 -vn -acodec mp3 -ar 16000 -ac 1 -y /tmp/social_clip_audio.mp3
rm -f /tmp/social_clip_video.mp4
```
Playwright 脚本本身无 CDN 输出 → 检查 `~/.claude/skills/yt-dlp-downloader/xhs_get_video.py` 是否存在,并告知用户"CDN 拦截失败,建议手动下载后提供本地路径"。
**Step 3** 转写(见下"voice-bridge 转写统一前置")→ **Step 4** 清本次临时文件:`find /tmp -maxdepth 1 -name 'social_clip_*' -exec rm -rf {} + 2>/dev/null`

### 2C. 评论提取(NEW)

`get_feed_detail` 默认返回前10条一级评论。用户要更全/明确要评论时:
```
mcp__xiaohongshu__get_feed_detail(feed_id=..., xsec_token=...,
    load_all_comments=true, limit=20, click_more_replies=true)
```
- `load_all_comments=true` 滚动加载更多;`limit` 控一级评论数;`click_more_replies=true` 展开二级回复
- 从评论里提取**增量信息**:补充经验、纠错、不同观点、作者回复——单列"评论区补充"一节(见 summary-standard.md)

---

## 非小红书平台

**先读 `references/platform-recipes.md`**,后端 autocli 优先(登录态)、fetch-everything 兜底:
- 检索 → `autocli <site> search`;正文/文章 → `autocli read "<url>"`,再从正文提 img URL 逐张下载 Read
- 视频:B站 → `autocli bilibili subtitle`;其他 → yt-dlp **字幕优先**,无字幕降级 ASR
- 评论 → 装了该平台评论 MCP(可选,见 recipes)则优先用它满血读;否则 autocli read/fetch-everything 抓首屏(尽力而为,标注部分抓取)
- autocli 抓空/无命令 → fetch-everything(知乎/微博登录墙必要时 CDP 登录态);仍失败 🛑 HALT 告知用户

---

## voice-bridge 转写(统一前置)

**任何音频转写前,先 health 检查**(XHS 视频、yt-dlp 流程都走这里);服务地址取环境变量,未部署则跳过转写改用字幕:
```bash
VB="${VOICE_BRIDGE_URL:-http://127.0.0.1:7788}"
curl -s "$VB/health"   # {"ok":true,"model_loaded":true} 才继续;未就绪→告知"转写服务未部署",改用字幕或让用户提供文本
curl -s -X POST "$VB/transcribe_file" \
  -H "Content-Type: application/json" -d '{"path": "/tmp/social_clip_audio.mp3"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('text',''))"
```

---

## 内容总结

**这一步是技能核心价值。产出笔记前读 `references/summary-standard.md`**(零遗漏细则、口语→书面、ASR 纠错方法、结构模板)。
要点:每个数字/例子/反面案例/操作顺序/高赞评论都不能省;口语转书面化结构笔记,不是誊抄;重要数字加粗。

---

## 保存到 Obsidian

### 定位 vault(可移植,不写死)

保存前按优先级确定 vault 根目录:
1. 环境变量 `$OBSIDIAN_VAULT` 已设 → 直接用
2. 否则探测 iCloud Obsidian(各用户 home 通用,无特定用户名):
   ```bash
   ls -d ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/*/ 2>/dev/null   # 也可找本地含 .obsidian 的目录
   ```
3. 恰好一个 → 自动用它;🔴 **多个或零个 → STOP,问用户要 vault 路径**(别瞎猜目录)

### 选目录与文件名

**确定 vault 后自动保存,不再逐次询问**。按内容主题归类(vault 内已有相关目录就放进去,否则在 vault 根下建主题顶层目录):

| 内容主题 | 目录(示例,按实际 vault 结构调整) |
|----------|----------|
| 装修/选材/家电 | `House/经验避坑/` |
| 数码/科技 | `Tech/` |
| 美食/职场/旅行/其他 | 对应主题目录;拿不准放 vault 根 |

文件名用内容主题命名,不用日期前缀(如 `净水器选购避坑9点.md`)。
**同主题文件已存在 → 先 Read 再追加/更新,不直接覆盖。**

---

## 🔴 红线与反例(不要做)

- **不用 WebFetch 抓小红书**:基本只拿到登录墙;失败走 fetch-everything 隐身降级
- **抓不到就 HALT,不硬刷、不假装完整**:登录墙/风控挡住评论或正文 → 标注"未抓取"并告知用户,**绝不编造**评论/正文/数字
- **不跳图、不压缩转写**:imageList 每张都 Read;总结不把多个例子压成"多种情况"(详见 summary-standard.md)
- **保存不覆盖**:同名文件先 Read 再追加/更新,绝不直接覆盖既有笔记
- **微信公众号/Twitter/TikTok 评论别折腾**:无干净可部署方案,只交付正文或跳过,不耗时逆向
- **不写死个人路径/端口**:vault、代理、转写地址一律走环境变量或运行时探测(见依赖表)
- **写操作(发帖/评论/点赞)默认不做**:autocli/MCP 的 publish/comment 类命令属互动写操作,本技能只读;确需执行 🔴 先展示内容等用户确认

---

## 快速检查清单

- [ ] 图文帖:每张图都 Read 了?(含非XHS从正文提取的图)
- [ ] 视频:字幕/转写文本完整,没被截断?
- [ ] 评论:抓取了吗?增量观点写进"评论区补充"了?(部分抓取已标注?)
- [ ] 总结:每个要点、数字、例子、反面案例都写进去了?
- [ ] Obsidian 已保存?目录/文件名正确?同名已合并?
- [ ] **无论成功失败**,已跑 `find /tmp -maxdepth 1 -name 'social_clip_*' -exec rm -rf {} + 2>/dev/null` 清临时文件?
