---
name: yt-dlp-downloader
description: Download videos/audio from YouTube, Bilibili, and 1000+ sites using yt-dlp. Always ask preferences before downloading.
---

# yt-dlp Video Downloader

Download videos/audio from YouTube, Bilibili, Twitter, TikTok, and 1000+ platforms using yt-dlp.

## MANDATORY WORKFLOW (每次必问)

当用户提供视频链接时，**必须先问以下问题**再执行下载：

### 1. 下载模式 (必问)
- **视频** - 下载视频+音频（合并）
- **音频** - 仅提取音频
- **都下载** - 下载视频并同时提取音频（保留视频）

### 2. 质量选择 (必问)
- **最佳** - 不限制（可能很大）
- **1080p** - 1080p或更低（默认推荐）
- **720p** - 720p或更低
- **480p** - 480p或更低

### 3. 格式选择 (必问)
- **视频容器**：mp4（默认）/ mkv / webm
- **音频格式**：mp3（默认）/ m4a

### 4. 保存路径 (必问)
- **默认**：`/Users/wsxwj/Downloads/video-download`
- **桌面**：`/Users/wsxwj/Desktop`
- **自定义**：用户指定的完整路径

### 5. 播放速度 (可选)
- **原速** (默认)
- **倍速** (如 1.25x, 1.5x, 2.0x) - *注意：需要重新编码，处理时间较长*

### 6. 可选项 (根据需要问)
- 是否下载字幕？（中文/英文/自动生成）
- 播放列表处理？（全部/指定范围/单个视频）
- 需要登录？（B站高清/私密视频）

## 默认值总结

- 模式：视频
- 质量：1080p封顶
- 视频容器：mp4
- 音频格式：mp3
- 播放速度：原速 (1.0x)
- 输出目录：`/Users/wsxwj/Downloads/video-download`
- 文件名：`%(title)s [%(id)s].%(ext)s`（保留中文）

## 命令构建模板

### 质量映射

```bash
# 最佳质量（不限制）
-f "bestvideo+bestaudio/best"

# 1080p封顶（默认推荐）
-f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"

# 720p封顶
-f "bestvideo[height<=720]+bestaudio/best[height<=720]/best"

# 480p封顶
-f "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
```

### 模式 1: 视频（合并）

```bash
mkdir -p "OUTPUT_DIR"
yt-dlp \
  QUALITY_FORMAT \
  --merge-output-format mp4 \
  -P "OUTPUT_DIR" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "VIDEO_URL"
```

**实际示例**（默认1080p + mp4 + 默认目录）：
```bash
mkdir -p "/Users/wsxwj/Downloads/video-download"
yt-dlp \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "https://www.bilibili.com/video/BV1SC6TBqEF9/"
```

### 模式 2: 音频（仅提取）

```bash
mkdir -p "OUTPUT_DIR"
yt-dlp \
  -x --audio-format mp3 --audio-quality 0 \
  -P "OUTPUT_DIR" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "VIDEO_URL"
```

**实际示例**（mp3 + 默认目录）：
```bash
mkdir -p "/Users/wsxwj/Downloads/video-download"
yt-dlp \
  -x --audio-format mp3 --audio-quality 0 \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "https://www.bilibili.com/video/BV1SC6TBqEF9/"
```

### 模式 3: 都下载（视频+音频）

```bash
mkdir -p "OUTPUT_DIR"
yt-dlp \
  QUALITY_FORMAT \
  --merge-output-format mp4 \
  -x --audio-format mp3 --audio-quality 0 \
  --keep-video \
  -P "OUTPUT_DIR" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "VIDEO_URL"
```

**实际示例**：
```bash
mkdir -p "/Users/wsxwj/Downloads/video-download"
yt-dlp \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -x --audio-format mp3 --audio-quality 0 \
  --keep-video \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "https://www.bilibili.com/video/BV1SC6TBqEF9/"
```

## 倍速下载 (特殊功能)

若用户选择倍速（例如 1.25x），需要添加 `--postprocessor-args` 参数调用 ffmpeg 进行转码。

**公式：**
- 视频滤镜：`setpts=1/SPEED*PTS`
- 音频滤镜：`atempo=SPEED`

**1.25x 倍速示例：**
```bash
yt-dlp \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  --postprocessor-args "ffmpeg:-filter:v setpts=0.8*PTS -filter:a atempo=1.25" \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s_1.25x [%(id)s].%(ext)s" \
  "VIDEO_URL"
```

**2.0x 倍速示例：**
```bash
yt-dlp \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  --postprocessor-args "ffmpeg:-filter:v setpts=0.5*PTS -filter:a atempo=2.0" \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s_2.0x [%(id)s].%(ext)s" \
  "VIDEO_URL"
```

> **注意**：倍速处理需要重新编码整个视频，下载完成后会占用大量 CPU 资源进行转换，耗时较长。建议告知用户。

## 批量下载

### 从文本文件批量下载

创建 `urls.txt`（一行一个URL）：
```bash
cat > urls.txt << 'EOF'
https://www.youtube.com/watch?v=VIDEO1
https://www.bilibili.com/video/BV1xxx
https://www.youtube.com/watch?v=VIDEO2
EOF

# 批量下载
yt-dlp \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -a urls.txt \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s"
```

### 跳过已下载的视频

```bash
yt-dlp \
  --download-archive downloaded.txt \
  -a urls.txt \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s"
```

### 直接多个URL

```bash
yt-dlp \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "URL1" "URL2" "URL3"
```

## 播放列表下载

### 整个播放列表

```bash
yt-dlp \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(playlist)s/%(playlist_index)s - %(title)s [%(id)s].%(ext)s" \
  "PLAYLIST_URL"
```

### 播放列表范围

```bash
# 前10个视频
yt-dlp --playlist-end 10 "PLAYLIST_URL"

# 第5到第15个
yt-dlp --playlist-start 5 --playlist-end 15 "PLAYLIST_URL"
```

## 字幕下载

```bash
# 自动生成字幕（中文优先，然后英文）
yt-dlp \
  --write-auto-sub --sub-langs "zh-Hans,zh,en" \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "VIDEO_URL"

# 嵌入字幕到视频
yt-dlp \
  --write-sub --embed-subs --sub-langs "zh-Hans,zh,en" \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "VIDEO_URL"
```

## B站特殊处理

### 需要登录获取高清

```bash
# 从Chrome导入cookies
yt-dlp --cookies-from-browser chrome "BILIBILI_URL"

# 或指定cookies文件
yt-dlp --cookies cookies.txt "BILIBILI_URL"
```

### 查看可用格式

```bash
yt-dlp -F "VIDEO_URL"
```

## 故障排除

### 问题1: "No video formats found"

```bash
# 尝试best格式
yt-dlp -f best "VIDEO_URL"

# 或列出所有可用格式
yt-dlp -F "VIDEO_URL"
```

### 问题2: 下载慢或失败

```bash
# 限速避免封禁
yt-dlp --limit-rate 1M "VIDEO_URL"

# 使用代理
yt-dlp --proxy "http://proxy.example.com:8080" "VIDEO_URL"
```

### 问题3: 文件名过长或特殊字符

```bash
# 启用Windows文件名兼容
yt-dlp --windows-filenames "VIDEO_URL"

# 或限制文件名长度
yt-dlp --trim-filenames 100 "VIDEO_URL"
```

## 验证输出路径（不下载）

在真正下载前，验证输出路径是否正确：

```bash
yt-dlp \
  --simulate --get-filename \
  -P "/Users/wsxwj/Downloads/video-download" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "VIDEO_URL"
```

这会打印出最终文件路径，但不会真正下载。

## 输出模板变量

- `%(title)s` - 视频标题
- `%(id)s` - 视频ID
- `%(ext)s` - 文件扩展名
- `%(uploader)s` - 上传者
- `%(upload_date)s` - 上传日期 (YYYYMMDD)
- `%(playlist)s` - 播放列表名称
- `%(playlist_index)s` - 在播放列表中的位置

## 安装/更新 yt-dlp

```bash
# 检查是否安装
which yt-dlp && yt-dlp --version

# 安装（macOS/Linux）
pip install yt-dlp

# 或使用brew（macOS）
brew install yt-dlp

# 更新到最新版
pip install -U yt-dlp
```

## 支持的平台

- **视频**: YouTube, Vimeo, Dailymotion, Twitch
- **社交**: Twitter/X, TikTok, Instagram, Facebook
- **中国**: Bilibili, Youku, iQiyi, Douyin
- **直播**: Twitch Live, YouTube Live, Bilibili Live
- **教育**: Coursera, Udemy, Khan Academy
- **1000+ 其他平台**

查看所有支持的网站：
```bash
yt-dlp --list-extractors
```

## 重要提示

- 尊重版权和服务条款
- 某些平台可能限制自动下载
- 大文件下载前检查磁盘空间
- 批量下载建议先测试少量URL
- 使用 `--download-archive` 避免重复下载
