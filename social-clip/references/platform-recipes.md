# 各平台抓取配方(非小红书)

> **何时加载**:处理 B站/知乎/微博/豆瓣/YouTube/抖音等**非小红书**平台,或需主动检索它们的内容时读本文件。
> 小红书全流程在 SKILL.md 正文(它有原生 MCP,评论最完整)。

---

## 后端优先级:autocli 打头,fetch-everything 兜底

`autocli` 复用本机 Chrome 登录态,对登录墙站点(知乎/微博)远比隐身抓取可靠——**非小红书平台一律先试 autocli**。
- 假设 `autocli` 在 PATH;`command -v autocli` 找不到 → 提示安装(见 SKILL.md 依赖表),不写死绝对路径;`autocli doctor` 自检
- autocli 无对应命令/抓空 → 降级 `fetch-everything`(Scrapling 隐身 + CDP 登录态兜底)→ 再不行 HALT 告知用户

| 能力 | 首选(autocli) | 降级(fetch-everything) |
|------|----------------|------------------------|
| 主动检索 | `autocli <site> search "关键词" --format json`(关键词是**位置参数**) | 抓搜索页(脆弱) |
| 正文/文案 | `autocli read "<url>"`(Readability→Markdown,含登录墙页) | `fetch_everything.py "<url>" --json` |
| B站字幕 | `autocli bilibili subtitle <BVID>`(bvid 是**位置参数**) | yt-dlp 字幕 |
| 视频音频 | yt-dlp(见下) | — |
| 评论 | ⚠️ autocli 无通用读评论命令 | 见下「评论」 |

---

## 主动检索(登录态,可靠)

各平台都有 `search`,直接拿候选条目列给用户选或取 top-N,再逐条进详情:
```bash
# 关键词是位置参数,不要加 --keyword/--query;--type/--limit/--format 才是选项
autocli bilibili search "显卡选购" --type video --limit 20 --format json
autocli zhihu     search "大模型"   --limit 20 --format json
autocli weibo     search "关键词"   --limit 20 --format json
autocli douban    search "书名"     --type book --limit 20 --format json   # --type movie|book|music
autocli youtube   search "LLM"       --limit 20 --format json
autocli reddit    search "关键词"     --limit 20 --format json   # 可选 --subreddit xxx / --sort relevance|hot|top|new|comments / --time hour|day|week|month|year|all
```

> **微信公众号无检索**:`autocli weixin` 只有 `download`(下单篇),不能按关键词搜文章。要看公众号内容只能拿到具体文章链接(`mp.weixin.qq.com/...`)再抓单篇。

---

## 正文 / 文案(图文帖、文章、文字微博)

非视频内容**不要走音频管线**(无音轨,yt-dlp 必失败)。`autocli read` 优先:
```bash
autocli read "<详情页URL>"                       # → Markdown 正文
# 抓空/不是正文 → 降级
python3 ~/.claude/skills/fetch-everything/scripts/fetch_everything.py "<url>" --json
```
拿到正文 → 进总结流程(summary-standard.md)。

---

## Reddit(正文+评论一把抓,满血)

Reddit 评论和小红书一样满血:`autocli reddit read` **一次同时返回帖子正文 + 评论树**,不用再单独抓评论。
```bash
# read 接 post-id 或完整 URL(位置参数,不要加 --url)
autocli reddit read "https://www.reddit.com/r/xxx/comments/1abc123/..." --format json
autocli reddit read 1abc123 --format json                      # 也可直接给 post-id
# 评论控制:--limit 一级评论数(默认25) --depth 回复深度(默认2) --replies 每层回复数(默认5)
#           --sort best|top|new|controversial|old|qa --max-length 单条最长字符(默认2000)
autocli reddit read "<url>" --limit 30 --depth 3 --format json
```
- 正文(selftext)、评论树(含楼中楼)都在这一条结果里 → 直接进总结,评论区高赞/补充观点单列"评论区补充"。
- 帖子带图/视频 → 从结果里取媒体 URL,图片走下方「图片识图」逐张 Read;视频走下方「视频音频」yt-dlp。
- 风控:`--limit` 别拉太大(默认 25 已够),撞 `429`/`Access denied` 即停,见 SKILL.md 风控约束。

---

## 微信公众号(只抓单篇正文,不能搜、没评论)

**只有文章链接才能处理**(`mp.weixin.qq.com/s/...`),且**只拿正文**:
```bash
autocli weixin download "<公众号文章URL>"          # 下载为 Markdown(首选)
# 抓空/失败 → fetch-everything 兜底(它专门处理公众号链接)
python3 ~/.claude/skills/fetch-everything/scripts/fetch_everything.py "<公众号文章URL>" --json
```
拿到正文 → 从中提图走「图片识图」逐张 Read → 进总结流程。

> 🔴 **公众号边界**:需求就是**抓正文(+图)即可,评论不取**(用户明确无需评论,别去折腾);不能按关键词搜文章(无检索接口)。对用户人话说:"公众号给我文章链接我抓正文和图,搜不了、评论也不抓(你也用不上)。"

---

## 图片识图(非小红书)

从正文(autocli read 的 Markdown / fetch-everything 结果)提取图片 URL,**逐张下载 + Read**(Claude 原生视觉),不跳过:
```bash
curl -sL "图片URL" -o /tmp/social_clip_img_1.jpg   # 失败或 <1KB 记"第X张失败"继续
# → Read /tmp/social_clip_img_1.jpg
find /tmp -maxdepth 1 -name 'social_clip_img_*' -exec rm -f {} + 2>/dev/null
```
图里的文字、表格、对比图全部提取。

---

## 视频音频(B站 / YouTube / 抖音 / 微博视频等)

**B站字幕最优**(autocli 走登录态,比 yt-dlp 稳):
```bash
autocli bilibili subtitle <BVID> --format json   # bvid 位置参数;有字幕→去时间轴→进总结
```

**通用字幕优先**(其他平台,有官方/自动字幕时比 ASR 快且准):
```bash
source ~/.zshrc 2>/dev/null; eval "$(pyenv init -)" 2>/dev/null
yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "zh.*,en.*" \
  --convert-subs srt -o "/tmp/social_clip_sub.%(ext)s" "<VIDEO_URL>" 2>&1
find /tmp -maxdepth 1 -name 'social_clip_sub*.srt'   # 有输出 → 读 srt 去时间轴(zsh 安全)
```

**无字幕 → 降级 ASR**:
```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 -P "/tmp" -o "social_clip_audio.%(ext)s" "<VIDEO_URL>" 2>&1
# B站高清需 cookies:加 --cookies-from-browser chrome
```
转写前先 health 检查(见 SKILL.md「voice-bridge 转写统一前置」),地址取环境变量:
```bash
VB="${VOICE_BRIDGE_URL:-http://127.0.0.1:7788}"
curl -s "$VB/health"   # 未就绪→跳过转写,改用字幕或提示
curl -s -X POST "$VB/transcribe_file" -H "Content-Type: application/json" \
  -d '{"path": "/tmp/social_clip_audio.mp3"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('text',''))"
find /tmp -maxdepth 1 -name 'social_clip_*' -exec rm -rf {} + 2>/dev/null   # 清本次音频/字幕
```

---

## 评论(非小红书)

autocli 对 B站/知乎/微博/豆瓣**没有读评论命令**(满血评论途径:小红书走 MCP 见 SKILL.md 2C;**Reddit 走 `autocli reddit read` 自带评论,见上方 Reddit 配方**)。
评论后端按可用性**分级**——**对应平台评论 MCP 全部可选(opt-in),装了就满血、没装就兜底,技能在裸环境照常运行**:

1. **(可选增强)本机已装该平台评论 MCP** → 优先用它读评论(满血,含楼中楼/分级)。运行前用工具列表判断对应 `mcp__*` 是否可用;可用就走 MCP。各平台推荐(想要评论增强者自行安装,**本技能不代装、不设为依赖**):

   | 平台 | 推荐 MCP(GitHub/npm) | 安装 | 登录态 |
   |------|----------------------|------|--------|
   | B站 | `@xzxzzx/bilibili-mcp` | `npx -y` | Cookie(独立 config 存,会过期) |
   | 知乎 | `Douyh123/zhihu-mcp` | pip + playwright | 扫码 |
   | 抖音 | `pazwusimple-netizen/douyin-mcp` | Node + playwright | 扫码(autocli 不支持抖音,装了才有抖音能力) |
   | 豆瓣 | `yoyooyooo/douban-mcp` | `npx` | 详情页需 Cookie |

   > 微信公众号/Twitter/TikTok 评论**无干净可部署方案**,别折腾,直接走第 2 级或只交付正文。

2. **没装 MCP** → 先看 `autocli read "<url>"` 的 Markdown 是否自带部分评论(Readability 有时会带);否则 fetch-everything 走浏览器路线抓**首屏渲染后**评论,需滚动/点"查看更多"的深层评论拿不全
3. **都拿不到** → 只交付正文 + 标注"评论需登录态/未能抓取",**不假装完整、不硬刷**
