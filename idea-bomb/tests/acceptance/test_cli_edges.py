# -*- coding: utf-8 -*-
"""CLI 与参数边缘：空 stdin、路径参数生效性、expect 归一化
（依据 INTERFACE 0.2、0.4、3.0、3.3、3.4）。"""
import os

import pytest

from conftest import TODAY, good_cell, legacy_cell, read_json, sha256_of, zh

IDEA_A = "让厌氧工程菌从被动乏氧富集升级为主动探测肿瘤代谢梯度的导航系统"


# ================================================= 空 / 退化 stdin

def test_verdict空stdin_退出码3_BAD_JSON(run_map, mapfile, backup_dir):
    """管道无任何数据：空输入不是合法 JSON，退出码 3，gate=input，BAD_JSON。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    before = sha256_of(m)
    r = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_raw="")
    r.assert_rejected("verdict", 3, gate="input")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]
    assert sha256_of(m) == before


def test_commit空stdin_退出码3_BAD_JSON(run_map, mapfile, seeded, session_dir,
                                        backup_dir):
    """commit 收到空 stdin：退出码 3，BAD_JSON，地图未改。"""
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    before = sha256_of(m)
    sid = seeded(1)[0]
    r = run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
                 "--backup-dir", backup_dir, "--today", TODAY], stdin_raw="")
    r.assert_rejected("commit", 3, gate="input")
    assert sha256_of(m) == before


def test_register空stdin_退出码3_BAD_JSON(run_seed, session_dir):
    """register 收到空 stdin：退出码 3，gate=input，BAD_JSON。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_raw="")
    r.assert_rejected("register", 3, gate="input")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]


@pytest.mark.parametrize("raw", ["null", "123", "true", '"abc"'])
def test_verdict退化JSON值_退出码3(run_map, mapfile, backup_dir, raw):
    """stdin 是 null/数字/布尔/字符串等非数组 JSON：退出码 3，gate=input。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    r = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_raw=raw)
    r.assert_rejected("verdict", 3, gate="input")


@pytest.mark.parametrize("raw", ["null", "123", "true", "[]"])
def test_commit退化JSON值_退出码3(run_map, mapfile, seeded, session_dir,
                                  backup_dir, raw):
    """commit 的 stdin 必须是单个对象：null/数字/布尔/数组一律退出码 3。"""
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    sid = seeded(1)[0]
    r = run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
                 "--backup-dir", backup_dir, "--today", TODAY], stdin_raw=raw)
    r.assert_rejected("commit", 3, gate="input")


def test_register元素为null_退出码3(run_seed, session_dir):
    """数组里混入 null 元素：退出码 3，gate=input。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[{"text": zh(12)}, None])
    r.assert_rejected("register", 3, gate="input")


# ================================================= 路径参数生效性（0.2 硬性要求）

def test_map指向目录_退出码4(run_map, tmp_path):
    """--map 指向一个目录：退出码 4，gate=storage（读不了地图）。"""
    d = tmp_path / "a_dir"
    os.makedirs(str(d))
    r = run_map(["status", "--map", d])
    r.assert_rejected("status", 4, gate="storage")
    assert set([e["code"] for e in r.json["errors"]]) & set(["IO_FAILED", "BAD_JSON"])


def test_session_dir参数生效_只读写指定目录(run_seed, tmp_path):
    """--session-dir 必须真正生效：登记后只有该目录下出现会话文件。"""
    sd = tmp_path / "my_session"
    run_seed(["register", "--session-dir", sd, "--today", TODAY],
             stdin_obj=[{"text": "把宿主节律当成工程菌治疗的隐藏变量"}]).assert_ok("register")
    assert os.path.isdir(str(sd))
    assert os.listdir(str(sd)) == ["seeds-%s.json" % TODAY.replace("-", "")]


def test_backup_dir参数生效_备份只落在指定目录(run_map, mapfile, backup_dir,
                                               tmp_path):
    """--backup-dir 必须真正生效：备份不得落到 map 同级的默认 backups/ 里。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    custom = tmp_path / "custom_bk"
    run_map(["verdict", "--map", m, "--backup-dir", custom, "--today", TODAY],
            stdin_obj=[{"index": 0, "expect": IDEA_A[:10], "user_verdict": "采纳"}]
            ).assert_ok("verdict")
    assert len(os.listdir(str(custom))) == 1
    default_dir = tmp_path / "backups"
    assert not os.path.exists(str(default_dir)) or os.listdir(str(default_dir)) == [], \
        "传了 --backup-dir 就不得再往默认 backups/ 写"


def test_today参数生效_写入的date用注入值(run_map, mapfile, run_seed, session_dir,
                                          backup_dir):
    """--today 必须真正生效：注入 2026-01-05 时落盘 date 就是该值，不是系统日期。"""
    inject = "2026-01-05"
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    run_seed(["register", "--session-dir", session_dir, "--today", inject],
             stdin_obj=[{"text": "把宿主节律当成工程菌治疗的隐藏变量"}]).assert_ok("register")
    d = run_map(["commit", "--seed-id", "S1", "--map", m, "--session-dir", session_dir,
                 "--backup-dir", backup_dir, "--today", inject],
                stdin_obj=good_cell()).assert_ok("commit")
    assert d["date"] == inject
    assert read_json(m)["cells"][-1]["date"] == inject


def test_today参数生效_verdict_date用注入值(run_map, mapfile, backup_dir):
    """verdict 写入的 verdict_date 取 --today 注入值。"""
    inject = "2026-01-05"
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", inject],
            stdin_obj=[{"index": 0, "expect": IDEA_A[:10], "user_verdict": "采纳"}]
            ).assert_ok("verdict")
    assert read_json(m)["cells"][0]["verdict_date"] == inject


@pytest.mark.parametrize("bad", ["not-a-date", "2026/09/23", "20260923", "2026-13-45"])
def test_today格式非法_退出码3(run_seed, session_dir, bad):
    """--today 值格式不对属于"参数值类型不对"：退出码 3（0.4）。"""
    r = run_seed(["list", "--session-dir", session_dir, "--today", bad])
    assert r.code == 3, "非法日期应返回退出码 3，实际 %s；stdout=%s" % (r.code, r.out[:200])
    r.assert_rejected("list", 3)


# ================================================= expect 归一化

def test_expect带首尾空白_仍视为前缀(run_map, mapfile, backup_dir):
    """3.4："不做 strip 以外的归一化"——expect 带首尾空白应被 strip 后按前缀比对，放行。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[{"index": 0, "expect": "  " + IDEA_A[:10] + "  ",
                        "user_verdict": "采纳"}]).assert_ok("verdict")
    assert read_json(m)["cells"][0]["user_verdict"] == "采纳"


def test_expect非字符串_拒绝(run_map, mapfile, backup_dir):
    """expect 传数字：退出码 2，gate=addressing，地图未改。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    before = sha256_of(m)
    r = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=[{"index": 0, "expect": 12345678, "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    assert sha256_of(m) == before


def test_verdict元素不是对象_拒绝(run_map, mapfile, backup_dir):
    """数组元素是字符串而非对象：退出码 2 或 3，但必须被拒且地图未改。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    before = sha256_of(m)
    r = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=["index 0 采纳"])
    assert r.code in (2, 3), "应被拒，实际退出码 %s" % r.code
    assert r.json is not None and r.json["ok"] is False
    assert sha256_of(m) == before
