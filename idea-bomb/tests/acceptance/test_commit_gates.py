# -*- coding: utf-8 -*-
"""ib_map.py commit：种子引用闸、假说数量闸、裁决终态闸、受控字段覆写
（INTERFACE 3.3 第 1-5/7/8 步、1.6、5.1、5.4）。"""
import json

import pytest

from conftest import (TODAY, YESTERDAY, good_cell, legacy_cell, read_json,
                      sha256_of, zh)

IDEA_OLD = "让厌氧工程菌从被动乏氧富集升级为主动探测肿瘤代谢梯度的导航系统"


@pytest.fixture
def env(run_map, run_seed, mapfile, session_dir, backup_dir):
    """一个完整的 commit 运行环境：地图 + 会话目录 + 备份目录。"""
    class Env(object):
        def __init__(self):
            self.map = mapfile([legacy_cell(IDEA_OLD, "采纳")])
            self.session_dir = session_dir
            self.backup_dir = backup_dir

        def register(self, n=1, today=TODAY):
            items = [{"text": "种子%d：把宿主节律当成工程菌治疗的隐藏变量" % i}
                     for i in range(n)]
            r = run_seed(["register", "--session-dir", session_dir, "--today", today],
                         stdin_obj=items)
            return [s["seed_id"] for s in r.assert_ok("register")["registered"]]

        def commit(self, cell, seed_id, today=TODAY, stdin_raw=None, extra=()):
            args = ["commit", "--map", self.map, "--session-dir", session_dir,
                    "--backup-dir", backup_dir, "--today", today] + list(extra)
            if seed_id is not None:
                args += ["--seed-id", seed_id]
            return run_map(args, stdin_obj=cell, stdin_raw=stdin_raw)

        def sha(self):
            return sha256_of(self.map)

        def doc(self):
            return read_json(self.map)

    return Env()


# ================================================= 输入格式（第 1-2 步）

def test_commit_stdin非法JSON_退出码3(env):
    """stdin 不是合法 JSON：退出码 3，gate=input，BAD_JSON，地图未改。"""
    sid = env.register()[0]
    before = env.sha()
    r = env.commit(None, sid, stdin_raw="{ 不是 json")
    r.assert_rejected("commit", 3, gate="input")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]
    assert env.sha() == before


def test_commit_stdin是数组不是对象_退出码3(env):
    """stdin 是数组：commit 只收单个对象，退出码 3，BAD_JSON。"""
    sid = env.register()[0]
    r = env.commit([good_cell()], sid)
    r.assert_rejected("commit", 3, gate="input")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]


def test_commit_stdin是字符串字面量_退出码3(env):
    """stdin 是 JSON 字符串而非对象：退出码 3，BAD_JSON。"""
    sid = env.register()[0]
    r = env.commit(None, sid, stdin_raw='"just a string"')
    r.assert_rejected("commit", 3, gate="input")


def test_commit_缺seed_id参数_退出码3(env):
    """缺 --seed-id：退出码 3，gate=input，code=MISSING，field='--seed-id'。"""
    env.register()
    before = env.sha()
    r = env.commit(good_cell(), None)
    r.assert_rejected("commit", 3, gate="input")
    r.assert_error("--seed-id", "MISSING")
    assert env.sha() == before


# ================================================= 种子引用闸（第 3-4 步）

def test_commit_seed_id不存在_UNKNOWN_SEED(env):
    """引用当天不存在的 seed_id：退出码 2，gate=seed_link，UNKNOWN_SEED。"""
    env.register(2)  # 只有 S1/S2
    before = env.sha()
    r = env.commit(good_cell(), "S9")
    r.assert_rejected("commit", 2, gate="seed_link")
    assert "UNKNOWN_SEED" in [e["code"] for e in r.json["errors"]]
    assert env.sha() == before


def test_commit_会话文件不存在_UNKNOWN_SEED(env):
    """当天根本没登记过任何种子（会话文件不存在）：UNKNOWN_SEED，退出码 2。"""
    r = env.commit(good_cell(), "S1")
    r.assert_rejected("commit", 2, gate="seed_link")
    assert "UNKNOWN_SEED" in [e["code"] for e in r.json["errors"]]


def test_commit_引用昨天的种子_UNKNOWN_SEED(env):
    """种子按天隔离：昨天登记的 S1 不能在今天被展开。"""
    env.register(3, today=YESTERDAY)
    r = env.commit(good_cell(), "S1", today=TODAY)
    r.assert_rejected("commit", 2, gate="seed_link")
    assert "UNKNOWN_SEED" in [e["code"] for e in r.json["errors"]]


def test_commit_同一seed_id第二次使用_SEED_ALREADY_USED(env):
    """同一种子当天只能展开一次：第二次 commit 报 SEED_ALREADY_USED，退出码 2。"""
    sids = env.register(3)
    env.commit(good_cell(), sids[0]).assert_ok("commit")
    before = env.sha()
    r = env.commit(good_cell(idea=zh(40)), sids[0])
    r.assert_rejected("commit", 2, gate="seed_link")
    assert "SEED_ALREADY_USED" in [e["code"] for e in r.json["errors"]]
    assert env.sha() == before, "重复种子被拒时地图不得改动"


def test_commit_不同seed_id可各展开一次(env):
    """反例防误杀：S1 用过后 S2 仍然可用。"""
    sids = env.register(3)
    env.commit(good_cell(), sids[0]).assert_ok("commit")
    d = env.commit(good_cell(idea=zh(40)), sids[1]).assert_ok("commit")
    assert d["seed_id"] == sids[1]
    assert d["today_count"] == 2


def test_commit_昨天用过的seed_id今天同名可用(env):
    """跨天隔离：昨天的 S1 已展开，今天重新登记的 S1 仍可用（date 不同不算复用）。"""
    env.register(1, today=YESTERDAY)
    env.commit(good_cell(), "S1", today=YESTERDAY).assert_ok("commit")
    env.register(1, today=TODAY)
    d = env.commit(good_cell(idea=zh(40)), "S1", today=TODAY).assert_ok("commit")
    assert d["today_count"] == 1, "新的一天日计数应重新开始"


def test_commit_校验顺序_种子闸先于必填闸(env):
    """未知种子 + 字段全缺：应先被 seed_link 拦下（第 3 步在第 6 步之前）。"""
    env.register(1)
    r = env.commit({}, "S99")
    r.assert_rejected("commit", 2, gate="seed_link")


# ================================================= 假说数量闸（第 5 步）

def test_commit_当天第三个_放行(env):
    """边界：当天已有 2 个 schema2 cell，第 3 个仍放行，today_count=3。"""
    sids = env.register(5)
    for i in range(2):
        env.commit(good_cell(idea=zh(31 + i)), sids[i]).assert_ok("commit")
    d = env.commit(good_cell(idea=zh(40)), sids[2]).assert_ok("commit")
    assert d["today_count"] == 3


def test_commit_老schema1格子不计入日上限(env, run_map, mapfile, session_dir, backup_dir):
    """5.1 关键行：地图里 47 个 date=2026-09-15 的 schema1 cell 不占今天的 3 个名额。"""
    cells = [legacy_cell(IDEA_OLD + str(i), "采纳", {"date": "2026-09-15"})
             for i in range(47)]
    env.map = mapfile(cells, name="map_with_47.json")
    sid = env.register(1)[0]
    d = env.commit(good_cell(), sid).assert_ok("commit")
    assert d["today_count"] == 1, "老格子不是 schema2，不计入日上限"
    assert d["cells_before"] == 47 and d["cells_after"] == 48


def test_commit_同日期的schema1也不计入(env, mapfile):
    """即使老格子 date 就是今天，只要不是 schema2 就不计入日上限。"""
    cells = [legacy_cell(IDEA_OLD + str(i), "采纳", {"date": TODAY}) for i in range(5)]
    env.map = mapfile(cells, name="map_today_legacy.json")
    sid = env.register(1)[0]
    d = env.commit(good_cell(), sid).assert_ok("commit")
    assert d["today_count"] == 1


def test_commit_昨天的schema2不计入今天(env, mapfile):
    """日上限按日历日计：昨天写的 3 个 schema2 不影响今天。"""
    old2 = [dict(good_cell(), schema=2, date=YESTERDAY, seed_id="S%d" % (i + 1))
            for i in range(3)]
    env.map = mapfile(old2, name="map_yesterday2.json")
    sid = env.register(1)[0]
    d = env.commit(good_cell(), sid).assert_ok("commit")
    assert d["today_count"] == 1


# ================================================= 裁决终态闸（第 6 步）

@pytest.mark.parametrize("v", ["采纳", "否决"])
def test_commit_终态采纳否决_放行(env, v):
    """采纳/否决无需 restart_condition，放行。"""
    sid = env.register(1)[0]
    d = env.commit(good_cell(user_verdict=v), sid).assert_ok("commit")
    assert d["user_verdict"] == v


def test_commit_归档加重启条件长10_放行(env):
    """边界含等号：归档 + restart_condition 恰好 10 字，放行。"""
    sid = env.register(1)[0]
    d = env.commit(good_cell(user_verdict="归档", restart_condition=zh(10)),
                   sid).assert_ok("commit")
    assert d["user_verdict"] == "归档"


def test_commit_归档缺重启条件_拒绝(env):
    """归档缺 restart_condition：退出码 2，field=restart_condition，code=MISSING。"""
    sid = env.register(1)[0]
    before = env.sha()
    r = env.commit(good_cell(user_verdict="归档"), sid)
    r.assert_rejected("commit", 2)
    r.assert_error("restart_condition", "MISSING")
    assert env.sha() == before


def test_commit_归档重启条件长9_TOO_SHORT(env):
    """边界：restart_condition 恰好 9 字，低于下限 10，拒绝。"""
    sid = env.register(1)[0]
    r = env.commit(good_cell(user_verdict="归档", restart_condition=zh(9)), sid)
    r.assert_rejected("commit", 2)
    r.assert_error("restart_condition", "TOO_SHORT")


@pytest.mark.parametrize("rc,code", [("待定", "PLACEHOLDER"), ("", "EMPTY"),
                                     ("   ", "EMPTY"),
                                     ("待确认：等柚子看完再说这个重启条件", "PLACEHOLDER")])
def test_commit_归档重启条件占位或空_拒绝(env, rc, code):
    """归档的 restart_condition 为占位/空：拒绝并报对应 code。"""
    sid = env.register(1)[0]
    r = env.commit(good_cell(user_verdict="归档", restart_condition=rc), sid)
    r.assert_rejected("commit", 2)
    r.assert_error("restart_condition", code)


def test_commit_采纳时多余的重启条件不导致拒绝(env):
    """反例防误杀：采纳时即便带了 restart_condition，也不应因此被拒。"""
    sid = env.register(1)[0]
    env.commit(good_cell(user_verdict="采纳", restart_condition=zh(20)),
               sid).assert_ok("commit")


def test_commit_采纳时重启条件为占位_不拒绝(env):
    """反例防误杀：非归档时 restart_condition 可缺省，写成占位也不该触发校验。"""
    sid = env.register(1)[0]
    env.commit(good_cell(user_verdict="否决", restart_condition="—"), sid).assert_ok("commit")


@pytest.mark.parametrize("v", ["待定", "待柚子确认", "pending", "PENDING", "搁置",
                               "", "   ", "采纳：作为 2027 青基主线", "采纳 ",
                               "归档（等测序）", "否决。", "Adopt", "不建议作主课题",
                               "已否决（2026-09-15）：打不过纯肽方案"])
def test_commit_user_verdict非三终态_NOT_ALLOWED(env, v):
    """精确相等，不做前缀匹配：任何非三终态取值一律 NOT_ALLOWED，退出码 2。"""
    sid = env.register(1)[0]
    before = env.sha()
    r = env.commit(good_cell(user_verdict=v), sid)
    r.assert_rejected("commit", 2, gate="verdict")
    r.assert_error("user_verdict", "NOT_ALLOWED")
    assert env.sha() == before


def test_commit_缺user_verdict_MISSING(env):
    """缺 user_verdict 键：拒绝，code=MISSING。"""
    sid = env.register(1)[0]
    r = env.commit(good_cell(user_verdict=None), sid)
    r.assert_rejected("commit", 2)
    r.assert_error("user_verdict", "MISSING")


def test_commit_不做零积压检查(env, mapfile):
    """3.3 末行：commit 不做零积压检查——地图里有 87 个未裁决也照样能写入。"""
    cells = [legacy_cell(IDEA_OLD + str(i), "待定") for i in range(87)]
    env.map = mapfile(cells, name="map_backlog.json")
    sid = env.register(1)[0]
    d = env.commit(good_cell(), sid).assert_ok("commit")
    assert d["cells_after"] == 88
    assert d.get("gate") is None


# ================================================= 受控字段覆写（1.6）

def test_commit_schema被强制写为2(env):
    """写入后该 cell 的 schema 必须是整数 2，即使 stdin 传了别的值。"""
    sid = env.register(1)[0]
    env.commit(good_cell(schema=1), sid).assert_ok("commit")
    cell = env.doc()["cells"][-1]
    assert cell["schema"] == 2 and isinstance(cell["schema"], int)


def test_commit_date被覆写为当天(env):
    """1.6 可断言行为：stdin 传 date=1999-01-01，落盘必须是当天日期。"""
    sid = env.register(1)[0]
    env.commit(good_cell(date="1999-01-01"), sid).assert_ok("commit")
    assert env.doc()["cells"][-1]["date"] == TODAY


def test_commit_seed_id取参数而非stdin(env):
    """seed_id 由 --seed-id 决定，stdin 里的同名字段被忽略。"""
    sids = env.register(3)
    env.commit(good_cell(seed_id="S999"), sids[1]).assert_ok("commit")
    assert env.doc()["cells"][-1]["seed_id"] == sids[1]


def test_commit_committed_at被写入(env):
    """committed_at 由脚本写入，为 ISO 8601 带时区的字符串。"""
    sid = env.register(1)[0]
    env.commit(good_cell(committed_at="不是时间"), sid).assert_ok("commit")
    ts = env.doc()["cells"][-1]["committed_at"]
    assert isinstance(ts, str) and ts.startswith(TODAY) and len(ts) >= 19, ts
    assert ("+" in ts[10:]) or ts.endswith("Z") or ("-" in ts[11:]), "须带时区：%s" % ts


def test_commit_归档时archived为true(env):
    """user_verdict=归档 → archived 写为 true。"""
    sid = env.register(1)[0]
    env.commit(good_cell(user_verdict="归档", restart_condition=zh(20)),
               sid).assert_ok("commit")
    assert env.doc()["cells"][-1]["archived"] is True


@pytest.mark.parametrize("v", ["采纳", "否决"])
def test_commit_非归档时不写archived键(env, v):
    """1.6：非归档时"不写这个键"——写入后的 cell 不应含 archived。"""
    sid = env.register(1)[0]
    env.commit(good_cell(user_verdict=v), sid).assert_ok("commit")
    assert "archived" not in env.doc()["cells"][-1], "非归档不得新增 archived 键"


def test_commit_非归档时stdin的archived也被清掉(env):
    """stdin 里带 archived=true 但裁决是采纳：脚本值优先，该键不得留下 true。"""
    sid = env.register(1)[0]
    env.commit(good_cell(user_verdict="采纳", archived=True), sid).assert_ok("commit")
    cell = env.doc()["cells"][-1]
    assert cell.get("archived") is not True, "archived 由脚本按裁决决定，不能沿用 stdin"


def test_commit_未受控的自定义字段被保留(env):
    """反例防误杀：1.6 之外的自定义字段（如 notes）应原样落盘，不被丢弃。"""
    sid = env.register(1)[0]
    env.commit(good_cell(notes="柚子口述，2026 青基备选", tags=["工程菌", "节律"]),
               sid).assert_ok("commit")
    cell = env.doc()["cells"][-1]
    assert cell["notes"] == "柚子口述，2026 青基备选"
    assert cell["tags"] == ["工程菌", "节律"]


def test_commit_成功响应index等于追加位置(env, mapfile):
    """成功响应的 index 等于新 cell 在 cells 里的下标（= cells_before）。"""
    cells = [legacy_cell(IDEA_OLD + str(i), "采纳") for i in range(103)]
    env.map = mapfile(cells, name="map103.json")
    sid = env.register(1)[0]
    d = env.commit(good_cell(), sid).assert_ok("commit")
    assert d["index"] == 103 and d["cells_before"] == 103 and d["cells_after"] == 104
    assert env.doc()["cells"][103]["schema"] == 2
