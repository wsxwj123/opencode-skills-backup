---
name: social-clip
description: >
  分享社交/视频平台链接(小红书、B站、知乎、微博、豆瓣、抖音、YouTube、Twitter 等)、粘贴短链(xhslink.com、b23.tv 等),或要求"搜/找某主题的内容或评论"时,**优先用本技能**——不要用通用的 read / fetch-everything / autocli(它们只取单页正文,会漏图、漏视频、漏评论)。
  本技能做完整社交剪藏:主动检索、逐张下载图片识图、音视频转文字、抓评论,整理后按需存入 Obsidian。
  支持小红书(原生检索+评论最全)、B站、知乎、微博、豆瓣、抖音、YouTube、Twitter、Reddit(评论满血)、微信公众号(仅正文)、网易云音乐(搜歌/歌词/乐评,不能下音频)等。
  触发后按归档意图分档:明示"存/记/收藏/整理到笔记"才全量提取并存档;只想知道讲了啥则先轻量给结论再问是否存;说"看看就好"则仅速览。
  核心承诺(全量档):不跳过任何图片、不压缩转写、每个要点/例子/数据/高赞评论都完整保留。
---

# social-clip:社交内容聚合技能

## 核心原则

内容提取的最大敌人是"偷懒"——跳过图片、压缩转写、遗漏评论里的增量信息。
**进入全量归档档时**(见下「意图分档」),强制**完整提取**:图文逐张读图,视频完整转写,评论抓取增量观点,总结不省略任何有意义的要点、数字、例子、反面案例。速览档则只给轻量结论,不下载、不存。

---

## 能力矩阵(决定每个平台用什么后端)

| 平台 | 主动检索 | 正文/文案 | 图片识图 | 视频/音频 | 评论 |
|------|----------|-----------|----------|-----------|------|
| 小红书 | ✅ MCP search | ✅ `desc` | ✅ `imageList` | ✅ Playwright+ffmpeg | ✅ MCP 满血 |
| B站 | ✅ autocli search | ✅ autocli read | read 提图 | ✅ autocli subtitle→yt-dlp | 🟡 尽力(read/fetch) |
| 知乎/微博/豆瓣 | ✅ autocli search(登录态) | ✅ autocli read | read 提图 | yt-dlp(若视频) | 🟡 尽力(脆弱) |
| YouTube/抖音/其他 | autocli search / 给链接 | autocli read | read 提图 | yt-dlp 字幕优先 | 🟡 尽力 |
| Reddit | ✅ autocli search | ✅ autocli read | read 提图 | 🟡 yt-dlp(若视频) | ✅ autocli read **直接带帖子+评论(满血)** |
| 微信公众号 | ❌ 无 | 🟡 autocli weixin download / fetch 单篇 | read 提图 | — | ❌ 全网无方案 |
| 网易云音乐 | ✅ curl 免加密接口 | ✅ 歌词(原词/译/罗马音) | 🟡 封面图 | ❌ 下音频需加密 | ✅ 热门+分页 |

- **后端原则**:非小红书平台一律先试 `autocli`(复用本机 Chrome 登录态,对登录墙站点远比隐身抓取可靠),无对应命令/抓空再降级 `fetch-everything`,再不行 🛑 HALT 告知用户。
- ✅ 满血可靠 · 🟡 尽力而为(尤其评论:autocli 无通用读评论命令,非小红书评论靠 read/fetch 部分抓取,抓不到不硬刷)
- **评论 MCP 可选增强**:为某平台装了评论 MCP(B站/知乎/抖音/豆瓣,见 platform-recipes.md)则自动用它满血读评论;不装也能跑,纯 opt-in、不进硬依赖。
- **非小红书平台的所有抓取配方在 `references/platform-recipes.md`**——处理它们时先读那个文件。
- **网易云音乐**单独走 `references/netease-recipe.md`(curl 直连免加密接口,不用 autocli):遇 `music.163.com` 链接或"搜网易云歌曲/歌单/歌手/拿歌词/拿评论"时读它;能搜歌、歌词(含译/罗马音)、热门评论、歌单/歌手详情,**下载音频做不到**(需加密)。

---

## 🛡️ 风控自我约束(账号安全,务必遵守)

用你真实账号做自动化(尤其小红书)有**封号风险**。硬性约束,宁可慢、宁可少,不赌账号:

**① 小批量,不海捞**
- 关键词检索:一次最多取 **8–10 条**候选给用户挑,别一次拉几十篇详情
- 评论:默认前 10 条(`get_feed_detail` 自带),**不主动 `load_all_comments`**,除非用户明确要全部
- 多篇处理:逐篇之间**停 2–3 秒**(`sleep 2`),别连发

**② 撞到风控 🛑 立即熔断,绝不硬刷**
识别这些 = 撞风控了:
- 小红书:"笔记不可访问/请扫码"、`search_feeds` 超时、要验证码
- 网页/autocli:登录墙、验证码、`Access denied`、`429` 限流
→ **立刻停该平台的自动请求,不重试**(越刷越严),并告诉用户人话:
  "撞到 X 的风控了,先停下。要么我换隐身方式抓(可能不全),要么你过会儿再试,别连着刷免得封号。"

**③ 写操作永不自动**
发帖/评论/点赞(MCP/autocli 的 `publish`/`comment`/`like`)封号风险最高,本技能**只读**;确需互动 🔴 先给用户看内容、等点头。

> 原则:像正常人浏览,不像爬虫。撞墙就停,不硬冲。

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
- `OBSIDIAN_VAULT`(可选):覆盖默认 vault;不设则用固定的 `obsidian-xwj-ios`(本技能本人专用)
- `VOICE_BRIDGE_URL`:转写服务地址,默认 `http://127.0.0.1:7788`
- 网络代理:默认直连;本机需代理时 `export http_proxy=...` 即可,技能不写死端口

> **跨技能路径按当前 runtime 的 skills 根解析**:Claude Code=`~/.claude/skills`、Codex=`~/.codex/skills`、OpenCode=`~/.config/opencode/skills`。本技能与 fetch-everything/yt-dlp-downloader 同级,**取本技能所在目录的父目录**即可定位它们;下文示例按 Claude Code 路径书写,换 runtime 时相应替换根目录。不出现任何特定用户名的绝对路径。

---

## 第〇步:判断意图档位(决定走多深)

给链接/关键词后,**先看用户有没有明示归档意图**,别默不作声跑完全套再建档:

| 用户信号 | 档位 | 做什么 |
|---------|------|--------|
| 明示"存/记/收藏/整理到笔记/记下来/存进库" | 📦 全量归档 | 完整提取(图/视频/评论)+ 总结 + 存 Obsidian |
| 只给链接 / 问"讲了啥/值不值得/什么内容/怎么样" | 👀 速览 | 轻量提取给结论(读正文/desc、必要时扫几张关键图),**结尾问**"要我提取完整干货存进 Obsidian 吗?" |
| 明示"看看就好/不用/不存" | ⚡ 速读 | 只读正文/desc 给要点,不下载图片、不转写、不存 |

> 拿不准 → 走 👀 速览档(轻量+问),用户回"存"再走 📦 全量。**只有 📦 全量档**才执行下面的完整下载/转写/识图/存档流程。

---

## 快速路由(确定要走全量/检索后)

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
| `reddit.com` / `redd.it` | Reddit |
| `mp.weixin.qq.com` | 微信公众号 |
| `music.163.com` / `y.music.163.com` | 网易云音乐 |

**短链展开**(xhslink.com、b23.tv 等):
```bash
curl -sL --max-redirs 5 -o /dev/null -w "%{url_effective}" "SHORT_URL"
```

---

## 临时文件管理(防残留)

下载的图片/视频/音频统一用前缀 `/tmp/social_clip_*`。**会下载的流程(图文配图/视频/音频)开始第一步先清上次残留、全部完成后再清一次,并明确告知用户"已删除下载的临时文件(图片/视频/音频)"**——幂等 self-healing:某次中途跳步残留,下次入口也兜底清掉,不累积。统一清理命令:
```bash
find /tmp -maxdepth 1 -name 'social_clip_*' -exec rm -rf {} + 2>/dev/null
```
> 🔴 **清理必须用 `find`,禁止 `rm -rf /tmp/social_clip_*`**:zsh 下通配无匹配会报错中断,且一条命令含多个通配只要一个无匹配就连累整条(该删的也删不掉)。`find` 无匹配静默、bash/zsh/Linux 一致。
> 技能跨多次独立 Bash 调用执行,单进程 `trap` 覆盖不了全程,故用"入口+出口双清"而非 trap。

---

## 小红书(XHS)完整流程

### 关键词检索(无链接时)

```
mcp__xiaohongshu-mcp__search_feeds(keyword="关键词", filters={...})
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
mcp__xiaohongshu-mcp__get_feed_detail(feed_id=..., xsec_token=...)
```
`note.type`:`"normal"`→图文帖,`"video"`→视频帖。**返回里已含前10条评论**(见 2C)。
> 返回结构(实测):`data.note.{title,desc,type,imageList[].urlDefault,interactInfo}` + `data.comments.list[]`(每条 `content`/`likeCount`/`userInfo.nickname`/`subComments[]` 二级回复)。下文 `note.xxx` 均指 `data.note.xxx`。

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

**Step 1** Playwright 拦截 CDN 视频 URL(**先初始化 pyenv**——playwright 装在 pyenv 的 python 里,系统 python3 没装,不初始化会误报"没装 playwright"):
```bash
source ~/.zshrc 2>/dev/null; eval "$(pyenv init -)" 2>/dev/null   # 确保用 pyenv 的 python
python3 ~/.claude/skills/yt-dlp-downloader/xhs_get_video.py "XHS_URL"   # 多行CDN URL,取第一行
```
> 若仍报错,看**确切信息**:`No module named playwright`=python 环境问题(上面没生效);`Target page/context closed`或`browser is already in use`=Chrome 占用了 Profile 5,关掉 Chrome 再跑。
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
mcp__xiaohongshu-mcp__get_feed_detail(feed_id=..., xsec_token=...,
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

### 定位 vault(本人专用,固定)

本技能仅作者本人使用,vault **固定**为 iCloud 下的 `obsidian-xwj-ios`,**不探测、不询问、绝不存到任何其他 vault 或文件夹**:
```bash
VAULT="${OBSIDIAN_VAULT:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/obsidian-xwj-ios}"
[ -d "$VAULT" ] || echo "⚠️ vault 不存在,确认 iCloud Obsidian 已同步;在它出现前不要存到别处"
```
> 下文 `$VAULT` 即此固定 vault。(`OBSIDIAN_VAULT` 环境变量仅为换机时覆盖,日常不用设。)

### 选目录与文件名(用你已有结构,别硬套内置主题)

1. **先列 vault 现有顶层目录**,按你真实的结构归类——不要用内置英文主题表硬套:
   ```bash
   ls -d "$VAULT"/*/ 2>/dev/null   # 看真实目录命名(可能是 02-装修/生活/家/Inbox 等个人化命名)
   ```
2. 内容主题**匹配最接近的现有目录**就放进去(装修内容→你已有的 `House/`/`装修/`/`生活`,而非新造一个)
3. **没有能匹配的现有目录**才在 vault 根新建,且 🔴 **告知落点**(如"存到了新建的 `装修避坑/` 下")
4. 文件名用内容主题命名,不用日期前缀(如 `净水器选购避坑9点.md`)
5. **同名文件已存在 → 先 Read 再追加/更新,绝不直接覆盖**

> 让用户**始终知道笔记存哪了**:每次保存后一句"已存到 `<目录>/<文件名>`"。

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

## 失败/降级时对用户怎么说(人话,不吐术语)

内部用 MCP/autocli/Scrapling/CDP/CDN 这些后端,但**对用户只说人话 + 明确下一步**,别让用户看"MCP 失败已隐身降级"这种话:

| 内部情况 | ❌ 别这么说 | ✅ 这么说 |
|---------|-----------|----------|
| 评论需登录态没抓到 | "评论需登录态/CDP" | "正文拿到了,评论要登录才能看、这条没抓到——要的话我用你 Chrome 登录态再试" |
| 小红书 MCP 失败转 fetch | "MCP 失败已隐身降级" | "小红书原生通道没通,我换了个方式还是拿到了图文和前10条评论,评论可能不全" |
| 视频 CDN 拦截失败 | "CDN 拦截失败" | "视频源没取到,方便的话你把视频下下来给我本地路径,我接着转写" |
| 转写服务未起 | "voice-bridge 未就绪" | "语音转文字服务没开,我先用字幕;没字幕的话你开下服务、或我只整理画面和简介" |

原则:告诉用户 ①拿到了什么 ②缺了什么 ③要不要他做点什么(登录/开服务/给文件)。

---

## 快速检查清单(📦 全量归档档完成前自查;速览/速读档不适用)

- [ ] 图文帖:每张图都 Read 了?(含非XHS从正文提取的图)
- [ ] 视频:字幕/转写文本完整,没被截断?
- [ ] 评论:抓取了吗?增量观点写进"评论区补充"了?(部分抓取已标注?)
- [ ] 总结:每个要点、数字、例子、反面案例都写进去了?
- [ ] Obsidian 已保存?目录/文件名正确?同名已合并?
- [ ] **无论成功失败**,已跑 `find /tmp -maxdepth 1 -name 'social_clip_*' -exec rm -rf {} + 2>/dev/null` 清临时文件,**并告知用户已删除**?
