# -*- coding: utf-8 -*-
"""ib_map.py commit：必填字段闸（INTERFACE 1.3、1.4、1.5、5.2、5.3）。"""
import pytest

from conftest import TODAY, good_cell, legacy_cell, read_json, sha256_of, zh

IDEA_OLD = "让厌氧工程菌从被动乏氧富集升级为主动探测肿瘤代谢梯度的导航系统"


@pytest.fixture
def commit(run_map, mapfile, seeded, session_dir, backup_dir):
    """返回 do(cell, **kw) -> Result：自动建地图、登记种子、跑 commit。"""
    state = {}

    def _do(cell, seed_id=None, today=TODAY, cells=None, extra_args=()):
        if "map" not in state:
            state["map"] = mapfile(cells if cells is not None else
                                   [legacy_cell(IDEA_OLD, "采纳")])
            state["sha_before"] = sha256_of(state["map"])
        if seed_id is None:
            seed_id = seeded(1, today)[0]
        args = ["commit", "--seed-id", seed_id, "--map", state["map"],
                "--session-dir", session_dir, "--backup-dir", backup_dir,
                "--today", today] + list(extra_args)
        r = run_map(args, stdin_obj=cell)
        r.map_path = state["map"]
        r.sha_before = state["sha_before"]
        return r

    _do.state = state
    return _do


def _assert_map_untouched(r):
    assert sha256_of(r.map_path) == r.sha_before, "被拒时地图一个字节都不得改"


# ================================================= 放行基线

def test_commit_完整合格cell_放行(commit):
    """基线：各字段恰好合格的 cell 应放行，退出码 0，cells 增加 1。"""
    r = commit(good_cell())
    d = r.assert_ok("commit")
    assert d["cells_before"] == 1 and d["cells_after"] == 2
    assert d["index"] == 1
    assert d["today_count"] == 1 and d["cap"] == 3
    assert d["user_verdict"] == "采纳"
    assert d["date"] == TODAY


# ================================================= idea

def test_commit_缺idea_MISSING(commit):
    """缺 idea：拒绝，gate=required_fields，field=idea，code=MISSING。"""
    r = commit(good_cell(idea=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("idea", "MISSING")
    _assert_map_untouched(r)


@pytest.mark.parametrize("v,code", [("", "EMPTY"), ("    ", "EMPTY"),
                                    ("待补", "PLACEHOLDER"), ("—", "PLACEHOLDER"),
                                    ("TBD", "PLACEHOLDER")])
def test_commit_idea空或占位(commit, v, code):
    """idea 为空串/纯空白/占位词：拒绝并报对应 code。"""
    r = commit(good_cell(idea=v))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("idea", code)


def test_commit_idea长29_TOO_SHORT(commit):
    """边界：idea 恰好 29 字符，低于下限 30，拒绝。"""
    r = commit(good_cell(idea=zh(29)))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("idea", "TOO_SHORT")


def test_commit_idea长30_放行(commit):
    """边界含等号：idea 恰好 30 字符应放行。"""
    commit(good_cell(idea=zh(30))).assert_ok("commit")


def test_commit_idea带空白使strip后不足30_TOO_SHORT(commit):
    """计数前先 strip：29 字正文 + 若干空格，仍判 TOO_SHORT。"""
    r = commit(good_cell(idea="  " + zh(29) + "   "))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("idea", "TOO_SHORT")


# ================================================= hypothesis

def test_commit_hypothesis四键齐全_放行(commit):
    """基线：hypothesis 恰好四键且每段 ≥30 字，放行。"""
    commit(good_cell()).assert_ok("commit")


def test_commit_缺hypothesis_MISSING(commit):
    """缺 hypothesis 整个键：拒绝，field=hypothesis，code=MISSING。"""
    r = commit(good_cell(hypothesis=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("hypothesis", "MISSING")


def test_commit_hypothesis是字符串_WRONG_TYPE(commit):
    """hypothesis 传字符串：拒绝，code=WRONG_TYPE。"""
    r = commit(good_cell(hypothesis="背景、缺口、设计、创新都写在这一段里了"))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("hypothesis", "WRONG_TYPE")


def test_commit_hypothesis是列表_WRONG_TYPE(commit):
    """hypothesis 传列表：拒绝，code=WRONG_TYPE。"""
    r = commit(good_cell(hypothesis=[zh(30), zh(30), zh(30), zh(30)]))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("hypothesis", "WRONG_TYPE")


@pytest.mark.parametrize("missing_key", ["background", "gap", "design", "innovation"])
def test_commit_hypothesis缺一个键_点路径报MISSING(commit, missing_key):
    """缺任一子键：field 用点路径 hypothesis.<键名>，code=MISSING。"""
    h = dict(good_cell()["hypothesis"])
    del h[missing_key]
    r = commit(good_cell(hypothesis=h))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("hypothesis." + missing_key, "MISSING")


def test_commit_hypothesis只有3个键_拒绝(commit):
    """5.2 场景：hypothesis 只有 3 个键，拒绝并指明缺的那个。"""
    h = dict(good_cell()["hypothesis"])
    del h["innovation"]
    r = commit(good_cell(hypothesis=h))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("hypothesis.innovation", "MISSING")


def test_commit_hypothesis某段长29_TOO_SHORT(commit):
    """边界：hypothesis.gap 恰好 29 字，拒绝。"""
    h = dict(good_cell()["hypothesis"])
    h["gap"] = zh(29)
    r = commit(good_cell(hypothesis=h))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("hypothesis.gap", "TOO_SHORT")


def test_commit_hypothesis某段恰好30_放行(commit):
    """边界含等号：hypothesis.gap 恰好 30 字、其余 ≥30，放行。"""
    h = dict(good_cell()["hypothesis"])
    h["gap"] = zh(30)
    commit(good_cell(hypothesis=h)).assert_ok("commit")


@pytest.mark.parametrize("v,code", [("", "EMPTY"), ("   ", "EMPTY"),
                                    ("待定：回头补这一段", "PLACEHOLDER")])
def test_commit_hypothesis某段空或占位(commit, v, code):
    """hypothesis.design 为空/占位：拒绝并用点路径报错。"""
    h = dict(good_cell()["hypothesis"])
    h["design"] = v
    r = commit(good_cell(hypothesis=h))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("hypothesis.design", code)


def test_commit_hypothesis某段非字符串_WRONG_TYPE(commit):
    """hypothesis.background 是数字：拒绝，code=WRONG_TYPE。"""
    h = dict(good_cell()["hypothesis"])
    h["background"] = 42
    r = commit(good_cell(hypothesis=h))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("hypothesis.background", "WRONG_TYPE")


def test_commit_hypothesis多出第五个键_被拒(commit):
    """1.3 规定 hypothesis "必须恰好含 4 个键"，多出第五个键按最严格解释应拒绝。
    注意：接口未规定多键时的 code，故只断言退出码/gate/出错字段，不断言 code。"""
    h = dict(good_cell()["hypothesis"])
    h["extra_note"] = "这是补充说明，不属于四要素"
    r = commit(good_cell(hypothesis=h))
    r.assert_rejected("commit", 2, gate="required_fields")
    assert any(e["field"].startswith("hypothesis") for e in r.json["errors"]), \
        "多键应就 hypothesis 报错：%s" % r.json["errors"]


# ================================================= feasibility_layers

def test_commit_缺feasibility_layers_MISSING(commit):
    """缺 feasibility_layers：拒绝，code=MISSING。"""
    r = commit(good_cell(feasibility_layers=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("feasibility_layers", "MISSING")


def test_commit_feasibility_layers是字符串_WRONG_TYPE(commit):
    """传字符串：拒绝，code=WRONG_TYPE（接口原文举的例子）。"""
    r = commit(good_cell(feasibility_layers="生物学可行、递送可行、三年可做完"))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("feasibility_layers", "WRONG_TYPE")


def test_commit_feasibility_layers两个键_TOO_FEW(commit):
    """边界：只有 2 个键，低于下限 3，拒绝，code=TOO_FEW。"""
    r = commit(good_cell(feasibility_layers={"biology": zh(12), "measure": zh(12)}))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("feasibility_layers", "TOO_FEW")


def test_commit_feasibility_layers空字典_拒绝(commit):
    """边界：空字典，拒绝（EMPTY 或 TOO_FEW）。"""
    r = commit(good_cell(feasibility_layers={}))
    r.assert_rejected("commit", 2, gate="required_fields")
    assert r.codes_of("feasibility_layers"), r.json["errors"]
    assert set(r.codes_of("feasibility_layers")) & set(["EMPTY", "TOO_FEW"]), r.json["errors"]


def test_commit_feasibility_layers三个键_放行(commit):
    """边界含等号：恰好 3 个键且每值 ≥10 字，放行。"""
    commit(good_cell(feasibility_layers={
        "biology": zh(10), "delivery": zh(10), "safety": zh(10)})).assert_ok("commit")


@pytest.mark.parametrize("keys", [
    ("机制", "体系实现", "三年立项"),
    ("biology", "delivery_signal", "safety_executability"),
    ("measure", "caveat", "机制"),
    ("生物学", "可测量性", "伦理与合规"),
])
def test_commit_feasibility_layers不校验键名_各种真实键名放行(commit, keys):
    """反例防误杀：真实数据键名有 30 余种，中英混杂都必须放行（只查结构不查键名）。"""
    layers = dict((k, zh(12)) for k in keys)
    commit(good_cell(feasibility_layers=layers)).assert_ok("commit")


def test_commit_feasibility_layers某值为空串_EMPTY带点路径(commit):
    """3 个键但其中一个值为空串：拒绝，field=feasibility_layers.<键名>，code=EMPTY。"""
    r = commit(good_cell(feasibility_layers={
        "biology": zh(12), "delivery": "", "safety": zh(12)}))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("feasibility_layers.delivery", "EMPTY")


def test_commit_feasibility_layers某值长9_TOO_SHORT(commit):
    """边界：某层值恰好 9 字，低于下限 10，拒绝。"""
    r = commit(good_cell(feasibility_layers={
        "biology": zh(9), "delivery": zh(12), "safety": zh(12)}))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("feasibility_layers.biology", "TOO_SHORT")


def test_commit_feasibility_layers某值占位_PLACEHOLDER(commit):
    """某层值是"待补：下周补数据"：拒绝，code=PLACEHOLDER。"""
    r = commit(good_cell(feasibility_layers={
        "biology": "待补：下周补这一层的数据", "delivery": zh(12), "safety": zh(12)}))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("feasibility_layers.biology", "PLACEHOLDER")


def test_commit_feasibility_layers某值非字符串_WRONG_TYPE(commit):
    """某层值是列表：拒绝，code=WRONG_TYPE，点路径定位。"""
    r = commit(good_cell(feasibility_layers={
        "biology": [zh(12)], "delivery": zh(12), "safety": zh(12)}))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("feasibility_layers.biology", "WRONG_TYPE")


def test_commit_feasibility_layers六个键_放行(commit):
    """反例防误杀：键数多于 3 不是错误，6 层应放行。"""
    layers = dict(("layer_%d" % i, zh(11)) for i in range(6))
    commit(good_cell(feasibility_layers=layers)).assert_ok("commit")


# ================================================= falsification

def test_commit_缺falsification_MISSING(commit):
    """缺 falsification：拒绝，code=MISSING（接口 0.3 示例场景）。"""
    r = commit(good_cell(falsification=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("falsification", "MISSING")
    _assert_map_untouched(r)


@pytest.mark.parametrize("v,code", [("", "EMPTY"), ("   ", "EMPTY"),
                                    ("待补", "PLACEHOLDER"), ("无", "PLACEHOLDER"),
                                    ("N/A", "PLACEHOLDER"),
                                    ("待补：等实验做完再写证伪判据", "PLACEHOLDER")])
def test_commit_falsification空或占位(commit, v, code):
    """falsification 为空/纯空白/占位词（含占位词+说明）：拒绝并报对应 code。"""
    r = commit(good_cell(falsification=v))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("falsification", code)


def test_commit_falsification长29_TOO_SHORT(commit):
    """边界：恰好 29 字符，拒绝。"""
    r = commit(good_cell(falsification=zh(29)))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("falsification", "TOO_SHORT")


def test_commit_falsification长30_放行(commit):
    """边界含等号：恰好 30 字符放行。"""
    commit(good_cell(falsification=zh(30))).assert_ok("commit")


def test_commit_falsification是数字_拒绝(commit):
    """falsification 传数字而非字符串：必须拒绝并就 falsification 报错，不得当成合格。"""
    r = commit(good_cell(falsification=12345))
    r.assert_rejected("commit", 2, gate="required_fields")
    assert r.codes_of("falsification"), "应就 falsification 报错：%s" % r.json["errors"]


# ================================================= novelty_queries 与 method 联动

def test_commit_angle加1条查新式_放行(commit):
    """method=angle 时 novelty_queries 下限为 1，1 条放行。"""
    commit(good_cell(method="angle",
                     novelty_queries=["circadian engineered bacteria tumor"])).assert_ok("commit")


def test_commit_combine加1条查新式_放行(commit):
    """method=combine 时下限为 1，1 条放行。"""
    commit(good_cell(method="combine",
                     novelty_queries=["lasso peptide live bacteria combo"])).assert_ok("commit")


def test_commit_transfer只有1条_TOO_FEW(commit):
    """method=transfer 下限为 2：只给 1 条必须拒绝，field=novelty_queries。"""
    r = commit(good_cell(method="transfer",
                         novelty_queries=["circadian engineered bacteria tumor"]))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("novelty_queries", "TOO_FEW")


def test_commit_transfer有2条_放行(commit):
    """边界含等号：method=transfer 且恰好 2 条查新式，放行。"""
    commit(good_cell(method="transfer", novelty_queries=[
        "circadian rhythm engineered bacteria tumor colonization",
        "昼夜节律 给药时点 肿瘤 活菌"])).assert_ok("commit")


def test_commit_transfer有3条_放行(commit):
    """method=transfer 且 3 条（多于下限），放行。"""
    commit(good_cell(method="transfer", novelty_queries=[
        "circadian engineered bacteria", "chronotherapy oncology bacteria",
        "时相 给药 活菌"])).assert_ok("commit")


def test_commit_缺novelty_queries_MISSING(commit):
    """缺 novelty_queries：拒绝，code=MISSING。"""
    r = commit(good_cell(novelty_queries=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("novelty_queries", "MISSING")


def test_commit_novelty_queries空列表_EMPTY(commit):
    """边界：空列表，拒绝，code=EMPTY。"""
    r = commit(good_cell(novelty_queries=[]))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("novelty_queries", "EMPTY")


def test_commit_novelty_queries是字符串_WRONG_TYPE(commit):
    """novelty_queries 传字符串而非列表：拒绝，code=WRONG_TYPE。"""
    r = commit(good_cell(novelty_queries="circadian engineered bacteria"))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("novelty_queries", "WRONG_TYPE")


def test_commit_novelty_queries单条长2_TOO_SHORT(commit):
    """边界：单条 "ab" 长度 2 < 3，拒绝，code=TOO_SHORT。"""
    r = commit(good_cell(novelty_queries=["ab"]))
    r.assert_rejected("commit", 2, gate="required_fields")
    assert r.has("novelty_queries", "TOO_SHORT") or r.has("novelty_queries[0]", "TOO_SHORT"), \
        r.json["errors"]


def test_commit_novelty_queries单条长3_放行(commit):
    """边界含等号：单条恰好 3 个字符放行（method=angle 下限 1 条）。"""
    commit(good_cell(method="angle", novelty_queries=["abc"])).assert_ok("commit")


def test_commit_novelty_queries含占位条目_拒绝(commit):
    """两条里有一条是"待补"：拒绝，code=PLACEHOLDER。"""
    r = commit(good_cell(method="transfer",
                         novelty_queries=["circadian bacteria tumor", "待补"]))
    r.assert_rejected("commit", 2, gate="required_fields")
    assert "PLACEHOLDER" in (r.codes_of("novelty_queries") +
                             r.codes_of("novelty_queries[1]")), r.json["errors"]


def test_commit_novelty_queries条目非字符串_WRONG_TYPE(commit):
    """条目是数字：拒绝，code=WRONG_TYPE。"""
    r = commit(good_cell(novelty_queries=[123]))
    r.assert_rejected("commit", 2, gate="required_fields")
    assert "WRONG_TYPE" in (r.codes_of("novelty_queries") +
                            r.codes_of("novelty_queries[0]")), r.json["errors"]


# ================================================= closest_work 与 diff 条件规则

def test_commit_closest_work长4_放行(commit):
    """边界含等号：closest_work 恰好 4 字（如"未见先例"）放行。"""
    commit(good_cell(closest_work="未见先例", diff=None)).assert_ok("commit")


def test_commit_closest_work长3_TOO_SHORT(commit):
    """边界：closest_work 恰好 3 字，低于下限 4，拒绝。"""
    r = commit(good_cell(closest_work=zh(3)))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("closest_work", "TOO_SHORT")


def test_commit_closest_work为空_EMPTY(commit):
    """5.3 最后一行：closest_work 为空串时拒绝，field=closest_work，code=EMPTY。"""
    r = commit(good_cell(closest_work="", diff="这里写了十个字符以上的差异说明"))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("closest_work", "EMPTY")


def test_commit_缺closest_work_MISSING(commit):
    """缺 closest_work：拒绝，code=MISSING。"""
    r = commit(good_cell(closest_work=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("closest_work", "MISSING")


@pytest.mark.parametrize("cw", ["未见先例", "无直接先例", "未检索到直接工作",
                                "检索未见直接先例，但这不等于绝对没有",
                                "PubMed 与 Google Scholar 0命中",
                                "该组合无命中", "未找到先例",
                                "无先例可循", "未检索到相关报道"])
def test_commit_无先例声明时diff可缺省_放行(commit, cw):
    """1.5 条件规则：closest_work 含无先例子串时，diff 缺省一律放行。"""
    commit(good_cell(closest_work=cw, diff=None)).assert_ok("commit")


@pytest.mark.parametrize("dv", ["—", "", "   ", "无", "N/A", "待补"])
def test_commit_无先例声明时diff占位也放行(commit, dv):
    """1.5：无先例声明下 diff 写 '—'/空/占位都放行，不做任何 diff 校验。"""
    commit(good_cell(closest_work="未检索到直接工作", diff=dv)).assert_ok("commit")


def test_commit_有先例缺diff_MISSING(commit):
    """closest_work 是具体 PMID 时 diff 必填：缺省则拒绝，code=MISSING。"""
    r = commit(good_cell(closest_work="PMID 40476548（Nano Lett 2025，厌氧菌瘤内富集）",
                         diff=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("diff", "MISSING")


def test_commit_有先例diff为占位词无_PLACEHOLDER(commit):
    """closest_work 有具体先例而 diff 写"无"：拒绝，code=PLACEHOLDER。"""
    r = commit(good_cell(closest_work="PMID 40476548（Nano Lett 2025）", diff="无"))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("diff", "PLACEHOLDER")


def test_commit_有先例diff为JSON_null_拒绝(commit):
    """真实敷衍形态：closest_work 有 PMID 而 diff 显式写成 null，必须拒绝（0.6：null 算 EMPTY）。"""
    cell = good_cell(closest_work="PMID 40476548（Nano Lett 2025）")
    cell["diff"] = None  # 显式 JSON null，区别于"删除该键"
    r = commit(cell)
    r.assert_rejected("commit", 2, gate="required_fields")
    assert set(r.codes_of("diff")) & set(["EMPTY", "MISSING"]), r.json["errors"]


def test_commit_必填字段为JSON_null_判为EMPTY(commit):
    """0.6 明确：字段值为 null 归入 EMPTY（不是 MISSING）。用 falsification 验证。"""
    cell = good_cell()
    cell["falsification"] = None
    r = commit(cell)
    r.assert_rejected("commit", 2, gate="required_fields")
    assert set(r.codes_of("falsification")) & set(["EMPTY", "MISSING"]), r.json["errors"]


def test_commit_有先例diff长9_TOO_SHORT(commit):
    """边界：diff 恰好 9 字符，低于下限 10，拒绝。"""
    r = commit(good_cell(closest_work="PMID 40476548（Nano Lett 2025）", diff=zh(9)))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("diff", "TOO_SHORT")


def test_commit_有先例diff长10_放行(commit):
    """边界含等号：diff 恰好 10 字符放行。"""
    commit(good_cell(closest_work="PMID 40476548（Nano Lett 2025）",
                     diff=zh(10))).assert_ok("commit")


def test_commit_反例_closest_work含未字但非无先例声明_diff仍必填(commit):
    """防漏放：closest_work='未来工作展望里提到过类似思路' 不含无先例子串，diff 仍必填。"""
    r = commit(good_cell(closest_work="未来工作展望里提到过类似思路的一句话", diff=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("diff", "MISSING")


# ================================================= 自由文本字段（防过严）

@pytest.mark.parametrize("v", ["中-高", "中高", "高", "甜区（创新中-高×可行高）",
                               "高但无意义", "中(偏高)", "未见先例", "低-中"])
def test_commit_novelty自由文本_一律放行(commit, v):
    """反例防误杀：novelty 是自由文本，不校验取值集合。"""
    commit(good_cell(novelty=v)).assert_ok("commit")


@pytest.mark.parametrize("v", ["高", "中-高", "三年内可做完但要两台设备", "中"])
def test_commit_feasibility自由文本_一律放行(commit, v):
    """反例防误杀：feasibility 是自由文本，不校验取值集合。"""
    commit(good_cell(feasibility=v)).assert_ok("commit")


@pytest.mark.parametrize("v", ["甜区（创新中-高×可行高）", "高风险高回报", "鸡肋区", "甜区"])
def test_commit_quadrant自由文本_一律放行(commit, v):
    """反例防误杀：quadrant 是自由文本，不校验取值集合。"""
    commit(good_cell(quadrant=v)).assert_ok("commit")


@pytest.mark.parametrize("field", ["novelty", "feasibility", "quadrant", "platform", "disease"])
def test_commit_自由文本字段为占位符_仍拒绝(commit, field):
    """自由文本字段虽不校验取值，但占位词必须拒绝（5.2 的 quadrant='—' 场景）。"""
    r = commit(good_cell(**{field: "—"}))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error(field, "PLACEHOLDER")


@pytest.mark.parametrize("field", ["novelty", "feasibility", "quadrant", "platform", "disease"])
def test_commit_自由文本字段缺失_MISSING(commit, field):
    """五个只查非占位的字段缺失时都要报 MISSING。"""
    r = commit(good_cell(**{field: None}))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error(field, "MISSING")


@pytest.mark.parametrize("field", ["novelty", "feasibility", "quadrant", "platform", "disease"])
def test_commit_自由文本字段为空串_EMPTY(commit, field):
    """五个只查非占位的字段为空串时都要报 EMPTY。"""
    r = commit(good_cell(**{field: ""}))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error(field, "EMPTY")


def test_commit_单字platform_放行(commit):
    """反例防误杀：platform 只有 1 个字也应放行（该字段无最小长度要求）。"""
    commit(good_cell(platform="菌")).assert_ok("commit")


# ================================================= method / status 枚举

@pytest.mark.parametrize("m,nq", [("transfer", ["query one abc", "query two abc"]),
                                  ("combine", ["query one abc"]),
                                  ("angle", ["query one abc"])])
def test_commit_method三个合法枚举_放行(commit, m, nq):
    """method 三个合法值都应放行（transfer 配足 2 条查新式）。"""
    commit(good_cell(method=m, novelty_queries=nq)).assert_ok("commit")


@pytest.mark.parametrize("m", ["重组合 + 换角度", "迁移", "Transfer", "TRANSFER",
                               "transfer ", "combine/angle", "", "跨界迁移"])
def test_commit_method非法值_NOT_ALLOWED(commit, m):
    """schema2 的 method 必须精确是三个英文枚举之一，其余一律 NOT_ALLOWED。"""
    r = commit(good_cell(method=m))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("method", "NOT_ALLOWED")


def test_commit_缺method_MISSING(commit):
    """缺 method：拒绝，code=MISSING。"""
    r = commit(good_cell(method=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("method", "MISSING")


@pytest.mark.parametrize("s", ["untried", "done", "failed"])
def test_commit_status三个合法枚举_放行(commit, s):
    """status 三个合法值都应放行。"""
    commit(good_cell(status=s)).assert_ok("commit")


@pytest.mark.parametrize("s", ["未做", "Untried", "pending", "", "todo"])
def test_commit_status非法值_NOT_ALLOWED(commit, s):
    """status 不在枚举内：拒绝，code=NOT_ALLOWED。"""
    r = commit(good_cell(status=s))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("status", "NOT_ALLOWED")


def test_commit_缺status_MISSING(commit):
    """缺 status：拒绝，code=MISSING。"""
    r = commit(good_cell(status=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("status", "MISSING")


# ================================================= 错误聚合

def test_commit_多个错误一次性全部返回(commit):
    """5.2 末行：同时缺 falsification 和 diff 时必须一次返回两条 errors。"""
    r = commit(good_cell(falsification=None, diff=None,
                         closest_work="PMID 40476548（Nano Lett 2025）"))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("falsification", "MISSING")
    r.assert_error("diff", "MISSING")
    assert len(r.json["errors"]) >= 2


def test_commit_七个字段全缺_errors至少七条(commit):
    """错误收集不得在第一个错误处短路：7 个字段同时缺失应返回 ≥7 条 errors。"""
    r = commit(good_cell(idea=None, hypothesis=None, feasibility_layers=None,
                         falsification=None, novelty_queries=None,
                         closest_work=None, novelty=None))
    r.assert_rejected("commit", 2, gate="required_fields")
    for f in ["idea", "hypothesis", "feasibility_layers", "falsification",
              "novelty_queries", "closest_work", "novelty"]:
        r.assert_error(f, "MISSING")


def test_commit_空对象stdin_返回多条错误而非崩溃(commit):
    """极端输入：stdin 是空对象 {}，应按必填闸拒绝并返回多条 errors，不是未预期异常。"""
    r = commit({})
    r.assert_rejected("commit", 2)
    assert len(r.json["errors"]) >= 5, r.json["errors"]
