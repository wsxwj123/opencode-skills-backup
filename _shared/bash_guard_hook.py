#!/usr/bin/env python3
"""Bash 守卫钩子 —— 拦"绕开门禁脚本、直接用 shell 把凭证/正文写出来"的常见形态。

挂 PreToolUse / matcher:"Bash"（academic-gate/hooks/hooks.json，timeout 15）。

  F5  自签：同一段命令里同时出现 structure_signoff_gate(.py) 与 confirm → deny。
      "用户本人确认了大纲"这个签字动作不能由 AI 代跑。
  F9-A 受保护凭证：同一段里同时出现"写入动作词"与 structure_signoff.json /
      .review_pass → deny。判定确定，不需要 cwd。
  F9-B 受管正文：同一段里有写入动作词，且抽出的路径落在某强证据项目根内、命中
      该技能 managed_globs → 走与 PreToolUse 完全相同的 F10 + signoff 判定
      （调 academic_gate_hook._judge，绝不在这里重写一套判据）。

🔴 先按 `;`/`&&`/`||`/`|`/换行分段，**同一段内同时命中**才判。跨段的"同时出现"
（`cat structure_signoff.json; python3 gen.py > out.txt`）是误判，必须放行。
分段用朴素字符串切分，不做 shell 解析：引号里的分隔符可能被多切一刀，方向是更容易
漏判 = fail-open，与本层取向一致。

🔴 缺 cwd 时：A 级（F5/F9-A）**照判**——纯文本匹配不需要 cwd；B 级跳过（判不了
归属）。禁止 `if not cwd: return` 一刀切放行。

🔴 F9 是黑名单，**原理上不完备**：heredoc、base64 -d |、自写小程序、编辑器命令、
经 MCP/子代理写盘……写文件的形态无穷。任何文档不得宣称"堵死"，口径固定为
"拦常见形态，不完备"。

stdin: PreToolUse 事件 JSON（tool_input.command、cwd）。stdout: deny JSON 或空。
exit: 恒 0。
"""
from __future__ import annotations

# 🔴 stdout/stderr 强制 UTF-8（照抄 academic_gate_hook.py:27-32 的既有写法）。
# 中文 deny 理由在 cp1252/cp437 上 print() 会抛 UnicodeEncodeError → 脚本非 0 退出
# → 门禁在真正命中拦截的那一刻自炸并放行。
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_guard_core as core  # noqa: E402

COMMAND_SCAN_LIMIT = 64 * 1024   # 只扫前 64 KB（如实登载为不完备点之一）
STDIN_LIMIT = 4 * 1024 * 1024

_SEGMENT_RE = re.compile(r"\|\||&&|[;|\n\r]")
_SIGNOFF_SCRIPT_RE = re.compile(r"structure_signoff_gate(\.py)?")
_CONFIRM_RE = re.compile(r"\bconfirm\b")
_PROTECTED_RE = re.compile(r"structure_signoff\.json|\.review_pass")
_WRITE_ACTION_RE = re.compile(
    r">"                                  # > 与 >>（含 awk ... > 形态）
    r"|\btee\b"
    r"|\bsed\s+(-i|--in-place)"
    r"|\bperl\s+-i"
    r"|\bpython3?\s+-c"
    r"|\bcp\b|\bmv\b|\bdd\b|\binstall\b|\btruncate\b"
    r"|\bex\s+-s"
)
# 路径 token：引号包裹的整段，或不含空白的一串
_TOKEN_RE = re.compile(r"'([^']*)'|\"([^\"]*)\"|(\S+)")

REASON_F5 = (
    "[学术门禁] structure_signoff_gate.py confirm 是\"用户本人确认了大纲\"的签字动作，"
    "不能由 AI 代跑，本次已拦下。正确做法：把完整大纲/storyline 展示给用户，等用户在"
    "对话里明确确认，然后请用户在自己的终端里运行这条 confirm 命令。"
    "（用户本人在终端运行不经过本钩子，天然可用。）"
)
REASON_F9A = (
    "[学术门禁] 这条命令会绕过门禁脚本直接写 structure_signoff.json 或 .review_pass/，"
    "这两类文件只能由 structure_signoff_gate.py / delegate_review.py 产生，本次已拦下。"
)
F9B_PREFIX = "[学术门禁] 这条命令会经 shell 写入受管正文文件："


def _emit_deny(reason: str) -> None:
    """已判定命中后拼装/编码失败也绝不静默放行：兜底用纯 ASCII 精简文案重发。"""
    payload = {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}
    try:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:
        try:
            sys.stdout.write(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason":
                    "[academic-gate] blocked by academic writing gate.",
            }}) + "\n")
            sys.stdout.flush()
        except Exception:
            pass


def _segments(command: str) -> list:
    return [s for s in _SEGMENT_RE.split(command[:COMMAND_SCAN_LIMIT]) if s.strip()]


def _tokens(segment: str) -> list:
    out = []
    for quoted1, quoted2, bare in _TOKEN_RE.findall(segment):
        tok = quoted1 or quoted2 or bare
        tok = tok.strip("'\"")
        if not tok or tok.startswith("-"):
            continue
        if "/" not in tok and "." not in tok:
            continue                      # 只看像路径的 token
        out.append(tok)
        if len(out) >= 20:
            break
    return out


def _audit_root(cwd) -> Path | None:
    """审计落点：cwd 能认出项目根才写；陌生目录一律不写（不在别人目录里造文件）。"""
    if cwd is None:
        return None
    ev = core.detect(cwd)
    return ev.root if ev.tier != "none" else None


def _judge_b_level(segment: str, cwd: Path, registry: dict):
    """B 级：抽路径 → 落在强证据项目内且命中 managed_globs → 走与 PreToolUse
    同一套 F10/signoff 判定（判据只有一份，不在这里另写）。"""
    try:
        import academic_gate_hook as gate
    except Exception:
        return None
    for tok in _tokens(segment):
        try:
            p = Path(tok)
            if not p.is_absolute():
                p = cwd / p
            p = Path(os.path.realpath(str(p)))
        except Exception:
            continue
        try:
            verdict = gate._judge(p, registry)
        except Exception:
            continue
        # 只认 deny：weak 档的 ask 不在 Bash 层做（陌生目录不许误伤）
        if verdict and verdict[0] == "deny":
            return verdict
    return None


def run() -> None:
    data = sys.stdin.buffer.read(STDIN_LIMIT)
    try:
        payload = json.loads(data.decode("utf-8", "replace"))
    except Exception:
        return
    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return

    raw_cwd = payload.get("cwd")
    cwd = None
    if isinstance(raw_cwd, str) and raw_cwd:
        try:
            cand = Path(os.path.realpath(raw_cwd))
            cwd = cand if cand.is_dir() else None
        except OSError:
            cwd = None

    segments = _segments(command)

    # ---- A 级：纯文本匹配，不需要 cwd
    for seg in segments:
        if _SIGNOFF_SCRIPT_RE.search(seg) and _CONFIRM_RE.search(seg):
            _emit_deny(REASON_F5)
            core.audit_append(_audit_root(cwd), event="PreToolUse", tool="Bash",
                              rule="F5-self-signoff", decision="deny",
                              target="structure_signoff.json", detail="AI 代跑 confirm")
            return
    for seg in segments:
        if _WRITE_ACTION_RE.search(seg) and _PROTECTED_RE.search(seg):
            _emit_deny(REASON_F9A)
            core.audit_append(_audit_root(cwd), event="PreToolUse", tool="Bash",
                              rule="F9A-protected-write", decision="deny",
                              target="", detail="shell 直写受保护凭证")
            return

    # ---- B 级：判归属要 cwd；没有就跳过并留痕（不是一刀切放行）
    if cwd is None:
        if any(_WRITE_ACTION_RE.search(seg) for seg in segments):
            core.audit_append(None, event="PreToolUse", tool="Bash",
                              rule="F9B-skipped-no-cwd", decision="unchecked")
        return
    registry = core.load_registry()
    if not registry.get("skills"):
        return
    for seg in segments:
        if not _WRITE_ACTION_RE.search(seg):
            continue
        verdict = _judge_b_level(seg, cwd, registry)
        if verdict:
            _, reason, root, rule, skill, target, detail = verdict
            _emit_deny(F9B_PREFIX + reason)
            core.audit_append(root, event="PreToolUse", tool="Bash",
                              rule=rule, decision="deny", skill=skill,
                              target=target, detail=detail)
            return


def main() -> None:
    try:
        run()
    except Exception:
        # 未判定成功不算命中：喂/拦通用兜底，绝不因自身异常拦人
        if os.environ.get("CONTEXT_GUARD_DEBUG"):
            import traceback
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
    sys.exit(0)
