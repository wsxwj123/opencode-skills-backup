#!/usr/bin/env python3
"""
AI 自治开发系统 3.0 - Agent Team 多智能体协作驱动脚本
功能：CTO 统筹分派 → 多 Agent 并发执行 → 汇总结果 → 循环
"""

import json
import subprocess
import sys
import os
import time
import signal
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).resolve().parent
AUTONOMY_DIR = SCRIPT_DIR.parent  # .autonomy/
ROOT = AUTONOMY_DIR.parent        # 项目根目录

# 自动加载 .env
from dotenv import load_dotenv
load_dotenv(AUTONOMY_DIR / "config" / ".env")

FEATURE_FILE = ROOT / "feature_list.json"
PROGRESS_FILE = ROOT / "progress.txt"
PROVIDERS_FILE = AUTONOMY_DIR / "config" / "providers.json"
TEAM_CONFIG_FILE = AUTONOMY_DIR / "config" / "agent_team_config.json"

TASK_TIMEOUT = 600
COOLDOWN_SEC = 5

running = True
def signal_handler(sig, frame):
    global running
    print("\n🛑 收到退出信号，等待当前任务完成...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_progress(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{ts}] {msg}")


def get_provider_config() -> dict:
    cfg = load_json(PROVIDERS_FILE)
    active = cfg["active_provider"]
    provider = cfg["providers"][active]
    provider["_key"] = active
    return provider


def load_agent_prompt(agent_id: str) -> str:
    """加载 Agent 角色 Prompt"""
    team_cfg = load_json(TEAM_CONFIG_FILE)
    # 查找对应 agent
    if agent_id == "lead-cto":
        prompt_file = AUTONOMY_DIR / team_cfg["team"]["lead"]["prompt_file"]
    else:
        specialist = next(
            (s for s in team_cfg["team"]["specialists"] if s["id"] == agent_id),
            None
        )
        if not specialist:
            return ""
        prompt_file = AUTONOMY_DIR / specialist["prompt_file"]

    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return ""


def assign_task_to_agent(task: dict, team_cfg: dict) -> str:
    """根据任务类别分配给对应 Agent"""
    category = task.get("category", "")
    rules = team_cfg["workflow"]["task_assignment_rules"]
    return rules.get(category, "backend-integrator")


def get_pending_tasks(features: dict) -> list:
    """获取所有 pending 任务，按优先级排序"""
    pending = [f for f in features["features"] if f["status"] == "pending"]
    return sorted(pending, key=lambda x: x.get("priority", 999))


def run_agent(agent_id: str, task: dict, provider: dict) -> dict:
    """运行单个 Agent 执行任务"""
    agent_prompt = load_agent_prompt(agent_id)
    criteria = "\n".join(f"  - {c}" for c in task.get("acceptance_criteria", []))

    prompt = f"""{agent_prompt}

---

## 当前任务分派

你被 CTO 分派了以下任务：

- 任务ID: {task['id']}
- 类别: {task['category']}
- 描述: {task['description']}
- 验收标准:
{criteria}

请立即执行。完成后按照你的输出规范报告结果。
如果遇到问题，记录在 progress.txt 中并报告给 CTO。
"""

    cfg = load_json(PROVIDERS_FILE)
    cli_cfg = cfg.get("claude_code_overrides", {})
    cli_path = cli_cfg.get("cli_path", "claude")
    skip_perms = cli_cfg.get("dangerously_skip_permissions", False)

    cmd = [cli_path, "-p", prompt, "--output-format", "text"]
    if skip_perms:
        cmd.append("--dangerously-skip-permissions")

    env = os.environ.copy()
    api_key = os.environ.get(provider.get("api_key_env", ""), "")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    if provider.get("type") == "openai_compatible":
        env["OPENAI_API_BASE"] = provider["base_url"]
        env["OPENAI_API_KEY"] = api_key

    result = {
        "agent_id": agent_id,
        "task_id": task["id"],
        "success": False,
        "output": "",
        "error": ""
    }

    try:
        proc = subprocess.run(
            cmd, cwd=ROOT, env=env,
            timeout=TASK_TIMEOUT,
            capture_output=True, text=True
        )
        result["output"] = proc.stdout[-1000:] if proc.stdout else ""
        result["success"] = proc.returncode == 0
    except subprocess.TimeoutExpired:
        result["error"] = f"超时 ({TASK_TIMEOUT}s)"
    except FileNotFoundError:
        result["error"] = f"未找到 CLI: {cli_path}"
    except Exception as e:
        result["error"] = str(e)

    return result


def cto_review(results: list) -> dict:
    """CTO 审查所有 Agent 的执行结果"""
    summary = {
        "total": len(results),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "details": []
    }
    for r in results:
        status = "✅" if r["success"] else "❌"
        summary["details"].append(
            f"{status} {r['task_id']} by @{r['agent_id']}: "
            f"{'完成' if r['success'] else r.get('error', '失败')}"
        )
    return summary


def main():
    print("=" * 50)
    print("  🤖 AI 自治开发系统 3.0 - Agent Team 模式")
    print("=" * 50)

    provider = get_provider_config()
    team_cfg = load_json(TEAM_CONFIG_FILE)
    max_parallel = team_cfg["workflow"].get("max_parallel_agents", 3)

    print(f"🧠 模型: {provider['name']} ({provider['model']})")
    print(f"👥 团队: {team_cfg['team']['name']}")
    print(f"   CTO: {team_cfg['team']['lead']['role']}")
    for s in team_cfg["team"]["specialists"]:
        print(f"   专家: @{s['id']} ({s['role']})")
    print(f"⚡ 最大并行: {max_parallel}")
    print()

    round_num = 0
    while running:
        round_num += 1
        print(f"\n{'='*50}")
        print(f"  🔄 第 {round_num} 轮 - CTO 规划中...")
        print(f"{'='*50}")

        features = load_json(FEATURE_FILE)
        pending = get_pending_tasks(features)

        if not pending:
            print("🎉 所有任务已完成！")
            append_progress("🎉 所有任务已完成，Agent Team 停止。")
            break

        # CTO 分派：取最多 max_parallel 个任务并行
        batch = pending[:max_parallel]
        assignments = []
        for task in batch:
            agent_id = assign_task_to_agent(task, team_cfg)
            assignments.append((agent_id, task))
            print(f"📋 分派: {task['id']} → @{agent_id} ({task['description']})")

        # 并发执行
        print(f"\n🚀 启动 {len(assignments)} 个 Agent 并发执行...\n")
        results = []

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {
                executor.submit(run_agent, agent_id, task, provider): (agent_id, task)
                for agent_id, task in assignments
            }
            for future in as_completed(futures):
                if not running:
                    break
                agent_id, task = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} @{agent_id} 完成 {task['id']}")
                except Exception as e:
                    print(f"  ❌ @{agent_id} 异常: {e}")
                    results.append({
                        "agent_id": agent_id,
                        "task_id": task["id"],
                        "success": False,
                        "error": str(e)
                    })

        # CTO 审查
        print(f"\n📊 CTO 审查结果:")
        review = cto_review(results)
        for detail in review["details"]:
            print(f"  {detail}")
        print(f"  总计: {review['success']}/{review['total']} 成功")

        # 更新状态
        features = load_json(FEATURE_FILE)
        for r in results:
            target = next(
                (f for f in features["features"] if f["id"] == r["task_id"]),
                None
            )
            if target and r["success"]:
                target["status"] = "done"
                target["passes"] = True
                append_progress(f"✅ [Team] {r['task_id']} by @{r['agent_id']} 完成")
            elif target:
                target["notes"] = f"第{round_num}轮 @{r['agent_id']} 失败: {r.get('error', '')}"
                append_progress(f"❌ [Team] {r['task_id']} by @{r['agent_id']} 失败")

        save_json(FEATURE_FILE, features)

        # Git 提交本轮结果
        subprocess.run(["git", "add", "-A"], cwd=ROOT, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m",
             f"team(round-{round_num}): {review['success']}/{review['total']} tasks done"],
            cwd=ROOT, capture_output=True
        )

        if review["failed"] > 0:
            print(f"\n💤 有失败任务，冷却 {COOLDOWN_SEC}s...")
            time.sleep(COOLDOWN_SEC)

    print("\n👋 Agent Team 已停止")


if __name__ == "__main__":
    main()
