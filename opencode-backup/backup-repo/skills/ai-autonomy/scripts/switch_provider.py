#!/usr/bin/env python3
"""
一键切换模型提供商 / 模型
用法：
  python3 switch_provider.py                        # 列出所有提供商和模型
  python3 switch_provider.py deepseek               # 切换到 DeepSeek
  python3 switch_provider.py fangzhou claude-opus-4-6  # 切换到方舟的 opus 模型
"""

import json
import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AUTONOMY_DIR = SCRIPT_DIR.parent  # .autonomy/
ROOT = AUTONOMY_DIR.parent        # 项目根目录

# 尝试加载 .env（dotenv 可选）
try:
    from dotenv import load_dotenv
    load_dotenv(AUTONOMY_DIR / "config" / ".env")
except ImportError:
    env_file = AUTONOMY_DIR / "config" / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

PROVIDERS_FILE = AUTONOMY_DIR / "config" / "providers.json"


def load_config() -> dict:
    with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict):
    with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write("\n")


def list_providers():
    cfg = load_config()
    active = cfg["active_provider"]
    print("\n🤖 可用模型提供商:\n")
    for key, p in cfg["providers"].items():
        marker = " ← 当前" if key == active else ""
        api_key_env = p.get("api_key_env", "")
        has_key = "🔑" if os.environ.get(api_key_env) else "⚠️ 无Key"
        print(f"  [{key}] {p['name']}{marker} {has_key}")
        print(f"    默认模型: {p['model']}")
        print(f"    opencode: {p.get('opencode_model', '未配置')}")
        alt = p.get("alt_models", [])
        if alt:
            print(f"    可选模型: {', '.join(alt)}")
        print()

    print(f"💡 用法:")
    print(f"   python3 {sys.argv[0]} <provider>              # 切换提供商")
    print(f"   python3 {sys.argv[0]} <provider> <model>      # 切换提供商+模型\n")


def switch_provider(target: str, model: str = None):
    cfg = load_config()
    if target not in cfg["providers"]:
        print(f"❌ 未知提供商: {target}")
        print(f"   可选: {', '.join(cfg['providers'].keys())}")
        sys.exit(1)

    old = cfg["active_provider"]
    old_model = cfg["providers"][old].get("model", "")
    cfg["active_provider"] = target
    p = cfg["providers"][target]

    # 如果指定了模型，更新 model 和 opencode_model
    if model:
        all_models = [p["model"]] + p.get("alt_models", [])
        if model not in all_models:
            print(f"❌ 未知模型: {model}")
            print(f"   {target} 可用模型: {', '.join(all_models)}")
            sys.exit(1)
        p["model"] = model
        # 自动推断 opencode_model 的 provider 前缀
        old_oc = p.get("opencode_model", "")
        if "/" in old_oc:
            prefix = old_oc.split("/")[0]
            p["opencode_model"] = f"{prefix}/{model}"

    save_config(cfg)

    print(f"✅ 已切换: {old}({old_model}) → {target}({p['model']})")
    print(f"   opencode --model {p.get('opencode_model', 'N/A')}")

    api_key_env = p.get("api_key_env", "")
    if api_key_env and not os.environ.get(api_key_env):
        print(f"   ⚠️  请确保已设置环境变量: {api_key_env}")


def main():
    if len(sys.argv) < 2:
        list_providers()
    elif len(sys.argv) == 2:
        switch_provider(sys.argv[1])
    else:
        switch_provider(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
