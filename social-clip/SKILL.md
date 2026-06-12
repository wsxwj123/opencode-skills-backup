---
name: social-clip
description: >
  从社交平台链接提取完整内容并保存到 Obsidian 知识库。
  支持平台：小红书（图文帖/视频帖）、B站、微博、抖音、YouTube、Twitter 等。
  只要用户分享社交/视频平台链接（无论是否附带文字），都自动触发。
  也适用于直接粘贴短链（xhslink.com、b23.tv 等）的场景。
  也支持按关键词检索小红书（"搜小红书"、"找几篇XX笔记"），检索后提取选中笔记。
  除非用户明确说"看看就好"、"不用"等否定词，否则不需要确认。
  核心承诺：不跳过任何图片、不压缩转写内容、每个要点/例子/数据都完整保留。
---

# social-clip：社交内容剪藏技能

## 核心原则

内容提取的最大敌人是"偷懒"——跳过图片、压缩转写、遗漏细节。
这个技能存在的意义就是**强制执行完整提取**：图文帖逐张读图，视频帖完整转写，总结不允许省略任何有意义的要点、数字、举例或反面案例。

---

## 快速路由

先判断用户给的是**链接**还是**关键词**：

```
输入 → 有链接？
  ├── 否（只有关键词/主题，限小红书）
  │     → [小红书关键词检索] → 选笔记 → get_feed_detail → 图文/视频流程
  └── 是 → 判断平台
         ├── 小红书（xhslink / xiaohongshu）
         │     → 展开短链 → get_feed_detail
         │           ├── type=normal → [2A 图文帖流程]
         │           └── type=video  → [2B 视频帖流程]
         │     （MCP 失败 → fetch-everything 隐身降级，不用 WebFetch）
         ├── B站 / bilibili
         │     → yt-dlp 提取音频 → voice-bridge 转写 → [总结标准] → Obsidian
         └── 其他平台（YouTube/抖音/微博等）
               → yt-dlp 提取音频 → voice-bridge 转写 → [总结标准] → Obsidian
```

---

## 第一步：平台识别和 URL 解析

根据 URL 判断平台：

| URL 特征 | 平台 |
|----------|------|
| `xhslink.com` / `xiaohongshu.com` | 小红书 |
| `bilibili.com` / `b23.tv` | B站 |
| `weibo.com` / `t.cn` | 微博 |
| `douyin.com` / `iesdouyin.com` | 抖音 |
| `youtube.com` / `youtu.be` | YouTube |
| `twitter.com` / `x.com` | Twitter/X |

**短链展开**（xhslink.com、b23.tv 等）：
```bash
curl -sL --max-redirs 5 -o /dev/null -w "%{url_effective}" "SHORT_URL"
```

---

## 小红书关键词检索（无链接，按主题找内容）

当用户给的是**关键词/主题**而非具体链接（"搜小红书看看XXX"、"找几篇XXX的笔记"），先检索再提取：

### 1. 检索笔记

```
mcp__xiaohongshu__search_feeds(keyword="关键词", filters={...})
```

`filters` 可选项：`sort_by`(综合/最新/最多点赞/最多评论/最多收藏)、`note_type`(不限/视频/图文)、`publish_time`(不限/一天内/一周内/半年内)、`search_scope`、`location`。用户没指定就用默认。

### 2. 过滤并展示候选

- **丢弃 `modelType == "hot_query"` 的条目**（那是热搜词，不是笔记）
- 只保留 `modelType == "note"`，从 `noteCard` 取：`displayTitle`、`user.nickname`、`type`(normal/video)、`interactInfo`(点赞/收藏/评论数)
- 按互动数排序，列给用户选，或按用户要求自动取 top-N

### 3. 提取选中笔记

对每条选中的笔记，用其 `id`(=feed_id) 和 `xsecToken`(=xsec_token) 直接进入下面的详情流程（**跳过短链展开**，检索结果已带这两个字段）：

```
mcp__xiaohongshu__get_feed_detail(feed_id=<id>, xsec_token=<xsecToken>)
```

→ 之后按 `note.type` 走 [2A 图文帖] 或 [2B 视频帖]，多篇则逐篇走完整提取 + 总结。

---

## 小红书（XHS）完整流程

### 1. 获取帖子信息

从展开后的 URL 中提取 `feed_id`（URL path 最后一段）和 `xsec_token`（query 参数）。

调用 MCP：
```
mcp__xiaohongshu__get_feed_detail(feed_id=..., xsec_token=...)
```

返回的 `note.type` 决定后续流程：
- `"normal"` → 图文帖
- `"video"` → 视频帖

**MCP 调用失败时（报错/超时/空返回）**：
1. 检查 `feed_id` 和 `xsec_token` 是否提取正确（URL 格式：`/discovery/item/{feed_id}?xsec_token={token}`）
2. 仍然失败 → 用 **fetch-everything 执行器**降级抓取（它把小红书识别为动态站点，走 Scrapling 隐身浏览器，比 WebFetch 更能突破风控）：
   ```bash
   python3 ~/.claude/skills/fetch-everything/scripts/fetch_everything.py "完整XHS链接" --json
   ```
   能提取多少算多少；**不要用 WebFetch**（对小红书风控基本只能拿到登录墙）
3. 告知用户 "MCP 获取失败，已用 fetch-everything 隐身路线降级"

---

### 2A. 图文帖处理

**文字内容**：直接读取 `note.desc`，保留全文。

**图片内容**（关键！）：
- 从 `note.imageList` 拿到所有图片 URL
- **逐张下载并用 Read 工具读取**，Claude 原生视觉识别，不跳过任何一张
- 图片里可能有文字、表格、对比图，全部提取

**明确的迭代模式**（假设 imageList 有 N 张）：
```bash
# 第1张
curl -s "imageList[0].urlDefault" -o /tmp/social_clip_img_1.jpg
# → Read /tmp/social_clip_img_1.jpg

# 第2张
curl -s "imageList[1].urlDefault" -o /tmp/social_clip_img_2.jpg
# → Read /tmp/social_clip_img_2.jpg

# ...依此类推，每张都下载 + Read，共 N 次，一张不能跳过
# 下载失败（curl 报错或文件 < 1KB）→ 跳过该张但记录"第X张下载失败"，继续后续图片
```

所有图片读完后删除临时文件：
```bash
rm -f /tmp/social_clip_img_*.jpg /tmp/social_clip_img_*.png /tmp/social_clip_img_*.webp
```

---

### 2B. 视频帖处理

**Step 1**：用 Playwright 脚本拦截 CDN 视频 URL
```bash
python3 ~/.claude/skills/yt-dlp-downloader/xhs_get_video.py "XHS_URL"
# 输出多行 CDN URL，取第一行
```

**Step 2**：用 ffmpeg 直接从 CDN URL 提取音频（不下载整个视频，更快）
```bash
ffmpeg -http_proxy http://127.0.0.1:7897 \
  -i "CDN_URL" \
  -vn -acodec mp3 -ar 16000 -ac 1 \
  -y /tmp/social_clip_audio.mp3 2>/dev/null
```

如果 ffmpeg 走代理失败，尝试不带代理（CDN URL 通常可直连）：
```bash
ffmpeg -i "CDN_URL" -vn -acodec mp3 -ar 16000 -ac 1 -y /tmp/social_clip_audio.mp3 2>/dev/null
```

**ffmpeg 仍然失败（CDN 鉴权过期/网络不通）**：
```bash
# 降级：用 curl 把视频完整下载到本地再转写
curl -L --proxy http://127.0.0.1:7897 -o /tmp/social_clip_video.mp4 "CDN_URL"
# 再用 ffmpeg 从本地文件提取音频
ffmpeg -i /tmp/social_clip_video.mp4 -vn -acodec mp3 -ar 16000 -ac 1 -y /tmp/social_clip_audio.mp3
# 清理视频文件
rm -f /tmp/social_clip_video.mp4
```

**Playwright 脚本本身失败**（无 CDN URL 输出）：
- 检查脚本 `~/.claude/skills/yt-dlp-downloader/xhs_get_video.py` 是否存在
- 告知用户"XHS 视频 CDN 拦截失败，建议手动下载后提供本地路径"

**Step 3**：调用 voice-bridge 转写（先检查服务在线）
```bash
curl -s http://127.0.0.1:7788/health
# 返回 {"ok": true, "model_loaded": true} 才继续

curl -s -X POST http://127.0.0.1:7788/transcribe_file \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/social_clip_audio.mp3"}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('text',''))"
```

**Step 4**：清理临时文件
```bash
rm -f /tmp/social_clip_audio.mp3
```

---

## B站 / 其他平台（yt-dlp 流程）

适用于：B站、YouTube、微博、抖音、Twitter/X 等 yt-dlp 支持的平台。

**Step 1**：初始化环境并提取音频
```bash
source ~/.zshrc 2>/dev/null; eval "$(pyenv init -)" 2>/dev/null
yt-dlp \
  -x --audio-format mp3 --audio-quality 0 \
  -P "/tmp" \
  -o "social_clip_audio.%(ext)s" \
  "VIDEO_URL" 2>&1
```

B站高清格式需要 cookies：
```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  --cookies-from-browser chrome \
  -P "/tmp" -o "social_clip_audio.%(ext)s" "BILIBILI_URL"
```

**Step 2**：转写
```bash
curl -s -X POST http://127.0.0.1:7788/transcribe_file \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/social_clip_audio.mp3"}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('text',''))"
```

**Step 3**：清理
```bash
rm -f /tmp/social_clip_audio.mp3
```

---

## 内容总结标准（最重要！）

这一步是整个技能的核心价值所在。目标是把口语化的视频/图文内容，转化成**条理清晰、细节完整、可以直接当参考手册用**的书面笔记。

---

### 第一原则：零遗漏

以下内容**一条都不能省**：

**要点层面**
- 每一个编号点、每一个小点，包括"最后说一个细节"、"顺带提一下"这类看似补充的内容
- 作者特意强调的措辞（"千万别…"、"一定要…"、"这个很关键"）

**具体数字和规格**
- 价格：2000元、一年上千、贵了400多
- 尺寸/高度：窗帘盒至少15cm、离地1.3米、高约2米
- 容量/功率：1000G通量、16A三孔、10A五孔、额定4000L
- 时间：用了大半年、一年半载

**举的每一个具体例子**
- 作者说"比如…"、"就像…"、"举个例子…"之后的内容，完整保留
- 不能用"例如某些情况"这种模糊替代，要写出具体是什么情况

**反面案例和踩坑故事**
- "商家会说X，你别信"——X 是什么、为什么别信，都要写
- 作者自己踩坑的经历（买了退、退了再买、发现问题的过程）
- 品牌/产品的具体槽点

**操作顺序和条件**
- "先做A再做B"的顺序不能搞反
- "在X情况下选Y，在Z情况下选W"的条件分支要保留

**对比和选择依据**
- A vs B 的具体差异点
- "哪种情况选哪个"的判断逻辑

---

### 第二原则：口语→书面，不是口语→压缩口语

原始内容是口语，转化后必须是**书面化的结构化笔记**，不是把口语誊抄一遍。

**要做的事：**
- 把"就是那种…你懂吧…反正就是很烦"提炼成一句准确的书面表述
- 把散落在不同段落的同一话题归并到同一个章节下
- 用表格呈现多选项对比（比如洗衣机方案、插座规格）
- 用层级标题组织内容，让人扫一眼就能找到想看的部分

**不要做的事：**
- 不要把五个具体例子压成"有多种情况"
- 不要把"用不到半年就提示换滤芯，请了个祖宗回家供着"改写成"使用寿命较短"
- 不要因为觉得某个细节"不重要"就删掉——作者提到就是有意义的

---

### 第三原则：ASR 转写修正

voice-bridge 转写的文本有同音字错误，要结合上下文修正：

| 转写原文 | 正确含义 |
|----------|----------|
| 构思 | 起球（面料起毛球） |
| 安孔 / 1安 | 10A（安培，插座规格） |
| 五孔 / 无孔 | 五孔插座 |
| 3米 | 30厘米（高度描述时注意辨别） |
| 锤平 / 锤屏 | 冲筋（墙面找平工艺） |
| 赫6 / 赫7 | 鹤6 / 鹤7（雷鸟电视型号） |

遇到明显不通顺的词，先想"这个读音对应什么装修/生活用语"，再判断。

---

### 笔记结构模板

```
# [内容主题]

来源：[平台@作者] / [B站视频标题]

[一句话核心结论或前言]

---

## [大标题1]

### [子标题]
- 具体要点（含数字、例子）
- 反面案例：商家会说X → 实际是Y

| 对比项 | 选项A | 选项B |
|--------|-------|-------|
| ...    | ...   | ...   |

## [大标题2]
...
```

重要数字/规格用**加粗**，正确 vs 错误的对比要视觉上清晰区分。

---

## 保存到 Obsidian

Obsidian vault 路径：
`/Users/wsxwj/Library/Mobile Documents/iCloud~md~obsidian/Documents/obsidian-xwj-ios/`

**自动保存，不需要询问用户**。根据内容主题判断目录：

| 内容类型 | 保存目录 |
|----------|----------|
| 装修/选材/施工/家电/软装 | `House/经验避坑/` |
| 其他装修相关（预算/报价/攻略） | `House/` 下对应子目录 |
| 其他主题 | 根据内容判断，或放 vault 根目录 |

文件名：用内容主题命名，不用日期前缀，例如：
- `窗帘选购避坑4点.md`
- `全屋插座预留指南.md`
- `净水器选购避坑9点.md`

**如果同主题文件已存在，先 Read 再追加/更新，不要直接覆盖。**

---

## 快速检查清单

完成前自查：

- [ ] 图文帖：imageList 里每张图都 Read 了吗？
- [ ] 视频帖：转写文本完整了吗？没有被截断？
- [ ] 总结：每个要点都写进去了吗？具体数字、例子、反面案例？
- [ ] Obsidian 文件已保存？路径正确？
- [ ] 临时文件（/tmp/social_clip_*）已清理？
