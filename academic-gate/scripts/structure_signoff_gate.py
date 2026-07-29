#!/usr/bin/env python3
"""结构签字门禁（共享，粗粒度）——"大纲/故事线没经用户确认，不许写正文"。

为什么是它：跳步的 AI（尤其弱模型）最常见的失误就是没等用户确认大纲/storyline
就开写正文。本门禁把"用户确认"理化成一个签字文件，hook 在每次写正文产物前
check 它——签字不存在就物理拦截写入。逐节时序仍由各技能自己的 prewrite_gate
+ token 链负责；本门禁只管这个从文件状态就能可靠判定的粗粒度不变量。

用法：
  confirm: python structure_signoff_gate.py confirm --root <project_root> [--note "用户确认要点"]
    仅当用户在对话中明确确认了大纲/storyline 后才能运行——AI 不得代替用户确认。
    写 <root>/structure_signoff.json（含 UTC 时间戳与 note），解锁正文写作。
  check:   python structure_signoff_gate.py check --root <project_root>

退出码（INTERFACE §8.6）：
  0  通过
  2  还没签：签字文件不存在 / 坏 JSON / 顶层不是对象 / confirmed≠true
  3  预留给"签过但大纲已变，要重签"
  64 用法错（EX_USAGE）。**必须与 2 分开**：argparse 的用法错默认也是 2，撞码时
     调用方（和人）分不出"参数写错了"和"用户还没确认大纲"，只能去猜 stderr 里
     有没有 usage 字样——那是拿文案兜语义，换一版 Python 就失效。

签字后大纲又大改了怎么办：重跑 confirm 覆盖即可（append 历史到 history 字段）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SIGNOFF_NAME = "structure_signoff.json"

EX_OK = 0
EX_UNSIGNED = 2
EX_RESIGN = 3
EX_USAGE = 64


def cmd_confirm(root: Path, note: str) -> int:
    path = root / SIGNOFF_NAME
    history = []
    if path.is_file():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            history = prev.get("history", [])
            history.append({k: prev[k] for k in ("confirmed_epoch", "note") if k in prev})
        except Exception:
            pass
    payload = {
        "confirmed": True,
        "confirmed_epoch": int(time.time()),
        "note": note or "",
        "history": history[-10:],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "signoff": str(path)}, ensure_ascii=False))
    return EX_OK


def cmd_check(root: Path) -> int:
    path = root / SIGNOFF_NAME
    if not path.is_file():
        print(
            "结构签字缺失：大纲/故事线还没有经过用户确认。\n"
            "正确流程：① 把完整大纲/storyline 展示给用户 → ② 用户在对话里明确说'确认'"
            " → ③ 运行 python <本脚本> confirm --root <项目根> 落盘签字 → ④ 才能写正文。\n"
            "AI 不得在用户未确认时自行运行 confirm。"
        )
        return EX_UNSIGNED
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        print("structure_signoff.json 损坏（非合法 JSON），请让用户重新确认大纲后重跑 confirm。")
        return EX_UNSIGNED
    if not isinstance(data, dict):
        print("structure_signoff.json 损坏（顶层不是 JSON 对象），"
              "请让用户重新确认大纲后重跑 confirm。")
        return EX_UNSIGNED
    # 严格 is True：`1` / `"true"` 都不算确认过——签字是凭证，不做真值转换。
    if data.get("confirmed") is not True:
        print("structure_signoff.json 存在但 confirmed≠true，请让用户确认大纲后重跑 confirm。")
        return EX_UNSIGNED
    return EX_OK


class _Parser(argparse.ArgumentParser):
    """把用法错从 argparse 默认的 2 挪到 64（EX_USAGE）。

    2 已经是"还没签"的语义，撞码会让调用方（和人）分不出"参数写错了"和
    "用户还没确认大纲"。"""

    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        sys.exit(EX_USAGE)


def main() -> int:
    parser = _Parser(description="结构签字门禁：用户确认大纲前不许写正文")
    sub = parser.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    p_confirm = sub.add_parser("confirm", help="用户已在对话中确认大纲后落盘签字")
    p_confirm.add_argument("--root", required=True)
    p_confirm.add_argument("--note", default="", help="用户确认时的要点/原话摘录")
    p_check = sub.add_parser("check", help="校验签字是否存在(hook 调用)")
    p_check.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        sys.stderr.write("%s: error: --root 不是目录: %s\n" % (parser.prog, root))
        return EX_USAGE
    if args.cmd == "confirm":
        return cmd_confirm(root, args.note)
    return cmd_check(root)


if __name__ == "__main__":
    sys.exit(main())
