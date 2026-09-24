# -*- coding: utf-8 -*-
"""ib_map.py verdict：寻址校验、覆盖保护、四键限制（INTERFACE 3.4、5.4、5.7）。"""
import pytest

from conftest import (NO_VERDICT, TODAY, legacy_cell, read_json, sha256_of, zh)

IDEA_A = "让厌氧工程菌从被动乏氧富集升级为主动探测肿瘤代谢梯度的导航系统"
IDEA_B = "把蛋白酶从降解ECM的工具改造成瘤内压力传感器的读出元件"
IDEA_C = "用菌分裂稀释当瘤内活菌计时器，把定植时长换算成可读的剂量曲线"
RC = "若能论证 VE-cadherin 连接可逆自恢复，且给出微出血定量数据"


@pytest.fixture
def vd(run_map, mapfile, backup_dir):
    """返回 v(items, cells=..., overwrite=False) -> Result，自动带 --today。"""
    class V(object):
        def __init__(self):
            self.map = None

        def setup(self, cells):
            self.map = mapfile(cells)
            self.sha_before = sha256_of(self.map)
            return self.map

        def run(self, items, overwrite=False, stdin_raw=None):
            if self.map is None:
                self.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定"),
                            legacy_cell(IDEA_C, "待定")])
            args = ["verdict", "--map", self.map, "--backup-dir", backup_dir,
                    "--today", TODAY]
            if overwrite:
                args.append("--allow-overwrite")
            return run_map(args, stdin_obj=items, stdin_raw=stdin_raw)

        def doc(self):
            return read_json(self.map)

        def sha(self):
            return sha256_of(self.map)

    return V()


# ================================================= 放行路径

def test_verdict_单条采纳_放行(vd):
    """基线：单条采纳（用数组包裹），退出码 0，updated=1，cells 数不变。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    d = vd.run([{"index": 0, "expect": IDEA_A[:10], "user_verdict": "采纳"}]).assert_ok("verdict")
    assert d["updated"] == 1
    assert d["by_verdict"]["采纳"] == 1
    assert d["cells_before"] == d["cells_after"] == 1
    assert d["undecided_before"] == 1 and d["undecided_after"] == 0
    assert vd.doc()["cells"][0]["user_verdict"] == "采纳"


def test_verdict_归档写入四个键(vd):
    """归档：写 user_verdict/restart_condition/archived=true/verdict_date=当天。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "归档",
             "restart_condition": RC}]).assert_ok("verdict")
    c = vd.doc()["cells"][0]
    assert c["user_verdict"] == "归档"
    assert c["restart_condition"] == RC
    assert c["archived"] is True
    assert c["verdict_date"] == TODAY


def test_verdict_归档不搬家_留在cells原位(vd):
    """3.4 末行：归档后 cells 长度不变、下标不变，rejected_or_downgraded 不变。"""
    cells = [legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定")]
    vd.setup(cells)
    before_rej = vd.doc()["rejected_or_downgraded"]
    d = vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "归档",
                 "restart_condition": RC}]).assert_ok("verdict")
    doc = vd.doc()
    assert d["cells_after"] == d["cells_before"] == 2
    assert len(doc["cells"]) == 2
    assert doc["cells"][0]["idea"] == IDEA_A, "归档后下标必须稳定"
    assert doc["cells"][1]["idea"] == IDEA_B
    assert doc["rejected_or_downgraded"] == before_rej, "该数组被冻结，脚本只读"


def test_verdict_批量三条_by_verdict统计正确(vd):
    """批量：三条不同终态，by_verdict 计数正确，updated=3。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待补"),
              legacy_cell(IDEA_C, NO_VERDICT)])
    d = vd.run([
        {"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"},
        {"index": 1, "expect": IDEA_B[:8], "user_verdict": "否决"},
        {"index": 2, "expect": IDEA_C[:8], "user_verdict": "归档", "restart_condition": RC},
    ]).assert_ok("verdict")
    assert d["updated"] == 3
    assert d["by_verdict"] == {"采纳": 1, "否决": 1, "归档": 1}
    assert d["undecided_before"] == 3 and d["undecided_after"] == 0


def test_verdict_expect恰好6字符_放行(vd):
    """边界含等号：expect 恰好 6 个字符且确为前缀，放行。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    vd.run([{"index": 0, "expect": IDEA_A[:6], "user_verdict": "采纳"}]).assert_ok("verdict")


def test_verdict_expect为整个idea_放行(vd):
    """反例防误杀：expect 等于完整 idea 也是合法前缀。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    vd.run([{"index": 0, "expect": IDEA_A, "user_verdict": "否决"}]).assert_ok("verdict")


def test_verdict_重启条件恰好10字_放行(vd):
    """边界含等号：restart_condition 恰好 10 字，放行。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "归档",
             "restart_condition": zh(10)}]).assert_ok("verdict")


# ================================================= 输入格式

def test_verdict_stdin非法JSON_退出码3(vd):
    """stdin 不是合法 JSON：退出码 3，gate=input，BAD_JSON，地图未改。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run(None, stdin_raw="[{index: 0}")
    r.assert_rejected("verdict", 3, gate="input")
    assert vd.sha() == vd.sha_before


def test_verdict_stdin裸对象不接受_退出码3(vd):
    """3.4 明确：单条也要用数组包，裸对象一律退出码 3、BAD_JSON。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run({"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"})
    r.assert_rejected("verdict", 3, gate="input")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]
    assert vd.doc()["cells"][0]["user_verdict"] == "待定", "拒绝时不得写入"


def test_verdict_空数组_退出码3_EMPTY(vd):
    """空数组：退出码 3，gate=input，code=EMPTY。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([])
    r.assert_rejected("verdict", 3, gate="input")
    assert "EMPTY" in [e["code"] for e in r.json["errors"]]


# ================================================= 寻址校验

def test_verdict_index越界_INDEX_OUT_OF_RANGE(vd):
    """index=999 超界：退出码 2，gate=addressing，地图未改。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 999, "expect": IDEA_A[:8], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].index", "INDEX_OUT_OF_RANGE")
    assert vd.sha() == vd.sha_before


def test_verdict_index负数_INDEX_OUT_OF_RANGE(vd):
    """负下标不得被当成 Python 尾部索引：index=-1 应判越界。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定")])
    r = vd.run([{"index": -1, "expect": IDEA_B[:8], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].index", "INDEX_OUT_OF_RANGE")
    assert vd.sha() == vd.sha_before


def test_verdict_index等于长度_越界(vd):
    """边界：cells 长度为 2 时 index=2 越界（下标 0 起）。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定")])
    r = vd.run([{"index": 2, "expect": IDEA_A[:8], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].index", "INDEX_OUT_OF_RANGE")


def test_verdict_index非整数_INDEX_OUT_OF_RANGE(vd):
    """index 是字符串 "0"：按非整数处理，退出码 2，gate=addressing。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": "0", "expect": IDEA_A[:8], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].index", "INDEX_OUT_OF_RANGE")


def test_verdict_缺index_拒绝(vd):
    """缺 index 键：退出码 2，gate=addressing，地图未改。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"expect": IDEA_A[:8], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    assert vd.sha() == vd.sha_before


def test_verdict_缺expect_MISSING(vd):
    """缺 expect：退出码 2，gate=addressing，code=MISSING。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 0, "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].expect", "MISSING")


def test_verdict_expect长5_TOO_SHORT(vd):
    """边界：expect 恰好 5 字符，低于下限 6，拒绝。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 0, "expect": IDEA_A[:5], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].expect", "TOO_SHORT")


def test_verdict_expect不是前缀_PREFIX_MISMATCH带actual_prefix(vd):
    """expect 与目标 idea 前缀不符：PREFIX_MISMATCH，该条须带 actual_prefix（前 12 字）。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定")])
    r = vd.run([{"index": 1, "expect": IDEA_A[:10], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].expect", "PREFIX_MISMATCH")
    err = [e for e in r.json["errors"] if e["code"] == "PREFIX_MISMATCH"][0]
    assert err.get("actual_prefix") == IDEA_B[:12], \
        "PREFIX_MISMATCH 须带目标 idea 的前 12 字便于排错：%s" % err
    assert vd.sha() == vd.sha_before


def test_verdict_expect是中间子串非前缀_拒绝(vd):
    """防误放：expect 是 idea 的中间子串而非前缀，必须 PREFIX_MISMATCH。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 0, "expect": IDEA_A[5:15], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].expect", "PREFIX_MISMATCH")


def test_verdict_expect大小写不同_拒绝(vd):
    """区分大小写：全大写的 ECM 改成小写后不再是前缀，应拒绝。"""
    idea = "ECM 重塑通路里的蛋白酶改造成瘤内压力传感器的读出元件"
    vd.setup([legacy_cell(idea, "待定")])
    r = vd.run([{"index": 0, "expect": "ecm 重塑通路", "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="addressing")
    r.assert_error("[0].expect", "PREFIX_MISMATCH")


def test_verdict_批量中第三条前缀不符_整批拒绝(vd):
    """全有或全无：3 条里第 3 条 expect 不符 → 整批拒绝，前两条也不写。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定"),
              legacy_cell(IDEA_C, "待定")])
    r = vd.run([
        {"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"},
        {"index": 1, "expect": IDEA_B[:8], "user_verdict": "否决"},
        {"index": 2, "expect": "完全不相干的前缀文字", "user_verdict": "采纳"},
    ])
    r.assert_rejected("verdict", 2, gate="addressing")
    assert "updated" not in r.json, "整批拒绝时不应出现 updated"
    assert vd.sha() == vd.sha_before, "整批拒绝时地图必须逐字节不变"
    for c in vd.doc()["cells"]:
        assert c["user_verdict"] == "待定"


def test_verdict_50条里第37条不符_整批拒绝(vd):
    """5.7 场景：批量 50 条里第 37 条 expect 不符，整批拒绝，地图逐字节未改。"""
    cells = [legacy_cell(IDEA_A + "#%d" % i, "待定") for i in range(50)]
    vd.setup(cells)
    items = [{"index": i, "expect": (IDEA_A + "#%d" % i)[:10], "user_verdict": "否决"}
             for i in range(50)]
    items[36]["expect"] = "彻底对不上的前缀内容"
    r = vd.run(items)
    r.assert_rejected("verdict", 2, gate="addressing")
    assert "updated" not in r.json
    assert vd.sha() == vd.sha_before


def test_verdict_同批index重复_NOT_ALLOWED(vd):
    """同一批里 index 重复：退出码 2，gate=addressing，code=NOT_ALLOWED。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定")])
    r = vd.run([
        {"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"},
        {"index": 0, "expect": IDEA_A[:8], "user_verdict": "否决"},
    ])
    r.assert_rejected("verdict", 2, gate="addressing")
    assert any(e["code"] == "NOT_ALLOWED" and e["field"].endswith(".index")
               for e in r.json["errors"]), r.json["errors"]
    assert vd.sha() == vd.sha_before


# ================================================= 裁决终态闸

@pytest.mark.parametrize("v", ["待定", "搁置", "pending", "", "   ", "采纳：作为主线",
                               "不建议作主课题", "Adopt", "归档 "])
def test_verdict_非三终态_NOT_ALLOWED(vd, v):
    """verdict 同样要求精确三终态：其余一律 NOT_ALLOWED，退出码 2，地图未改。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": v}])
    r.assert_rejected("verdict", 2, gate="verdict")
    assert "NOT_ALLOWED" in [e["code"] for e in r.json["errors"]]
    assert vd.sha() == vd.sha_before


def test_verdict_缺user_verdict_拒绝(vd):
    """缺 user_verdict 键：退出码 2，gate=verdict。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 0, "expect": IDEA_A[:8]}])
    r.assert_rejected("verdict", 2, gate="verdict")


def test_verdict_归档缺重启条件_拒绝(vd):
    """归档缺 restart_condition：gate=verdict，field='[0].restart_condition'，MISSING。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "归档"}])
    r.assert_rejected("verdict", 2, gate="verdict")
    r.assert_error("[0].restart_condition", "MISSING")
    assert vd.sha() == vd.sha_before


def test_verdict_归档重启条件长9_TOO_SHORT(vd):
    """边界：restart_condition 恰好 9 字，拒绝。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "归档",
                 "restart_condition": zh(9)}])
    r.assert_rejected("verdict", 2, gate="verdict")
    r.assert_error("[0].restart_condition", "TOO_SHORT")


def test_verdict_归档重启条件占位_PLACEHOLDER(vd):
    """restart_condition='待定：等柚子看完再说'：占位，拒绝。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    r = vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "归档",
                 "restart_condition": "待定：等柚子看完再说"}])
    r.assert_rejected("verdict", 2, gate="verdict")
    r.assert_error("[0].restart_condition", "PLACEHOLDER")


def test_verdict_批量中一条非终态_整批不写(vd):
    """全有或全无：批里有一条 user_verdict='待定'，另外两条也不得写入。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定"),
              legacy_cell(IDEA_C, "待定")])
    r = vd.run([
        {"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"},
        {"index": 1, "expect": IDEA_B[:8], "user_verdict": "待定"},
        {"index": 2, "expect": IDEA_C[:8], "user_verdict": "否决"},
    ])
    r.assert_rejected("verdict", 2, gate="verdict")
    assert vd.sha() == vd.sha_before


# ================================================= 覆盖保护

def test_verdict_目标已有真实裁决_ALREADY_DECIDED(vd):
    """目标 cell 已是"不建议作主课题"（非占位）且无 --allow-overwrite：拒绝。"""
    vd.setup([legacy_cell(IDEA_A, "不建议作主课题")])
    r = vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="verdict")
    assert "ALREADY_DECIDED" in [e["code"] for e in r.json["errors"]]
    assert vd.sha() == vd.sha_before
    assert vd.doc()["cells"][0]["user_verdict"] == "不建议作主课题"


def test_verdict_带allow_overwrite_放行并覆盖(vd):
    """带 --allow-overwrite 时同一场景放行，值被覆盖为新裁决。"""
    vd.setup([legacy_cell(IDEA_A, "不建议作主课题")])
    d = vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"}],
               overwrite=True).assert_ok("verdict")
    assert d["updated"] == 1
    assert vd.doc()["cells"][0]["user_verdict"] == "采纳"


def test_verdict_目标是占位裁决_无需overwrite即可写(vd):
    """反例防误杀：目标裁决是占位（"待定"）时不触发覆盖保护，直接放行。"""
    vd.setup([legacy_cell(IDEA_A, "待定：拟作 2027 青基主线方案 A")])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "归档",
             "restart_condition": RC}]).assert_ok("verdict")


def test_verdict_目标缺user_verdict键_无需overwrite(vd):
    """反例防误杀：目标完全没有 user_verdict 键时不算已裁决，直接放行。"""
    vd.setup([legacy_cell(IDEA_A, NO_VERDICT)])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"}]).assert_ok("verdict")


def test_verdict_批量中一条已裁决_整批拒绝(vd):
    """全有或全无：批里有一条命中覆盖保护，整批不写。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "已否决（2026-09-15）：打不过纯肽")])
    r = vd.run([
        {"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"},
        {"index": 1, "expect": IDEA_B[:8], "user_verdict": "归档", "restart_condition": RC},
    ])
    r.assert_rejected("verdict", 2, gate="verdict")
    assert vd.sha() == vd.sha_before


# ================================================= 只改四个键

def test_verdict_只改四个键_其余字段逐字段不变(vd):
    """3.4 铁规：除四个键外所有原字段原样保留，含非常规键名。"""
    extra = {"intervention_2026-09-12": "柚子口头否掉了一半",
             "novelty": "中-高", "refs": ["PMID 40476548"],
             "nested": {"a": [1, 2, {"b": "c"}]}}
    vd.setup([legacy_cell(IDEA_A, "待定", extra)])
    before = dict(vd.doc()["cells"][0])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "归档",
             "restart_condition": RC}]).assert_ok("verdict")
    after = vd.doc()["cells"][0]
    mutable = set(["user_verdict", "restart_condition", "archived", "verdict_date"])
    for k, v in before.items():
        if k not in mutable:
            assert after[k] == v, "字段 %s 被改动了：%r -> %r" % (k, v, after.get(k))
    assert set(after.keys()) - set(before.keys()) <= mutable, \
        "不得新增四个键之外的键：%s" % (set(after.keys()) - set(before.keys()))


def test_verdict_采纳时不新增archived键(vd):
    """archived 规则：原本没有该键 + 裁决是采纳 → 不新增。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"}]).assert_ok("verdict")
    assert "archived" not in vd.doc()["cells"][0]


def test_verdict_采纳时原有archived置false(vd):
    """archived 规则：原本 archived=true + 改判采纳 → 置为 false（不是删键）。"""
    vd.setup([legacy_cell(IDEA_A, "待定", {"archived": True})])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"}]).assert_ok("verdict")
    c = vd.doc()["cells"][0]
    assert "archived" in c and c["archived"] is False


def test_verdict_否决时原有archived置false(vd):
    """archived 规则：否决与采纳同理，原有键置 false。"""
    vd.setup([legacy_cell(IDEA_A, "待定", {"archived": True})])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "否决"}]).assert_ok("verdict")
    assert vd.doc()["cells"][0]["archived"] is False


def test_verdict_非归档不写restart_condition(vd):
    """restart_condition 仅归档时写入：采纳时即使传了也不应写进 cell。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳",
             "restart_condition": RC}]).assert_ok("verdict")
    c = vd.doc()["cells"][0]
    assert c.get("restart_condition") != RC or "restart_condition" not in c, \
        "非归档不应写入 restart_condition：%r" % c.get("restart_condition")


def test_verdict_不改动其他cell(vd):
    """反向断言：只有目标下标被改，其余 cell 逐字段不变。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定"),
              legacy_cell(IDEA_C, "待定")])
    before = vd.doc()["cells"]
    vd.run([{"index": 1, "expect": IDEA_B[:8], "user_verdict": "采纳"}]).assert_ok("verdict")
    after = vd.doc()["cells"]
    assert after[0] == before[0]
    assert after[2] == before[2]
    assert after[1]["user_verdict"] == "采纳"


def test_verdict_version与note不被改写(vd):
    """1.1：version/note 脚本只读不写。"""
    vd.setup([legacy_cell(IDEA_A, "待定")])
    before = vd.doc()
    vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "采纳"}]).assert_ok("verdict")
    after = vd.doc()
    assert after["version"] == before["version"]
    assert after["note"] == before["note"]


def test_verdict_绝不自动裁决_不得凭空给别的格子下裁决(vd):
    """反向断言：批里只提了 index 0，index 1/2 不得被脚本"顺手"裁决。"""
    vd.setup([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_B, "待定"),
              legacy_cell(IDEA_C, "待定")])
    d = vd.run([{"index": 0, "expect": IDEA_A[:8], "user_verdict": "否决"}]).assert_ok("verdict")
    assert d["updated"] == 1
    assert d["undecided_after"] == 2, "未提及的格子必须仍是未裁决"
    assert vd.doc()["cells"][1]["user_verdict"] == "待定"
    assert vd.doc()["cells"][2]["user_verdict"] == "待定"
