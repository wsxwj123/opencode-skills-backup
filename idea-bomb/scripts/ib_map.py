#!/usr/bin/env python3
"""ib_map.py —— 迁移地图的唯一写入通道。

四个子命令：
    status   只读体检：总数、已裁决/未裁决、备份占用。退出码恒 0。
    gate     零积压闸（闸门 3）：库里还有未裁决项就拦住开工。
    commit   写入一条 schema 2 新假说（闸门 1 下半 + 闸门 2 + 闸门 4）。
    verdict  给已有格子补裁决（闸门 4；存量分诊用）。

两条写入路径（commit / verdict）走完全相同的安全流程：取写锁 → 备份 → 临时文件 →
fsync → 回读校验 → 替换前核对内容指纹 → os.replace 原子替换 → fsync 目录。
任何一步失败，原文件一个字节都不动。

脚本**永不删除**任何备份文件。备份多了由用户自己清。

契约见 .devflow/INTERFACE.md 第 1、3、4 节。
"""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ib_common as ib  # noqa: E402

HYPOTHESIS_CAP_PER_DAY = ib.HYPOTHESIS_CAP_PER_DAY  # 常量只在 ib_common 存一份
LOCK_TIMEOUT_SECONDS = 10

DEFAULT_MAP = os.path.expanduser("~/.idea-bomb/migration_map.json")
DEFAULT_SESSION_DIR = os.path.expanduser("~/.idea-bomb/session")
KNOWN_COMMANDS = ("status", "gate", "commit", "verdict")

ALLOWED_METHODS = ("transfer", "combine", "angle")
ALLOWED_STATUS = ("untried", "done", "failed")
HYPOTHESIS_KEYS = ("background", "gap", "design", "innovation")

# closest_work 里出现这些子串，就算作「查新确实做了但没找到先例」，此时 diff 可以留空。
NO_PRIOR_ART_MARKERS = (
    "未检索到", "未检索", "检索未见", "未见先例", "未见直接",
    "无直接先例", "无先例", "未找到先例", "0命中", "无命中",
)

UNDECIDED_PREVIEW_LIMIT = 30
IDEA_PREFIX_LEN = 12
SHA_PLACEHOLDER = "0" * 64


# ================================================================ 地图读写


def load_map(path, command):
    """读地图。不存在或解析失败都直接中止，绝不重建、绝不覆盖。"""
    if not os.path.exists(path):
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_IO_FAILED, "迁移地图不存在：%s" % path)],
                       exit_code=ib.EXIT_DATA)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as exc:
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_IO_FAILED, "读不了迁移地图：%s" % exc)],
                       exit_code=ib.EXIT_DATA)
    try:
        data = ib.strict_json_loads(raw)
    except ValueError:
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_BAD_JSON,
                               "迁移地图不是合法 JSON：%s。脚本不会覆盖它，请人工修。" % path)],
                       exit_code=ib.EXIT_DATA)
    if not isinstance(data, dict) or not isinstance(data.get("cells"), list):
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_BAD_JSON, "迁移地图结构不对，缺 cells 数组")],
                       exit_code=ib.EXIT_DATA)
    # 每个 cell 都得是对象。手工编辑最容易在这里留下 null 或裸字符串，
    # 而 status 正是用来诊断手工编辑事故的，它自己先崩就什么都查不了了。
    for index, cell in enumerate(data["cells"]):
        if not isinstance(cell, dict):
            ib.emit_reject(command, "storage",
                           [ib.err("cells[%d]" % index, ib.CODE_BAD_JSON,
                                   "cells[%d] 不是对象（是 %s），地图被改坏了，脚本不动它"
                                   % (index, type(cell).__name__))],
                           exit_code=ib.EXIT_DATA)
    return data, raw


def acquire_write_lock(map_path, command):
    """写入期间独占地图。锁加在单独的 .lock 文件上——map 本身会被 os.replace 换掉，
    锁在旧 inode 上就等于没锁。

    没有这道锁，load_map 到 os.replace 之间是一段 read-modify-write 竞态：两个进程
    并发跑 verdict，后完成的那个会拿旧快照整体覆盖，两边都返回 ok，改动静默消失。
    """
    lock_path = map_path + ".lock"
    try:
        handle = open(lock_path, "a+")
    except OSError as exc:
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_IO_FAILED, "建不了锁文件：%s" % exc)],
                       exit_code=ib.EXIT_DATA)
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except OSError:
            if time.monotonic() >= deadline:
                handle.close()
                ib.emit_reject(command, "storage",
                               [ib.err("-", ib.CODE_IO_FAILED,
                                       "另一个进程正在写迁移地图，等了 %d 秒还没轮到，"
                                       "本次不写。请确认没有卡住的进程后重跑。"
                                       % LOCK_TIMEOUT_SECONDS)],
                               exit_code=ib.EXIT_DATA)
            time.sleep(0.05)


def integrity_of(data, raw_text):
    """对比文件实际内容与上次写入时记下的 sha256。

    sha 存在文件内部，字面上无法自指。解法：算 sha 时把 last_sha256 那 64 个字符
    换成定长占位串，两边用同一口径，就自洽了。
    """
    record = data.get("_integrity")
    if not isinstance(record, dict) or not record.get("last_sha256"):
        # 存量地图没有这个字段，视为 bootstrap，不报警。
        return {"checked": False, "external_edit_suspected": False}
    recorded = record["last_sha256"]
    normalized = raw_text.replace('"last_sha256": "%s"' % recorded,
                                 '"last_sha256": "%s"' % SHA_PLACEHOLDER, 1)
    actual = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    suspected = actual != recorded
    if suspected:
        ib.warn("警告：迁移地图的内容与上次脚本写入时不一致，疑似被外部直接编辑过。"
                "闸门无法拦住绕过脚本的写入，只能这样事后提醒。")
    return {"checked": True, "external_edit_suspected": suspected}


def pick_backup_path(backup_dir, command):
    """备份文件名固定 migration_map.<YYYYMMDD-HHMMSS>.json。

    同一秒内连写两次会撞名，撞了就把时间戳往后推一秒——绝不覆盖已有备份。
    """
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except OSError as exc:
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_IO_FAILED, "备份目录建不了：%s" % exc)],
                       exit_code=ib.EXIT_DATA)
    base = datetime.now()
    for bump in range(3600):
        stamp = (base + timedelta(seconds=bump)).strftime("%Y%m%d-%H%M%S")
        candidate = os.path.join(backup_dir, "migration_map.%s.json" % stamp)
        if not os.path.exists(candidate):
            return candidate
    ib.emit_reject(command, "storage",
                   [ib.err("-", ib.CODE_IO_FAILED, "备份文件名连续一小时都被占用，放弃写入")],
                   exit_code=ib.EXIT_DATA)


def serialize_with_integrity(data, cells_count, previous_writes, command):
    """生成最终文本，顺便把 _integrity 更新成本次写入后的状态。"""
    data["_integrity"] = {
        "writes": previous_writes + 1,
        "last_write": ib.now_iso(),
        "last_cells_count": cells_count,
        "last_sha256": SHA_PLACEHOLDER,
    }
    try:
        # allow_nan 默认是 True，NaN/Infinity 会被原样写出去，写完这份文件对严格
        # JSON 解析器就不可读了，而回读校验只看条目数，根本发现不了。
        text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    except ValueError as exc:
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_IO_FAILED,
                               "数据里有 NaN/Infinity 这类非标准 JSON 值，写出去会让文件"
                               "读不回来，已中止：%s" % exc)],
                       exit_code=ib.EXIT_DATA)
    new_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    final_text = text.replace('"last_sha256": "%s"' % SHA_PLACEHOLDER,
                              '"last_sha256": "%s"' % new_sha, 1)
    data["_integrity"]["last_sha256"] = new_sha
    return final_text


def safe_write(map_path, backup_dir, data, expected_cells, previous_writes, command,
               loaded_sha):
    """INTERFACE 4.1 的七步写入路径。返回备份文件的绝对路径。

    `loaded_sha` 是 load_map 那一刻磁盘上的内容指纹，替换前会重新核对一次：写锁之外
    的人（比如拿编辑器直接改 JSON 的）动过文件就拒绝写入，绝不拿旧快照盖掉别人的改动。
    """
    original_size = os.path.getsize(map_path)

    backup_path = pick_backup_path(backup_dir, command)
    try:
        shutil.copy2(map_path, backup_path)
    except OSError as exc:
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_IO_FAILED, "备份失败，未做任何写入：%s" % exc)],
                       exit_code=ib.EXIT_DATA)
    if os.path.getsize(backup_path) != original_size:
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_IO_FAILED, "备份体积和原文件对不上，中止写入")],
                       exit_code=ib.EXIT_DATA)

    text = serialize_with_integrity(data, expected_cells, previous_writes, command)
    tmp_path = "%s.tmp-%d" % (map_path, os.getpid())
    try:
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            ib.emit_reject(command, "storage",
                           [ib.err("-", ib.CODE_IO_FAILED, "临时文件写失败：%s" % exc)],
                           exit_code=ib.EXIT_DATA)

        # 回读校验：条目数一旦对不上，原文件还没被动过，炸在这里是最便宜的。
        try:
            with open(tmp_path, "r", encoding="utf-8") as handle:
                reread = json.load(handle)
        except (ValueError, OSError) as exc:
            ib.emit_reject(command, "storage",
                           [ib.err("-", ib.CODE_IO_FAILED, "回读校验失败：%s" % exc)],
                           exit_code=ib.EXIT_DATA)
        if len(reread.get("cells", [])) != expected_cells:
            ib.emit_reject(command, "storage",
                           [ib.err("-", ib.CODE_IO_FAILED,
                                   "回读后条目数是 %d，期望 %d，中止写入"
                                   % (len(reread.get("cells", [])), expected_cells))],
                           exit_code=ib.EXIT_DATA)

        # 乐观锁：替换前确认磁盘上还是我们读到的那一版
        current_sha = disk_sha(map_path)
        if current_sha != loaded_sha:
            ib.emit_reject(command, "storage",
                           [ib.err("-", ib.CODE_IO_FAILED,
                                   "这次操作期间迁移地图被别的写入改过了，本次改动没写入，"
                                   "以免盖掉对方的改动。重新跑一遍即可。")],
                           exit_code=ib.EXIT_DATA)

        os.replace(tmp_path, map_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass  # 清理失败不许顶掉正在传播的 SystemExit，否则会吐出第二个 JSON

    ib.fsync_dir(map_path)
    return os.path.abspath(backup_path)


def disk_sha(path):
    """磁盘上这份文件的字节指纹，用于替换前的乐观锁比对。"""
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def previous_writes_of(data):
    record = data.get("_integrity")
    if isinstance(record, dict) and isinstance(record.get("writes"), int):
        return record["writes"]
    return 0


# ================================================================ 统计


def idea_prefix(cell):
    idea = cell.get("idea")
    if not isinstance(idea, str):
        return ""
    return idea[:IDEA_PREFIX_LEN]


def undecided_items_of(cells):
    items = []
    for index, cell in enumerate(cells):
        if ib.is_undecided(cell):
            items.append({"index": index,
                          "idea_prefix": idea_prefix(cell),
                          "user_verdict": cell.get("user_verdict"),
                          "date": cell.get("date")})
    return items


def is_schema2(cell):
    return cell.get("schema") == 2


def backups_report(backup_dir):
    entries = []
    if os.path.isdir(backup_dir):
        for name in os.listdir(backup_dir):
            full = os.path.join(backup_dir, name)
            if name.startswith("migration_map.") and name.endswith(".json") and os.path.isfile(full):
                entries.append(os.path.getsize(full))
    return {"dir": os.path.abspath(backup_dir), "count": len(entries), "bytes": sum(entries),
            "note": "脚本不会自动删除备份，需手动清理"}


# ================================================================ 字段校验


def no_prior_art(closest_work):
    text = closest_work.strip()
    return any(marker in text for marker in NO_PRIOR_ART_MARKERS)


def validate_hypothesis(cell):
    errors = []
    if "hypothesis" not in cell:
        errors.append(ib.err("hypothesis", ib.CODE_MISSING, "缺少假说四要素"))
        return errors
    value = cell["hypothesis"]
    if not isinstance(value, dict):
        errors.append(ib.err("hypothesis", ib.CODE_WRONG_TYPE,
                             "hypothesis 必须是含四要素的对象"))
        return errors
    for key in HYPOTHESIS_KEYS:
        if key not in value:
            errors.append(ib.err("hypothesis.%s" % key, ib.CODE_MISSING,
                                 "假说缺 %s" % key))
            continue
        problem = ib.check_text_field(value, key, 30, field_name="hypothesis.%s" % key)
        if problem:
            errors.append(problem)
    for key in value:
        if key not in HYPOTHESIS_KEYS:
            errors.append(ib.err("hypothesis.%s" % key, ib.CODE_NOT_ALLOWED,
                                 "hypothesis 只收四要素，多出来的 %s 请挪到别的字段" % key))
    return errors


def validate_feasibility_layers(cell):
    errors = []
    if "feasibility_layers" not in cell:
        errors.append(ib.err("feasibility_layers", ib.CODE_MISSING, "缺少三层可行性"))
        return errors
    value = cell["feasibility_layers"]
    if not isinstance(value, dict):
        errors.append(ib.err("feasibility_layers", ib.CODE_WRONG_TYPE,
                             "feasibility_layers 必须是对象"))
        return errors
    if not value:
        errors.append(ib.err("feasibility_layers", ib.CODE_EMPTY, "三层可行性是空的"))
        return errors
    if len(value) < 3:
        errors.append(ib.err("feasibility_layers", ib.CODE_TOO_FEW,
                             "可行性只写了 %d 层，至少三层" % len(value)))
    for key in value:
        problem = ib.check_text_field(value, key, 10,
                                      field_name="feasibility_layers.%s" % key)
        if problem:
            errors.append(problem)
    return errors


def validate_novelty_queries(cell, method_value):
    errors = []
    minimum = 2 if method_value == "transfer" else 1
    if "novelty_queries" not in cell:
        errors.append(ib.err("novelty_queries", ib.CODE_MISSING, "缺少查新检索式"))
        return errors
    value = cell["novelty_queries"]
    if not isinstance(value, list):
        errors.append(ib.err("novelty_queries", ib.CODE_WRONG_TYPE,
                             "novelty_queries 必须是字符串数组"))
        return errors
    if not value:
        errors.append(ib.err("novelty_queries", ib.CODE_EMPTY, "一条检索式都没填"))
        return errors
    for i, item in enumerate(value):
        field = "novelty_queries[%d]" % i
        if not isinstance(item, str):
            errors.append(ib.err(field, ib.CODE_WRONG_TYPE, "第 %d 条检索式不是字符串" % i))
            continue
        stripped = item.strip()
        if not stripped:
            errors.append(ib.err(field, ib.CODE_EMPTY, "第 %d 条检索式是空的" % i))
        elif ib.is_placeholder(stripped):
            errors.append(ib.err(field, ib.CODE_PLACEHOLDER, "第 %d 条检索式是占位词" % i))
        elif len(stripped) < 3:
            errors.append(ib.err(field, ib.CODE_TOO_SHORT, "第 %d 条检索式太短" % i))
    if len(value) < minimum:
        # 跨界迁移必须用源领域原名再搜一遍，只搜目标领域会漏掉撞车。
        errors.append(ib.err("novelty_queries", ib.CODE_TOO_FEW,
                             "method=%s 至少要 %d 条检索式，只给了 %d 条"
                             % (method_value, minimum, len(value))))
    return errors


def validate_novelty_evidence(cell):
    """closest_work + diff 的条件规则，见 INTERFACE 1.5。"""
    errors = []
    problem = ib.check_text_field(cell, "closest_work", 4)
    if problem:
        # closest_work 都不合格时不再连坐 diff，免得一次报两条把人绕晕。
        return [problem]
    if no_prior_art(cell["closest_work"]):
        return errors
    problem = ib.check_text_field(cell, "diff", 10)
    if problem:
        errors.append(problem)
    return errors


def validate_enum(cell, key, allowed):
    if key not in cell:
        return ib.err(key, ib.CODE_MISSING, "缺少 %s" % key)
    if cell[key] not in allowed:
        return ib.err(key, ib.CODE_NOT_ALLOWED,
                      "%s 只能是 %s 之一" % (key, "/".join(allowed)))
    return None


def validate_cell_fields(cell):
    """schema 2 新 cell 的必填校验。一次把全部问题收齐，别让人来回补七八次。

    不含 user_verdict / restart_condition——它们归裁决终态闸（gate=verdict）。
    """
    errors = []
    problem = ib.check_text_field(cell, "idea", 30)
    if problem:
        errors.append(problem)
    errors.extend(validate_hypothesis(cell))
    errors.extend(validate_feasibility_layers(cell))
    problem = ib.check_text_field(cell, "falsification", 30)
    if problem:
        errors.append(problem)

    method_problem = validate_enum(cell, "method", ALLOWED_METHODS)
    if method_problem:
        errors.append(method_problem)
    method_value = cell.get("method") if not method_problem else None
    errors.extend(validate_novelty_queries(cell, method_value))
    errors.extend(validate_novelty_evidence(cell))

    for key in ("novelty", "feasibility", "quadrant", "platform", "disease"):
        problem = ib.check_text_field(cell, key, 1)
        if problem:
            errors.append(problem)

    status_problem = validate_enum(cell, "status", ALLOWED_STATUS)
    if status_problem:
        errors.append(status_problem)
    return errors


def validate_verdict_fields(payload, field_prefix=""):
    """裁决终态闸：只收三终态，归档必须带重启条件。"""
    errors = []
    verdict_field = field_prefix + "user_verdict"
    if "user_verdict" not in payload:
        errors.append(ib.err(verdict_field, ib.CODE_MISSING, "缺少 user_verdict"))
        return errors
    verdict = payload["user_verdict"]
    # 精确相等，不 strip、不前缀匹配：「采纳：作为 2027 青基主线」这种补充说明请写别处。
    if verdict not in ib.FINAL_VERDICTS:
        errors.append(ib.err(verdict_field, ib.CODE_NOT_ALLOWED,
                             "user_verdict 只接受 采纳/否决/归档，不收「%s」这类占位或带注解的写法"
                             % verdict))
        return errors
    if verdict == "归档":
        problem = ib.check_text_field(payload, "restart_condition", 10,
                                      field_name=field_prefix + "restart_condition")
        if problem:
            errors.append(problem)
    return errors


# ================================================================ 子命令


def cmd_status(args):
    command = "status"
    data, raw = load_map(args.map, command)
    cells = data["cells"]
    undecided = undecided_items_of(cells)
    schema2 = sum(1 for cell in cells if is_schema2(cell))
    ib.emit_ok(command,
               total=len(cells),
               schema1=len(cells) - schema2,
               schema2=schema2,
               decided=len(cells) - len(undecided),
               undecided=len(undecided),
               archived=sum(1 for cell in cells if cell.get("archived") is True),
               undecided_items=undecided,
               integrity=integrity_of(data, raw),
               backups=backups_report(args.backup_dir))


def cmd_gate(args):
    command = "gate"
    data, raw = load_map(args.map, command)
    cells = data["cells"]
    undecided = undecided_items_of(cells)
    integrity = integrity_of(data, raw)
    if not undecided:
        ib.emit_ok(command, undecided=0, total=len(cells), integrity=integrity)
    ib.emit_reject(command, "backlog",
                   [ib.err("-", ib.CODE_BACKLOG_NOT_EMPTY,
                           "库里还有 %d 格没裁决，先清干净再出新想法。"
                           "跑 ib_map.py status 看清单，用 ib_map.py verdict 逐条下裁决。"
                           % len(undecided))],
                   undecided=len(undecided),
                   total=len(cells),
                   undecided_items=undecided[:UNDECIDED_PREVIEW_LIMIT],
                   undecided_truncated=len(undecided) > UNDECIDED_PREVIEW_LIMIT,
                   integrity=integrity)


def load_seed_ids(session_dir, today, command):
    path = os.path.join(session_dir, "seeds-%s.json" % today.replace("-", ""))
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            session = json.load(handle)
    except (ValueError, OSError):
        ib.emit_reject(command, "storage",
                       [ib.err("-", ib.CODE_BAD_JSON, "当天会话文件无法解析：%s" % path)],
                       exit_code=ib.EXIT_DATA)
    seeds = session.get("seeds") if isinstance(session, dict) else None
    if not isinstance(seeds, list):
        return []
    return [s.get("seed_id") for s in seeds if isinstance(s, dict)]


def cmd_commit(args):
    command = "commit"
    today = ib.resolve_today(args.today, command, args.sandboxed)
    lock = acquire_write_lock(args.map, command)     # 持到进程退出，见 acquire_write_lock
    data, raw = load_map(args.map, command)
    loaded_sha = disk_sha(args.map)
    integrity = integrity_of(data, raw)
    cell = ib.read_stdin_json(command, "object")

    if not args.seed_id:
        ib.emit_reject(command, "input",
                       [ib.err("--seed-id", ib.CODE_MISSING,
                               "必须指明这条假说展开自哪个种子（--seed-id）")],
                       exit_code=ib.EXIT_INPUT, integrity=integrity)

    known_seeds = load_seed_ids(args.session_dir, today, command)
    if args.seed_id not in known_seeds:
        ib.emit_reject(command, "seed_link",
                       [ib.err("--seed-id", ib.CODE_UNKNOWN_SEED,
                               "今天没登记过种子 %s。第二段只能展开第一段登记过的种子。"
                               % args.seed_id)],
                       known_seeds=known_seeds, integrity=integrity)

    cells = data["cells"]
    today_cells = [c for c in cells if is_schema2(c) and c.get("date") == today]
    if any(c.get("seed_id") == args.seed_id for c in today_cells):
        ib.emit_reject(command, "seed_link",
                       [ib.err("--seed-id", ib.CODE_SEED_ALREADY_USED,
                               "种子 %s 今天已经展开过一次了" % args.seed_id)],
                       integrity=integrity)

    if len(today_cells) >= HYPOTHESIS_CAP_PER_DAY:
        ib.emit_reject(command, "hypothesis_cap",
                       [ib.err("-", ib.CODE_CAP_EXCEEDED,
                               "今天已经写进 %d 个深度假说，到顶了。宁可给 1 个尖的。"
                               % len(today_cells))],
                       today_count=len(today_cells), cap=HYPOTHESIS_CAP_PER_DAY,
                       integrity=integrity)

    field_errors = validate_cell_fields(cell)
    if field_errors:
        ib.emit_reject(command, "required_fields", field_errors, integrity=integrity)

    verdict_errors = validate_verdict_fields(cell)
    if verdict_errors:
        ib.emit_reject(command, "verdict", verdict_errors, integrity=integrity)

    # 受控字段一律以脚本的值为准，防的是靠伪造 date 绕开日上限。
    cell["schema"] = 2
    cell["date"] = today
    cell["committed_at"] = ib.now_iso()
    cell["seed_id"] = args.seed_id
    if cell["user_verdict"] == "归档":
        cell["archived"] = True
    else:
        cell.pop("archived", None)

    before_count = len(cells)
    cells.append(cell)
    backup_path = safe_write(args.map, args.backup_dir, data, before_count + 1,
                             previous_writes_of(data), command, loaded_sha)
    lock.close()

    ib.emit_ok(command, index=before_count, seed_id=args.seed_id, date=today,
               user_verdict=cell["user_verdict"],
               today_count=len(today_cells) + 1, cap=HYPOTHESIS_CAP_PER_DAY,
               backup=backup_path, cells_before=before_count, cells_after=len(cells),
               integrity=integrity)


def validate_verdict_batch(items, cells, allow_overwrite, command, integrity):
    """全有或全无：任一条不合格则整批拒绝，一格不写。分层收错，同层收齐。"""
    structure_errors = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            structure_errors.append(ib.err("[%d]" % i, ib.CODE_WRONG_TYPE, "第 %d 项不是对象" % i))
    if structure_errors:
        ib.emit_reject(command, "input", structure_errors,
                       exit_code=ib.EXIT_INPUT, integrity=integrity)

    index_errors = []
    for i, item in enumerate(items):
        index = item.get("index")
        if not isinstance(index, int) or isinstance(index, bool) \
                or index < 0 or index >= len(cells):
            index_errors.append(ib.err("[%d].index" % i, ib.CODE_INDEX_OUT_OF_RANGE,
                                       "第 %d 项的 index 不是 0..%d 之间的整数"
                                       % (i, len(cells) - 1)))
    if index_errors:
        ib.emit_reject(command, "addressing", index_errors, integrity=integrity)

    prefix_errors = []
    for i, item in enumerate(items):
        field = "[%d].expect" % i
        cell = cells[item["index"]]
        expect = item.get("expect")
        if expect is None:
            prefix_errors.append(ib.err(field, ib.CODE_MISSING, "第 %d 项缺 expect" % i))
            continue
        if not isinstance(expect, str):
            prefix_errors.append(ib.err(field, ib.CODE_WRONG_TYPE, "第 %d 项的 expect 不是字符串" % i))
            continue
        stripped = expect.strip()
        if len(stripped) < 6:
            prefix_errors.append(ib.err(field, ib.CODE_TOO_SHORT,
                                        "第 %d 项的 expect 至少 6 字，用于防下标错位" % i))
            continue
        idea = cell.get("idea")
        idea_text = idea.strip() if isinstance(idea, str) else ""
        if not idea_text.startswith(stripped):
            problem = ib.err(field, ib.CODE_PREFIX_MISMATCH,
                             "第 %d 项的 expect 和 cells[%d] 对不上，下标可能错位"
                             % (i, item["index"]))
            problem["actual_prefix"] = idea_text[:IDEA_PREFIX_LEN]
            prefix_errors.append(problem)
    if prefix_errors:
        ib.emit_reject(command, "addressing", prefix_errors, integrity=integrity)

    seen = {}
    duplicate_errors = []
    for i, item in enumerate(items):
        index = item["index"]
        if index in seen:
            duplicate_errors.append(ib.err("[%d].index" % i, ib.CODE_NOT_ALLOWED,
                                           "index %d 在本批里重复出现（第 %d 项和第 %d 项）"
                                           % (index, seen[index], i)))
        else:
            seen[index] = i
    if duplicate_errors:
        ib.emit_reject(command, "addressing", duplicate_errors, integrity=integrity)

    verdict_errors = []
    for i, item in enumerate(items):
        verdict_errors.extend(validate_verdict_fields(item, field_prefix="[%d]." % i))
    if verdict_errors:
        ib.emit_reject(command, "verdict", verdict_errors, integrity=integrity)

    if not allow_overwrite:
        overwrite_errors = []
        for i, item in enumerate(items):
            cell = cells[item["index"]]
            if not ib.is_undecided(cell):
                overwrite_errors.append(
                    ib.err("[%d].user_verdict" % i, ib.CODE_ALREADY_DECIDED,
                           "cells[%d] 已经有裁决「%s」，不覆盖。真要改加 --allow-overwrite"
                           % (item["index"], cell.get("user_verdict"))))
        if overwrite_errors:
            ib.emit_reject(command, "verdict", overwrite_errors, integrity=integrity)


def cmd_verdict(args):
    command = "verdict"
    today = ib.resolve_today(args.today, command, args.sandboxed)
    lock = acquire_write_lock(args.map, command)     # 持到进程退出，见 acquire_write_lock
    data, raw = load_map(args.map, command)
    loaded_sha = disk_sha(args.map)
    integrity = integrity_of(data, raw)
    items = ib.read_stdin_json(command, "array")
    if not items:
        ib.emit_reject(command, "input",
                       [ib.err("-", ib.CODE_EMPTY, "裁决数组是空的")],
                       exit_code=ib.EXIT_INPUT, integrity=integrity)

    cells = data["cells"]
    undecided_before = len(undecided_items_of(cells))
    validate_verdict_batch(items, cells, args.allow_overwrite, command, integrity)

    by_verdict = {}
    for item in items:
        cell = cells[item["index"]]
        verdict = item["user_verdict"]
        # 老格子只允许动这四个键，其余字段（含 intervention_2026-09-12 这种非常规键）原样留着。
        cell["user_verdict"] = verdict
        cell["verdict_date"] = today
        if verdict == "归档":
            cell["restart_condition"] = item["restart_condition"]
            cell["archived"] = True
        elif "archived" in cell:
            cell["archived"] = False
        by_verdict[verdict] = by_verdict.get(verdict, 0) + 1

    before_count = len(cells)
    backup_path = safe_write(args.map, args.backup_dir, data, before_count,
                             previous_writes_of(data), command, loaded_sha)
    lock.close()

    ib.emit_ok(command, updated=len(items), by_verdict=by_verdict,
               undecided_before=undecided_before,
               undecided_after=len(undecided_items_of(cells)),
               backup=backup_path, cells_before=before_count, cells_after=len(cells),
               integrity=integrity)


# ================================================================ 入口


def main():
    parser = ib.make_parser(argparse, KNOWN_COMMANDS, "idea-bomb 迁移地图的唯一写入通道")
    sub = parser.add_subparsers(dest="command")
    for name in KNOWN_COMMANDS:
        child = sub.add_parser(name)
        child.add_argument("--map", default=DEFAULT_MAP)
        child.add_argument("--backup-dir", default=None)
        child.add_argument("--today", default=None)
        if name == "commit":
            child.add_argument("--seed-id", default=None)
            child.add_argument("--session-dir", default=DEFAULT_SESSION_DIR)
        if name == "verdict":
            child.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()
    if not args.command:
        ib.emit({"ok": False, "command": "-", "gate": "input",
                 "errors": [ib.err("-", ib.CODE_BAD_JSON,
                                   "缺子命令：status / gate / commit / verdict")]},
                ib.EXIT_INPUT)

    args.map = os.path.realpath(os.path.expanduser(args.map))
    # --today 只在数据路径被指到默认位置之外时生效，见 ib_common.resolve_today
    args.sandboxed = ib.path_is_overridden(args.map, DEFAULT_MAP)
    if args.backup_dir is None:
        args.backup_dir = os.path.join(os.path.dirname(os.path.abspath(args.map)), "backups")
    else:
        args.backup_dir = os.path.expanduser(args.backup_dir)
    if getattr(args, "session_dir", None):
        args.session_dir = os.path.expanduser(args.session_dir)

    {"status": cmd_status, "gate": cmd_gate,
     "commit": cmd_commit, "verdict": cmd_verdict}[args.command](args)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # 兜底：正常路径不该走到这
        ib.emit({"ok": False, "command": ib.guess_command(KNOWN_COMMANDS), "gate": "storage",
                 "errors": [ib.err("-", "UNEXPECTED", "未预期异常：%s" % exc)]},
                ib.EXIT_UNEXPECTED)
