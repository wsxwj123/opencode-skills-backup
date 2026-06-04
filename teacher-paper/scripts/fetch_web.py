#!/usr/bin/env python3
"""
网页素材抓取器 —— teacher-paper skill 自包含组件
默认输出 Markdown 正文，多策略降级，任何电脑可运行。
用法：
    python3 fetch_web.py "<url>" [更多url ...]          # 抓取并打印到 stdout
    python3 fetch_web.py "<url>" --save materials/x.md  # 抓取并落盘（写入抓取凭证头）

策略顺序（自动降级）：
  1. r.jina.ai 代理（纯 HTTP，无需本地依赖，对多数站点有效，输出 Markdown）
  2. requests + readability-lxml 本地正文提取（需 pip 安装）
  3. requests 取原始 HTML 粗清洗

反爬站点（学科网、组卷网、希沃白板、小红书登录态内容等）可能全部失败；
此时脚本会明确提示："该网站有访问限制，请截图相关内容，由助手多模态识别。"

--save 落盘时会在文件头写入机器可校验的【抓取凭证】（url/strategy/sha256/fetched_at），
assemble.py build 的素材溯源门禁据此区分"真抓取"与"凭记忆默写"——网络来源的素材
若缺此凭证头会被拒绝出卷。凭记忆默写古文/新闻极易出错，务必用本脚本真抓取。
"""

# Windows 控制台默认 GBK：强制 stdout/stderr 用 UTF-8，避免中文 print 乱码（幂等，mac/Linux 无副作用）
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
import sys
import os
import urllib.request

CRED_MARK = "teacher-paper:fetched"   # 抓取凭证标记，须与 assemble.py 的 _FETCH_CRED_MARK 一致

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
    """返回 (ok, strategy, text)：ok=False 时 text 为失败提示。"""
    errors = []
    for name, fn in (("jina", via_jina),
                     ("readability", via_readability),
                     ("raw", via_raw)):
        try:
            out = fn(url)
            if out and len(out.strip()) > 120:
                return True, name, out.strip()
            errors.append(f"{name}:内容过短")
        except Exception as e:
            errors.append(f"{name}:{e}")
    return False, "", f"{BLOCK_HINT}\n\n（已尝试：{'; '.join(errors)}）"


def _save_with_credential(path, url, strategy, text):
    """落盘正文，并在文件头写入机器可校验的抓取凭证（供 assemble 门禁识别）。"""
    import hashlib
    import datetime
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (f"<!-- {CRED_MARK}\n"
              f"url: {url}\n"
              f"strategy: {strategy}\n"
              f"chars: {len(text)}\n"
              f"sha256: {sha}\n"
              f"fetched_at: {now}\n"
              f"-->\n\n"
              f"来源：{url}\n"
              f"抓取日期：{now[:10]}\n\n")
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + text + "\n")


def expand_short_link(url):
    """小红书/B站等短链：跟随重定向取真实地址。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.geturl()
    except Exception:
        return url


def _expand(url):
    return expand_short_link(url) if any(
        s in url for s in ("xhslink", "b23.tv", "t.cn", "dwz")) else url


def main():
    argv = sys.argv[1:]
    save_path = None
    if "--save" in argv:
        i = argv.index("--save")
        save_path = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
        if not save_path:
            print("[错误] --save 后须跟落盘路径，如 --save materials/非连_xxx.md")
            sys.exit(1)
    if not argv:
        print(__doc__)
        sys.exit(1)

    if save_path:                       # 落盘模式：只抓第一个 url，写入凭证头
        real = _expand(argv[0])
        ok, strategy, text = fetch(real)
        if not ok:
            print(text)
            print("\n[未落盘] 抓取失败，未写入文件——请改用截图，由助手多模态识别后落盘。")
            sys.exit(2)
        _save_with_credential(save_path, real, strategy, text)
        print(f"[已落盘] {save_path}（策略:{strategy}，{len(text)} 字，已写抓取凭证头）")
        return

    for url in argv:                    # 打印模式（原行为）
        real = _expand(url)
        print(f"\n{'='*60}\n# URL: {real}\n{'='*60}")
        ok, strategy, text = fetch(real)
        print(f"[策略:{strategy} 成功]\n\n{text}" if ok else text)


if __name__ == "__main__":
    main()
