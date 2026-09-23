# -*- coding: utf-8 -*-
"""写入安全：备份、原子写、条目守恒、失败回退、_integrity
（INTERFACE 4.1、4.2、4.3、5.7、3.0）。"""
import json
import os
import stat

import pytest

from conftest import (BACKUP_NAME_RE, TODAY, good_cell, legacy_cell, read_json,
                      sha256_of, tmp_leftovers, write_json, zh)

IDEA_A = "让厌氧工程菌从被动乏氧富集升级为主动探测肿瘤代谢梯度的导航系统"
IDEA_B = "把蛋白酶从降解ECM的工具改造成瘤内压力传感器的读出元件"
RC = "若能论证 VE-cadherin 连接可逆自恢复，且给出微出血定量数据"


def _v_item(idea, index=0, verdict="采纳"):
    return {"index": index, "expect": idea[:10], "user_verdict": verdict}


def _backups(backup_dir):
    if not os.path.exists(str(backup_dir)):
        return []
    return sorted(os.listdir(str(backup_dir)))


# ================================================= 地图文件异常（3.0）

def test_map文件不存在_退出码4_不创建空地图(run_map, tmp_path):
    """--map 指向不存在的文件：退出码 4，gate=storage，IO_FAILED，且不得创建该文件。"""
    missing = tmp_path / "nope" / "migration_map.json"
    r = run_map(["status", "--map", missing])
    r.assert_rejected("status", 4, gate="storage")
    assert "IO_FAILED" in [e["code"] for e in r.json["errors"]]
    assert not missing.exists(), "不得凭空创建空地图"


@pytest.mark.parametrize("cmd", ["status", "gate"])
def test_map文件损坏_只读命令也退出码4(run_map, tmp_path, cmd):
    """损坏的 map：只读命令同样退出码 4、BAD_JSON，文件内容原样保留。"""
    p = tmp_path / "migration_map.json"
    p.write_text("{ broken", encoding="utf-8")
    r = run_map([cmd, "--map", p])
    r.assert_rejected(cmd, 4, gate="storage")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]
    assert p.read_text(encoding="utf-8") == "{ broken", "损坏文件不得被重建或覆盖"


def test_map文件损坏_verdict退出码4且不覆盖(run_map, tmp_path, backup_dir):
    """5.7：map 内容是 '{ broken' 时 verdict 退出码 4，文件未被重建。"""
    p = tmp_path / "migration_map.json"
    p.write_text("{ broken", encoding="utf-8")
    r = run_map(["verdict", "--map", p, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=[_v_item(IDEA_A)])
    r.assert_rejected("verdict", 4, gate="storage")
    assert p.read_text(encoding="utf-8") == "{ broken"
    assert tmp_leftovers(p) == []


def test_map文件损坏_commit退出码4(run_map, run_seed, tmp_path, session_dir, backup_dir):
    """损坏 map 时 commit 退出码 4，且不得写入。"""
    run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
             stdin_obj=[{"text": "把宿主节律当成工程菌治疗的隐藏变量"}]).assert_ok("register")
    p = tmp_path / "migration_map.json"
    p.write_text("not json at all", encoding="utf-8")
    r = run_map(["commit", "--seed-id", "S1", "--map", p, "--session-dir", session_dir,
                 "--backup-dir", backup_dir, "--today", TODAY], stdin_obj=good_cell())
    r.assert_rejected("commit", 4, gate="storage")
    assert p.read_text(encoding="utf-8") == "not json at all"


def test_map是空文件_退出码4_BAD_JSON(run_map, tmp_path):
    """边界：0 字节的 map 文件不是合法 JSON，退出码 4。"""
    p = tmp_path / "migration_map.json"
    p.write_text("", encoding="utf-8")
    r = run_map(["status", "--map", p])
    r.assert_rejected("status", 4, gate="storage")


def test_不得回退到默认路径(run_map, tmp_path):
    """0.2 硬性要求：传了 --map 就绝不能回退默认路径 ~/.idea-bomb/migration_map.json。
    指向不存在的临时路径时必须报 4，而不是读到真实地图后返回成功。"""
    missing = tmp_path / "definitely_not_there.json"
    r = run_map(["status", "--map", missing])
    assert r.code == 4, "传入的 --map 不存在却返回 %s，疑似回退到了默认路径" % r.code


# ================================================= 备份

def test_commit_产生备份且命名合规(run_map, mapfile, seeded, session_dir, backup_dir):
    """commit 成功后 backup-dir 里有 1 个 migration_map.YYYYMMDD-HHMMSS.json。"""
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    sid = seeded(1)[0]
    d = run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
                 "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=good_cell()).assert_ok("commit")
    names = _backups(backup_dir)
    assert len(names) == 1, names
    assert BACKUP_NAME_RE.match(names[0]), "备份文件名不合规：%s" % names[0]
    assert os.path.isabs(d["backup"]) and os.path.exists(d["backup"])
    assert os.path.basename(d["backup"]) == names[0]


def test_备份内容等于写入前的map(run_map, mapfile, seeded, session_dir, backup_dir):
    """备份必须是写入前的快照：与调用前的 map 逐字节相同。"""
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    before_bytes = open(str(m), "rb").read()
    sid = seeded(1)[0]
    d = run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
                 "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=good_cell()).assert_ok("commit")
    assert open(d["backup"], "rb").read() == before_bytes
    assert open(str(m), "rb").read() != before_bytes, "写入后 map 本身应该变了"


def test_backup_dir不存在时自动创建(run_map, mapfile, seeded, session_dir, backup_dir):
    """4.1 第 3 步：backup-dir 不存在则创建。"""
    assert not os.path.exists(str(backup_dir))
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    sid = seeded(1)[0]
    run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
             "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=good_cell()).assert_ok("commit")
    assert os.path.isdir(str(backup_dir))


def test_连续5次写入产生5个备份且不自动删除(run_map, mapfile, run_seed, session_dir,
                                            backup_dir):
    """4.2：脚本永不删除备份，连续 5 次写入后应有 5 个备份文件。"""
    cells = [legacy_cell(IDEA_A + "#%d" % i, "待定") for i in range(5)]
    m = mapfile(cells)
    for i in range(5):
        run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=[_v_item(IDEA_A + "#%d" % i, index=i, verdict="否决")]
                ).assert_ok("verdict")
    assert len(_backups(backup_dir)) == 5, _backups(backup_dir)


def test_verdict也产生备份(run_map, mapfile, backup_dir):
    """verdict 与 commit 走同一写入流程，同样产生备份。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    d = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=[_v_item(IDEA_A)]).assert_ok("verdict")
    assert os.path.exists(d["backup"])
    assert BACKUP_NAME_RE.match(os.path.basename(d["backup"]))


def test_业务性拒绝时不产生备份(run_map, mapfile, backup_dir):
    """备份只在进入写入流程前做：被闸门拦下（退出码 2）时不应产生备份。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    r = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=[{"index": 999, "expect": IDEA_A[:10], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    assert _backups(backup_dir) == [], "校验阶段被拒不应留下备份"


def test_备份目录只读_退出码4且map未改(run_map, mapfile, tmp_path):
    """5.7：backup-dir 指向只读目录 → 退出码 4，IO_FAILED，map 未改、无 tmp 残留。"""
    ro = tmp_path / "ro_backups"
    os.makedirs(str(ro))
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    before = sha256_of(m)
    os.chmod(str(ro), stat.S_IRUSR | stat.S_IXUSR)  # r-x------
    try:
        r = run_map(["verdict", "--map", m, "--backup-dir", ro, "--today", TODAY],
                    stdin_obj=[_v_item(IDEA_A)])
        r.assert_rejected("verdict", 4, gate="storage")
        assert "IO_FAILED" in [e["code"] for e in r.json["errors"]]
        assert sha256_of(m) == before, "备份失败时绝不能进入写入"
        assert tmp_leftovers(m) == []
    finally:
        os.chmod(str(ro), stat.S_IRWXU)


# ================================================= 条目守恒与只追加

def test_commit只追加_原有cell逐字段不变(run_map, mapfile, seeded, session_dir,
                                          backup_dir):
    """4.2 只追加：commit 后 cells[0..before-1] 与调用前逐字段相同，新 cell 在末尾。"""
    cells = [legacy_cell(IDEA_A + "#%d" % i, "采纳",
                         {"intervention_2026-09-12": "柚子口头否掉了一半"})
             for i in range(10)]
    m = mapfile(cells)
    before = read_json(m)["cells"]
    sid = seeded(1)[0]
    run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
             "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=good_cell()).assert_ok("commit")
    after = read_json(m)["cells"]
    assert len(after) == 11
    assert after[:10] == before, "既有 cell 不得被改写或重排"
    assert after[10]["schema"] == 2


def test_verdict条目数守恒(run_map, mapfile, backup_dir):
    """4.2 不搬家：verdict 后 len(cells) 不变。"""
    cells = [legacy_cell(IDEA_A + "#%d" % i, "待定") for i in range(20)]
    m = mapfile(cells)
    items = [{"index": i, "expect": (IDEA_A + "#%d" % i)[:10], "user_verdict": "归档",
              "restart_condition": RC} for i in range(20)]
    d = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=items).assert_ok("verdict")
    assert d["cells_before"] == d["cells_after"] == 20
    assert len(read_json(m)["cells"]) == 20


def test_rejected_or_downgraded被冻结(run_map, mapfile, backup_dir, seeded,
                                      session_dir):
    """3.4：rejected_or_downgraded 只读不写——归档大批量后该数组逐字节不变。"""
    rej = [{"idea": "旧的被否决想法 %d" % i, "reason": "打不过纯肽方案"} for i in range(4)]
    cells = [legacy_cell(IDEA_A + "#%d" % i, "待定") for i in range(6)]
    m = mapfile(cells, rejected=rej)
    items = [{"index": i, "expect": (IDEA_A + "#%d" % i)[:10], "user_verdict": "归档",
              "restart_condition": RC} for i in range(6)]
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=items).assert_ok("verdict")
    assert read_json(m)["rejected_or_downgraded"] == rej


def test_写入后文件仍是合法JSON且中文不转义(run_map, mapfile, seeded, session_dir,
                                            backup_dir):
    """0.3 约定 ensure_ascii=False：落盘的中文不应被转成 \\uXXXX。"""
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    sid = seeded(1)[0]
    run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
             "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=good_cell()).assert_ok("commit")
    raw = open(str(m), encoding="utf-8").read()
    json.loads(raw)
    assert "把宿主免疫的昼夜相位" in raw, "中文应以 UTF-8 原样落盘"


def test_任何失败路径都不留tmp残留(run_map, mapfile, backup_dir, run_seed,
                                   session_dir, tmp_path):
    """4.2：多条失败路径跑完后，<map>.tmp-* 都不得残留。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[{"index": 99, "expect": IDEA_A[:10], "user_verdict": "采纳"}])
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_raw="not json")
    run_map(["commit", "--seed-id", "S404", "--map", m, "--session-dir", session_dir,
             "--backup-dir", backup_dir, "--today", TODAY], stdin_obj=good_cell())
    run_map(["commit", "--seed-id", "S1", "--map", m, "--session-dir", session_dir,
             "--backup-dir", backup_dir, "--today", TODAY], stdin_obj={})
    assert tmp_leftovers(m) == []


def test_成功路径也不留tmp残留(run_map, mapfile, backup_dir):
    """os.replace 后临时文件应当消失。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[_v_item(IDEA_A)]).assert_ok("verdict")
    assert tmp_leftovers(m) == []


# ================================================= _integrity

def test_integrity_bootstrap_无该键时不报警(run_map, mapfile):
    """4.3：首次遇到没有 _integrity 的地图 → checked=false，不报警，退出码 0。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    assert "_integrity" not in read_json(m)
    d = run_map(["status", "--map", m]).assert_ok("status")
    assert d["integrity"]["checked"] is False
    assert d["integrity"].get("external_edit_suspected") in (False, None)


def test_integrity_首次写入时建立该字段(run_map, mapfile, backup_dir):
    """bootstrap 写入：第一次 verdict 之后地图里应出现 _integrity 及其四个键。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[_v_item(IDEA_A)]).assert_ok("verdict")
    integ = read_json(m)["_integrity"]
    assert set(["writes", "last_write", "last_cells_count", "last_sha256"]).issubset(
        integ.keys()), integ
    assert integ["writes"] >= 1
    assert integ["last_cells_count"] == 1


def test_integrity_writes随每次写入递增(run_map, mapfile, backup_dir):
    """writes 计数：连续 3 次 verdict 后应递增 3。"""
    cells = [legacy_cell(IDEA_A + "#%d" % i, "待定") for i in range(3)]
    m = mapfile(cells)
    seen = []
    for i in range(3):
        run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=[_v_item(IDEA_A + "#%d" % i, index=i, verdict="否决")]
                ).assert_ok("verdict")
        seen.append(read_json(m)["_integrity"]["writes"])
    assert seen == [seen[0], seen[0] + 1, seen[0] + 2], seen


def test_integrity_last_cells_count跟随commit更新(run_map, mapfile, seeded,
                                                  session_dir, backup_dir):
    """commit 后 last_cells_count 等于写入后的 cells 长度。"""
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    sid = seeded(1)[0]
    run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
             "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=good_cell()).assert_ok("commit")
    assert read_json(m)["_integrity"]["last_cells_count"] == 2


def test_integrity_脚本自身写入后不被误判为外部编辑(run_map, mapfile, backup_dir):
    """关键：脚本写完后紧接着跑 status，不得报 external_edit_suspected=true。"""
    cells = [legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定")]
    m = mapfile(cells)
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[_v_item(IDEA_A)]).assert_ok("verdict")
    d = run_map(["status", "--map", m]).assert_ok("status")
    assert d["integrity"]["checked"] is True
    assert d["integrity"]["external_edit_suspected"] is False, \
        "刚由脚本写入的地图不得被判为外部编辑"


def test_integrity_外部编辑后被检出且不阻断(run_map, mapfile, backup_dir):
    """5.7：绕过脚本直接改 JSON 后，status 报 external_edit_suspected=true，退出码仍 0。"""
    cells = [legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定")]
    m = mapfile(cells)
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[_v_item(IDEA_A)]).assert_ok("verdict")
    doc = read_json(m)
    doc["cells"][1]["user_verdict"] = "采纳"  # 手动改，绕过脚本
    write_json(m, doc)
    d = run_map(["status", "--map", m]).assert_ok("status")
    assert d["integrity"]["external_edit_suspected"] is True


def test_integrity_外部编辑不阻断后续写入(run_map, mapfile, backup_dir):
    """事后发现不是事前阻止：外部编辑过的地图仍能正常 verdict（退出码 0）。"""
    cells = [legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定")]
    m = mapfile(cells)
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[_v_item(IDEA_A)]).assert_ok("verdict")
    doc = read_json(m)
    doc["note"] = "我手动加了一句话"
    write_json(m, doc)
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[_v_item(IDEA_B, index=1, verdict="否决")]).assert_ok("verdict")
    assert read_json(m)["cells"][1]["user_verdict"] == "否决"


def test_integrity_gate命令也报告完整性(run_map, mapfile, backup_dir):
    """3.0 第 2 步：所有子命令（含 gate）都要把 integrity 写进响应体。"""
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    d = run_map(["gate", "--map", m]).assert_ok("gate")
    assert "integrity" in d and "checked" in d["integrity"], d


def test_integrity_不影响退出码(run_map, mapfile, backup_dir):
    """完整性检查不影响退出码：外部编辑后的地图 gate 仍按积压情况判定为 0。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[_v_item(IDEA_A)]).assert_ok("verdict")
    doc = read_json(m)
    doc["cells"].append(legacy_cell(IDEA_B, "否决"))
    write_json(m, doc)
    d = run_map(["gate", "--map", m]).assert_ok("gate")
    assert d["undecided"] == 0
