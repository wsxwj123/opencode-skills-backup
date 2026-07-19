#!/usr/bin/env python3
"""检查 fetch-everything 技能的本地执行环境。"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

SCRIPT_DIR = Path(__file__).parent
REQUIRED_SCRIPTS = [
    "check_fetch_env.py",
    "fetch_everything.py",
    "assess_fetch_quality.py",
    "clean_fetched_markdown.py",
    "url-converter.py",
]
OPTIONAL_COMMANDS = [
    ["scrapling", "--help"],
]


def run_cmd(cmd, timeout=None):
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr=f"timeout after {timeout}s")


def check_python() -> Dict[str, Any]:
    return {
        "ok": True,
        "executable": sys.executable,
        "version": sys.version.split()[0],
    }


def check_scripts() -> Dict[str, Any]:
    missing = []
    sizes = {}
    for name in REQUIRED_SCRIPTS:
        p = SCRIPT_DIR / name
        if not p.exists():
            missing.append(name)
        else:
            sizes[name] = p.stat().st_size
    return {
        "ok": not missing,
        "missing": missing,
        "sizes": sizes,
    }


def check_requests() -> Dict[str, Any]:
    proc = run_cmd([sys.executable, "-c", "import requests; print(requests.__version__)"])
    return {
        "ok": proc.returncode == 0,
        "detail": proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip(),
    }


def check_scrapling() -> Dict[str, Any]:
    # 与 fetch_everything 一致：优先当前解释器同目录的 scrapling（重入后即 venv 那套），
    # 保证自检报告里的 scrapling 就是真正被调用的那个。
    sibling = Path(sys.executable).with_name("scrapling")
    path = str(sibling) if sibling.exists() else shutil.which("scrapling")
    if not path:
        return {"ok": False, "detail": "scrapling not found in PATH", "subcmds": {}}
    proc = run_cmd([path, "--help"])
    if proc.returncode != 0:
        return {"ok": False, "path": path, "detail": proc.stderr.strip(), "subcmds": {}}

    # 深度检查：验证各子命令的依赖是否可用
    subcmd_checks = {
        "get": [sys.executable, "-c", "from scrapling.fetchers import Fetcher; print('ok')"],
        "stealthy-fetch": [sys.executable, "-c", "from scrapling.fetchers import StealthyFetcher; print('ok')"],
        "fetch": [sys.executable, "-c", "from scrapling.fetchers import DynamicFetcher; print('ok')"],
    }
    subcmds = {}
    all_ok = True
    for name, cmd in subcmd_checks.items():
        p = run_cmd(cmd)
        ok = p.returncode == 0 and "ok" in p.stdout
        subcmds[name] = {"ok": ok, "error": p.stderr.strip() if not ok else None}
        if not ok:
            all_ok = False

    return {
        "ok": all_ok,
        "path": path,
        "detail": (proc.stdout.splitlines()[0] if proc.stdout else proc.stderr.strip()),
        "subcmds": subcmds,
    }


def check_browsers() -> Dict[str, Any]:
    """验证 scrapling 浏览器路线的 chromium 二进制是否真就绪。
    关键：`import StealthyFetcher` 成功 ≠ 浏览器可执行文件存在
    （StealthyFetcher 走 patchright、DynamicFetcher 走 playwright，各需自己版本的 chromium）。"""
    probe = (
        "from {mod}.sync_api import sync_playwright\n"
        "import os, sys\n"
        "p = sync_playwright().start()\n"
        "path = p.chromium.executable_path\n"
        "p.stop()\n"
        "sys.stdout.write(path or '')\n"
        "sys.exit(0 if path and os.path.exists(path) else 3)\n"
    )
    engines = {}
    for label, mod in (("stealthy-fetch(patchright)", "patchright"),
                       ("fetch(playwright)", "playwright")):
        proc = run_cmd([sys.executable, "-c", probe.format(mod=mod)], timeout=30)
        ok = proc.returncode == 0
        engines[label] = {
            "ok": ok,
            "path": proc.stdout.strip() if ok else None,
            "hint": None if ok else f"运行 `python3 -m {mod} install chromium` 下载浏览器二进制",
        }
    return {"ok": all(e["ok"] for e in engines.values()), "engines": engines}


def main() -> None:
    # 入口先解析到"playwright 就绪"的解释器（可能 os.execv 重入）；重入后 sys.executable
    # 即最终解释器，自检报告里的 python.executable 就显示实际用的那套。对无 venv 机器透明。
    sys.path.insert(0, str(SCRIPT_DIR))
    from _pyresolve import ensure_resolved
    ensure_resolved()

    parser = argparse.ArgumentParser(description="检查 fetch-everything 的本地执行环境")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    result = {
        "python": check_python(),
        "scripts": check_scripts(),
        "requests": check_requests(),
        "scrapling": check_scrapling(),
        "browsers": check_browsers(),
    }
    result["ok"] = all(section.get("ok", False) for section in result.values())

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    for name, section in result.items():
        if name == "ok":
            continue
        print(f"[{name}] {'OK' if section.get('ok') else 'FAIL'}")
        for key, value in section.items():
            if key == "ok":
                continue
            print(f"  - {key}: {value}")
    print(f"\nOVERALL: {'OK' if result['ok'] else 'FAIL'}")


if __name__ == "__main__":
    main()
