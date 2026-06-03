#!/usr/bin/env python3
"""
网页素材抓取器 —— teacher-paper skill 自包含组件
默认输出 Markdown 正文，多策略降级，任何电脑可运行。
用法：
    python3 fetch_web.py "<url>" [更多url ...]

策略顺序（自动降级）：
  1. r.jina.ai 代理（纯 HTTP，无需本地依赖，对多数站点有效，输出 Markdown）
  2. requests + readability-lxml 本地正文提取（需 pip 安装）
  3. requests 取原始 HTML 粗清洗

反爬站点（学科网、组卷网、希沃白板、小红书登录态内容等）可能全部失败；
此时脚本会明确提示："该网站有访问限制，请截图相关内容，由助手多模态识别。"
"""

# Windows 控制台默认 GBK：强制 stdout/stderr 用 UTF-8，避免中文 print 乱码（幂等，mac/Linux 无副作用）
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
import sys
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

BLOCK_HINT = ("【抓取失败】该网站可能有反爬限制（如学科网/组卷网/希沃白板/"
              "需登录的小红书等）。请在浏览器打开后**截图**相关内容，"
              "由助手用多模态 Read 工具识别提取。")


def _http_get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def via_jina(url):
    """r.jina.ai 阅读代理：返回 Markdown 正文。"""
    target = "https://r.jina.ai/" + url
    txt = _http_get(target)
    if txt and len(txt.strip()) > 120:
        return txt
    raise RuntimeError("jina 返回过短")


def via_readability(url):
    try:
        from readability import Document
    except ImportError:
        raise RuntimeError("readability-lxml 未安装")
    html = _http_get(url)
    doc = Document(html)
    title = doc.short_title()
    content_html = doc.summary()
    # 极简 HTML→文本
    import re
    text = re.sub(r"<br\s*/?>", "\n", content_html)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return f"# {title}\n\n{text}"


def via_raw(url):
    import re
    html = _http_get(url)
    html = re.sub(r"(?is)<script.*?</script>", "", html)
    html = re.sub(r"(?is)<style.*?</style>", "", html)
    text = re.sub(r"(?is)<[^>]+>", "\n", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)


def fetch(url):
    errors = []
    for name, fn in (("jina", via_jina),
                     ("readability", via_readability),
                     ("raw", via_raw)):
        try:
            out = fn(url)
            if out and len(out.strip()) > 120:
                return f"[策略:{name} 成功]\n\n{out.strip()}"
            errors.append(f"{name}:内容过短")
        except Exception as e:
            errors.append(f"{name}:{e}")
    return f"{BLOCK_HINT}\n\n（已尝试：{'; '.join(errors)}）"


def expand_short_link(url):
    """小红书/B站等短链：跟随重定向取真实地址。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.geturl()
    except Exception:
        return url


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for url in sys.argv[1:]:
        real = expand_short_link(url) if any(
            s in url for s in ("xhslink", "b23.tv", "t.cn", "dwz")) else url
        print(f"\n{'='*60}\n# URL: {real}\n{'='*60}")
        print(fetch(real))


if __name__ == "__main__":
    main()
