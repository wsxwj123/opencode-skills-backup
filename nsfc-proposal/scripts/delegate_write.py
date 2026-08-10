#!/usr/bin/env python3
# delegate_write.py —— nsfc-proposal 撰写编排入口（薄封装：import 本家 vendored 共享核心）
#
# 逻辑全在 delegate_write_core.py（四家逐字节一致，L4 md5 守卫）。本文件只声明 nsfc
# 的账本映射 config：section 形态 P1..P7；文献库是 data/literature_index.json 的 dict
# 形态 {metadata, entries:[...]}，条目主键 id；本节文献切片无独立矩阵，
# 走 entries[].used_in_sections 含本 PX 过滤（§7）。核心已 config 化 index_shape=data_dict，
# 直接读原生 dict，不再需要主会话把 data/ 布局投影成 root list。

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from delegate_write_core import (  # noqa: E402
    BARE_NUM_RE, KEY_RE, SECTION_RE, _claim_set_hash, main,
)

__all__ = ["BARE_NUM_RE", "KEY_RE", "SECTION_RE", "CONFIG", "main"]

CONFIG = {
    "family": "nsfc-proposal",
    "section_regex": r"^P\d+(\.\d+)*$",  # P1 / P2.3 等
    # data/outline.json 是 outline_manager.py confirm 落的 P1 大纲真源（round19）。
    # 后两项原样保留只为不改 fallthrough；storyline.json 是 gsw 产物，nsfc 永不产出（遗留项）。
    "outline_files": ["data/outline.json", "project_state.json", "storyline.json"],
    "outline_id_field": "section_id",
    "index_path": "data/literature_index.json",   # dict {metadata, entries:[...]}
    "index_shape": "data_dict",
    "index_entries_key": "entries",
    "index_id_field": "id",                        # 条目主键 L-001 等
    # 无独立矩阵：used_in_sections 含本 PX 过滤（§7）
    "lit_section": {"mode": "index_used_in", "file": None},
}


GATE_SUBCOMMANDS = ("pack-write", "pack-prep")
GATE_SECTION = "P1"


def _argv_value(argv, flag):
    """取 --flag 的值，口径与 argparse 对齐。取不到返回 None。

    🔴 不许改回「按完整参数名逐字比对」：共享核心的解析走 argparse，它**默认接受
    无歧义的长选项前缀缩写**，`--sec P1` 照样被解析成 `--section P1`。闸口按字面量
    比就会被一条缩写整个绕过（round19 首版实测：`--sec` 让未确认的大纲 rc=0 出包，
    连 fail-closed 那道保险一起废掉）。写命令行的正是本闸口要约束的 AI 自己，
    缩写一个参数比伪造签名便宜得多。

    三条对齐：① 长选项前缀匹配；② `--flag=value` 形式；③ 重复传参取**最后一个**。
    宁可多认：真有歧义时 argparse 自己会报错退出，不会放行。
    """
    name = flag[2:]
    found = None
    for i, arg in enumerate(argv):
        if not arg.startswith("--"):
            continue
        head, sep, tail = arg.partition("=")
        abbrev = head[2:]
        # abbrev 为空＝裸 `--`（argparse 的选项终止符），不是本 flag
        if not abbrev or not name.startswith(abbrev):
            continue
        if sep:
            found = tail
        elif i + 1 < len(argv):
            found = argv[i + 1]
    return found


def _gate_die(reason, detail=""):
    sys.stderr.write("OUTLINE_GATE: %s%s\n" % (reason, (" " + detail) if detail else ""))
    sys.exit(2)


def outline_gate(argv):
    """P1 大纲闸口：没经用户确认 / 被改过 / 核证过期，一律不许出任务包。

    只在 pack-write / pack-prep 且 --section P1 时介入；verify-write 与其余节
    行为与改造前逐字节相同。大纲文件不存在时也不介入 —— 那句
    `outline has no section: P1` 由共享核心报，比闸口的话更可操作。

    🔴 fail-closed：outline_manager 不可用（缺文件/import 炸/返回值形态不对）时
    **拦住**，不许 try/except 放行 —— 检查器坏了却照常出包就是新的假绿点。
    """
    if not argv or argv[0] not in GATE_SUBCOMMANDS:
        return
    if _argv_value(argv, "--section") != GATE_SECTION:
        return
    root = _argv_value(argv, "--root")
    if not root:
        return
    outline_file = os.path.join(root, "data", "outline.json")
    if not os.path.exists(outline_file):
        return

    try:
        import outline_manager
        result = outline_manager.check(root)
        ok, reason = result
        if not isinstance(ok, bool):
            raise TypeError("check() 第一个返回值不是布尔: %r" % (ok,))
    except Exception:
        _gate_die("outline_checker_unavailable",
                  "outline_manager.py 缺失或不可用，无法确认大纲已经用户点头；"
                  "先修好它再出包")
    if not ok:
        _gate_die(reason, "跑 outline_manager.py check --root %s 看详情" % root)

    if argv[0] != "pack-write":
        return  # pack-prep 正是为了产核证草案，不做核证过期闸

    ev_path = os.path.join(root, "claim_evidence.json")
    if not os.path.isfile(ev_path):
        return  # 缺证据/坏 JSON 交给共享核心报，它的文案更可操作
    try:
        with open(ev_path, "r", encoding="utf-8") as f:
            evidence = json.load(f)
    except Exception:
        return

    expected = _claim_set_hash(_load_bearing_claims(outline_file))
    got = evidence.get("outline_claim_set_hash") if isinstance(evidence, dict) else None
    rows_ok = isinstance(evidence, dict) and isinstance(evidence.get("rows"), list)
    if not rows_ok or not isinstance(got, str) or got != expected:
        _gate_die("claim_evidence_stale",
                  "大纲论点已变更，需重跑核证：claim_evidence.json 顶层需为 "
                  '{"outline_claim_set_hash": ..., "rows": [...]}，'
                  "指纹原样抄自 .prep_task_P1.json（重跑 pack-prep）")


def _load_bearing_claims(outline_file):
    """取 P1 的派生承重论点。走到这里 check() 已经过了，文件必然是好的。"""
    with open(outline_file, "r", encoding="utf-8") as f:
        doc = json.load(f)
    for sec in doc.get("sections") or []:
        if isinstance(sec, dict) and sec.get("section_id") == GATE_SECTION:
            return sec.get("load_bearing_claims") or []
    return []


if __name__ == "__main__":
    outline_gate(sys.argv[1:])
    main(CONFIG)
