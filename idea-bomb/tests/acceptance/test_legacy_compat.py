# -*- coding: utf-8 -*-
"""老数据兼容：103 格 schema1 存量必须全绿（INTERFACE 1.2、5.5、5.6）。

这一组是改造的底线：老格子永久豁免新必填规则，只补裁决就能清空积压。
"""
import json

import pytest

from conftest import (NO_VERDICT, TODAY, good_cell, read_json, sha256_of, zh)

RC = "若能论证 VE-cadherin 连接可逆自恢复，且给出微出血定量数据"

# 贴近真实存量的裁决取值分布：16 个已裁决（含自由文本裁决），87 个占位
DECIDED_VALUES = [
    "不建议作主课题",
    "已否决（2026-09-15）：套索肽+活菌组合打不过纯肽方案，不做",
    "建议立即纳入工作流",
    "定位为元件，不作主课题",
    "采纳", "否决",
]
UNDECIDED_VALUES = [
    "待定", "待柚子确认", "待定：拟作 2027 青基主线方案 A", "搁置", "—", "?", "暂无",
    "TBD", "pending", NO_VERDICT,
]


# 构造约定：下标 0..15 为已裁决（自由文本终态），16..102 为占位裁决
DECIDED_INDICES = list(range(0, 16))
UNDECIDED_INDICES = list(range(16, 103))


def _legacy103():
    """构造 103 个 schema1 老格子：87 未裁决 + 16 已裁决，字段形态贴近真实数据。"""
    cells = []
    for i in range(103):
        idea = "让厌氧工程菌从被动乏氧富集升级为主动探测肿瘤代谢梯度的导航系统 #%03d" % i
        cell = {
            "idea": idea,
            "novelty": ["中-高", "中高", "高", "高但无意义"][i % 4],
            "feasibility": ["高", "中", "中-高"][i % 3],
            "quadrant": ["甜区（创新中-高×可行高）", "甜区", "高风险高回报"][i % 3],
            "platform": "工程菌",
            "disease": ["结直肠癌", "胰腺癌", "实体瘤"][i % 3],
            "method": "重组合 + 换角度",       # 老格子用中文自由文本，schema2 才要英文枚举
            "status": "untried",
            "date": "2026-07-08",
            "notes": "历史对话直接写入，未走脚本",
        }
        if i % 7 == 0:
            cell["intervention_2026-09-12"] = "柚子口头否掉了一半"   # 非常规键名
        if i % 11 == 0:
            cell["refs"] = ["PMID 40476548", "PMID 39990001"]
        if i < 16:
            cell["user_verdict"] = DECIDED_VALUES[i % len(DECIDED_VALUES)]
        else:
            v = UNDECIDED_VALUES[i % len(UNDECIDED_VALUES)]
            if v is not NO_VERDICT:
                cell["user_verdict"] = v
        # 老格子一律没有 schema 键，也没有新必填字段
        assert "schema" not in cell
        for k in ("hypothesis", "falsification", "feasibility_layers",
                  "novelty_queries", "closest_work", "diff", "seed_id"):
            assert k not in cell
        cells.append(cell)
    return cells


@pytest.fixture
def legacy_map(mapfile):
    """103 格全 schema1 的真实形态地图副本。"""
    return mapfile(_legacy103())


def _items_for(cells, indices, verdict="归档"):
    out = []
    for i in indices:
        it = {"index": i, "expect": cells[i]["idea"][:12], "user_verdict": verdict}
        if verdict == "归档":
            it["restart_condition"] = RC
        out.append(it)
    return out


# ================================================= status / gate

def test_老地图_status统计正确(run_map, legacy_map):
    """5.6：103 格全 schema1，total=103、schema1=103、schema2=0、undecided=87。"""
    d = run_map(["status", "--map", legacy_map]).assert_ok("status")
    assert d["total"] == 103
    assert d["schema1"] == 103
    assert d["schema2"] == 0
    assert d["undecided"] == 87
    assert d["decided"] == 16


def test_老地图_gate因积压拦下但不因缺字段报错(run_map, legacy_map):
    """老地图 gate 退出码 2 只因为积压（BACKLOG_NOT_EMPTY），不是因为缺新字段。"""
    r = run_map(["gate", "--map", legacy_map])
    d = r.assert_rejected("gate", 2, gate="backlog")
    assert d["undecided"] == 87
    assert all(e["code"] == "BACKLOG_NOT_EMPTY" for e in r.json["errors"]), r.json["errors"]


def test_老地图_status不因缺新字段返回非0(run_map, legacy_map):
    """5.6 末行：任何子命令都不得因老格子缺新必填字段而返回非 0 退出码。"""
    assert run_map(["status", "--map", legacy_map]).code == 0


# ================================================= verdict 单格

def test_老格子缺三大新字段仍可裁决(run_map, legacy_map, backup_dir):
    """5.6：给一个缺 feasibility_layers/falsification/hypothesis 的老格子写"归档"+重启条件，
    必须放行（退出码 0）。"""
    cells = read_json(legacy_map)["cells"]
    idx = 20
    assert "hypothesis" not in cells[idx] and "falsification" not in cells[idx]
    d = run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
                 "--today", TODAY],
                stdin_obj=_items_for(cells, [idx])).assert_ok("verdict")
    assert d["updated"] == 1
    after = read_json(legacy_map)["cells"][idx]
    assert after["user_verdict"] == "归档" and after["archived"] is True


def test_老格子method是中文自由文本_不触发枚举校验(run_map, legacy_map, backup_dir):
    """老格子 method='重组合 + 换角度' 不合 schema2 枚举，verdict 仍必须放行。"""
    cells = read_json(legacy_map)["cells"]
    assert cells[30]["method"] == "重组合 + 换角度"
    run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
             "--today", TODAY],
            stdin_obj=_items_for(cells, [30], "采纳")).assert_ok("verdict")


def test_老格子被改后其余字段逐字段不变(run_map, legacy_map, backup_dir):
    """5.6：除四个可变键外，所有原字段（含 intervention_2026-09-12 这类非常规键）不变。"""
    cells_before = read_json(legacy_map)["cells"]
    idx = 21  # 21 % 7 == 0，带 intervention 键
    assert "intervention_2026-09-12" in cells_before[idx]
    run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
             "--today", TODAY],
            stdin_obj=_items_for(cells_before, [idx])).assert_ok("verdict")
    after = read_json(legacy_map)["cells"][idx]
    mutable = set(["user_verdict", "restart_condition", "archived", "verdict_date"])
    for k, v in cells_before[idx].items():
        if k not in mutable:
            assert after[k] == v, "字段 %s 被改动：%r -> %r" % (k, v, after.get(k))
    assert "schema" not in after, "老格子不得被脚本升级成 schema2"


def test_老格子不被脚本补齐新字段(run_map, legacy_map, backup_dir):
    """反向断言：裁决后不得给老格子凭空补 hypothesis/falsification 等新字段。"""
    cells = read_json(legacy_map)["cells"]
    run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
             "--today", TODAY],
            stdin_obj=_items_for(cells, [40], "否决")).assert_ok("verdict")
    after = read_json(legacy_map)["cells"][40]
    for k in ("hypothesis", "falsification", "feasibility_layers", "novelty_queries",
              "closest_work", "diff", "seed_id", "committed_at"):
        assert k not in after, "不得给老格子凭空补 %s" % k


# ================================================= 批量清空 87 格

def test_批量裁决87格_清空积压(run_map, legacy_map, backup_dir):
    """5.6 核心：一次给 87 个未裁决格子写裁决 → updated=87、undecided_after=0、
    cells_after=103（不搬家）。"""
    cells = read_json(legacy_map)["cells"]
    undec = UNDECIDED_INDICES  # 构造时即确定：下标 16..102 共 87 个占位裁决
    assert len(undec) == 87
    d = run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
                 "--today", TODAY],
                stdin_obj=_items_for(cells, undec)).assert_ok("verdict")
    assert d["updated"] == 87
    assert d["undecided_before"] == 87
    assert d["undecided_after"] == 0
    assert d["cells_before"] == 103 and d["cells_after"] == 103
    assert d["by_verdict"]["归档"] == 87


def test_清空积压后gate放行(run_map, legacy_map, backup_dir):
    """闭环：87 格裁决完之后 gate 退出码变为 0，undecided=0。"""
    cells = read_json(legacy_map)["cells"]
    undec = UNDECIDED_INDICES
    run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
             "--today", TODAY],
            stdin_obj=_items_for(cells, undec)).assert_ok("verdict")
    d = run_map(["gate", "--map", legacy_map]).assert_ok("gate")
    assert d["undecided"] == 0 and d["total"] == 103


def test_清空后status的archived计数(run_map, legacy_map, backup_dir):
    """87 格全部归档后 archived=87，total 仍为 103。"""
    cells = read_json(legacy_map)["cells"]
    undec = UNDECIDED_INDICES
    run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
             "--today", TODAY],
            stdin_obj=_items_for(cells, undec)).assert_ok("verdict")
    d = run_map(["status", "--map", legacy_map]).assert_ok("status")
    assert d["archived"] == 87
    assert d["total"] == 103
    assert d["schema1"] == 103 and d["schema2"] == 0


# ================================================= 覆盖保护与老数据

def test_老格子已有自由文本裁决_不带overwrite被拒(run_map, legacy_map, backup_dir):
    """5.6：目标是已有"不建议作主课题"的格子，不带 --allow-overwrite → ALREADY_DECIDED。"""
    cells = read_json(legacy_map)["cells"]
    idx = 0
    assert cells[idx]["user_verdict"] == "不建议作主课题"
    before = sha256_of(legacy_map)
    r = run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
                 "--today", TODAY], stdin_obj=_items_for(cells, [idx], "采纳"))
    r.assert_rejected("verdict", 2, gate="verdict")
    assert "ALREADY_DECIDED" in [e["code"] for e in r.json["errors"]]
    assert sha256_of(legacy_map) == before


def test_老格子已有裁决_带overwrite放行(run_map, legacy_map, backup_dir):
    """5.6：同一场景带 --allow-overwrite 放行，值被改写。"""
    cells = read_json(legacy_map)["cells"]
    run_map(["verdict", "--map", legacy_map, "--backup-dir", backup_dir,
             "--today", TODAY, "--allow-overwrite"],
            stdin_obj=_items_for(cells, [0], "采纳")).assert_ok("verdict")
    assert read_json(legacy_map)["cells"][0]["user_verdict"] == "采纳"


# ================================================= 老地图上写新假说

def test_老地图上commit新假说_老格子不受影响(run_map, legacy_map, seeded,
                                            session_dir, backup_dir):
    """在 103 格老地图上 commit：新 cell 追加为 index 103，前 103 格逐字段不变。"""
    before = read_json(legacy_map)["cells"]
    sid = seeded(1)[0]
    d = run_map(["commit", "--seed-id", sid, "--map", legacy_map,
                 "--session-dir", session_dir, "--backup-dir", backup_dir,
                 "--today", TODAY], stdin_obj=good_cell()).assert_ok("commit")
    assert d["index"] == 103 and d["cells_after"] == 104
    after = read_json(legacy_map)["cells"]
    assert after[:103] == before
    assert after[103]["schema"] == 2


def test_老地图积压87格也不挡commit(run_map, legacy_map, seeded, session_dir,
                                    backup_dir):
    """commit 不做零积压检查：即使 87 格积压也能写入（闸门 3 是开工前的闸）。"""
    sid = seeded(1)[0]
    run_map(["commit", "--seed-id", sid, "--map", legacy_map,
             "--session-dir", session_dir, "--backup-dir", backup_dir,
             "--today", TODAY], stdin_obj=good_cell()).assert_ok("commit")


def test_老地图commit后status区分两种schema(run_map, legacy_map, seeded,
                                            session_dir, backup_dir):
    """写入 1 个 schema2 后：schema1=103、schema2=1、total=104。"""
    sid = seeded(1)[0]
    run_map(["commit", "--seed-id", sid, "--map", legacy_map,
             "--session-dir", session_dir, "--backup-dir", backup_dir,
             "--today", TODAY], stdin_obj=good_cell()).assert_ok("commit")
    d = run_map(["status", "--map", legacy_map]).assert_ok("status")
    assert d["total"] == 104 and d["schema1"] == 103 and d["schema2"] == 1


def test_schema值不是2的cell按schema1处理(run_map, mapfile, backup_dir):
    """1.2 判定方式：schema=1 或 schema='2'（字符串）都应按 schema1 计。"""
    c1 = dict(good_cell(), schema=1, idea="某个带 schema=1 的格子" + zh(20))
    c2 = dict(good_cell(), schema="2", idea="某个 schema 是字符串的格子" + zh(20))
    d = run_map(["status", "--map", mapfile([c1, c2])]).assert_ok("status")
    assert d["schema1"] == 2 and d["schema2"] == 0
