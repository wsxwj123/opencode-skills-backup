#!/usr/bin/env python3
"""
AI 自治开发系统 2.0 - 无限循环驱动脚本
功能：自动读取任务 → 调用 AI → 验证 → 更新状态 → 失败回滚 → 循环
支持多模型提供商一键切换
"""

import json
import subprocess
import sys
import os
import time
import signal
from datetime import datetime
from pathlib import Path

# 项目根目录（脚本在 .autonomy/scripts/ 下，根目录是上两级）
SCRIPT_DIR = Path(__file__).resolve().parent
AUTONOMY_DIR = SCRIPT_DIR.parent  # .autonomy/
ROOT = AUTONOMY_DIR.parent        # 项目根目录

# 自动加载 .env
from dotenv import load_dotenv
load_dotenv(AUTONOMY_DIR / "config" / ".env")

FEATURE_FILE = ROOT / "feature_list.json"
PROGRESS_FILE = ROOT / "progress.txt"
PROVIDERS_FILE = AUTONOMY_DIR / "config" / "providers.json"

# 配置
MAX_RETRIES = 3          # 单任务最大重试次数
COOLDOWN_SEC = 5         # 失败后冷却时间
TASK_TIMEOUT = 600       # 单任务超时（秒）

# 优雅退出
running = True
def signal_handler(sig, frame):
    global running
    print("\n🛑 收到退出信号，完成当前任务后停止...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_progress(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] {message}")


def get_next_task(features: dict) -> dict | None:
    """获取优先级最高的 pending 任务"""
    pending = [f for f in features["features"] if f["status"] == "pending"]
    if not pending:
        return None
    return sorted(pending, key=lambda x: x.get("priority", 999))[0]


def get_provider_config() -> dict:
    """读取当前活跃的模型提供商配置"""
    cfg = load_json(PROVIDERS_FILE)
    active = cfg["active_provider"]
    provider = cfg["providers"][active]
    provider["_provider_key"] = active
    return provider


def git_snapshot() -> str:
    """创建 Git 快照，返回 commit hash"""
    subprocess.run(["git", "add", "-A"], cwd=ROOT, capture_output=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip()


def git_rollback(commit_hash: str):
    """回滚到指定 commit"""
    print(f"⏪ 回滚到 {commit_hash[:8]}...")
    subprocess.run(["git", "checkout", "."], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "clean", "-fd"], cwd=ROOT, capture_output=True)


def build_prompt(task: dict) -> str:
    """构建发送给 AI 的 Prompt"""
    criteria = "\n".join(f"  - {c}" for c in task.get("acceptance_criteria", []))
    return f"""你现在是一个自治开发 Agent。请严格按照 CLAUDE.md 中的协议执行。

## 当前任务
- 任务ID: {task['id']}
- 类别: {task['category']}
- 描述: {task['description']}
- 验收标准:
{criteria}

## 执行要求
1. 先运行 `source init.sh` 确认环境
2. 读取 feature_list.json 和 progress.txt 了解上下文
3. 实现上述任务，逐条满足验收标准
4. 完成后更新 feature_list.json（status→done, passes→true）
5. 在 progress.txt 追加工作记录
6. git commit 提交代码

{f"备注: {task['notes']}" if task.get('notes') else ""}
"""


def run_with_opencode(prompt: str, provider: dict) -> bool:
    """通过 OpenCode CLI 执行任务"""
    cfg = load_json(PROVIDERS_FILE)
    cli_cfg = cfg.get("opencode_overrides", {})
    cli_path = cli_cfg.get("cli_path", "opencode")

    # opencode run <message> --dir <project_root> --model <provider/model>
    cmd = [cli_path, "run", prompt, "--dir", str(ROOT)]

    # 如果配置了模型，通过 --model 指定
    model_override = cli_cfg.get("model")
    if model_override:
        cmd.extend(["--model", model_override])

    # 设置环境变量
    env = os.environ.copy()
    api_key = os.environ.get(provider["api_key_env"], "")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    if provider["type"] == "openai_compatible":
        env["OPENAI_API_BASE"] = provider["base_url"]
        env["OPENAI_API_KEY"] = api_key

    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            timeout=TASK_TIMEOUT,
            capture_output=True,
            text=True
        )
        print(f"📝 AI 输出:\n{result.stdout[-500:]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⏰ 任务超时（{TASK_TIMEOUT}s）")
        return False
    except FileNotFoundError:
        print(f"❌ 未找到 CLI: {cli_path}")
        print("   请确认已安装 OpenCode: npm i -g opencode")
        return False


def run_with_api(prompt: str, provider: dict) -> bool:
    """直接通过 API 调用模型（不依赖 OpenCode CLI）"""
    try:
        import httpx
    except ImportError:
        print("📦 安装 httpx...")
        subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], capture_output=True)
        import httpx

    api_key = os.environ.get(provider["api_key_env"], "")
    if not api_key:
        print(f"❌ 未设置 API Key: {provider['api_key_env']}")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    body = {
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": "你是一个自治开发 Agent，严格按照指令执行开发任务。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": provider.get("max_tokens", 8192),
        "temperature": provider.get("temperature", 0.7)
    }

    try:
        url = f"{provider['base_url'].rstrip('/')}/chat/completions"
        resp = httpx.post(url, json=body, headers=headers, timeout=TASK_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        print(f"📝 AI 输出:\n{content[-500:]}")
        return True
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        return False


def execute_task(task: dict, provider: dict) -> bool:
    """执行单个任务"""
    cfg = load_json(PROVIDERS_FILE)
    use_cli = cfg.get("opencode_overrides", {}).get("cli_path", "opencode") != ""

    prompt = build_prompt(task)

    if use_cli:
        return run_with_opencode(prompt, provider)
    else:
        return run_with_api(prompt, provider)


def main():
    print("=" * 50)
    print("  🤖 AI 自治开发系统 2.0")
    print("  无限循环模式启动")
    print("=" * 50)

    # 加载提供商配置
    provider = get_provider_config()
    print(f"🧠 当前模型: {provider['name']} ({provider['model']})")
    print(f"🔑 API Key 环境变量: {provider['api_key_env']}")
    print()

    round_num = 0
    while running:
        round_num += 1
        print(f"\n{'='*40}")
        print(f"  🔄 第 {round_num} 轮")
        print(f"{'='*40}")

        # 重新加载任务（可能被上一轮更新了）
        features = load_json(FEATURE_FILE)
        task = get_next_task(features)

        if not task:
            print("🎉 所有任务已完成！")
            append_progress("所有任务已完成，系统停止。")
            break

        task_id = task["id"]
        print(f"📋 当前任务: {task_id} - {task['description']}")

        # Git 快照
        snapshot = git_snapshot()

        # 执行任务（带重试）
        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            if not running:
                break
            print(f"🚀 尝试 {attempt}/{MAX_RETRIES}...")
            success = execute_task(task, provider)
            if success:
                break
            print(f"💤 冷却 {COOLDOWN_SEC}s...")
            time.sleep(COOLDOWN_SEC)

        # 更新状态
        features = load_json(FEATURE_FILE)  # 重新加载（AI 可能已修改）
        target = next((f for f in features["features"] if f["id"] == task_id), None)

        if success and target:
            if target["status"] != "done":
                target["status"] = "done"
                target["passes"] = True
                save_json(FEATURE_FILE, features)
            append_progress(f"✅ {task_id} 完成: {task['description']}")
            print(f"✅ {task_id} 完成!")
            # Git 提交
            subprocess.run(
                ["git", "add", "-A"],
                cwd=ROOT, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"feat({task_id}): {task['description']}"],
                cwd=ROOT, capture_output=True
            )
        else:
            if target:
                target["notes"] = f"第{round_num}轮失败，已重试{MAX_RETRIES}次"
                save_json(FEATURE_FILE, features)
            append_progress(f"❌ {task_id} 失败: {task['description']}，已回滚")
            git_rollback(snapshot)
            print(f"❌ {task_id} 失败，已回滚")

    print("\n👋 AI 自治开发系统已停止")


if __name__ == "__main__":
    main()
