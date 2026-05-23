#!/usr/bin/env python3
"""
XHS (小红书) 视频 URL 提取器
用法: python3 xhs_get_video.py "https://www.xiaohongshu.com/explore/xxx"
"""
import asyncio
import sys

from playwright.async_api import async_playwright

XHS_URL = sys.argv[1] if len(sys.argv) > 1 else ""

if not XHS_URL:
    print("用法: python3 xhs_get_video.py <XHS_URL>", file=sys.stderr)
    sys.exit(1)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="/Users/wsxwj/Library/Application Support/Google/Chrome/Profile 5",
            headless=True,
            args=["--no-sandbox"],
            proxy={"server": "http://127.0.0.1:7897"},
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        video_urls = []

        def on_request(request):
            url = request.url
            if any(x in url for x in ["sns-video", ".mp4", "xhscdn.com/note"]):
                video_urls.append(url)

        page.on("request", on_request)
        await page.goto(XHS_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        await browser.close()

    for u in video_urls:
        print(u)


asyncio.run(main())
