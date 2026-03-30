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


def run_cmd(cmd):
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


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
    path = shutil.which("scrapling")
    if not path:
        return {"ok": False, "detail": "scrapling not found in PATH"}
    proc = run_cmd([path, "--help"])
    return {
        "ok": proc.returncode == 0,
        "path": path,
        "detail": (proc.stdout.splitlines()[0] if proc.stdout else proc.stderr.strip()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 fetch-everything 的本地执行环境")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    result = {
        "python": check_python(),
        "scripts": check_scripts(),
        "requests": check_requests(),
        "scrapling": check_scrapling(),
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
