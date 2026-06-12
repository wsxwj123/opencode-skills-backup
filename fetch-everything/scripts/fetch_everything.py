#!/usr/bin/env python3
"""统一抓取执行器：多路线抓取、质量判定、轻量清洗。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
URL_ROUTER = SCRIPT_DIR / "url-converter.py"
QUALITY = SCRIPT_DIR / "assess_fetch_quality.py"
CLEANER = SCRIPT_DIR / "clean_fetched_markdown.py"

ONLINE_SERVICES = ["markdown.new", "defuddle.md", "r.jina.ai"]
SCRAPLING_COMMANDS = [
    ["scrapling", "extract", "get"],
    ["scrapling", "extract", "stealthy-fetch", "--timeout", "45000", "--network-idle"],
    ["scrapling", "extract", "fetch", "--timeout", "45000", "--network-idle"],
]

# 在线服务作为"快速尝试"，不重试、低超时，挂掉立即降级（避免 92s/服务 的超时叠加）
ONLINE_RETRY = "1"
ONLINE_TIMEOUT = "15"
# 候选达到此分且通过质量门即停止降级，不再跑后续更慢的路线
EARLY_EXIT_SCORE = 25
# scrapling 子进程的 wall-clock 上限（秒）：防止浏览器启动/下载卡死拖垮整个抓取
SCRAPLING_WALL_TIMEOUT = 100


def _env_proxy() -> Optional[str]:
    """读取环境代理，透传给 scrapling（浏览器不自动读 http_proxy，需 --proxy）。"""
    for key in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"):
        value = os.environ.get(key)
        if value:
            return value
    return None

# 需要浏览器渲染的动态站点域名（SKILL.md 规定这些站点优先走 Scrapling）
DYNAMIC_SITE_DOMAINS = [
    "xiaohongshu.com", "xhslink.com",
    "weibo.com", "weibo.cn",
    "douyin.com",
    "bilibili.com",
    "zhihu.com",
    "mp.weixin.qq.com", "weixin.qq.com",  # 微信公众号：在线服务必然触发风控
]

def resolve_short_url(url: str) -> str:
    """跟随重定向返回最终 URL（短链、跟踪链接统一归一）；失败回退原 URL。"""
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        resp = requests.head(url, allow_redirects=True, timeout=10, headers=headers)
        if resp.url and resp.url != url:
            return resp.url
    except Exception:
        pass
    # fallback: 部分服务器不支持 HEAD，用 GET（stream 避免下载正文）
    try:
        resp = requests.get(url, allow_redirects=True, timeout=10, stream=True, headers=headers)
        final = resp.url
        resp.close()
        if final and final != url:
            return final
    except Exception:
        pass
    return url


def _strip_www(netloc: str) -> str:
    lower = netloc.lower()
    return lower[4:] if lower.startswith("www.") else lower


def is_dynamic_site(url: str) -> bool:
    from urllib.parse import urlparse
    domain = _strip_www(urlparse(url).netloc)
    return any(domain == d or domain.endswith("." + d) for d in DYNAMIC_SITE_DOMAINS)


def run_cmd(cmd: List[str], input_text: Optional[str] = None,
            timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        # 超时按失败处理（returncode=124），调用方据此降级到下一路线
        return subprocess.CompletedProcess(
            cmd, returncode=124,
            stdout=exc.stdout or "", stderr=f"wall-clock timeout after {timeout}s",
        )


def assess_text(text: str) -> Dict:
    proc = run_cmd([sys.executable, str(QUALITY)], input_text=text)
    if proc.returncode != 0:
        return {"score": -999, "passed": False, "reasons": [proc.stderr.strip() or "quality_failed"]}
    return json.loads(proc.stdout)


def clean_text(text: str) -> str:
    proc = run_cmd([sys.executable, str(CLEANER)], input_text=text)
    if proc.returncode != 0:
        return text
    return proc.stdout


_SERVICE_BASE_URLS = {
    "markdown.new": "https://markdown.new/",
    "defuddle.md": "https://defuddle.md/",
    "r.jina.ai": "https://r.jina.ai/",
}


def _is_good_enough(item: Dict) -> bool:
    """候选已通过质量门且分数达到 early-exit 阈值。"""
    q = item.get("quality", {})
    return bool(q.get("passed")) and q.get("score", -999) >= EARLY_EXIT_SCORE


def fetch_via_online_services(url: str) -> List[Dict]:
    results: List[Dict] = []
    for service in ONLINE_SERVICES:
        content = run_cmd([sys.executable, str(URL_ROUTER), "--url", url, "--service", service,
                           "--get-content", "--retry", ONLINE_RETRY, "--timeout", ONLINE_TIMEOUT])
        if content.returncode != 0:
            continue
        item = {
            "method": f"online:{service}",
            "service_url": _SERVICE_BASE_URLS.get(service, "") + url,
            "content": content.stdout,
        }
        _assess_candidate(item)
        results.append(item)
        if _is_good_enough(item):
            break  # 已拿到优质正文，不再消耗后续在线服务
    return results


def fetch_via_scrapling(url: str) -> List[Dict]:
    results: List[Dict] = []
    proxy = _env_proxy()
    for base_cmd in SCRAPLING_COMMANDS:
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        cmd = list(base_cmd) + [url, str(tmp_path)]
        if proxy:
            cmd += ["--proxy", proxy]
        proc = run_cmd(cmd, timeout=SCRAPLING_WALL_TIMEOUT)
        if proc.returncode != 0 or not tmp_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            continue
        text = tmp_path.read_text(encoding="utf-8", errors="ignore")
        item = {
            "method": " ".join(base_cmd),
            "content": text,
            "stderr": proc.stderr.strip(),
        }
        _assess_candidate(item)
        results.append(item)
        tmp_path.unlink(missing_ok=True)
        if _is_good_enough(item):
            break  # 已拿到优质正文，不再跑更慢的浏览器路线
    return results


def _assess_candidate(item: Dict) -> None:
    """原地填充 cleaned_content 和 quality（幂等，已评估则跳过）。"""
    if "quality" not in item:
        cleaned = clean_text(item["content"])
        item["cleaned_content"] = cleaned
        item["quality"] = assess_text(cleaned)


def choose_best(candidates: List[Dict]) -> Optional[Dict]:
    best = None
    for item in candidates:
        _assess_candidate(item)
        if best is None or item["quality"]["score"] > best["quality"]["score"]:
            best = item
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="统一抓取执行器")
    parser.add_argument("url", help="目标 URL")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 元信息")
    args = parser.parse_args()

    url = args.url
    # 统一预解析重定向：短链、跟踪链接都归一到最终 URL（也让小红书等短链能被正确识别为动态站点）
    resolved = resolve_short_url(url)
    if resolved != url:
        print(f"[info] 重定向解析: {url} -> {resolved}", file=sys.stderr)
        url = resolved

    candidates: List[Dict] = []
    # 根据站点类型调整抓取顺序；任一路线拿到优质正文即停止降级
    if is_dynamic_site(url):
        # 动态站点：优先浏览器路线，跳过在线服务（在线服务必触发风控）
        print(f"[info] 检测到动态站点，优先使用 Scrapling 浏览器路线", file=sys.stderr)
        candidates.extend(fetch_via_scrapling(url))
        if not any(_is_good_enough(c) for c in candidates):
            candidates.extend(fetch_via_online_services(url))
    else:
        candidates.extend(fetch_via_online_services(url))
        if not any(_is_good_enough(c) for c in candidates):
            candidates.extend(fetch_via_scrapling(url))

    best = choose_best(candidates)
    if not best:
        print(json.dumps({
            "url": args.url,
            "status": "failed",
            "reason": "no_candidate",
            "next_step": "所有自动路线均无结果。建议 AI 接力：用 WebFetch 工具直接抓取，或确认是否需要登录/cookie（见 SKILL.md HALT 流程）。",
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    cleaned = best.get("cleaned_content", clean_text(best["content"]))
    result = {
        "url": args.url,
        "status": "success" if best["quality"].get("passed") else "partial",
        "method": best["method"],
        "score": best["quality"]["score"],
        "reasons": best["quality"]["reasons"],
        "content": cleaned,
    }

    if args.output:
        Path(args.output).write_text(cleaned, encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(cleaned)


if __name__ == "__main__":
    main()
