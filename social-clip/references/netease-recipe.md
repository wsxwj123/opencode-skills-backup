# 网易云音乐抓取配方

> **何时加载**:用户分享 `music.163.com` / `y.music.163.com` 链接,或要求搜网易云的歌曲/歌单/歌手、拿歌词、拿评论时读本文件。
> **后端现状**:autocli **不支持**网易云(无 `netease` 子命令)。本配方走**网易云免加密老接口**直连(`curl` / `python3`),零安装、无需登录。

---

## 能力总览(实测 2026-06-19,代理 7897 下全部通过)

| 能力 | 可行性 | 途径 |
|------|--------|------|
| 搜索 歌曲/歌单/歌手/专辑 | ✅ 满血 | `/api/search/get/web`(老接口,免加密) |
| 歌词(含翻译/罗马音) | ✅ 满血 | `/api/song/lyric`(免加密) |
| 热门评论 + 全部评论(分页) | ✅ 满血 | `/api/v1/resource/comments/...`(免加密,含 hotComments) |
| 歌单详情 + 曲目列表 | ✅ 满血 | `/api/v3/playlist/detail`(免加密) |
| 歌手简介 + 热门 50 首 | ✅ 满血 | `/api/v1/artist/{id}`(免加密) |
| 歌曲详情(名/艺人/专辑/封面) | ✅ 满血 | `/api/song/detail`(免加密) |
| 专辑曲目(`/api/album/{id}`) | ⚠️ 受限 | 该接口被风控(`code -462` 要求绑手机)→ 改用搜歌单/歌曲详情绕开 |
| 听歌/下载音频文件 | ❌ 做不到 | 播放 URL 走 weapi/eapi **加密 + 版权风控**,零安装拿不到。本技能不做下载 |

> **诚实边界**:网易云核心接口(播放地址、登录态操作)确实是 weapi/eapi 加密 + 风控,**零安装做不了**。但「搜索 / 歌词 / 评论 / 歌单 / 歌手」这几个用户要的能力,老接口至今开放,**不用装任何东西**。别把做不到的下载硬塞进流程。

---

## 公共请求约定

所有请求都加这两个头(缺 Referer 部分接口会拒),走代理:

```bash
export http_proxy=http://127.0.0.1:7897 https_proxy=http://127.0.0.1:7897   # 按本机代理端口,无代理可去掉
UA="User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
REF="Referer: https://music.163.com"
```

链接里的 ID 提取(分享链常见形态):
- 歌曲 `music.163.com/song?id=1330348068` 或 `/#/song?id=...` → `id`
- 歌单 `music.163.com/playlist?id=24381616` → `id`
- 歌手 `music.163.com/artist?id=6452` → `id`
- 短链 `y.music.163.com/m/song?id=...` 同样含 `id=`,直接取数字即可;拿不到 ID 时先 `curl -sIL "<短链>"` 看跳转后的 `Location`。

---

## 1. 搜索(歌曲 / 歌单 / 歌手 / 专辑)

一个接口,靠 `type` 区分。`s`=关键词(URL 编码),`type`:1=单曲 100=歌手 10=专辑 1000=歌单。

```bash
# 搜歌曲(type=1)
curl -s "https://music.163.com/api/search/get/web?s=$(python3 -c 'import urllib.parse;print(urllib.parse.quote("起风了"))')&type=1&limit=10&offset=0" \
  -H "$UA" -H "$REF" --max-time 15 \
  | python3 -c 'import json,sys; d=json.load(sys.stdin)["result"]; [print(s["id"], s["name"], "-", "/".join(a["name"] for a in s["artists"])) for s in d.get("songs",[])]'

# 搜歌单 type=1000 / 歌手 type=100 / 专辑 type=10 —— 改 type 即可,返回字段分别在 result.playlists / result.artists / result.albums
```

返回结构:`result.songs` / `result.playlists` / `result.artists` / `result.albums`。把候选 id+名称列给用户选,或取 top-N 进详情。

---

## 2. 歌词(含翻译 + 罗马音)

```bash
curl -s "https://music.163.com/api/song/lyric?id=1330348068&lv=1&kv=1&tv=-1&rv=-1" \
  -H "$UA" -H "$REF" --max-time 15 \
  | python3 -c '
import json,sys,re
d=json.load(sys.stdin)
def strip(x): return re.sub(r"\[\d+:\d+\.\d+\]","",x or "").strip()
print("=== 原词 ==="); print(strip(d.get("lrc",{}).get("lyric")))
t=d.get("tlyric",{}).get("lyric")
if t: print("\n=== 翻译 ==="); print(strip(t))
r=d.get("romalrc",{}).get("lyric")
if r: print("\n=== 罗马音 ==="); print(strip(r))
'
```

- 字段:`lrc`=原词、`tlyric`=中文翻译(外语歌才有)、`romalrc`=罗马音(日韩歌才有)、`klyric`=逐字卡拉OK。
- 纯音乐返回空 lyric;歌词带 `[mm:ss.xxx]` 时间轴,进总结时按需 strip 掉。

---

## 3. 评论(热门 + 全部,满血分页)

资源 ID 拼前缀:歌曲 `R_SO_4_{songId}`、歌单 `A_PL_0_{playlistId}`、专辑 `R_AL_3_{albumId}`、MV `R_MV_5_{mvId}`。

```bash
# 歌曲热门评论(hotComments 直接就是按赞排序的精华)
curl -s "https://music.163.com/api/v1/resource/comments/R_SO_4_1330348068?limit=20&offset=0" \
  -H "$UA" -H "$REF" --max-time 15 \
  | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("总评论数:", d.get("total"))
print("\n=== 热门评论 ===")
for c in d.get("hotComments",[]):
    print(f"[{c.get(\"likedCount\",0)}赞] {c[\"user\"][\"nickname\"]}: {c[\"content\"]}")
'
```

- `hotComments`=热门评论(已按点赞排序,做剪藏直接用这个),`comments`=最新评论流(`offset`/`limit` 翻页,`total` 是真实总量,`more` 标识还有没有)。
- 这是老接口残留的免加密通道,**意外地好用**——歌曲评论满血。歌单/专辑评论同理,换前缀即可(冷门歌单可能确实 0 评论,不是接口坏)。

---

## 4. 歌单详情 + 曲目

```bash
curl -s "https://music.163.com/api/v3/playlist/detail?id=24381616&n=1000" \
  -H "$UA" -H "$REF" --max-time 15 \
  | python3 -c '
import json,sys
p=json.load(sys.stdin)["playlist"]
print("歌单:", p["name"], "| 创建者:", p["creator"]["nickname"], "| 曲目数:", p["trackCount"])
print("简介:", (p.get("description") or "")[:200])
for t in p.get("tracks",[]):
    print(t["id"], t["name"], "-", "/".join(a["name"] for a in t["ar"]))
'
```

- `n` 控制返回曲目数;超大歌单 `tracks` 可能只回前若干首 + `trackIds` 全量 id 列表,需要全曲再按 id 批量查 `/api/song/detail`。

---

## 5. 歌手(简介 + 热门 50 首)

```bash
curl -s "https://music.163.com/api/v1/artist/6452" \
  -H "$UA" -H "$REF" --max-time 15 \
  | python3 -c '
import json,sys
d=json.load(sys.stdin)
a=d["artist"]
print("歌手:", a["name"], "| 单曲数:", a.get("musicSize"), "| 专辑数:", a.get("albumSize"))
print("简介:", (a.get("briefDesc") or "")[:300])
print("\n=== 热门歌曲 ===")
for s in d.get("hotSongs",[]):
    print(s["id"], s["name"])
'
```

返回 `artist`(含 `briefDesc` 简介)+ `hotSongs`(热门约 50 首)。

---

## 6. 歌曲详情(批量)

```bash
# ids 是 JSON 数组的 URL 编码
curl -s "https://music.163.com/api/song/detail?ids=$(python3 -c 'import urllib.parse;print(urllib.parse.quote("[1330348068,347230]"))')" \
  -H "$UA" -H "$REF" --max-time 15 \
  | python3 -c 'import json,sys; [print(s["id"], s["name"], "-", "/".join(a["name"] for a in s["artists"]), "| 封面:", s.get("album",{}).get("picUrl","")) for s in json.load(sys.stdin)["songs"]]'
```

封面图 URL 在 `album.picUrl`,要识图就走 SKILL.md / platform-recipes.md 的「图片识图」逐张 Read。

---

## 失败处理 / 风控

- 某接口返回 `{"code":-462,...,"blockText":"绑定手机后..."}` 或 `{"code":20001}` → 该接口被风控(如 `/api/album`、老版 `/api/playlist/detail`)。**换上面列出的可用接口**(v3 歌单、song/detail),别在被封接口上重试。
- 连续超时/返回 HTML 登录页 → 老接口可能临时调整,降级到「可选增强」方案(下),或 HALT 告知用户「网易云接口临时不可用」。
- **不要高频刷**:评论/搜索别开大并发,撞风控就停,符合 SKILL.md 风控约束。

---

## 可选增强(⚠️ 需用户确认安装,本配方不执行)

零安装方案已覆盖用户要的全部能力(搜索/歌词/评论/歌单/歌手)。**仅当**需要更多(如**播放/下载音频、登录态操作、签到、私人歌单**)时,才考虑下面方案——**安装动作必须先经用户明确同意**:

| 方案 | 装什么 | 能多拿什么 | 代价 |
|------|--------|-----------|------|
| **NeteaseCloudMusicApi**(`Binaryify/NeteaseCloudMusicApi`,社区维护已归档) | `git clone` + `npm install` 起本地 Node server(默认 :3000) | 内置 weapi/eapi 加密,几乎全部官方能力(播放 URL、登录、私人内容、每日推荐) | 需起常驻 server;原作者已停更,部分接口随官方风控失效 |
| **NeteaseCloudMusicApi 的 MCP 封装** | 同上 + 一层 MCP wrapper | 同上,且能作为 `mcp__*` 工具直接调 | 同上 + 多一层维护 |

> 这些都涉及 `git clone` / `npm install` / 起 server,属硬约束禁止的安装动作。**如用户要这些能力,先把上表方案+步骤摆给用户,等明确确认再动手**,绝不自行安装。

---

## 与 SKILL.md 流程衔接

拿到歌词/评论/歌单文本后,进 `summary-standard.md` 总结流程;封面/歌手图走「图片识图」。网易云**无视频/音频转写需求**(本配方不下载音频),跳过 voice-bridge 管线。
