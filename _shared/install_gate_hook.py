#!/usr/bin/env python3
"""学术门禁 hook 自动安装器 + 心跳探测。各技能 env_preflight 调它一次。

用户零手动步骤：正常调用技能 → preflight 跑本脚本 →
  1) settings.json 里没装门禁 hook → 自动装（备份→只追加→JSON 校验，失败回滚）
     → 提示"已安装保护，重启一次会话后生效"
  2) 已装但心跳陈旧/缺失 → 该环境不透传 hook（如某些第三方壳）→ 报 degraded，
     让技能据此告诉用户"本环境无法强制门禁，请按监工卡人工盯防"
  3) 已装且心跳新鲜 → 强制门禁在岗 → active

输出：一行 JSON {status, action, message}。status ∈ installed|active|degraded|error。
stdlib-only、跨平台。改 settings.json 属敏感操作，三重保险：改前备份、只追加
hooks.PreToolUse 且跳过重复、写后 json.loads 校验失败即从备份回滚。
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

HOOK_TAG = "academic_gate_hook.py"  # 用于识别我们的 hook，避免重复安装
HEARTBEAT_NAME = "hook_heartbeat.json"
HEARTBEAT_FRESH_SEC = 24 * 3600  # 24h 内 fire 过算新鲜


def _shared_dir() -> Path:
    return Path(__file__).resolve().parent


def _settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _hook_command() -> str:
    hook = _shared_dir() / "academic_gate_hook.py"
    # 引号包路径以容纳空格；python 交给 PATH（Windows 上用户须保证 python 可用）
    return f'python "{hook}"'


def _our_hook_present(settings: dict) -> bool:
    for entry in (settings.get("hooks", {}) or {}).get("PreToolUse", []) or []:
        for h in entry.get("hooks", []) or []:
            if HOOK_TAG in str(h.get("command", "")):
                return True
    return False


def _heartbeat_status() -> str:
    hb = _shared_dir() / HEARTBEAT_NAME
    if not hb.is_file():
        return "none"
    try:
        data = json.loads(hb.read_text(encoding="utf-8"))
        age = time.time() - int(data.get("last_fire_epoch", 0))
        return "fresh" if age <= HEARTBEAT_FRESH_SEC else "stale"
    except Exception:
        return "none"


def _install(settings_path: Path) -> tuple[bool, str]:
    """把门禁 hook 追加进 settings.json。返回 (ok, message)。"""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    original = settings_path.read_text(encoding="utf-8") if settings_path.is_file() else None
    backup = None
    if original is not None:
        try:
            settings = json.loads(original)
            if not isinstance(settings, dict):
                return False, "settings.json 不是对象，跳过自动安装（请手动配置 hook）"
        except Exception:
            return False, "settings.json 解析失败（可能手动编辑出错），跳过自动安装，未改动"
        backup = settings_path.with_suffix(".json.bak-gatehook")
        shutil.copyfile(settings_path, backup)
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    pretool = hooks.setdefault("PreToolUse", [])
    if _our_hook_present(settings):
        return True, "already-present"

    pretool.append({
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": _hook_command(), "timeout": 60}],
    })

    new_text = json.dumps(settings, ensure_ascii=False, indent=2)
    try:
        json.loads(new_text)  # 写前自校验
    except Exception:
        return False, "生成的 settings.json 非法，已放弃安装（原文件未动）"

    settings_path.write_text(new_text, encoding="utf-8")
    # 写后再校验一次，坏了立即从备份回滚
    try:
        json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        if backup and backup.is_file():
            shutil.copyfile(backup, settings_path)
        return False, "写入后校验失败，已从备份回滚，settings.json 未被破坏"
    return True, "installed"


def main() -> None:
    result = {"status": "error", "action": "none", "message": ""}
    try:
        sp = _settings_path()
        settings = {}
        if sp.is_file():
            try:
                settings = json.loads(sp.read_text(encoding="utf-8"))
            except Exception:
                settings = {}

        if _our_hook_present(settings if isinstance(settings, dict) else {}):
            hb = _heartbeat_status()
            if hb == "fresh":
                result.update(status="active", action="none",
                              message="强制门禁 hook 已在岗（近期触发过）。跳步会被物理拦截。")
            else:
                result.update(status="degraded", action="none", message=(
                    "门禁 hook 已写入 settings.json，但从未探测到它触发过——"
                    "说明当前运行环境可能不透传 hook。请把它当作【未受保护】："
                    "按开场监工卡逐项人工盯防，别信任'门禁会自动拦'。"))
        else:
            ok, msg = _install(sp)
            if ok:
                result.update(status="installed", action="installed", message=(
                    "已自动安装强制门禁保护到 settings.json（原文件已备份）。"
                    "⚠️ 需【重启一次本会话/客户端】后生效——hook 在启动时加载，无法热生效。"
                    "重启后再来用即受保护。注意：升级前就写到一半的旧项目，重启后再写正文可能被"
                    "'结构签字缺失'拦一次——按提示补跑一次 structure_signoff confirm 即可继续，属正常迁移。"))
            else:
                result.update(status="degraded", action="install-skipped", message=(
                    "未能自动安装门禁 hook：" + msg +
                    "。请当作未受保护，按监工卡人工盯防。"))
    except Exception as e:  # 安装器绝不能反过来卡住技能
        result.update(status="error", action="none",
                      message=f"门禁自检异常（不影响技能继续）：{e}")

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
