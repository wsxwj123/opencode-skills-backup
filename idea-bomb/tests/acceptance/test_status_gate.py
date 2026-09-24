# -*- coding: utf-8 -*-
"""ib_map.py status / gate：零积压闸与占位词黑名单判定（INTERFACE 3.1、3.2、5.5）。"""
import os

import pytest

from conftest import (NO_VERDICT, TODAY, good_cell, legacy_cell, read_json,
                      sha256_of, write_json, zh)

IDEA_A = "让厌氧工程菌从被动乏氧富集升级为主动探测肿瘤代谢梯度的导航系统"
IDEA_B = "把蛋白酶从降解ECM的工具改造成瘤内压力传感器的读出元件"
IDEA_C = "用菌分裂稀释当瘤内活菌计时器，把定植时长换算成可读的剂量曲线"


# ================================================= status 基本形

def test_status_退出码恒为0_即使全是未裁决(run_map, mapfile):
    """status 只报告不判定：87 格未裁决时退出码仍为 0。"""
    cells = [legacy_cell(IDEA_A + str(i), "待定") for i in range(87)]
    r = run_map(["status", "--map", mapfile(cells)])
    d = r.assert_ok("status")
    assert d["total"] == 87 and d["undecided"] == 87


def test_status_统计口径_总数与schema分类(run_map, mapfile, seeded, session_dir,
                                          backup_dir, tmp_path):
    """status 须正确区分 schema1/schema2：2 个老格子 + 1 个新写入 = total 3。"""
    m = mapfile([legacy_cell(IDEA_A, "采纳"), legacy_cell(IDEA_B, "否决")])
    sid = seeded(1)[0]
    run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
             "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=good_cell()).assert_ok("commit")
    d = run_map(["status", "--map", m, "--backup-dir", backup_dir]).assert_ok("status")
    assert d["total"] == 3
    assert d["schema1"] == 2
    assert d["schema2"] == 1
    assert d["undecided"] == 0


def test_status_空地图_各计数为0(run_map, mapfile):
    """边界：cells 为空数组时 total/schema1/schema2/undecided 全为 0。"""
    d = run_map(["status", "--map", mapfile([])]).assert_ok("status")
    assert d["total"] == 0 and d["schema1"] == 0 and d["schema2"] == 0
    assert d["undecided"] == 0 and d["decided"] == 0
    assert d["undecided_items"] == []


def test_status_idea_prefix取前12字符(run_map, mapfile):
    """idea_prefix 是 idea 的前 12 个 Unicode 码位。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, "待定")])]).assert_ok("status")
    item = d["undecided_items"][0]
    assert item["idea_prefix"] == IDEA_A[:12]
    assert len(item["idea_prefix"]) == 12


def test_status_idea短于12字符_全取(run_map, mapfile):
    """边界：idea 不足 12 字符时 idea_prefix 取全部，不补齐不报错。"""
    short = "短想法五字"
    d = run_map(["status", "--map", mapfile([legacy_cell(short, "待定")])]).assert_ok("status")
    assert d["undecided_items"][0]["idea_prefix"] == short


def test_status_undecided_items按index升序(run_map, mapfile):
    """undecided_items 必须按 index 升序排列。"""
    cells = [legacy_cell(IDEA_A, "采纳"), legacy_cell(IDEA_B, "待定"),
             legacy_cell(IDEA_C, "否决"), legacy_cell(IDEA_A + "x", "待补")]
    d = run_map(["status", "--map", mapfile(cells)]).assert_ok("status")
    idxs = [i["index"] for i in d["undecided_items"]]
    assert idxs == [1, 3]
    assert idxs == sorted(idxs)


def test_status_undecided_items字段齐全(run_map, mapfile):
    """每个 undecided_item 须含 index/idea_prefix/user_verdict/date。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, "待定")])]).assert_ok("status")
    it = d["undecided_items"][0]
    assert set(["index", "idea_prefix", "user_verdict", "date"]).issubset(it.keys()), it
    assert it["index"] == 0
    assert it["user_verdict"] == "待定"
    assert it["date"] == "2026-07-08"


def test_status_archived计数(run_map, mapfile):
    """archived 统计 archived==true 的 cell 数。"""
    cells = [legacy_cell(IDEA_A, "归档", {"archived": True}),
             legacy_cell(IDEA_B, "采纳", {"archived": False}),
             legacy_cell(IDEA_C, "否决")]
    d = run_map(["status", "--map", mapfile(cells)]).assert_ok("status")
    assert d["archived"] == 1
    assert d["decided"] == 3 and d["undecided"] == 0


def test_status_decided加undecided等于total(run_map, mapfile):
    """守恒：decided + undecided == total。"""
    cells = ([legacy_cell(IDEA_A + str(i), "待定") for i in range(7)] +
             [legacy_cell(IDEA_B + str(i), "采纳") for i in range(3)])
    d = run_map(["status", "--map", mapfile(cells)]).assert_ok("status")
    assert d["decided"] + d["undecided"] == d["total"] == 10
    assert d["undecided"] == 7


def test_status_backups统计_目录不存在时count为0(run_map, mapfile, backup_dir):
    """备份目录尚不存在时 backups.count 为 0，不得因此报错。"""
    d = run_map(["status", "--map", mapfile([]), "--backup-dir", backup_dir]).assert_ok("status")
    assert d["backups"]["count"] == 0
    assert d["backups"]["bytes"] == 0


def test_status_backups统计_有备份时计数正确(run_map, mapfile, backup_dir, tmp_path):
    """备份目录里有 2 个备份文件时 count=2，bytes 为其字节数之和。"""
    os.makedirs(str(backup_dir))
    a = backup_dir / "migration_map.20260922-101010.json"
    b = backup_dir / "migration_map.20260923-111111.json"
    a.write_text('{"a": 1}', encoding="utf-8")
    b.write_text('{"bb": 22}', encoding="utf-8")
    d = run_map(["status", "--map", mapfile([]), "--backup-dir", backup_dir]).assert_ok("status")
    assert d["backups"]["count"] == 2
    assert d["backups"]["bytes"] == os.path.getsize(str(a)) + os.path.getsize(str(b))
    assert os.path.abspath(d["backups"]["dir"]) == os.path.abspath(str(backup_dir))


def test_status_是只读_不改map不建备份(run_map, mapfile, backup_dir):
    """status 是只读命令：跑完 map sha256 不变，且不得产生备份文件。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    before = sha256_of(m)
    run_map(["status", "--map", m, "--backup-dir", backup_dir]).assert_ok("status")
    assert sha256_of(m) == before
    if os.path.exists(str(backup_dir)):
        assert os.listdir(str(backup_dir)) == []


# ================================================= 未裁决判定（黑名单）

@pytest.mark.parametrize("v", ["待定", "待确认", "待柚子确认", "待议", "待补", "待填",
                               "未定", "暂定", "搁置", "pending", "Pending", "PENDING",
                               "tbd", "TBD", "todo", "TODO",
                               "-", "—", "–", "?", "？", "无", "空", "暂无",
                               "N/A", "NA", "n/a", "null", "None",
                               "", "   ", "\t "])
def test_undecided_命中占位词表的裁决计为未裁决(run_map, mapfile, v):
    """0.7 占位词表每一项作为 user_verdict 都应计入 undecided。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, v)])]).assert_ok("status")
    assert d["undecided"] == 1, "user_verdict=%r 应计为未裁决" % v


@pytest.mark.parametrize("v", ["待定：拟作 2027 青基主线方案 A",
                               "待柚子确认：等他看完综述再定",
                               "暂定为元件方向，下周再议",
                               "pending review by 柚子",
                               "TODO: 补一次查新再说",
                               "搁置，等测序结果"])
def test_undecided_占位词开头加补充说明_仍计为未裁决(run_map, mapfile, v):
    """前缀匹配：占位词 + 补充说明这类真实写法必须计入 undecided。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, v)])]).assert_ok("status")
    assert d["undecided"] == 1, "user_verdict=%r 以占位词开头，应计为未裁决" % v


def test_undecided_缺user_verdict键_计为未裁决(run_map, mapfile):
    """cell 完全没有 user_verdict 键时计入 undecided。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, NO_VERDICT)])]).assert_ok("status")
    assert d["undecided"] == 1
    assert d["undecided_items"][0]["index"] == 0


def test_undecided_user_verdict为null_计为未裁决(run_map, mapfile):
    """user_verdict 为 null 视为占位，计入 undecided。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, None)])]).assert_ok("status")
    assert d["undecided"] == 1


@pytest.mark.parametrize("v", ["不建议作主课题",
                               "已否决（2026-09-15）：套索肽+活菌组合打不过纯肽方案，不做",
                               "建议立即纳入工作流",
                               "定位为元件，不作主课题",
                               "采纳", "否决", "归档",
                               "未检索到直接工作",
                               "未见先例",
                               "不做",
                               "降级为备选"])
def test_undecided_反例_真实裁决不得被误判为未裁决(run_map, mapfile, v):
    """反例防误杀：黑名单判定，非占位词的任何取值都算已裁决。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, v)])]).assert_ok("status")
    assert d["undecided"] == 0, "user_verdict=%r 不在占位词表内，不得判为未裁决" % v
    assert d["decided"] == 1


def test_undecided_大小写不敏感(run_map, mapfile):
    """占位判定大小写不敏感：'nOnE'/'Tbd'/'ToDo' 都应算占位。"""
    cells = [legacy_cell(IDEA_A, "nOnE"), legacy_cell(IDEA_B, "Tbd"),
             legacy_cell(IDEA_C, "ToDo")]
    d = run_map(["status", "--map", mapfile(cells)]).assert_ok("status")
    assert d["undecided"] == 3


def test_undecided_首尾空白先strip再判定(run_map, mapfile):
    """判定前先 strip：'  待定  ' 算占位，'  采纳  ' 算已裁决。"""
    cells = [legacy_cell(IDEA_A, "  待定  "), legacy_cell(IDEA_B, "  采纳  ")]
    d = run_map(["status", "--map", mapfile(cells)]).assert_ok("status")
    assert d["undecided"] == 1
    assert d["undecided_items"][0]["index"] == 0


# ================================================= gate

def test_gate_零积压_退出码0(run_map, mapfile):
    """所有 cell 都有终态裁决：gate 退出码 0，undecided=0。"""
    cells = [legacy_cell(IDEA_A, "采纳"), legacy_cell(IDEA_B, "否决"),
             legacy_cell(IDEA_C, "不建议作主课题")]
    d = run_map(["gate", "--map", mapfile(cells)]).assert_ok("gate")
    assert d["undecided"] == 0
    assert d["total"] == 3


def test_gate_空地图_放行(run_map, mapfile):
    """边界：cells 为空数组时 undecided=0，gate 退出码 0。"""
    d = run_map(["gate", "--map", mapfile([])]).assert_ok("gate")
    assert d["undecided"] == 0 and d["total"] == 0


def test_gate_有一个未裁决_退出码2(run_map, mapfile):
    """只要有 1 个未裁决就拦：退出码 2，gate=backlog，BACKLOG_NOT_EMPTY。"""
    cells = [legacy_cell(IDEA_A, "采纳"), legacy_cell(IDEA_B, "待定")]
    r = run_map(["gate", "--map", mapfile(cells)])
    d = r.assert_rejected("gate", 2, gate="backlog")
    r.assert_error("-", "BACKLOG_NOT_EMPTY")
    assert d["undecided"] == 1
    assert d["undecided_items"][0]["index"] == 1


def test_gate_87个未裁决_undecided为87(run_map, mapfile):
    """真实存量场景：87 格占位裁决 → 退出码 2，undecided=87。"""
    cells = ([legacy_cell(IDEA_A + str(i), "待定") for i in range(87)] +
             [legacy_cell(IDEA_B + str(i), "否决") for i in range(16)])
    r = run_map(["gate", "--map", mapfile(cells)])
    d = r.assert_rejected("gate", 2, gate="backlog")
    assert d["undecided"] == 87
    assert d["total"] == 103


def test_gate_未裁决超30条_截断为30并置truncated(run_map, mapfile):
    """undecided_items 最多返回 30 条，并置 undecided_truncated=true。"""
    cells = [legacy_cell(IDEA_A + str(i), "待定") for i in range(87)]
    r = run_map(["gate", "--map", mapfile(cells)])
    d = r.assert_rejected("gate", 2, gate="backlog")
    assert len(d["undecided_items"]) == 30
    assert d["undecided_truncated"] is True
    assert d["undecided"] == 87, "计数不受截断影响"


def test_gate_未裁决恰好30条_不截断(run_map, mapfile):
    """边界：恰好 30 条时全量返回，undecided_truncated=false。"""
    cells = [legacy_cell(IDEA_A + str(i), "待定") for i in range(30)]
    r = run_map(["gate", "--map", mapfile(cells)])
    d = r.assert_rejected("gate", 2, gate="backlog")
    assert len(d["undecided_items"]) == 30
    assert d["undecided_truncated"] is False


def test_gate_未裁决31条_截断(run_map, mapfile):
    """边界：31 条时返回 30 条且 truncated=true。"""
    cells = [legacy_cell(IDEA_A + str(i), "待定") for i in range(31)]
    r = run_map(["gate", "--map", mapfile(cells)])
    d = r.assert_rejected("gate", 2, gate="backlog")
    assert len(d["undecided_items"]) == 30
    assert d["undecided_truncated"] is True


def test_gate_不校验新必填字段_老格子补齐裁决即放行(run_map, mapfile):
    """关键约束：老格子缺 hypothesis/falsification/feasibility_layers，
    只要裁决齐全 gate 就必须放行（否则 103 格永远过不了闸）。"""
    cells = [legacy_cell(IDEA_A + str(i), "归档") for i in range(103)]
    for c in cells:
        assert "hypothesis" not in c and "falsification" not in c
    run_map(["gate", "--map", mapfile(cells)]).assert_ok("gate")


def test_gate_schema2缺字段但有裁决_也放行(run_map, mapfile):
    """gate 只看裁决：即使是 schema2 且字段残缺，有终态裁决就放行。"""
    broken2 = {"schema": 2, "idea": IDEA_A, "user_verdict": "采纳"}
    run_map(["gate", "--map", mapfile([broken2])]).assert_ok("gate")


def test_gate_是只读_不改map(run_map, mapfile):
    """gate 跑完 map 文件 sha256 不变。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    before = sha256_of(m)
    run_map(["gate", "--map", m])
    assert sha256_of(m) == before
