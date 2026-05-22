#!/usr/bin/env python3
"""
一键切换模型提供商
用法：
  python3 scripts/switch_provider.py              # 列出所有提供商
  python3 scripts/switch_provider.py qwen         # 切换到 Qwen
  python3 scripts/switch_provider.py deepseek     # 切换到 DeepSeek
  python3 scripts/switch_provider.py custom       # 切换到自定义
"""

import json
import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AUTONOMY_DIR = SCRIPT_DIR.parent  # .autonomy/
ROOT = AUTONOMY_DIR.parent        # 项目根目录

# 自动加载 .env
from dotenv import load_dotenv
load_dotenv(AUTONOMY_DIR / "config" / ".env")

PROVIDERS_FILE = AUTONOMY_DIR / "config" / "providers.json"


def load_config() -> dict:
    with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict):
    with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def list_providers():
    cfg = load_config()
    active = cfg["active_provider"]
    print("\n🤖 可用模型提供商:\n")
    print(f"  {'KEY':<15} {'名称':<30} {'模型':<25} {'状态'}")
    print(f"  {'-'*15} {'-'*30} {'-'*25} {'-'*6}")
    for key, p in cfg["providers"].items():
        marker = "✅ 当前" if key == active else ""
        api_key_env = p.get("api_key_env", "")
        has_key = "🔑" if os.environ.get(api_key_env) else "⚠️ 无Key"
        print(f"  {key:<15} {p['name']:<30} {p['model']:<25} {marker} {has_key}")
    print(f"\n💡 用法: python3 {sys.argv[0]} <provider_key>")
    print(f"   例如: python3 {sys.argv[0]} deepseek\n")


def switch_provider(target: str):
    cfg = load_config()
    if target not in cfg["providers"]:
        print(f"❌ 未知提供商: {target}")
        print(f"   可选: {', '.join(cfg['providers'].keys())}")
        sys.exit(1)

    old = cfg["active_provider"]
    cfg["active_provider"] = target
    save_config(cfg)

    p = cfg["providers"][target]
    print(f"✅ 已切换: {old} → {target}")
    print(f"   模型: {p['name']} ({p['model']})")
    print(f"   接口: {p['base_url']}")

    api_key_env = p.get("api_key_env", "")
    if api_key_env and not os.environ.get(api_key_env):
        print(f"   ⚠️  请确保已设置环境变量: {api_key_env}")


def main():
    if len(sys.argv) < 2:
        list_providers()
    else:
        switch_provider(sys.argv[1])


if __name__ == "__main__":
    main()
