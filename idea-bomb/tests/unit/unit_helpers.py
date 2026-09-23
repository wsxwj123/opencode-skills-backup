"""单元测试的共享工具：真实起子进程、真实读写临时文件，不用 mock。

铁规：全部测试只操作 tmp_path 下的副本，任何一条都不许碰
~/.idea-bomb/migration_map.json。所有调用都显式传 --map / --session-dir /
--backup-dir，脚本收到这三个参数后不得回退默认路径。
"""

import json
import os
import subprocess
import sys


SKILL_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
IB_MAP = os.path.join(SCRIPTS, "ib_map.py")
IB_SEED = os.path.join(SCRIPTS, "ib_seed.py")
FIXTURES = os.path.join(SKILL_DIR, "tests", "fixtures")
LEGACY_SAMPLE = os.path.join(FIXTURES, "legacy_sample.json")

TODAY = "2026-09-23"
YESTERDAY = "2026-09-22"


class Result:
    def __init__(self, completed):
        self.code = completed.returncode
        self.stderr = completed.stderr
        self.raw = completed.stdout
        try:
            self.body = json.loads(completed.stdout)
        except ValueError:
            raise AssertionError("stdout 不是单个 JSON 对象：%r" % completed.stdout)

    @property
    def codes(self):
        return [e["code"] for e in self.body.get("errors", [])]

    @property
    def fields(self):
        return [e["field"] for e in self.body.get("errors", [])]

    def error_for(self, field):
        for item in self.body.get("errors", []):
            if item["field"] == field:
                return item
        return None


def run(script, *args, stdin=None):
    completed = subprocess.run(
        [sys.executable, script] + [str(a) for a in args],
        input="" if stdin is None else stdin,
        capture_output=True, text=True,
    )
    result = Result(completed)
    # 契约 0.3：无论成功失败，响应体必带 ok / command；失败必带 gate 和非空 errors。
    assert "ok" in result.body and "command" in result.body
    if result.body["ok"] is False:
        assert result.body.get("gate"), "被拒时必须给出 gate"
        assert result.body.get("errors"), "被拒时 errors 至少一条"
        for item in result.body["errors"]:
            assert set(["field", "code", "msg"]) <= set(item)
    return result


def write_map(path, cells, extra=None):
    data = {"version": 1, "note": "测试用", "cells": cells,
            "rejected_or_downgraded": [{"idea": "历史否决项，脚本只读不写"}]}
    if extra:
        data.update(extra)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def read_map(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def legacy_cell(verdict="待定", idea="让厌氧工程菌从被动乏氧富集升级为主动梯度趋化定植肿瘤核心"):
    """一个典型 schema1 老格子：没有 schema 键，也没有任何新必填字段。"""
    return {"source_domain": "神经科学", "platform": "工程化细菌", "disease": "实体瘤",
            "idea": idea, "novelty": "高", "closest_work": "…", "feasibility": "中",
            "quadrant": "甜区", "status": "untried", "user_verdict": verdict,
            "date": "2026-07-08"}


def good_cell(**overrides):
    """一个刚好合格的 schema2 cell，各测试在它基础上改坏某一项。"""
    cell = {
        "idea": "把宿主免疫的昼夜相位当成工程菌瘤内治疗的隐藏变量，按相位择时给菌以对齐杀伤窗口",
        "hypothesis": {
            "background": "瘤内活菌治疗的疗效批次波动大，现有解释集中在菌株活性与乏氧程度，没人看给药时刻",
            "gap": "固有免疫细胞丰度有昼夜节律，但活菌剂量学默认给药时刻无关，这个假设从没被直接检验过",
            "design": "两个相位点给同批工程菌，比较瘤内定植量与清除速率，再用节律敲除鼠验证依赖性",
            "innovation": "把时间生物学的相位变量引入活菌治疗剂量学，给出零成本就能提升疗效的调度维度",
        },
        "feasibility_layers": {
            "机制": "中性粒细胞丰度的昼夜波动在小鼠里是公认现象，机理链条讲得通",
            "体系实现": "只改给药时刻，现有荷瘤模型与菌株都不动，成本几乎为零",
            "三年立项": "两个相位点的预实验两周内出结果，节律敲除鼠可外购",
        },
        "falsification": "承重变量是给药时刻的免疫细胞丰度差；若节律敲除鼠里两相位定植量差异消失，则证伪",
        "novelty_queries": ["circadian phase bacterial cancer therapy",
                            "chronotherapy neutrophil tumor colonization"],
        "closest_work": "PMID 38123456（Cell Rep 2024：昼夜节律影响 CAR-T 疗效）",
        "diff": "他们做的是 CAR-T 细胞疗法，本方案针对活菌定植与清除动力学，读出与机制链条都不同",
        "novelty": "中-高", "feasibility": "高", "quadrant": "甜区（创新中-高×可行高）",
        "platform": "工程化细菌", "disease": "实体瘤",
        "method": "transfer", "status": "untried", "user_verdict": "采纳",
    }
    for key, value in overrides.items():
        if value is None:
            cell.pop(key, None)
        else:
            cell[key] = value
    return cell


def text_of(length):
    """造一个指定 Unicode 长度、且不命中占位词的中文串。"""
    base = "承重变量拿掉后下游指标应回落基线否则假设不成立"
    return (base * (length // len(base) + 1))[:length]
