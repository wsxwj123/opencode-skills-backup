#!/usr/bin/env python3
"""idea-bomb 闸门脚本的共享底座。

只放两个入口脚本（ib_map.py / ib_seed.py）都要用的东西：占位词判定、字段校验、
JSON 响应、退出码、日期。占位词表只能有一份——两份迟早会改一处忘一处。

契约见 .devflow/INTERFACE.md。仅标准库，仅 macOS / Python 3。
"""

import json
import os
import sys
from datetime import date as date_cls, datetime

# ---------------------------------------------------------------- 退出码

EXIT_OK = 0            # 成功 / 放行
EXIT_REJECT = 2        # 业务性拒绝（闸门拦下）
EXIT_INPUT = 3         # 输入格式错误
EXIT_DATA = 4          # 数据文件异常
EXIT_UNEXPECTED = 1    # 兜底

# ---------------------------------------------------------------- 错误码

CODE_MISSING = "MISSING"
CODE_EMPTY = "EMPTY"
CODE_PLACEHOLDER = "PLACEHOLDER"
CODE_TOO_SHORT = "TOO_SHORT"
CODE_WRONG_TYPE = "WRONG_TYPE"
CODE_TOO_FEW = "TOO_FEW"
CODE_NOT_ALLOWED = "NOT_ALLOWED"

CODE_BACKLOG_NOT_EMPTY = "BACKLOG_NOT_EMPTY"
CODE_UNKNOWN_SEED = "UNKNOWN_SEED"
CODE_SEED_ALREADY_USED = "SEED_ALREADY_USED"
CODE_INDEX_OUT_OF_RANGE = "INDEX_OUT_OF_RANGE"
CODE_PREFIX_MISMATCH = "PREFIX_MISMATCH"
CODE_ALREADY_DECIDED = "ALREADY_DECIDED"
CODE_BAD_JSON = "BAD_JSON"
CODE_IO_FAILED = "IO_FAILED"

# ---------------------------------------------------------------- 占位词

# INTERFACE 0.7 第 2 条：整串相等（已统一为小写，比较前对输入 lower()）
PLACEHOLDER_EXACT = frozenset([
    "-", "—", "–", "?", "？", "无", "空", "暂无",
    "n/a", "na", "null", "none", "todo", "tbd",
])

# INTERFACE 0.7 第 3 条：前缀匹配。真实数据里存在「待定：拟作 2027 青基主线方案 A」
# 这类"占位词 + 补充说明"，只靠整串相等抓不住。
PLACEHOLDER_PREFIX = (
    "待定", "待确认", "待柚子确认", "待议", "待补", "待填",
    "未定", "暂定", "搁置", "pending", "tbd", "todo",
)

# 三个终态。白名单收紧未来的写入，黑名单（占位词）放行历史遗留的自由文本裁决。
FINAL_VERDICTS = ("采纳", "否决", "归档")


def is_placeholder(value):
    """判定一个值是否算作占位（含空字符串）。非字符串一律视为占位。"""
    if not isinstance(value, str):
        return True
    stripped = value.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    if lowered in PLACEHOLDER_EXACT:
        return True
    return lowered.startswith(PLACEHOLDER_PREFIX)


def is_undecided(cell):
    """一个 cell 是否算未裁决。黑名单判定：只看 user_verdict 是不是占位。

    「不建议作主课题」「已否决（2026-09-15）：…」这类历史自由文本算已裁决，
    不该逼用户把自己下过的判断重做一遍。
    """
    if "user_verdict" not in cell:
        return True
    return is_placeholder(cell.get("user_verdict"))


# ---------------------------------------------------------------- 错误对象


def err(field, code, msg):
    return {"field": field, "code": code, "msg": msg}


def check_text_field(container, key, min_len, field_name=None):
    """按固定顺序校验一个字符串字段，返回错误 dict 或 None。

    顺序是契约的一部分：MISSING → EMPTY(含 null) → WRONG_TYPE → EMPTY(空白) →
    PLACEHOLDER → TOO_SHORT。空字符串报 EMPTY 而不是 PLACEHOLDER，见 INTERFACE 5.2。
    """
    name = field_name or key
    if key not in container:
        return err(name, CODE_MISSING, "缺少 %s" % name)
    value = container[key]
    if value is None:
        return err(name, CODE_EMPTY, "%s 为 null" % name)
    if not isinstance(value, str):
        return err(name, CODE_WRONG_TYPE, "%s 必须是字符串，收到 %s" % (name, type(value).__name__))
    stripped = value.strip()
    if not stripped:
        return err(name, CODE_EMPTY, "%s 是空白" % name)
    if is_placeholder(stripped):
        return err(name, CODE_PLACEHOLDER, "%s 填的是占位词「%s」，不接受" % (name, stripped))
    if len(stripped) < min_len:
        return err(name, CODE_TOO_SHORT,
                   "%s 只有 %d 字，至少要 %d 字" % (name, len(stripped), min_len))
    return None


# ---------------------------------------------------------------- 输出


def emit(payload, exit_code):
    """stdout 永远是单个 JSON 对象，然后按退出码结束进程。"""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def emit_reject(command, gate, errors, exit_code=EXIT_REJECT, **extra):
    payload = {"ok": False, "command": command, "gate": gate, "errors": errors}
    payload.update(extra)
    emit(payload, exit_code)


def emit_ok(command, **fields):
    payload = {"ok": True, "command": command}
    payload.update(fields)
    emit(payload, EXIT_OK)


def warn(message):
    """人类可读提示走 stderr，不参与任何断言。"""
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


# ---------------------------------------------------------------- stdin


def _reject_constant(name):
    """json 默认吃 NaN/Infinity/-Infinity，吞进去就会写出严格解析器读不了的文件。"""
    raise ValueError("JSON 里不接受 %s" % name)


def strict_json_loads(text):
    """只认标准 JSON。NaN / Infinity / -Infinity 一律当解析失败。"""
    return json.loads(text, parse_constant=_reject_constant)


def read_stdin_json(command, expect):
    """读 stdin 并解析成 JSON。expect 为 'object' 或 'array'。"""
    raw = sys.stdin.read()
    try:
        data = strict_json_loads(raw)
    except (ValueError, TypeError):
        emit_reject(command, "input",
                    [err("-", CODE_BAD_JSON, "stdin 不是合法 JSON")],
                    exit_code=EXIT_INPUT)
    if expect == "object" and not isinstance(data, dict):
        emit_reject(command, "input",
                    [err("-", CODE_BAD_JSON, "stdin 必须是单个 JSON 对象")],
                    exit_code=EXIT_INPUT)
    if expect == "array" and not isinstance(data, list):
        emit_reject(command, "input",
                    [err("-", CODE_BAD_JSON, "stdin 必须是 JSON 数组")],
                    exit_code=EXIT_INPUT)
    return data


# ---------------------------------------------------------------- 日期


def path_is_overridden(actual, default):
    """调用方是不是把数据路径指到了默认位置之外。用 realpath 防 ../ 绕过。"""
    return os.path.realpath(os.path.expanduser(actual)) != \
        os.path.realpath(os.path.expanduser(default))


def resolve_today(raw, command, sandboxed):
    """--today 优先，否则系统本地日期。格式非法直接拒绝，不静默回退。

    但 `--today` 只在沙箱里生效——`sandboxed` 为真表示数据路径被显式指到了默认位置
    之外（测试就是这么跑的）。对真实数据文件动手时一律用系统时钟：契约说这个参数
    仅供测试注入，而脚本分不清谁在调用，只能看它碰的是不是真数据。否则改个日期就
    能把种子唯一性校验重置一遍，闸门 1 等于白做。
    """
    system_today = date_cls.today().isoformat()
    if raw is None:
        return system_today
    try:
        injected = date_cls.fromisoformat(raw.strip()).isoformat()
    except (ValueError, AttributeError):
        emit_reject(command, "input",
                    [err("--today", CODE_WRONG_TYPE, "--today 必须是 YYYY-MM-DD")],
                    exit_code=EXIT_INPUT)
    if not sandboxed:
        warn("提示：--today 只在指定了非默认数据路径时生效（测试用）。"
             "这次操作的是默认数据，已按系统日期 %s 计。" % system_today)
        return system_today
    return injected


def fsync_dir(file_path):
    """os.replace 改的是目录项，内容 fsync 了不代表改名落了盘。

    失败不算错——替换本身已经完成，这一步只是把它钉得更死。
    """
    try:
        dir_fd = os.open(os.path.dirname(os.path.abspath(file_path)), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


def atomic_write_text(path, text, command, gate="storage"):
    """同目录临时文件 + os.replace。

    直接 open(path, "w") 在打开的那一瞬间就把原文件清空了，中途崩掉只剩半截，
    连已有内容都读不回来。任何数据文件都不许那样写。
    """
    tmp_path = "%s.tmp-%d" % (path, os.getpid())
    try:
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        except OSError as exc:
            emit_reject(command, gate,
                        [err("-", CODE_IO_FAILED, "写入失败：%s" % exc)],
                        exit_code=EXIT_DATA)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass  # 清理失败不许顶掉正在传播的退出
    fsync_dir(path)


def now_iso():
    """本地时刻的 ISO 8601，带时区偏移。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- 参数解析


def guess_command(known_commands):
    """参数解析失败时也要给出 command 字段，从 argv 里捞第一个已知子命令名。"""
    for token in sys.argv[1:]:
        if token in known_commands:
            return token
    return "-"


def make_parser(argparse_module, known_commands, description):
    """argparse 默认出错退出码是 2，会和业务拒绝码撞车，必须改成 3。

    add_subparsers 默认沿用 type(parser) 作为子解析器类，所以子命令的参数错误
    也会走到这里。
    """

    class JsonErrorParser(argparse_module.ArgumentParser):
        def error(self, message):
            emit({"ok": False, "command": guess_command(known_commands), "gate": "input",
                  "errors": [err("-", CODE_BAD_JSON, "参数错误：%s" % message)]},
                 EXIT_INPUT)

    return JsonErrorParser(description=description)
