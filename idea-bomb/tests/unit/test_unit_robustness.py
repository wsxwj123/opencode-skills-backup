"""第二轮修复的回归测试：并发、非标准 JSON、日期后门、原子写、结构损坏、符号链接。

每条都对应一个先复现再修掉的真实缺陷，别删。
"""

import json
import os
import subprocess
import sys

import pytest

from unit_helpers import (IB_MAP, IB_SEED, SCRIPTS, TODAY, legacy_cell, read_map, run,
                          text_of, write_map)

sys.path.insert(0, SCRIPTS)
import ib_common as ib  # noqa: E402


def sha_of(path):
    import hashlib
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


# ---------------------------------------------------------------- 并发


def test_concurrent_verdicts_do_not_lose_updates(env):
    """无锁的 read-modify-write 会让后完成的进程拿旧快照整体覆盖，两边都报 ok。

    地图要够大（这里约 650KB，用户真实的是 185KB），否则读写窗口太窄，
    无锁版本也可能侥幸跑绿——用无锁副本验证过，这个体量下必现丢失。
    """
    cells = [legacy_cell("待定", idea="第%d个够长的老想法用来测并发写入不丢失更新" % i)
             for i in range(6)]
    padding = [dict(legacy_cell("采纳"), note=text_of(600)) for _ in range(300)]
    write_map(env.map_path, cells + padding)

    procs = []
    for i in range(6):
        payload = json.dumps([{"index": i, "expect": cells[i]["idea"][:10],
                               "user_verdict": "采纳"}], ensure_ascii=False)
        procs.append(subprocess.Popen(
            [sys.executable, IB_MAP, "verdict", "--map", env.map_path,
             "--backup-dir", env.backup_dir],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True))
        procs[-1].stdin.write(payload)
        procs[-1].stdin.close()
    outs = [(p.wait(), p.stdout.read()) for p in procs]

    after = read_map(env.map_path)["cells"]
    landed = [i for i in range(6) if after[i]["user_verdict"] == "采纳"]
    claimed = [code for code, _ in outs if code == 0]
    # 自报成功的次数必须等于真正落盘的次数——静默丢失就是这两个数对不上
    assert len(landed) == len(claimed), "自报成功 %d 次，实际落盘 %d 格" % (len(claimed), len(landed))
    assert len(landed) == 6, "6 个并发写入应该全部串行化成功，实际 %s" % landed
    assert len(after) == 306


def test_lock_file_is_not_the_map_itself(env):
    write_map(env.map_path, [legacy_cell("待定")])
    env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10], "user_verdict": "采纳"}])
    assert os.path.exists(env.map_path + ".lock")
    assert read_map(env.map_path)["cells"][0]["user_verdict"] == "采纳"


# ---------------------------------------------------------------- 非标准 JSON


def test_nan_in_stdin_is_rejected(env):
    from unit_helpers import good_cell
    write_map(env.map_path, [])
    env.register(["一个足够长的种子文本用来测试"])
    payload = json.dumps(good_cell(), ensure_ascii=False).replace(
        '"novelty": "中-高"', '"novelty": "中-高", "score": NaN')
    result = run(IB_MAP, "commit", "--map", env.map_path, "--backup-dir", env.backup_dir,
                 "--session-dir", env.session_dir, "--seed-id", "S1", "--today", TODAY,
                 stdin=payload)
    assert result.code == 3 and result.codes == ["BAD_JSON"]
    assert read_map(env.map_path)["cells"] == []


def test_nan_in_map_file_is_rejected_not_silently_read(env):
    with open(env.map_path, "w", encoding="utf-8") as handle:
        handle.write('{"version":1,"cells":[{"idea":"x","score":NaN}],'
                     '"rejected_or_downgraded":[]}')
    result = env.status()
    assert result.code == 4 and result.codes == ["BAD_JSON"]


def test_strict_json_loads_rejects_all_three_constants():
    for literal in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError):
            ib.strict_json_loads('{"v": %s}' % literal)
    assert ib.strict_json_loads('{"v": 1.5}') == {"v": 1.5}


# ---------------------------------------------------------------- --today 后门


def test_today_injection_only_works_outside_default_paths():
    """--today 是测试注入口，对真实数据动手时必须失效，否则改个日期就重置日上限。"""
    from datetime import date
    system_today = date.today().isoformat()
    assert ib.resolve_today("2027-01-01", "list", sandboxed=True) == "2027-01-01"
    assert ib.resolve_today("2027-01-01", "list", sandboxed=False) == system_today
    assert ib.resolve_today(None, "list", sandboxed=True) == system_today


def test_path_is_overridden_resolves_symlinks_and_dots(tmp_path):
    default = str(tmp_path / "data" / "map.json")
    os.makedirs(os.path.dirname(default))
    assert ib.path_is_overridden(str(tmp_path / "other.json"), default)
    assert not ib.path_is_overridden(str(tmp_path / "data" / ".." / "data" / "map.json"), default)


def test_seed_cap_survives_date_injection_in_default_mode(env):
    """沙箱内 --today 仍要能注入，否则验收测试没法构造跨日场景。"""
    env.register(["这是一个够长的种子文本 %d" % i for i in range(8)])
    blocked = env.register(["第九个种子应该被数量闸拦下来"])
    assert blocked.codes == ["CAP_EXCEEDED"]
    tomorrow = env.register(["换到第二天就该放行了吧"], today="2026-09-24")
    assert tomorrow.code == 0 and tomorrow.body["total_today"] == 1


# ---------------------------------------------------------------- 原子写


def test_session_file_is_not_truncated_on_failed_write(env):
    """open(path,"w") 会在打开瞬间清空原文件，写到一半崩就只剩半截，当天彻底停摆。"""
    env.register(["第一批种子文本够长了吧"])
    path = os.path.join(env.session_dir, "seeds-20260923.json")
    before = open(path, encoding="utf-8").read()

    os.chmod(env.session_dir, 0o500)  # 只读目录：临时文件建不出来
    try:
        result = env.register(["第二批种子写不进去才对"])
        assert result.code == 4 and result.codes == ["IO_FAILED"]
        assert open(path, encoding="utf-8").read() == before, "写失败不许动原文件"
    finally:
        os.chmod(env.session_dir, 0o700)
    assert env.seed("list", "--today", TODAY).body["total_today"] == 1
    assert not [n for n in os.listdir(env.session_dir) if ".tmp-" in n]


# ---------------------------------------------------------------- 结构损坏


@pytest.mark.parametrize("junk", [None, "裸字符串", 42, ["嵌套数组"]])
def test_broken_cell_element_reports_index_instead_of_crashing(env, junk):
    """status 是用来诊断手工编辑事故的，它自己崩了就什么都查不了。"""
    write_map(env.map_path, [legacy_cell("待定"), junk])
    for result in (env.status(), env.gate()):
        assert result.code == 4, "期望 4（数据异常），实得 %d" % result.code
        assert result.codes == ["BAD_JSON"]
        assert result.fields == ["cells[1]"]


def test_broken_cell_blocks_write_paths_too(env):
    write_map(env.map_path, [legacy_cell("待定"), None])
    before = sha_of(env.map_path)
    result = env.verdict([{"index": 0, "expect": legacy_cell()["idea"][:10],
                           "user_verdict": "采纳"}])
    assert result.code == 4 and sha_of(env.map_path) == before


# ---------------------------------------------------------------- 符号链接


def test_symlinked_map_stays_a_symlink(env, tmp_path):
    """用户可能把地图指向云盘里的真身，替换掉链接会让两边静默分叉。"""
    real = tmp_path / "cloud_real.json"
    write_map(str(real), [legacy_cell("待定")])
    link = tmp_path / "link_map.json"
    os.symlink(str(real), str(link))

    result = run(IB_MAP, "verdict", "--map", str(link), "--backup-dir", env.backup_dir,
                 stdin=json.dumps([{"index": 0, "expect": legacy_cell()["idea"][:10],
                                    "user_verdict": "采纳"}], ensure_ascii=False))
    assert result.code == 0
    assert os.path.islink(str(link)), "链接被实体文件顶掉了"
    assert read_map(str(real))["cells"][0]["user_verdict"] == "采纳"


# ---------------------------------------------------------------- 常量单一来源


def test_caps_have_a_single_source_of_truth():
    map_src = open(os.path.join(SCRIPTS, "ib_map.py"), encoding="utf-8").read()
    seed_src = open(os.path.join(SCRIPTS, "ib_seed.py"), encoding="utf-8").read()
    # 死常量会让人以为改了它就放宽了上限，实际另一个文件才生效
    assert "SEED_CAP_PER_DAY = 8" not in map_src
    assert "HYPOTHESIS_CAP_PER_DAY = 3" not in map_src
    assert "SEED_CAP_PER_DAY = 8" not in seed_src
    assert (ib.SEED_CAP_PER_DAY, ib.HYPOTHESIS_CAP_PER_DAY) == (8, 3)
