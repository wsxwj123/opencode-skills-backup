"""闸门 3（零积压）、闸门 4（存量分诊）、老数据兼容、寻址与写入安全。"""

import hashlib
import json
import os
import shutil
import stat

import pytest

from unit_helpers import (IB_MAP, LEGACY_SAMPLE, TODAY, good_cell, legacy_cell, read_map,
                      run, text_of, write_map)


def sha_of(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


# ---------------------------------------------------------------- 零积压闸


def test_gate_passes_on_empty_map(env):
    result = env.gate()
    assert result.code == 0 and result.body["undecided"] == 0 and result.body["total"] == 0


def test_gate_blocks_when_backlog_exists(env):
    write_map(env.map_path, [legacy_cell("待定"), legacy_cell("采纳")])
    result = env.gate()
    assert result.code == 2 and result.body["gate"] == "backlog"
    assert result.codes == ["BACKLOG_NOT_EMPTY"] and result.body["undecided"] == 1
    assert result.body["undecided_items"][0]["index"] == 0
    assert result.body["undecided_truncated"] is False


def test_gate_truncates_long_backlog_at_thirty(env):
    write_map(env.map_path, [legacy_cell("待定") for _ in range(35)])
    result = env.gate()
    assert result.body["undecided"] == 35
    assert len(result.body["undecided_items"]) == 30
    assert result.body["undecided_truncated"] is True


@pytest.mark.parametrize("verdict,undecided", [
    ("待定", True), ("待柚子确认", True), ("pending", True), ("PENDING", True),
    ("待定：拟作 2027 青基主线方案 A", True), ("搁置", True), ("TBD", True),
    ("—", True), ("无", True), ("", True), ("   ", True),
    ("不建议作主课题", False), ("已否决（2026-09-15）：套索肽+活菌组合打不过纯肽方案，不做", False),
    ("建议立即纳入工作流", False), ("定位为元件，不作主课题", False),
    ("采纳", False), ("归档", False),
])
def test_placeholder_blacklist_boundaries(env, verdict, undecided):
    write_map(env.map_path, [legacy_cell(verdict)])
    assert env.status().body["undecided"] == (1 if undecided else 0)


def test_missing_verdict_key_counts_as_undecided(env):
    cell = legacy_cell()
    cell.pop("user_verdict")
    write_map(env.map_path, [cell])
    assert env.status().body["undecided"] == 1


def test_gate_ignores_new_required_fields(env):
    """老格子缺 hypothesis/falsification，补齐裁决后 gate 就该放行。"""
    write_map(env.map_path, [legacy_cell("采纳"), legacy_cell("归档")])
    assert env.gate().code == 0


# ---------------------------------------------------------------- status


def test_status_counts_and_backup_note(env):
    write_map(env.map_path, [legacy_cell("待定"), dict(good_cell(), schema=2,
                                                       user_verdict="归档", archived=True)])
    result = env.status()
    assert result.code == 0
    assert (result.body["total"], result.body["schema1"], result.body["schema2"]) == (2, 1, 1)
    assert (result.body["decided"], result.body["undecided"], result.body["archived"]) == (1, 1, 1)
    assert result.body["undecided_items"][0]["idea_prefix"] == legacy_cell()["idea"][:12]
    assert "手动" in result.body["backups"]["note"]


# ---------------------------------------------------------------- verdict


def test_verdict_updates_only_four_keys(env):
    original = legacy_cell("待定")
    original["intervention_2026-09-12"] = "老数据里的非常规键，必须原样留着"
    write_map(env.map_path, [original])
    result = env.verdict([{"index": 0, "expect": original["idea"][:10], "user_verdict": "归档",
                           "restart_condition": text_of(20)}])
    assert result.code == 0
    assert result.body["updated"] == 1 and result.body["by_verdict"] == {"归档": 1}
    assert (result.body["undecided_before"], result.body["undecided_after"]) == (1, 0)
    assert result.body["cells_before"] == result.body["cells_after"] == 1
    cell = read_map(env.map_path)["cells"][0]
    changed = {k for k in set(cell) | set(original) if cell.get(k) != original.get(k)}
    assert changed == {"user_verdict", "restart_condition", "archived", "verdict_date"}
    assert cell["archived"] is True and cell["verdict_date"] == TODAY
    assert cell["intervention_2026-09-12"] == original["intervention_2026-09-12"]


def test_verdict_does_not_add_archived_key_when_absent(env):
    write_map(env.map_path, [legacy_cell("待定")])
    env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10], "user_verdict": "采纳"}])
    assert "archived" not in read_map(env.map_path)["cells"][0]


def test_verdict_clears_archived_flag_when_it_exists(env):
    cell = dict(legacy_cell("待定"), archived=True)
    write_map(env.map_path, [cell])
    env.verdict([{"index": 0, "expect": cell["idea"][:10], "user_verdict": "采纳"}])
    assert read_map(env.map_path)["cells"][0]["archived"] is False


def test_verdict_never_moves_cells_or_touches_rejected_array(env):
    write_map(env.map_path, [legacy_cell("待定")])
    before = read_map(env.map_path)["rejected_or_downgraded"]
    env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10], "user_verdict": "否决"}])
    after = read_map(env.map_path)
    assert after["rejected_or_downgraded"] == before and len(after["cells"]) == 1


def test_verdict_overwrite_protection(env):
    write_map(env.map_path, [legacy_cell("不建议作主课题")])
    payload = [{"index": 0, "expect": legacy_cell()["idea"][:10], "user_verdict": "否决"}]
    blocked = env.verdict(payload)
    assert blocked.code == 2 and blocked.codes == ["ALREADY_DECIDED"]
    assert read_map(env.map_path)["cells"][0]["user_verdict"] == "不建议作主课题"
    allowed = env.verdict(payload, extra=["--allow-overwrite"])
    assert allowed.code == 0
    assert read_map(env.map_path)["cells"][0]["user_verdict"] == "否决"


def test_verdict_rejects_non_final_values(env):
    write_map(env.map_path, [legacy_cell("待定")])
    result = env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10],
                           "user_verdict": "待柚子确认"}])
    assert result.code == 2 and result.body["gate"] == "verdict"
    assert result.error_for("[0].user_verdict")["code"] == "NOT_ALLOWED"


def test_verdict_archive_requires_restart_condition(env):
    write_map(env.map_path, [legacy_cell("待定")])
    result = env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10],
                           "user_verdict": "归档"}])
    assert result.error_for("[0].restart_condition")["code"] == "MISSING"


def test_verdict_empty_array_is_input_error(env):
    write_map(env.map_path, [legacy_cell("待定")])
    result = env.verdict([])
    assert result.code == 3 and result.codes == ["EMPTY"]


# ---------------------------------------------------------------- 寻址


def test_index_out_of_range(env):
    write_map(env.map_path, [legacy_cell("待定")])
    result = env.verdict([{"index": 999, "expect": "随便一个够长的前缀", "user_verdict": "采纳"}])
    assert result.code == 2 and result.body["gate"] == "addressing"
    assert result.error_for("[0].index")["code"] == "INDEX_OUT_OF_RANGE"
    assert read_map(env.map_path)["cells"][0]["user_verdict"] == "待定"


def test_negative_index_rejected(env):
    write_map(env.map_path, [legacy_cell("待定")])
    result = env.verdict([{"index": -1, "expect": legacy_cell()["idea"][:10],
                           "user_verdict": "采纳"}])
    assert result.codes == ["INDEX_OUT_OF_RANGE"]


def test_prefix_mismatch_reports_actual(env):
    write_map(env.map_path, [legacy_cell("待定")])
    result = env.verdict([{"index": 0, "expect": "完全对不上的另一个想法", "user_verdict": "采纳"}])
    assert result.codes == ["PREFIX_MISMATCH"]
    assert result.body["errors"][0]["actual_prefix"] == legacy_cell()["idea"][:12]


def test_short_expect_rejected(env):
    write_map(env.map_path, [legacy_cell("待定")])
    result = env.verdict([{"index": 0, "expect": "太短", "user_verdict": "采纳"}])
    assert result.codes == ["TOO_SHORT"]


def test_one_bad_row_rejects_whole_batch(env):
    cells = [legacy_cell("待定", idea="第%d个够长的老想法，用来测批量分诊的全有或全无语义" % i)
             for i in range(50)]
    write_map(env.map_path, cells)
    before = sha_of(env.map_path)
    batch = [{"index": i, "expect": cells[i]["idea"][:10], "user_verdict": "否决"}
             for i in range(50)]
    batch[37]["expect"] = "这个前缀是错的绝对对不上"
    result = env.verdict(batch)
    assert result.code == 2 and "updated" not in result.body
    assert sha_of(env.map_path) == before
    assert env.backup_count() == 0  # 校验没过就没进写入流程，连备份都不该产生


def test_duplicate_index_rejected(env):
    write_map(env.map_path, [legacy_cell("待定")])
    row = {"index": 0, "expect": legacy_cell()["idea"][:10], "user_verdict": "采纳"}
    result = env.verdict([row, dict(row)])
    assert result.code == 2 and result.codes == ["NOT_ALLOWED"]
    assert result.fields == ["[1].index"]


# ---------------------------------------------------------------- 老数据兼容


def test_legacy_sample_survives_every_command(env):
    """真实老格子抽样：缺一堆新必填字段，任何子命令都不许因此报错。"""
    shutil.copy2(LEGACY_SAMPLE, env.map_path)
    sample = read_map(env.map_path)["cells"]
    status = env.status()
    assert status.code == 0
    assert status.body["schema2"] == 0 and status.body["schema1"] == len(sample)
    assert status.body["undecided"] + status.body["decided"] == len(sample)
    assert env.gate().code == 2  # 样本里有占位裁决

    undecided = [item["index"] for item in status.body["undecided_items"]]
    batch = [{"index": i, "expect": sample[i]["idea"][:8], "user_verdict": "归档",
              "restart_condition": "若后续拿到体内定量证据并排除安全性顾虑，则重新评估"}
             for i in undecided]
    result = env.verdict(batch)
    assert result.code == 0, result.body
    assert result.body["undecided_after"] == 0
    assert result.body["cells_after"] == len(sample)
    assert env.gate().code == 0

    after = read_map(env.map_path)["cells"]
    for index in undecided:
        untouched = {k for k in sample[index]
                     if k not in ("user_verdict", "restart_condition", "archived", "verdict_date")}
        assert all(after[index][k] == sample[index][k] for k in untouched)


# ---------------------------------------------------------------- 写入安全


def test_backup_is_byte_identical_and_never_deleted(env):
    write_map(env.map_path, [legacy_cell("待定") for _ in range(5)])
    for i in range(5):
        before = open(env.map_path, "rb").read()
        result = env.verdict([{"index": i, "expect": legacy_cell()["idea"][:10],
                               "user_verdict": "采纳"}])
        assert result.code == 0
        assert os.path.isfile(result.body["backup"])
        assert open(result.body["backup"], "rb").read() == before
    names = sorted(os.listdir(env.backup_dir))
    assert len(names) == 5, names  # 脚本永不删备份
    import re
    assert all(re.match(r"^migration_map\.\d{8}-\d{6}\.json$", n) for n in names)


def test_broken_map_is_never_rebuilt(env):
    with open(env.map_path, "w", encoding="utf-8") as handle:
        handle.write("{ broken")
    for result in (env.status(), env.gate()):
        assert result.code == 4 and result.codes == ["BAD_JSON"]
    assert open(env.map_path, encoding="utf-8").read() == "{ broken"


def test_missing_map_is_not_created(env):
    os.remove(env.map_path)
    result = env.status()
    assert result.code == 4 and result.codes == ["IO_FAILED"]
    assert not os.path.exists(env.map_path)


def test_readonly_backup_dir_aborts_write(env):
    write_map(env.map_path, [legacy_cell("待定")])
    before = sha_of(env.map_path)
    os.makedirs(env.backup_dir)
    os.chmod(env.backup_dir, stat.S_IRUSR | stat.S_IXUSR)
    try:
        result = env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10],
                               "user_verdict": "采纳"}])
        assert result.code == 4 and result.codes == ["IO_FAILED"]
        assert sha_of(env.map_path) == before
    finally:
        os.chmod(env.backup_dir, stat.S_IRWXU)
    assert not [n for n in os.listdir(str(env.root)) if ".tmp-" in n]


def test_no_temp_file_left_behind(env):
    write_map(env.map_path, [legacy_cell("待定")])
    env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10], "user_verdict": "采纳"}])
    env.verdict([{"index": 9, "expect": "越界的请求", "user_verdict": "采纳"}])
    assert not [n for n in os.listdir(str(env.root)) if ".tmp-" in n]


def test_integrity_bootstrap_then_detects_external_edit(env):
    write_map(env.map_path, [legacy_cell("待定")])
    assert env.status().body["integrity"] == {"checked": False, "external_edit_suspected": False}
    env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10], "user_verdict": "采纳"}])
    assert env.status().body["integrity"] == {"checked": True, "external_edit_suspected": False}

    data = read_map(env.map_path)
    data["cells"][0]["idea"] = "绕过脚本用编辑器直接改的内容"
    with open(env.map_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    result = env.status()
    assert result.code == 0  # 事后发现，不阻断
    assert result.body["integrity"] == {"checked": True, "external_edit_suspected": True}
    assert "疑似" in result.stderr


def test_map_argument_never_falls_back_to_default(env):
    """全部子命令都必须真正用 --map，绝不能碰用户的真实地图。"""
    real = os.path.expanduser("~/.idea-bomb/migration_map.json")
    before = sha_of(real) if os.path.exists(real) else None
    write_map(env.map_path, [legacy_cell("待定")])
    env.status(); env.gate()
    env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10], "user_verdict": "采纳"}])
    env.register(["一个足够长的种子文本"])
    env.commit(good_cell())
    if before is not None:
        assert sha_of(real) == before
