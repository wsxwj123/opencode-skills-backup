# -*- coding: utf-8 -*-
"""反例集：这些输入脚本**必须放行**，防止实现把占位判定写成"包含即命中"而误杀真实数据
（INTERFACE 0.7 反例段、1.3 自由文本段、1.5）。

这一组失败 = 实现过严，会把柚子的合法写法判成敷衍。
"""
import pytest

from conftest import TODAY, good_cell, legacy_cell, read_json, zh

IDEA_A = "让厌氧工程菌从被动乏氧富集升级为主动探测肿瘤代谢梯度的导航系统"

# 0.7 明确列出的反例 + 同类危险形态
NOT_PLACEHOLDER = [
    "不建议作主课题",
    "已否决（2026-09-15）：套索肽+活菌组合打不过纯肽方案，不做",
    "建议立即纳入工作流",
    "定位为元件，不作主课题",
    "未检索到直接工作",
    "未见先例",
    # 以下是"占位词作为子串出现在非开头"的危险形态，必须放行
    "重新待定义这个方向的边界条件",
    "这个方案暂无法一句话说清，但核心是节律对齐",
    "无创监测方案：用体表温度反推瘤内菌载量",
    "空间转录组显示定植区与乏氧区高度重叠",
    "Nonequilibrium 稳态下的菌群竞争模型",
    "NAD+ 代谢通路被忽略了",
    "我搁置不了这件事，必须现在就做",      # "搁置"不在开头
    "这一条的 todo 标记在句子中间，不该触发占位判定",   # "todo"不在开头
]

# 反面对照：以下取值**以占位词开头**，按 0.7 第 3 条必须判为占位（不是反例）
IS_PLACEHOLDER_PREFIX = [
    "搁置不了，必须现在做",          # 以"搁置"开头 → 占位
    "todo 这个词出现在句子中间",     # 以"todo"开头 → 占位
    "待定：拟作 2027 青基主线方案 A",
    "pending review by 柚子",
]


@pytest.fixture
def commit(run_map, mapfile, seeded, session_dir, backup_dir):
    def _do(cell, today=TODAY):
        m = mapfile([legacy_cell(IDEA_A, "采纳")])
        sid = seeded(1, today)[0]
        return run_map(["commit", "--seed-id", sid, "--map", m,
                        "--session-dir", session_dir, "--backup-dir", backup_dir,
                        "--today", today], stdin_obj=cell)
    return _do


# ================================================= 未裁决判定的反例

@pytest.mark.parametrize("v", NOT_PLACEHOLDER)
def test_反例_这些裁决值不得计入未裁决(run_map, mapfile, v):
    """防过严：这些真实裁决写法都不在占位词表内，必须算已裁决。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, v)])]).assert_ok("status")
    assert d["undecided"] == 0, "user_verdict=%r 被误判为未裁决" % v


@pytest.mark.parametrize("v", NOT_PLACEHOLDER)
def test_反例_这些裁决值应触发覆盖保护(run_map, mapfile, backup_dir, v):
    """反向确认同一判定：既然算已裁决，不带 --allow-overwrite 改它就该被拦。"""
    m = mapfile([legacy_cell(IDEA_A, v)])
    r = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=[{"index": 0, "expect": IDEA_A[:10], "user_verdict": "采纳"}])
    r.assert_rejected("verdict", 2, gate="verdict")
    assert "ALREADY_DECIDED" in [e["code"] for e in r.json["errors"]], \
        "user_verdict=%r 应被视为已裁决" % v


# ================================================= 必填字段里的占位反例

@pytest.mark.parametrize("v", NOT_PLACEHOLDER)
def test_反例_novelty字段这些取值必须放行(commit, v):
    """防过严：novelty 是自由文本，这些取值都不是占位，必须放行。"""
    commit(good_cell(novelty=v)).assert_ok("commit")


@pytest.mark.parametrize("v", ["未见先例", "未检索到直接工作", "无先例", "不建议作主课题"])
def test_反例_quadrant这些取值必须放行(commit, v):
    """防过严：以"未"/"无"/"不"开头的短文本不在占位词表内。"""
    commit(good_cell(quadrant=v)).assert_ok("commit")


def test_反例_falsification以未开头_放行(commit):
    """防过严："未能观测到……"以"未"开头但不是占位词，长度够就应放行。"""
    commit(good_cell(
        falsification="未能在四个相位点观测到瘤内活菌载量差异，即视为本假说被直接证伪"
    )).assert_ok("commit")


def test_反例_falsification以不开头_放行(commit):
    """防过严："不建议……"这类以"不"开头的文本不是占位。"""
    commit(good_cell(
        falsification="不出现相位依赖的生存期差异就算证伪，无需再追加任何解释性实验"
    )).assert_ok("commit")


def test_反例_idea含待字但非开头_放行(commit):
    """防过严：idea 中间出现"待"字（如"有待验证"）不得触发占位判定。"""
    commit(good_cell(
        idea="把宿主免疫昼夜相位当作治疗窗口的隐藏变量，其机制细节仍有待验证但不影响可测性"
    )).assert_ok("commit")


def test_反例_feasibility_layers值以未开头_放行(commit):
    """防过严：某一层写"未见安全性风险报道"应放行。"""
    commit(good_cell(feasibility_layers={
        "safety": "未见同类给药方案的安全性风险报道",
        "biology": "节律相位差异在小鼠模型中可重复观测",
        "measure": "活菌载量与浸润细胞数均有成熟测法"})).assert_ok("commit")


def test_反例_restart_condition以未开头_放行(commit):
    """防过严：归档的重启条件写"未来若出现……"应放行。"""
    commit(good_cell(user_verdict="归档",
                     restart_condition="未来若出现可在体无创读出瘤内菌载量的方法，重启本方向"
                     )).assert_ok("commit")


def test_反例_novelty_queries含无字_放行(commit):
    """防过严：查新式里出现"无先例"字样不影响其合法性。"""
    commit(good_cell(method="angle",
                     novelty_queries=["昼夜节律 工程菌 无先例 检索"])).assert_ok("commit")


# ================================================= diff 条件规则的反例

@pytest.mark.parametrize("cw", ["未检索到直接工作", "未见先例", "无直接先例",
                                "检索未见直接先例，但这不等于绝对没有",
                                "综合检索 0命中", "PubMed 无命中", "未找到先例"])
def test_反例_无先例声明下diff不填也放行(commit, cw):
    """1.5：closest_work 含无先例子串时 diff 完全不校验，缺省必须放行。"""
    commit(good_cell(closest_work=cw, diff=None)).assert_ok("commit")


def test_反例_closest_work长度只有4也放行(commit):
    """1.5 来历段："未见先例"只有 4 字，恰好等于下限，必须放行。"""
    r = commit(good_cell(closest_work="未见先例", diff=None))
    d = r.assert_ok("commit")
    assert d["cells_after"] == 2


def test_反例_closest_work无直接先例5字放行(commit):
    """"无直接先例"5 字，既满足长度也算无先例声明。"""
    commit(good_cell(closest_work="无直接先例", diff=None)).assert_ok("commit")


# ================================================= 结构上的反例

def test_反例_多余的顶层键不影响解析(run_map, mapfile, backup_dir):
    """防过严：地图里有脚本不认识的顶层键（如 changelog）时不得报错。"""
    import json
    p = mapfile([legacy_cell(IDEA_A, "待定")])
    doc = read_json(p)
    doc["changelog"] = [{"d": "2026-09-01", "what": "手工整理"}]
    with open(str(p), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    run_map(["status", "--map", p]).assert_ok("status")
    run_map(["verdict", "--map", p, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[{"index": 0, "expect": IDEA_A[:10], "user_verdict": "采纳"}]
            ).assert_ok("verdict")
    assert read_json(p)["changelog"] == [{"d": "2026-09-01", "what": "手工整理"}], \
        "未知顶层键必须原样保留"


def test_反例_idea含emoji与特殊字符不影响前缀比对(run_map, mapfile, backup_dir):
    """Unicode 边界：idea 含 emoji 时按码位取前缀，expect 比对不得出错。"""
    idea = "把宿主节律🕐当成隐藏变量，用×号标记的相位点做对照实验"
    m = mapfile([legacy_cell(idea, "待定")])
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=[{"index": 0, "expect": idea[:10], "user_verdict": "采纳"}]
            ).assert_ok("verdict")


def test_反例_超长字段不被截断(run_map, mapfile, seeded, session_dir, backup_dir):
    """边界：8000 字的 falsification 应原样落盘，不得被截断。"""
    long_text = zh(8000)
    m = mapfile([legacy_cell(IDEA_A, "采纳")])
    sid = seeded(1)[0]
    run_map(["commit", "--seed-id", sid, "--map", m, "--session-dir", session_dir,
             "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=good_cell(falsification=long_text)).assert_ok("commit")
    assert read_json(m)["cells"][-1]["falsification"] == long_text


def test_反例_大批量100条verdict一次成功(run_map, mapfile, backup_dir):
    """规模边界：一次 100 条裁决应正常完成，updated=100。"""
    cells = [legacy_cell(IDEA_A + "#%03d" % i, "待定") for i in range(100)]
    m = mapfile(cells)
    items = [{"index": i, "expect": (IDEA_A + "#%03d" % i)[:10], "user_verdict": "否决"}
             for i in range(100)]
    d = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=items).assert_ok("verdict")
    assert d["updated"] == 100 and d["by_verdict"]["否决"] == 100


# ================================================= 幂等与重复调用

def test_只读命令重复调用结果一致(run_map, mapfile):
    """幂等：status 连跑三次输出的统计字段完全一致。"""
    m = mapfile([legacy_cell(IDEA_A, "待定"), legacy_cell(IDEA_A + "b", "采纳")])
    keys = ["total", "schema1", "schema2", "decided", "undecided", "archived"]
    runs = [run_map(["status", "--map", m]).assert_ok("status") for _ in range(3)]
    for k in keys:
        assert runs[0][k] == runs[1][k] == runs[2][k], k


def test_同一批裁决重复提交_第二次被覆盖保护拦下(run_map, mapfile, backup_dir):
    """非幂等是有意的：同一批 verdict 重复提交，第二次应报 ALREADY_DECIDED。"""
    m = mapfile([legacy_cell(IDEA_A, "待定")])
    items = [{"index": 0, "expect": IDEA_A[:10], "user_verdict": "采纳"}]
    run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
            stdin_obj=items).assert_ok("verdict")
    r = run_map(["verdict", "--map", m, "--backup-dir", backup_dir, "--today", TODAY],
                stdin_obj=items)
    r.assert_rejected("verdict", 2, gate="verdict")
    assert "ALREADY_DECIDED" in [e["code"] for e in r.json["errors"]]


# ================================================= CLI 层（文档未规定，宽松断言）

@pytest.mark.parametrize("script_fixture,cmd", [("run_map", "nonexistent_cmd"),
                                                ("run_seed", "nonexistent_cmd")])
def test_未知子命令不得返回成功(request, script_fixture, cmd, mapfile):
    """CLI 兜底：未知子命令绝不能返回退出码 0（具体码与输出格式接口未规定）。"""
    run = request.getfixturevalue(script_fixture)
    r = run([cmd, "--map", mapfile([])] if script_fixture == "run_map" else [cmd])
    assert r.code != 0, "未知子命令返回了成功：%r" % r


@pytest.mark.parametrize("v", IS_PLACEHOLDER_PREFIX)
def test_占位词开头即判占位_不得放宽为完全相等(run_map, mapfile, v):
    """0.7 第 3 条是前缀匹配：以占位词开头的长文本必须计入 undecided。"""
    d = run_map(["status", "--map", mapfile([legacy_cell(IDEA_A, v)])]).assert_ok("status")
    assert d["undecided"] == 1, "user_verdict=%r 以占位词开头，应判为未裁决" % v


@pytest.mark.parametrize("v", IS_PLACEHOLDER_PREFIX)
def test_占位词开头的值不得作为novelty通过(commit, v):
    """同一前缀规则用在必填字段上：以占位词开头的 novelty 必须被拒。"""
    r = commit(good_cell(novelty=v))
    r.assert_rejected("commit", 2, gate="required_fields")
    r.assert_error("novelty", "PLACEHOLDER")
