#!/usr/bin/env python3
"""P-1 最小验证 hook：确认 Claude Code 的 PreToolUse hook 在当前环境真的会
fire、真的能拦下一次 Write/Edit。**它不是正式门禁**，只拦一个特殊标记路径。

判定规则（stdlib-only，跨平台）：
  - 被写文件路径中含目录/文件名标记 "HOOK_SMOKE_TEST" → deny（拦截写入）
  - 其他一律放行（不影响任何正常工作）

验证方法：让 Claude 写一个名字带 HOOK_SMOKE_TEST 的文件，
  - 若写入被拒并显示"[hook-smoke-test] PreToolUse hook 已生效"，说明 hook 链路通；
  - 若文件被正常写出，说明 hook 没 fire（GUI 壳未透传 / 配置路径错 / python 不可用）。
"""
import json
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # 读不到输入时绝不误伤：静默放行
        return

    file_path = str((payload.get("tool_input") or {}).get("file_path") or "")

    if "HOOK_SMOKE_TEST" in file_path:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "[hook-smoke-test] PreToolUse hook 已生效：本次写入被测试 hook 拦截。"
                    "这证明当前环境（含 GUI 壳）正确透传了 settings.json 的 hooks，"
                    "P-1 验证通过，可以继续 P0 正式门禁 hook。"
                ),
            }
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
    sys.exit(0)
