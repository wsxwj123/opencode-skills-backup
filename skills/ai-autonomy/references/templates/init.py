#!/usr/bin/env python3
"""
AI 自治开发系统 - 跨平台环境初始化脚本
每次 AI 启动时首先执行：python3 init.py
支持 macOS / Windows / Linux
"""

import json
import os
import sys
import subprocess
import shutil
from pathlib import Path

# 项目根目录（init.py 放在项目根目录）
ROOT = Path(__file__).resolve().parent
AUTONOMY_DIR = ROOT / ".autonomy"


def load_env():
    """加载 .env 文件到环境变量"""
    env_file = AUTONOMY_DIR / "config" / ".env"
    if not env_file.exists():
        print("⚠️  [init] 未找到 .autonomy/config/.env，请先配置 API Key")
        return
    print("📦 [init] 加载 .env 环境变量...")
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


def check_python():
    """检查 Python 环境"""
    print(f"🐍 [init] Python: {sys.version.split()[0]}")


def install_deps():
    """安装 Python 依赖"""
    req_file = AUTONOMY_DIR / "requirements.txt"
    if req_file.exists():
        print("📦 [init] 安装 Python 依赖...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)],
            capture_output=True
        )


def check_git():
    """检查 Git 状态"""
    print("📋 [init] Git 状态:")
    if shutil.which("git"):
        result = subprocess.run(
            ["git", "status", "--short"], cwd=ROOT,
            capture_output=True, text=True
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"   {output}" if output else "   (工作区干净)")
        else:
            print("   (非 Git 仓库)")
    else:
        print("   (未安装 Git)")


def check_core_files():
    """检查核心文件"""
    print("📂 [init] 检查核心文件...")
    for f in ["feature_list.json", "progress.txt", "CLAUDE.md"]:
        path = ROOT / f
        status = "✅" if path.exists() else "❌ 缺失!"
        print(f"   {status} {f}")


def show_model():
    """显示当前模型配置"""
    providers_file = AUTONOMY_DIR / "config" / "providers.json"
    if not providers_file.exists():
        return
    try:
        with open(providers_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        active = cfg["active_provider"]
        p = cfg["providers"][active]
        print(f"🤖 [init] 当前活跃模型: {p['name']} ({p['model']})")
    except Exception:
        pass


def main():
    print("🔧 [init] AI 自治开发系统启动中...")
    print(f"   平台: {sys.platform}")
    print(f"   项目: {ROOT}")
    print()

    load_env()
    check_python()
    install_deps()
    check_git()
    check_core_files()
    show_model()

    print()
    print("✅ [init] 环境初始化完成！")
    print("=========================================")
    print("  下一步：读取 feature_list.json 获取任务")
    print("=========================================")


if __name__ == "__main__":
    main()
