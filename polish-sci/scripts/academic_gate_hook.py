#!/usr/bin/env python3
"""共享学术门禁 hook —— 一个 PreToolUse hook 服务全部学术技能。

它是"扳机"，本身不做内容检查：拦到一次 Write/Edit 时，判断该文件是否属于
某个学术技能项目的"受管产物"，若是就跑该技能已有的门禁脚本，门禁 exit≠0
就 deny 这次写入（把机器信号翻成对话里的人话）。检查逻辑一律复用各技能
scripts/ 里已存在的门禁，不在这里重写。

设计铁律：
- fail-open（对用户无害优先）：任何异常、读不到输入、认不出项目、注册表缺失
  → 静默放行。绝不因 hook 自身故障卡住用户的正常写作。
- 只碰"受管产物路径"（registry 的 managed_globs），其余一切写入零影响。
- 每次真正介入（判定为学术项目产物）都更新心跳文件，供 preflight 探测
  "hook 到底活没活"。

stdin: Claude Code PreToolUse 事件 JSON（含 tool_input.file_path）。
stdout: 命中拦截时输出 permissionDecision=deny 的 JSON；放行时无输出。
exit: 恒 0（deny 通过 JSON 表达，不用 exit 2，避免壳对 stderr 处理不一）。
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HEARTBEAT_NAME = "hook_heartbeat.json"


def _shared_dir() -> Path:
    return Path(__file__).resolve().parent


def _write_heartbeat(reason: str, extra: dict | None = None) -> None:
    """记录 hook 确实 fire 了一次。preflight 读它判断 hook 是否在岗。
    失败绝不抛（心跳是辅助，不能反过来拖垮 hook）。"""
    try:
        hb = {"last_fire_epoch": int(time.time()), "reason": reason}
        if extra:
            hb.update(extra)
        (_shared_dir() / HEARTBEAT_NAME).write_text(
            json.dumps(hb, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _load_registry() -> dict:
    try:
        return json.loads((_shared_dir() / "gate_registry.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _find_project_root(file_path: Path, state_files: set[str]) -> tuple[Path, str] | None:
    """从被写文件向上找，第一个含任一 registry state_file 的目录即项目根。
    返回 (root, matched_state_file)。找不到返回 None。"""
    for parent in [file_path] + list(file_path.parents):
        if not parent.is_dir():
            continue
        for sf in state_files:
            if (parent / sf).is_file():
                return parent, sf
    return None


def _identify_skill(root: Path, registry: dict, rel_path: str) -> tuple[str, dict] | None:
    """判断项目属于哪个技能。多个技能可能共用同名 state 文件(如 project_state.json)，
    故核心消歧靠"被写文件命中谁的 managed_globs"——各技能产物路径不重叠。
    返回 None 表示：该文件不是任何在场技能的受管产物(交回放行)。"""
    skills = registry.get("skills", {})
    present = [(n, c) for n, c in skills.items()
               if any((root / sf).is_file() for sf in c.get("state_files", []))]
    if not present:
        return None
    matched = [(n, c) for n, c in present
               if _is_managed(rel_path, c.get("managed_globs", []))]
    if len(matched) == 1:
        return matched[0]
    if len(matched) > 1:
        # 罕见：多个技能的 glob 都命中 → 再用 state 文件里的 skill 字段消歧
        for n, c in matched:
            for sf in c.get("state_files", []):
                p = root / sf
                if p.is_file():
                    try:
                        d = json.loads(p.read_text(encoding="utf-8"))
                        if isinstance(d, dict) and d.get("skill") == n:
                            return n, c
                    except Exception:
                        pass
        return matched[0]
    return None  # 文件非任何在场技能的产物 → 放行


def _is_managed(rel_path: str, globs: list[str]) -> bool:
    rel = rel_path.replace(os.sep, "/")
    return any(fnmatch.fnmatch(rel, g) for g in globs)


def _section_from_filename(file_path: Path) -> str:
    """从产物文件名抽 section_id：取数字/点组合，如 section_2.1.md→2.1、
    results_3.2.md→3.2。抽不出返回文件名主干（让门禁自己报错，不在这瞎猜）。"""
    stem = file_path.stem
    m = re.search(r"(\d+(?:[._]\d+)*)", stem)
    return m.group(1).replace("_", ".") if m else stem


def _gates_for(skill_cfg: dict, registry: dict) -> list[dict]:
    """该技能要跑哪些门禁。signoff:true → 共享结构签字门禁；否则无(仅心跳)。"""
    if skill_cfg.get("signoff") and registry.get("signoff_gate"):
        return [registry["signoff_gate"]]
    return []


def _run_gates(gates: list[dict], root: Path, file_path: Path) -> tuple[bool, str]:
    """跑门禁。返回 (blocked, message)。任一 gate exit≠0 即 blocked。"""
    py = sys.executable or "python"
    section = _section_from_filename(file_path)
    subs = {
        "{python}": py,
        "{project_root}": str(root),
        "{file_path}": str(file_path),
        "{section}": section,
        "{shared_dir}": str(_shared_dir()),
    }
    def _subst(tok: str) -> str:
        for k, v in subs.items():
            tok = tok.replace(k, v)
        return tok

    for gate in gates:
        cmd = [_subst(tok) for tok in gate.get("command", [])]
        if not cmd:
            continue
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, cwd=str(root)
            )
        except Exception:
            # 门禁自身跑不起来（缺依赖等）→ fail-open 放行，不误伤用户
            return False, ""
        if proc.returncode != 0:
            detail = (proc.stdout or "").strip() or (proc.stderr or "").strip()
            return True, (
                f"[学术门禁] 「{gate.get('name','gate')}」未通过，本次写入被拦下。\n"
                f"原因：{detail[:800]}\n"
                f"这不是 bug——是流程门禁在阻止跳步。请先补上门禁要求的步骤"
                f"（跑对应脚本、过上一节盲检等），过了再写。"
            )
    return False, ""


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # 读不到输入：放行

    tool_input = payload.get("tool_input") or {}
    raw_fp = tool_input.get("file_path")
    if not raw_fp:
        return

    try:
        file_path = Path(str(raw_fp))
    except Exception:
        return

    registry = _load_registry()
    if not registry.get("skills"):
        return  # 无注册表：放行

    all_state_files = {
        sf for cfg in registry["skills"].values() for sf in cfg.get("state_files", [])
    }
    found = _find_project_root(file_path, all_state_files)
    if not found:
        return  # 非学术项目：放行（绝大多数写入走这里，开销≈向上找一次文件）

    root, _ = found
    try:
        rel = str(file_path.resolve().relative_to(root.resolve()))
    except Exception:
        rel = file_path.name

    # 识别技能已内含"命中受管产物"判定：认不出/非产物文件 → 放行。
    ident = _identify_skill(root, registry, rel)
    if not ident:
        return
    skill_name, skill_cfg = ident

    _write_heartbeat("gate_evaluated", {"skill": skill_name, "file": rel})
    blocked, message = _run_gates(_gates_for(skill_cfg, registry), root, file_path)
    if blocked:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": message,
            }
        }, ensure_ascii=False))


def _forward_to_deployed() -> bool:
    """悬空防护:本文件若从开发真源 skills/_shared/ 被 settings.json 旧 entry 调起,
    且稳定部署副本 ~/.claude/academic-gate/ 已存在,则转发执行部署副本(单一运行时,
    心跳/registry 都落部署位)。_shared 里本文件因此永远不裸删:旧 entry 指过来时
    有文件可执行,不会 python 找不到路径 exit 2 拦死一切写入。
    测试可用环境变量 ACADEMIC_GATE_NO_FORWARD=1 关闭转发(直接测本文件逻辑)。"""
    if os.environ.get("ACADEMIC_GATE_NO_FORWARD"):
        return False
    here = Path(__file__).resolve()
    if "/_shared/" not in str(here).replace("\\", "/"):
        return False  # 部署副本/vendored 副本直接跑自己
    deployed = Path.home() / ".claude" / "academic-gate" / "academic_gate_hook.py"
    if not deployed.is_file() or deployed.resolve() == here:
        return False
    try:
        import runpy
        runpy.run_path(str(deployed), run_name="__main__")
        return True
    except SystemExit:
        raise
    except Exception:
        return False  # 转发失败回落本地逻辑(fail-open 精神)


if __name__ == "__main__":
    if not _forward_to_deployed():
        main()
    sys.exit(0)
