#!/usr/bin/env python3
"""ib_seed.py —— idea-bomb 第一段的种子登记（闸门 1 上半）。

只读写 <session-dir>/seeds-<YYYYMMDD>.json，完全不碰迁移地图。会话文件是可丢弃的
临时态，所以不做备份；但仍然原子写——写成半截会让当天配额既读不回也清不掉，整天
停摆。同理**绝不静默重建**一个坏掉的会话文件，那等于把已用掉的配额悄悄清零。

用法：
    python3 ib_seed.py register [--session-dir P] [--today YYYY-MM-DD]   # stdin: JSON 数组
    python3 ib_seed.py list     [--session-dir P] [--today YYYY-MM-DD]

契约见 .devflow/INTERFACE.md 第 2 节。
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ib_common as ib  # noqa: E402

SEED_CAP_PER_DAY = ib.SEED_CAP_PER_DAY   # 常量只在 ib_common 存一份，避免改一处漏一处
SEED_TEXT_MIN_LEN = 8

DEFAULT_SESSION_DIR = os.path.expanduser("~/.idea-bomb/session")
KNOWN_COMMANDS = ("register", "list")


def session_path(session_dir, today):
    """seeds-20260923.json"""
    return os.path.join(session_dir, "seeds-%s.json" % today.replace("-", ""))


def load_session(path, today, command):
    """读当天会话文件。不存在返回空壳；坏了直接报错，不重建。"""
    if not os.path.exists(path):
        return {"date": today, "seeds": []}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = ib.strict_json_loads(handle.read())
    except (ValueError, OSError):
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_BAD_JSON,
                               "会话文件无法解析：%s。请人工查看，脚本不会覆盖它。" % path)],
                       exit_code=ib.EXIT_DATA)
    if not isinstance(data, dict) or not isinstance(data.get("seeds"), list):
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_BAD_JSON,
                               "会话文件结构不对：%s" % path)],
                       exit_code=ib.EXIT_DATA)
    return data


def save_session(path, data, command):
    """原子写。会话文件丢得起，但不能写成半截——半截会让当天配额既读不回也清不掉。"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    except (OSError, ValueError) as exc:
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_IO_FAILED, "会话文件写入失败：%s" % exc)],
                       exit_code=ib.EXIT_DATA)
    ib.atomic_write_text(path, text, command)


def validate_batch(items, command):
    """结构错（退出码 3）和内容错（退出码 2）分两轮，同一轮内收集全部错误。"""
    structure_errors = []
    for i, item in enumerate(items):
        field = "[%d].text" % i
        if not isinstance(item, dict):
            structure_errors.append(ib.err("[%d]" % i, ib.CODE_WRONG_TYPE, "第 %d 项不是对象" % i))
            continue
        if "text" not in item:
            structure_errors.append(ib.err(field, ib.CODE_MISSING, "第 %d 项缺 text" % i))
        elif not isinstance(item["text"], str):
            structure_errors.append(ib.err(field, ib.CODE_WRONG_TYPE, "第 %d 项的 text 不是字符串" % i))
    if structure_errors:
        ib.emit_reject(command, "input", structure_errors, exit_code=ib.EXIT_INPUT)

    content_errors = []
    for i, item in enumerate(items):
        field = "[%d].text" % i
        text = item["text"]
        stripped = text.strip()
        # 这里空字符串归 PLACEHOLDER（INTERFACE 2.1 第 4 步只给了这两个 code）
        if ib.is_placeholder(stripped):
            content_errors.append(ib.err(field, ib.CODE_PLACEHOLDER,
                                         "第 %d 个种子是占位内容" % i))
        elif len(stripped) < SEED_TEXT_MIN_LEN:
            content_errors.append(ib.err(field, ib.CODE_TOO_SHORT,
                                         "第 %d 个种子只有 %d 字，至少 %d 字"
                                         % (i, len(stripped), SEED_TEXT_MIN_LEN)))
    if content_errors:
        ib.emit_reject(command, "input", content_errors)


def cmd_register(args):
    command = "register"
    today = ib.resolve_today(args.today, command, args.sandboxed)
    items = ib.read_stdin_json(command, "array")
    if not items:
        ib.emit_reject(command, "input",
                       [ib.err("-", ib.CODE_EMPTY, "种子数组是空的")],
                       exit_code=ib.EXIT_INPUT)

    validate_batch(items, command)

    path = session_path(args.session_dir, today)
    session = load_session(path, today, command)
    already = len(session["seeds"])
    if already + len(items) > SEED_CAP_PER_DAY:
        ib.emit_reject(command, "seed_cap",
                       [ib.err("-", ib.CODE_CAP_EXCEEDED,
                               "今天已登记 %d 个种子，这批 %d 个会超过上限 %d。"
                               "发散归发散，进库的种子每天只留 %d 个。"
                               % (already, len(items), SEED_CAP_PER_DAY, SEED_CAP_PER_DAY))],
                       already=already, incoming=len(items), cap=SEED_CAP_PER_DAY)

    registered = []
    stamp = ib.now_iso()
    for offset, item in enumerate(items):
        seed_id = "S%d" % (already + offset + 1)
        record = {"seed_id": seed_id, "text": item["text"], "registered_at": stamp}
        session["seeds"].append(record)
        registered.append({"seed_id": seed_id, "text": item["text"]})
    session["date"] = today
    save_session(path, session, command)

    ib.emit_ok(command, date=today, registered=registered,
               total_today=len(session["seeds"]), cap=SEED_CAP_PER_DAY)


def cmd_list(args):
    command = "list"
    today = ib.resolve_today(args.today, command, args.sandboxed)
    path = session_path(args.session_dir, today)
    session = load_session(path, today, command)
    ib.emit_ok(command, date=today, seeds=session["seeds"],
               total_today=len(session["seeds"]), cap=SEED_CAP_PER_DAY)


def main():
    parser = ib.make_parser(argparse, KNOWN_COMMANDS, "idea-bomb 第一段种子登记")
    sub = parser.add_subparsers(dest="command")
    for name in KNOWN_COMMANDS:
        child = sub.add_parser(name)
        child.add_argument("--session-dir", default=DEFAULT_SESSION_DIR)
        child.add_argument("--today", default=None)
    args = parser.parse_args()
    if not args.command:
        ib.emit({"ok": False, "command": "-", "gate": "input",
                 "errors": [ib.err("-", ib.CODE_BAD_JSON, "缺子命令：register 或 list")]},
                ib.EXIT_INPUT)
    args.session_dir = os.path.expanduser(args.session_dir)
    # --today 只在数据目录被指到默认位置之外时生效，见 ib_common.resolve_today
    args.sandboxed = ib.path_is_overridden(args.session_dir, DEFAULT_SESSION_DIR)
    if args.command == "register":
        cmd_register(args)
    else:
        cmd_list(args)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # 兜底：正常路径不该走到这
        ib.emit({"ok": False, "command": ib.guess_command(KNOWN_COMMANDS), "gate": "input",
                 "errors": [ib.err("-", "UNEXPECTED", "未预期异常：%s" % exc)]},
                ib.EXIT_UNEXPECTED)
