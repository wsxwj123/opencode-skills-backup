# -*- coding: utf-8 -*-
"""ib_seed.py：第一段种子登记（INTERFACE 2.x、5.1 数量闸）。"""
import json
import os

import pytest

from conftest import TODAY, YESTERDAY, read_json, zh


def _items(n, prefix="把宿主免疫昼夜相位当成工程菌治疗的隐藏变量"):
    return [{"text": "%s-%d" % (prefix, i + 1)} for i in range(n)]


# ================================================= register：放行路径

def test_register_单批两条_放行且返回递增seed_id(run_seed, session_dir):
    """正常登记两条种子：退出码 0，seed_id 为 S1/S2，total_today=2，cap=8。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=_items(2))
    d = r.assert_ok("register")
    assert d["date"] == TODAY
    assert [s["seed_id"] for s in d["registered"]] == ["S1", "S2"]
    assert d["total_today"] == 2
    assert d["cap"] == 8
    assert d["registered"][0]["text"] == _items(2)[0]["text"]


def test_register_恰好8条_放行(run_seed, session_dir):
    """边界：当天一批登记恰好 8 条命中上限但不超限，应放行。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=_items(8))
    d = r.assert_ok("register")
    assert d["total_today"] == 8
    assert [s["seed_id"] for s in d["registered"]][-1] == "S8"


def test_register_分两批5加3_累计8_均放行(run_seed, session_dir):
    """边界：5+3=8 恰好触顶，两批都放行，第二批 seed_id 从 S6 续号不重置。"""
    run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
             stdin_obj=_items(5)).assert_ok("register")
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=_items(3, "第二批种子把菌分裂稀释当瘤内活菌计时器"))
    d = r.assert_ok("register")
    assert [s["seed_id"] for s in d["registered"]] == ["S6", "S7", "S8"]
    assert d["total_today"] == 8


def test_register_追加不覆盖_先前种子仍在(run_seed, session_dir):
    """追加语义：第二次 register 不得清掉第一次的种子。"""
    run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
             stdin_obj=_items(3)).assert_ok("register")
    run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
             stdin_obj=_items(2, "另一条思路：用群体感应阈值当开关")).assert_ok("register")
    d = run_seed(["list", "--session-dir", session_dir, "--today", TODAY]).assert_ok("list")
    assert d["total_today"] == 5
    assert [s["seed_id"] for s in d["seeds"]] == ["S1", "S2", "S3", "S4", "S5"]


def test_register_text恰好8字符_放行(run_seed, session_dir):
    """边界：text 去空白后恰好 8 个码位，等于下限，应放行。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[{"text": zh(8)}])
    d = r.assert_ok("register")
    assert d["total_today"] == 1


def test_register_text带首尾空白但正文够长_放行(run_seed, session_dir):
    """strip 后长度达标的带空白输入应放行（计数前先 strip，不是整体长度）。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[{"text": "   " + zh(9) + "  \n"}])
    r.assert_ok("register")


def test_register_昨天已满8今天再登记_放行(run_seed, session_dir):
    """配额按日历日重置：昨天 8 个不影响今天。"""
    run_seed(["register", "--session-dir", session_dir, "--today", YESTERDAY],
             stdin_obj=_items(8)).assert_ok("register")
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=_items(1, "今天的新种子：让噬菌体当递送载体的时钟"))
    d = r.assert_ok("register")
    assert d["total_today"] == 1
    assert d["registered"][0]["seed_id"] == "S1", "新一天序号应从 S1 重新开始"
    assert d["date"] == TODAY


# ================================================= register：拒绝路径

def test_register_stdin非法JSON_退出码3(run_seed, session_dir):
    """stdin 不是合法 JSON：退出码 3，gate=input，code=BAD_JSON。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_raw="{ 这不是 json")
    r.assert_rejected("register", 3, gate="input")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]


def test_register_stdin是对象不是数组_退出码3(run_seed, session_dir):
    """stdin 是合法 JSON 但不是数组：仍按 BAD_JSON 拒绝（2.1 第 1 条）。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj={"text": "把宿主免疫昼夜相位当成隐藏变量"})
    r.assert_rejected("register", 3, gate="input")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]


def test_register_空数组_退出码3_EMPTY(run_seed, session_dir):
    """空数组：退出码 3，code=EMPTY，field='-'。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[])
    r.assert_rejected("register", 3, gate="input")
    r.assert_error("-", "EMPTY")


def test_register_元素缺text键_退出码3_MISSING(run_seed, session_dir):
    """第二个元素缺 text：退出码 3，field='[1].text'，code=MISSING。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[{"text": zh(12)}, {"idea": zh(12)}])
    r.assert_rejected("register", 3, gate="input")
    r.assert_error("[1].text", "MISSING")


def test_register_text非字符串_退出码3_WRONG_TYPE(run_seed, session_dir):
    """text 是数字：退出码 3，field='[0].text'，code=WRONG_TYPE。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[{"text": 12345}])
    r.assert_rejected("register", 3, gate="input")
    r.assert_error("[0].text", "WRONG_TYPE")


def test_register_元素不是对象_退出码3(run_seed, session_dir):
    """数组元素是字符串而非对象：退出码 3，gate=input。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=["把宿主免疫昼夜相位当成隐藏变量"])
    r.assert_rejected("register", 3, gate="input")
    assert r.json["errors"][0]["code"] in ("MISSING", "WRONG_TYPE")


@pytest.mark.parametrize("bad", ["", "   ", "\t\n ", "-", "—", "？", "无", "暂无",
                                 "N/A", "n/a", "null", "None", "TODO", "TBD",
                                 "待定", "待柚子确认：明天再说清楚这个想法", "搁置",
                                 "pending", "PENDING", "tbd", "todo：回头补"])
def test_register_text命中占位词_退出码2_PLACEHOLDER(run_seed, session_dir, bad):
    """占位文本（含"占位词+补充说明"形态）必须被拒：退出码 2，code=PLACEHOLDER。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[{"text": bad}])
    r.assert_rejected("register", 2, gate="input")
    assert r.has("[0].text", "PLACEHOLDER") or r.has("[0].text", "TOO_SHORT"), \
        "占位文本应报 PLACEHOLDER（过短时 TOO_SHORT 亦可接受）：%s" % r.json["errors"]


def test_register_text占位词开头且很长_仍判占位(run_seed, session_dir):
    """"待定：拟作 2027 青基主线方案 A" 这类长文本以占位词开头，必须判占位。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[{"text": "待定：拟作 2027 青基主线方案 A，等柚子拍板后再细化"}])
    r.assert_rejected("register", 2, gate="input")
    r.assert_error("[0].text", "PLACEHOLDER")


def test_register_text长7字符_退出码2_TOO_SHORT(run_seed, session_dir):
    """边界：strip 后 7 个码位，刚好低于下限 8，应拒绝。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=[{"text": zh(7)}])
    r.assert_rejected("register", 2, gate="input")
    r.assert_error("[0].text", "TOO_SHORT")


def test_register_一批9条_超上限拒绝(run_seed, session_dir):
    """一批 9 条超过 8：退出码 2，gate=seed_cap，CAP_EXCEEDED，带 already/incoming/cap。"""
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=_items(9))
    d = r.assert_rejected("register", 2, gate="seed_cap")
    r.assert_error("-", "CAP_EXCEEDED")
    assert d["already"] == 0
    assert d["incoming"] == 9
    assert d["cap"] == 8


def test_register_5加4超限_第二批一条都不写(run_seed, session_dir):
    """5+4=9 超限：第二批整批拒绝，且会话文件里仍然只有 5 个（一条都没写进去）。"""
    run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
             stdin_obj=_items(5)).assert_ok("register")
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=_items(4, "第二批：让菌群自毁开关绑定到宿主体温"))
    d = r.assert_rejected("register", 2, gate="seed_cap")
    assert d["already"] == 5 and d["incoming"] == 4 and d["cap"] == 8
    lst = run_seed(["list", "--session-dir", session_dir, "--today", TODAY]).assert_ok("list")
    assert lst["total_today"] == 5, "超限批次必须一条都不落盘"
    assert [s["seed_id"] for s in lst["seeds"]] == ["S1", "S2", "S3", "S4", "S5"]


def test_register_首条合法末条占位_整批不写(run_seed, session_dir):
    """遇第一类错误即整批拒绝：3 条里最后一条占位，前两条也不得写入。"""
    payload = _items(2) + [{"text": "待补"}]
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=payload)
    r.assert_rejected("register", 2, gate="input")
    lst = run_seed(["list", "--session-dir", session_dir, "--today", TODAY]).assert_ok("list")
    assert lst["total_today"] == 0, "整批拒绝时一条都不应落盘"


def test_register_校验顺序_格式错先于数量闸(run_seed, session_dir):
    """9 条且其中一条 text 非字符串：格式错（退出码 3）优先于数量闸（退出码 2）。"""
    payload = _items(9)
    payload[3]["text"] = None
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=payload)
    r.assert_rejected("register", 3, gate="input")


# ================================================= list

def test_list_当天无种子_退出码0且为空(run_seed, session_dir):
    """list 在当天无任何种子时仍退出码 0，seeds 为空数组，total_today=0。"""
    d = run_seed(["list", "--session-dir", session_dir, "--today", TODAY]).assert_ok("list")
    assert d["date"] == TODAY
    assert d["seeds"] == []
    assert d["total_today"] == 0
    assert d["cap"] == 8


def test_list_返回registered_at字段(run_seed, session_dir):
    """list 每条种子须含 seed_id/text/registered_at 三个键。"""
    run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
             stdin_obj=_items(1)).assert_ok("register")
    d = run_seed(["list", "--session-dir", session_dir, "--today", TODAY]).assert_ok("list")
    s = d["seeds"][0]
    assert set(["seed_id", "text", "registered_at"]).issubset(s.keys()), s
    assert isinstance(s["registered_at"], str) and s["registered_at"]


def test_list_只看当天_不串日期(run_seed, session_dir):
    """昨天的种子不得出现在今天的 list 里。"""
    run_seed(["register", "--session-dir", session_dir, "--today", YESTERDAY],
             stdin_obj=_items(3)).assert_ok("register")
    d = run_seed(["list", "--session-dir", session_dir, "--today", TODAY]).assert_ok("list")
    assert d["total_today"] == 0 and d["seeds"] == []


# ================================================= 会话文件本身

def test_会话文件路径为seeds日期json(run_seed, session_dir):
    """会话文件须落在 <session-dir>/seeds-YYYYMMDD.json，目录不存在时自动创建。"""
    assert not os.path.exists(str(session_dir))
    run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
             stdin_obj=_items(1)).assert_ok("register")
    expected = session_dir / ("seeds-%s.json" % TODAY.replace("-", ""))
    assert expected.exists(), "实际目录内容：%s" % os.listdir(str(session_dir))
    read_json(expected)  # 必须是合法 JSON


def test_会话文件损坏_退出码4且不被静默重建(run_seed, session_dir):
    """会话文件内容损坏：退出码 4，gate=storage，BAD_JSON，且文件内容原样保留。"""
    os.makedirs(str(session_dir))
    broken = session_dir / ("seeds-%s.json" % TODAY.replace("-", ""))
    broken.write_text("{ broken 这不是 json", encoding="utf-8")
    r = run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
                 stdin_obj=_items(1))
    r.assert_rejected("register", 4, gate="storage")
    assert "BAD_JSON" in [e["code"] for e in r.json["errors"]]
    assert broken.read_text(encoding="utf-8") == "{ broken 这不是 json", \
        "损坏的会话文件不得被静默重建覆盖（否则悄悄清零当天配额）"


def test_会话文件损坏时list同样退出码4(run_seed, session_dir):
    """只读的 list 遇到损坏会话文件同样报 4/storage/BAD_JSON，不得当成空。"""
    os.makedirs(str(session_dir))
    broken = session_dir / ("seeds-%s.json" % TODAY.replace("-", ""))
    broken.write_text("[ {", encoding="utf-8")
    r = run_seed(["list", "--session-dir", session_dir, "--today", TODAY])
    r.assert_rejected("list", 4, gate="storage")


def test_seed不碰迁移地图(run_seed, session_dir, mapfile, tmp_path):
    """ib_seed.py 完全不触碰迁移地图：register 前后 map 文件 sha256 不变。"""
    from conftest import legacy_cell, sha256_of
    m = mapfile([legacy_cell("让厌氧工程菌从被动乏氧富集升级为主动探测")])
    before = sha256_of(m)
    run_seed(["register", "--session-dir", session_dir, "--today", TODAY],
             stdin_obj=_items(2)).assert_ok("register")
    assert sha256_of(m) == before
