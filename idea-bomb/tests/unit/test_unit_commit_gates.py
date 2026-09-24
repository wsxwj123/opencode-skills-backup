"""闸门 1 下半 + 闸门 2 + 闸门 4：commit 的数量闸、必填字段闸、裁决终态闸。"""

import pytest

from unit_helpers import TODAY, good_cell, legacy_cell, read_map, text_of, write_map


@pytest.fixture
def ready(env):
    """种子已登记好的环境，省得每个用例重复登记。"""
    env.register(["把宿主免疫的昼夜相位当成隐藏变量", "用菌分裂稀释当瘤内活菌计时器",
                  "拿噬菌体展示做瘤内原位抗体成熟", "让菌群代谢物当剂量读出"])
    return env


# ---------------------------------------------------------------- 放行路径


def test_good_cell_passes_and_appends(ready):
    result = ready.commit(good_cell())
    assert result.code == 0, result.body
    assert (result.body["index"], result.body["cells_before"], result.body["cells_after"]) == (0, 0, 1)
    assert result.body["today_count"] == 1
    cell = read_map(ready.map_path)["cells"][0]
    assert cell["schema"] == 2 and cell["seed_id"] == "S1" and cell["date"] == TODAY
    assert "committed_at" in cell and "archived" not in cell


def test_controlled_fields_override_stdin(ready):
    """靠伪造 date 绕开日上限这条路必须堵死。"""
    result = ready.commit(good_cell(date="1999-01-01", schema=1, seed_id="伪造", archived=True))
    assert result.code == 0
    cell = read_map(ready.map_path)["cells"][0]
    assert cell["date"] == TODAY and cell["schema"] == 2 and cell["seed_id"] == "S1"
    assert "archived" not in cell  # 采纳不该留 archived 键


def test_commit_only_appends_never_rewrites_old_cells(ready):
    old = [legacy_cell("采纳"), legacy_cell("否决", idea="把蛋白酶从降解ECM改成只切特定连接")]
    write_map(ready.map_path, old)
    before = read_map(ready.map_path)["cells"]
    assert ready.commit(good_cell()).code == 0
    after = read_map(ready.map_path)["cells"]
    assert after[:2] == before and len(after) == 3


# ---------------------------------------------------------------- 数量闸


def test_old_schema1_cells_do_not_count_toward_daily_cap(ready):
    """47 个同日老格子不是 schema2，不该占今天的配额。"""
    write_map(ready.map_path, [dict(legacy_cell("采纳"), date=TODAY) for _ in range(47)])
    result = ready.commit(good_cell())
    assert result.code == 0 and result.body["today_count"] == 1


def test_unknown_seed_and_reused_seed_rejected(ready):
    assert ready.commit(good_cell(), seed_id="S9").codes == ["UNKNOWN_SEED"]
    assert ready.commit(good_cell(), seed_id="S9").body["gate"] == "seed_link"
    assert ready.commit(good_cell()).code == 0
    again = ready.commit(good_cell(idea=text_of(35)))
    assert again.code == 2 and again.codes == ["SEED_ALREADY_USED"]


def test_missing_seed_id_is_input_error(env):
    from unit_helpers import IB_MAP, run
    import json as _json
    result = run(IB_MAP, "commit", *env.map_args(), "--session-dir", env.session_dir,
                 "--today", TODAY, stdin=_json.dumps(good_cell(), ensure_ascii=False))
    assert result.code == 3 and result.fields == ["--seed-id"] and result.codes == ["MISSING"]


# ---------------------------------------------------------------- 必填字段闸


@pytest.mark.parametrize("override,field,code", [
    ({"falsification": None}, "falsification", "MISSING"),
    ({"falsification": ""}, "falsification", "EMPTY"),
    ({"falsification": "   "}, "falsification", "EMPTY"),
    ({"falsification": "待补"}, "falsification", "PLACEHOLDER"),
    ({"falsification": text_of(29)}, "falsification", "TOO_SHORT"),
    ({"idea": text_of(29)}, "idea", "TOO_SHORT"),
    ({"hypothesis": "写成一段话了"}, "hypothesis", "WRONG_TYPE"),
    ({"feasibility_layers": ["机制", "实现", "立项"]}, "feasibility_layers", "WRONG_TYPE"),
    ({"quadrant": "—"}, "quadrant", "PLACEHOLDER"),
    ({"novelty": ""}, "novelty", "EMPTY"),
    ({"platform": None}, "platform", "MISSING"),
    ({"method": "重组合 + 换角度"}, "method", "NOT_ALLOWED"),
    ({"method": None}, "method", "MISSING"),
    ({"status": "待做"}, "status", "NOT_ALLOWED"),
    ({"novelty_queries": []}, "novelty_queries", "EMPTY"),
    ({"novelty_queries": "一条字符串"}, "novelty_queries", "WRONG_TYPE"),
])
def test_required_field_rejections(ready, override, field, code):
    result = ready.commit(good_cell(**override))
    assert result.code == 2 and result.body["gate"] == "required_fields"
    problem = result.error_for(field)
    assert problem is not None, result.body["errors"]
    assert problem["code"] == code
    assert read_map(ready.map_path)["cells"] == []


def test_falsification_exactly_30_passes(ready):
    assert ready.commit(good_cell(falsification=text_of(30))).code == 0


def test_hypothesis_missing_key_uses_dot_path(ready):
    broken = good_cell()["hypothesis"]
    broken.pop("gap")
    result = ready.commit(good_cell(hypothesis=broken))
    assert result.error_for("hypothesis.gap")["code"] == "MISSING"


def test_hypothesis_key_exactly_30_passes(ready):
    cell = good_cell()
    cell["hypothesis"]["gap"] = text_of(30)
    assert ready.commit(cell).code == 0


def test_hypothesis_extra_key_rejected(ready):
    cell = good_cell()
    cell["hypothesis"]["experiment"] = text_of(40)
    result = ready.commit(cell)
    assert result.error_for("hypothesis.experiment")["code"] == "NOT_ALLOWED"


def test_feasibility_layers_two_keys_too_few(ready):
    result = ready.commit(good_cell(feasibility_layers={"机制": text_of(20), "实现": text_of(20)}))
    assert result.error_for("feasibility_layers")["code"] == "TOO_FEW"


def test_feasibility_layers_free_key_names_pass(ready):
    layers = {"机制": text_of(15), "体系实现": text_of(15), "三年立项": text_of(15)}
    assert ready.commit(good_cell(feasibility_layers=layers)).code == 0


def test_feasibility_layers_empty_value_reports_that_key(ready):
    layers = {"机制": text_of(15), "体系实现": "", "三年立项": text_of(15)}
    result = ready.commit(good_cell(feasibility_layers=layers))
    assert result.error_for("feasibility_layers.体系实现")["code"] == "EMPTY"


def test_free_text_axes_are_not_enumerated(ready):
    assert ready.commit(good_cell(novelty="中-高", feasibility="中高",
                                  quadrant="甜区（创新中-高×可行高）")).code == 0


def test_transfer_needs_two_queries(ready):
    """跨界迁移必须用源领域原名再搜一遍，只给一条检索式不算做过查新。"""
    one = ready.commit(good_cell(method="transfer", novelty_queries=["circadian bacteria"]))
    assert one.error_for("novelty_queries")["code"] == "TOO_FEW"
    assert ready.commit(good_cell(method="transfer",
                                  novelty_queries=["circadian bacteria", "chronotherapy"])).code == 0


def test_angle_needs_only_one_query(ready):
    assert ready.commit(good_cell(method="angle", novelty_queries=["one query"])).code == 0


def test_short_query_item_rejected(ready):
    result = ready.commit(good_cell(method="angle", novelty_queries=["ab"]))
    assert result.error_for("novelty_queries[0]")["code"] == "TOO_SHORT"


def test_all_errors_returned_at_once(ready):
    result = ready.commit(good_cell(falsification=None, diff=None))
    assert {"falsification", "diff"} <= set(result.fields)


# ---------------------------------------------------------------- diff 条件规则


@pytest.mark.parametrize("closest,diff,expected", [
    ("未见先例", None, 0),
    ("未检索到直接工作", "—", 0),
    ("检索未见直接先例，但这不等于绝对没有", "", 0),
    ("无直接先例", None, 0),
    ("PMID 40476548（Nano Lett 2025）", None, 2),
    ("PMID 40476548（Nano Lett 2025）", "无", 2),
    ("PMID 40476548（Nano Lett 2025）", text_of(9), 2),
    ("PMID 40476548（Nano Lett 2025）", text_of(10), 0),
])
def test_diff_conditional_rule(ready, closest, diff, expected):
    result = ready.commit(good_cell(closest_work=closest, diff=diff))
    assert result.code == expected, result.body
    if expected == 2:
        assert result.error_for("diff") is not None


def test_empty_closest_work_reports_itself_not_diff(ready):
    result = ready.commit(good_cell(closest_work="", diff=text_of(20)))
    assert result.error_for("closest_work")["code"] == "EMPTY"
    assert result.error_for("diff") is None


# ---------------------------------------------------------------- 裁决终态闸


@pytest.mark.parametrize("verdict,code", [
    ("待定", "NOT_ALLOWED"),
    ("待柚子确认", "NOT_ALLOWED"),
    ("pending", "NOT_ALLOWED"),
    ("PENDING", "NOT_ALLOWED"),
    ("搁置", "NOT_ALLOWED"),
    ("", "NOT_ALLOWED"),
    ("   ", "NOT_ALLOWED"),
    ("采纳：作为 2027 青基主线", "NOT_ALLOWED"),
    (None, "MISSING"),
])
def test_non_final_verdicts_rejected(ready, verdict, code):
    result = ready.commit(good_cell(user_verdict=verdict))
    assert result.code == 2 and result.body["gate"] == "verdict"
    assert result.error_for("user_verdict")["code"] == code
    assert read_map(ready.map_path)["cells"] == []


@pytest.mark.parametrize("verdict", ["采纳", "否决"])
def test_final_verdicts_pass(ready, verdict):
    assert ready.commit(good_cell(user_verdict=verdict)).code == 0


def test_archive_needs_restart_condition(ready):
    missing = ready.commit(good_cell(user_verdict="归档"))
    assert missing.error_for("restart_condition")["code"] == "MISSING"
    short = ready.commit(good_cell(user_verdict="归档", restart_condition=text_of(9)))
    assert short.error_for("restart_condition")["code"] == "TOO_SHORT"
    placeholder = ready.commit(good_cell(user_verdict="归档", restart_condition="待定"))
    assert placeholder.error_for("restart_condition")["code"] == "PLACEHOLDER"
    ok = ready.commit(good_cell(user_verdict="归档", restart_condition=text_of(10)))
    assert ok.code == 0
    assert read_map(ready.map_path)["cells"][0]["archived"] is True


def test_bad_stdin_rejected(ready):
    from unit_helpers import IB_MAP, run
    result = run(IB_MAP, "commit", *ready.map_args(), "--seed-id", "S1",
                 "--session-dir", ready.session_dir, "--today", TODAY, stdin="[1,2]")
    assert result.code == 3 and result.codes == ["BAD_JSON"]
