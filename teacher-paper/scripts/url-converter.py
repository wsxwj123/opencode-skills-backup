#!/usr/bin/env python3
"""
在线内容读取服务路由工具。

作用：
1. 将原始 URL 转换为各类在线读取服务格式
2. 测试服务可用性
3. 获取服务返回内容
4. 为 fetch-everything 技能提供快速在线分流能力

注意：
- 本脚本只处理在线服务路由
- 它不直接调用 Scrapling
- 如果在线服务失败，应切换到 Scrapling 或浏览器自动化
"""

import os
import sys
import argparse
import requests
import time
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
import json


class URLConverter:
    """在线服务路由器"""

    SERVICES = {
        'markdown.new': 'https://markdown.new/',
        'defuddle.md': 'https://defuddle.md/',
        'r.jina.ai': 'https://r.jina.ai/'
    }

    def __init__(self, timeout: int = 30, retry: int = 3, delay: float = 1.0):
        self.timeout = timeout
        self.retry = retry
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; FetchEverythingURLRouter/1.0)'
        })

    def _service_headers(self, service: str) -> Dict[str, str]:
        """部分服务支持鉴权以提升配额；r.jina.ai 无 key 时按免费档（重度限流）。"""
        if service == 'r.jina.ai':
            key = os.environ.get('JINA_API_KEY')
            if key:
                return {'Authorization': f'Bearer {key}'}
        return {}

    def convert_url(self, original_url: str, service: str = 'markdown.new') -> str:
        if service not in self.SERVICES:
            raise ValueError(f"不支持的服务: {service}。可选: {', '.join(self.SERVICES.keys())}")

        parsed = urlparse(original_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"无效的URL: {original_url}")

        service_url = self.SERVICES[service]
        # urljoin 对绝对 URL 会忽略 base，必须用字符串拼接
        return service_url + original_url

    def batch_convert(self, urls: List[str], service: str = 'markdown.new') -> Dict[str, str]:
        results = {}
        for url in urls:
            try:
                results[url] = self.convert_url(url, service)
            except ValueError as e:
                results[url] = f"错误: {str(e)}"
        return results

    def test_service(self, url: str, service: str = 'markdown.new') -> Tuple[bool, str, Optional[int]]:
        try:
            converted_url = self.convert_url(url, service)
            headers = self._service_headers(service)
            for attempt in range(self.retry):
                try:
                    response = self.session.get(converted_url, timeout=self.timeout, allow_redirects=True, headers=headers)
                    if response.status_code == 200:
                        return True, f"{service} 服务可用", response.status_code
                    return False, f"{service} 返回状态码: {response.status_code}", response.status_code
                except requests.exceptions.RequestException as e:
                    if attempt < self.retry - 1:
                        time.sleep(self.delay)
                        continue
                    return False, f"{service} 请求失败: {str(e)}", None
        except ValueError as e:
            return False, f"URL转换失败: {str(e)}", None
        return False, "未知错误", None

    def get_content(self, url: str, service: str = 'markdown.new') -> Tuple[bool, Optional[str], str]:
        try:
            converted_url = self.convert_url(url, service)
            headers = self._service_headers(service)
            for attempt in range(self.retry):
                try:
                    response = self.session.get(converted_url, timeout=self.timeout, allow_redirects=True, headers=headers)
                    if response.status_code == 200:
                        content = response.text
                        if len(content) < 50:
                            return False, None, f"{service} 返回内容过短"
                        return True, content, f"成功从 {service} 获取内容"
                    return False, None, f"{service} 返回状态码: {response.status_code}"
                except requests.exceptions.RequestException as e:
                    if attempt < self.retry - 1:
                        time.sleep(self.delay)
                        continue
                    return False, None, f"{service} 请求失败: {str(e)}"
        except ValueError as e:
            return False, None, f"URL转换失败: {str(e)}"
        return False, None, "未知错误"

    def find_best_service(self, url: str) -> Tuple[Optional[str], Optional[str], str]:
        for service in self.SERVICES:
            success, message, status_code = self.test_service(url, service)
            if success:
                return service, self.convert_url(url, service), f"{service} 可用 (状态码: {status_code})"
        return None, None, "未找到可用在线服务，建议切换到 Scrapling"


def main():
    parser = argparse.ArgumentParser(
        description='在线服务路由工具 - 将 URL 转换为内容读取服务格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --url https://example.com --service markdown.new
  %(prog)s --url https://example.com --test-all
  %(prog)s --url https://example.com --find-best
  %(prog)s --url https://example.com --get-content --service r.jina.ai
        """
    )

    parser.add_argument('--url', '-u', help='原始URL')
    parser.add_argument('--input', '-i', help='包含URL列表的文件（每行一个URL）')
    parser.add_argument('--output', '-o', help='输出文件（JSON格式）')
    parser.add_argument('--service', '-s', default='markdown.new',
                        choices=['markdown.new', 'defuddle.md', 'r.jina.ai'],
                        help='在线读取服务（默认: markdown.new）')
    parser.add_argument('--test-all', '-t', action='store_true', help='测试所有服务的可用性')
    parser.add_argument('--get-content', '-g', action='store_true', help='获取转换后的内容')
    parser.add_argument('--find-best', '-b', action='store_true', help='寻找最佳可用服务')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间（秒，默认: 30）')
    parser.add_argument('--retry', type=int, default=3, help='失败重试次数（默认: 3）')
    parser.add_argument('--delay', type=float, default=1.0, help='请求间延迟（秒，默认: 1.0）')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')

    args = parser.parse_args()

    if not args.url and not args.input:
        parser.print_help()
        print("\n错误: 需要指定URL或输入文件")
        sys.exit(1)

    converter = URLConverter(timeout=args.timeout, retry=args.retry, delay=args.delay)

    if args.url:
        if args.test_all:
            for service in converter.SERVICES:
                success, message, _ = converter.test_service(args.url, service)
                print(f"{service}: {'可用' if success else '不可用'} - {message}")
            return

        if args.find_best:
            service, converted_url, message = converter.find_best_service(args.url)
            print(json.dumps({
                'service': service,
                'converted_url': converted_url,
                'message': message,
            }, ensure_ascii=False, indent=2))
            return

        if args.get_content:
            success, content, message = converter.get_content(args.url, args.service)
            if not success:
                print(message)
                sys.exit(2)
            print(content)
            return

        print(converter.convert_url(args.url, args.service))
        return

    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        results = converter.batch_convert(urls, args.service)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
