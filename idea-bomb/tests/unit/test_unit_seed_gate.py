"""闸门 1 上半：第一段种子登记的日上限与输入校验。"""

import json
import os

from unit_helpers import TODAY, YESTERDAY


def texts(n, prefix="这是第"):
    return ["%s%d个用来测试的种子想法" % (prefix, i) for i in range(n)]


def test_register_eight_in_one_batch_passes(env):
    result = env.register(texts(8))
    assert result.code == 0
    assert result.body["total_today"] == 8
    assert result.body["cap"] == 8
    assert [s["seed_id"] for s in result.body["registered"]] == ["S%d" % i for i in range(1, 9)]


def test_register_five_then_three_passes_and_ids_keep_counting(env):
    assert env.register(texts(5)).code == 0
    second = env.register(texts(3, prefix="第二批第"))
    assert second.code == 0
    assert second.body["total_today"] == 8
    assert [s["seed_id"] for s in second.body["registered"]] == ["S6", "S7", "S8"]


def test_register_five_then_four_rejects_whole_batch(env):
    env.register(texts(5))
    result = env.register(texts(4, prefix="第二批第"))
    assert result.code == 2
    assert result.body["gate"] == "seed_cap"
    assert result.codes == ["CAP_EXCEEDED"]
    assert (result.body["already"], result.body["incoming"], result.body["cap"]) == (5, 4, 8)
    # 被拒的一批一条都不许落盘
    assert env.seed("list", "--today", TODAY).body["total_today"] == 5


def test_register_nine_in_one_batch_rejects(env):
    result = env.register(texts(9))
    assert result.code == 2 and result.codes == ["CAP_EXCEEDED"]
    assert env.seed("list", "--today", TODAY).body["total_today"] == 0


def test_register_empty_array_is_input_error(env):
    result = env.seed("register", "--today", TODAY, stdin="[]")
    assert result.code == 3
    assert result.body["gate"] == "input"
    assert result.codes == ["EMPTY"] and result.fields == ["-"]


def test_quota_resets_per_calendar_day(env):
    assert env.register(texts(8), today=YESTERDAY).code == 0
    assert env.register(texts(1), today=TODAY).code == 0
    assert env.seed("list", "--today", TODAY).body["total_today"] == 1


def test_register_rejects_bad_stdin(env):
    assert env.seed("register", "--today", TODAY, stdin="{ broken").code == 3
    result = env.seed("register", "--today", TODAY, stdin='{"text": "不是数组"}')
    assert result.code == 3 and result.codes == ["BAD_JSON"]


def test_register_reports_每条结构错(env):
    payload = json.dumps([{"text": "这是一个够长的正常种子"}, {"no_text": 1}, "裸字符串"],
                         ensure_ascii=False)
    result = env.seed("register", "--today", TODAY, stdin=payload)
    assert result.code == 3
    assert result.fields == ["[1].text", "[2]"]
    assert result.codes == ["MISSING", "WRONG_TYPE"]


def test_register_rejects_placeholder_and_short_text(env):
    payload = json.dumps([{"text": "待定"}, {"text": "太短了"}, {"text": "   "}],
                         ensure_ascii=False)
    result = env.seed("register", "--today", TODAY, stdin=payload)
    assert result.code == 2
    assert result.codes == ["PLACEHOLDER", "TOO_SHORT", "PLACEHOLDER"]


def test_list_on_empty_day_is_ok(env):
    result = env.seed("list", "--today", TODAY)
    assert result.code == 0
    assert result.body["seeds"] == [] and result.body["total_today"] == 0


def test_broken_session_file_is_not_silently_rebuilt(env):
    env.register(texts(3))
    path = os.path.join(env.session_dir, "seeds-20260923.json")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("{ 坏掉的 json")
    result = env.seed("list", "--today", TODAY)
    assert result.code == 4
    assert result.body["gate"] == "storage" and result.codes == ["BAD_JSON"]
    # 绝不静默重建：重建等于把当天已用掉的配额悄悄清零
    with open(path, "r", encoding="utf-8") as handle:
        assert handle.read() == "{ 坏掉的 json"


def test_session_file_never_touches_real_map(env):
    env.register(texts(2))
    assert os.path.exists(os.path.join(env.session_dir, "seeds-20260923.json"))
    assert os.listdir(env.session_dir) == ["seeds-20260923.json"]
