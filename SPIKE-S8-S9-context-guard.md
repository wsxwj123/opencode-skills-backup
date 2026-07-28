# SPIKE S8 / S9 操作手册（context-guard M-1 前置）

> 本文件只是**准备物**：探针脚本 + 逐步操作 + 结果怎么用。**开发代理没有执行**（S8/S9
> 需要真实交互会话，脚本测不出来），由用户在 Claude Code 与 Codex 各跑一次。
> 上游：`.devflow/PLAN-context-guard.md` §④ M-1、§⑥；`.devflow/INTERFACE-context-guard.md` §2.1.2、§7.1。
> 跑完请把结论写回 PLAN/INTERFACE（删掉不成立的那一支分支），并按 §4 改一个常量。

## 0. 一句话：这两条不验会返工什么

| # | 假设 | 压着它的东西 |
|---|---|---|
| **S8** | **PreToolUse 的 `additionalContext` 会被模型消费吗** | INTERFACE §2.1.2「路径解析失效必须留痕告知」与 §7.1「无 ask 端 weak 档的告知」两条**都压在它身上**。调研一只实证了 UserPromptSubmit / SessionStart / PostToolUse 三处注入，PreToolUse 的这个字段是官方文档字段但**本项目从未实测** |
| **S9** | **Codex 端标识的真值** | 端探测判据。上一版用 `CODEX_*` 环境变量已被判致命（环境变量从启动 shell 继承，会在 Claude Code 上误命中）。要确认 `tool_name == "apply_patch"` 是可靠的内在信号，并确认环境变量确实不可用 |

**当前实现取的是 S8 未通过的那一支**（`context_guard_core.NOTICE_MODE = "B"`：只写审计 +
`pending_notice`，由下一次 UserPromptSubmit 的状态卡补报）。S8 通过就改成 `"A"`，两条路径都已写好。

## 1. 造探针（一段命令，落在临时目录，不碰任何现役配置）

```bash
SPIKE=/tmp/cg-spike && rm -rf "$SPIKE" && mkdir -p "$SPIKE"/{.claude,.codex,logs}
cat > "$SPIKE/probe.py" <<'PY'
#!/usr/bin/env python3
"""S8+S9 探针：PreToolUse 上只发 additionalContext（不带 permissionDecision），
同时把整个 payload 与 CODEX_* 环境变量 dump 到日志。恒 exit 0，不拦任何东西。"""
import json, os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "probe.jsonl")
try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {"_": "stdin 不是 JSON"}
try:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "payload": payload,
            "codex_env": {k: "<非空>" for k in sorted(os.environ) if k.upper().startswith("CODEX")},
            "plugin_env": {k: "<非空>" for k in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DATA",
                                                 "CLAUDECODE") if os.environ.get(k)},
        }, ensure_ascii=False) + "\n")
except Exception:
    pass
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "探针XYZ：这是一条来自 PreToolUse 钩子的 additionalContext。"}},
    ensure_ascii=False))
sys.exit(0)
PY
HOOK='exec "$(command -v python3 || command -v python)" "'"$SPIKE"'/probe.py"'
python3 - "$SPIKE" "$HOOK" <<'PY'
import json, sys
spike, cmd = sys.argv[1], sys.argv[2]
entry = {"hooks": {"PreToolUse": [{"matcher": "Write|Edit",
         "hooks": [{"type": "command", "command": cmd, "timeout": 15}]}]}}
open(spike + "/.claude/settings.json", "w").write(json.dumps(entry, ensure_ascii=False, indent=2))
open(spike + "/.codex/hooks.json", "w").write(json.dumps(entry["hooks"], ensure_ascii=False, indent=2))
PY
echo "探针就绪：$SPIKE"
```

> 说明：Claude Code 读 `<项目>/.claude/settings.json` 的 hooks；Codex 读
> `<repo>/.codex/hooks.json`（调研四 §70-75）。**都用项目级配置，不碰
> `~/.codex/hooks.json`**（那里挂着 claude-pets 的 5 个钩子，改它会让那些钩子失信）。
> Codex 的 `hooks.json` 顶层就是事件表（不含外层 `"hooks"` 键），上面的脚本已按这个差异分别写。

## 2. S8：在 Claude Code 里跑

1. 新开一个会话，`cd /tmp/cg-spike`（**必须是这个目录**，项目级 settings 才生效；
   首次进入 Claude Code 会问是否信任该目录的设置，选信任）。
2. 让 AI 写一个文件：`请写一个文件 /tmp/cg-spike/hello.txt，内容是 hi`。
3. 写完后**紧接着**问：`你在刚才那次写文件时，有没有看到一条包含"探针XYZ"的内容？原样引用你看到的那句。`
4. 记录：
   - **AI 能原样引用"探针XYZ" → S8 通过（分支 A 成立）**
   - AI 说没看到 / 只字未提 → S8 不通过（分支 B）
   - AI 把那句话**当成消息甩给你**（"钩子给我发了个奇怪的指令"）→ 记为"触发注入防御"，
     等同不通过，并在 INTERFACE §2.1.2 里注明这个额外现象。
5. 同一次会话里再让 AI 用 **Edit** 改一次 `hello.txt`，重复第 3 步（确认不是 Write 独有）。

## 3. S9：在 Codex 里跑

1. `cd /tmp/cg-spike`，起 Codex；跑 `/hooks`，把上面这条 PreToolUse 钩子**信任**
   （不信任 = 不执行，会得到"什么都没发生"的假阴性）。
2. 让它写一个文件（Codex 走 `apply_patch`）：`请新建 /tmp/cg-spike/hello2.txt，内容 hi`。
3. 问同样的问题（第 2 节第 3 步）。
4. 看日志：`cat /tmp/cg-spike/logs/probe.jsonl | python3 -m json.tool`（或逐行看），确认三件事：
   - `payload.tool_name` 的真值（**预期 `apply_patch`**；这是端探测唯一允许用的内在信号）
   - `payload.tool_input` 里有没有 `file_path`（**预期没有**，只有 `command` 的补丁文本）
   - `codex_env` 是否非空 —— 顺便在 **Claude Code** 那次的日志里也看这个字段：
     只要两端都可能出现 `CODEX_*`，就实证了"环境变量不能当端探测判据"（C2 的根因）。

## 4. 结果怎么落（三处，缺一即返工）

| 结果 | 动作 |
|---|---|
| S8 **通过** | ① `_shared/context_guard_core.py` 的 `NOTICE_MODE` 改成 `"A"`（同步 vendored：`python3 _shared/sync_vendored.py --sync`）；② INTERFACE §2.1.2 删掉分支 B 那一行、§7.1 删掉 B 支；③ 跑一遍验收考卷（`test_context_guard_pretool` 的"取不到路径时不输出决策"两条对 A/B 都成立，不会红） |
| S8 **不通过** | ① `NOTICE_MODE` 保持 `"B"`（当前默认，无需改码）；② INTERFACE 删掉分支 A；③ 在 README 的诚实边界里加一句"路径解析失效的告知延迟到下一轮" |
| S9 确认 `apply_patch` | INTERFACE §7.1 的端探测判据定稿，M8 照此实现；`CODEX_*` 判据保持删除状态 |
| S9 发现 `tool_name` 不是 `apply_patch` | **停下来上报**：端探测没有内在信号可用，M8 的 weak 档处置要重新设计（不要临时改回环境变量判据） |

## 5. 收尾

```bash
rm -rf /tmp/cg-spike
```
Codex 端如果在 `~/.codex/config.toml` 里留下了这条探针的 `trusted_hash`，可以不管
（钩子定义已随目录删除而失效），也可以手动删掉那一条。
