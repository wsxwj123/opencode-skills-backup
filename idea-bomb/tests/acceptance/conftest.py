# -*- coding: utf-8 -*-
"""idea-bomb 验收测试公共夹具。

黑盒：只依据 .devflow/INTERFACE.md 设计，不读实现代码。
硬性约束：不使用 mock，全部用 tmp_path 造真实 JSON 文件、跑真实脚本、读真实结果。
"""
import hashlib
import json
import os
import re
import subprocess
import sys

import pytest

# 默认指向真实技能目录；设 IDEA_BOMB_ROOT 可指向副本（用于变异测试/CI 沙箱）
SKILL_ROOT = os.environ.get("IDEA_BOMB_ROOT",
                            "/Users/wsxwj/.claude/skills/idea-bomb")
IB_MAP = os.path.join(SKILL_ROOT, "scripts", "ib_map.py")
IB_SEED = os.path.join(SKILL_ROOT, "scripts", "ib_seed.py")

TODAY = "2026-09-23"
YESTERDAY = "2026-09-22"


# ---------------------------------------------------------------- 运行器

class Result(object):
    """一次脚本调用的结果。code=退出码，json=stdout 解析出的对象。"""

    def __init__(self, code, out, err):
        self.code = code
        self.out = out
        self.err = err
        self.json = None
        self.json_error = None
        try:
            self.json = json.loads(out)
        except Exception as exc:  # stdout 不是合法 JSON 本身就是违约
            self.json_error = "%s / stdout=%r" % (exc, out[:400])

    def __repr__(self):
        return "Result(code=%s, out=%r, err=%r)" % (self.code, self.out[:400], self.err[:200])

    # --- 契约断言（0.3 / 0.4）---
    def assert_ok(self, command):
        """断言成功：退出码 0，ok=true，command 正确，无 gate/errors。"""
        assert self.code == 0, "期望退出码 0，实际 %s；stderr=%s" % (self.code, self.err)
        assert self.json is not None, "stdout 必须是 JSON：%s" % self.json_error
        assert self.json.get("ok") is True, self.json
        assert self.json.get("command") == command, self.json
        assert "gate" not in self.json, "成功响应不应带 gate：%s" % self.json
        assert "errors" not in self.json, "成功响应不应带 errors：%s" % self.json
        return self.json

    def assert_rejected(self, command, code, gate=None):
        """断言被拒：退出码等于 code，ok=false，gate/errors 结构合规（0.3）。"""
        assert self.code == code, "期望退出码 %s，实际 %s；stdout=%s stderr=%s" % (
            code, self.code, self.out[:600], self.err[:300])
        assert self.json is not None, "非 0 退出码 stdout 仍须是 JSON：%s" % self.json_error
        assert self.json.get("ok") is False, self.json
        assert self.json.get("command") == command, self.json
        assert isinstance(self.json.get("gate"), str) and self.json["gate"], \
            "ok=false 时 gate 必有且为字符串：%s" % self.json
        assert self.json["gate"] in GATES, "gate 取值须在 0.5 全表内：%s" % self.json["gate"]
        errs = self.json.get("errors")
        assert isinstance(errs, list) and len(errs) >= 1, "errors 至少一个元素：%s" % self.json
        for e in errs:
            assert set(["field", "code", "msg"]).issubset(e.keys()), "每个 error 必有三键：%s" % e
            assert e["code"] in CODES, "code 须在 0.6 全表内：%s" % e["code"]
        if gate is not None:
            assert self.json["gate"] == gate, "期望 gate=%s，实际 %s" % (gate, self.json["gate"])
        return self.json

    # --- errors 查询 ---
    def codes_of(self, field):
        return [e["code"] for e in self.json.get("errors", []) if e["field"] == field]

    def fields(self):
        return [e["field"] for e in self.json.get("errors", [])]

    def has(self, field, code):
        return any(e["field"] == field and e["code"] == code
                   for e in self.json.get("errors", []))

    def assert_error(self, field, code):
        assert self.has(field, code), \
            "期望 errors 含 {field=%r, code=%r}，实际 errors=%s" % (
                field, code, self.json.get("errors"))


GATES = {"backlog", "seed_cap", "hypothesis_cap", "required_fields", "verdict",
         "addressing", "seed_link", "input", "storage"}

CODES = {"MISSING", "EMPTY", "PLACEHOLDER", "TOO_SHORT", "WRONG_TYPE", "TOO_FEW",
         "NOT_ALLOWED", "CAP_EXCEEDED", "BACKLOG_NOT_EMPTY", "UNKNOWN_SEED",
         "SEED_ALREADY_USED", "INDEX_OUT_OF_RANGE", "PREFIX_MISMATCH",
         "ALREADY_DECIDED", "BAD_JSON", "IO_FAILED"}


def _run(script, args, stdin_obj=None, stdin_raw=None):
    payload = None
    if stdin_raw is not None:
        payload = stdin_raw
    elif stdin_obj is not None:
        payload = json.dumps(stdin_obj, ensure_ascii=False)
    proc = subprocess.run(
        [sys.executable, script] + [str(a) for a in args],
        input=payload, capture_output=True, text=True, timeout=120,
    )
    return Result(proc.returncode, proc.stdout, proc.stderr)


@pytest.fixture
def run_map():
    """跑 ib_map.py。run_map(['status', '--map', p]) 或 run_map([...], stdin_obj=...)。"""
    def _call(args, stdin_obj=None, stdin_raw=None):
        return _run(IB_MAP, args, stdin_obj, stdin_raw)
    return _call


@pytest.fixture
def run_seed():
    """跑 ib_seed.py。"""
    def _call(args, stdin_obj=None, stdin_raw=None):
        return _run(IB_SEED, args, stdin_obj, stdin_raw)
    return _call


# ---------------------------------------------------------------- 文本工具

_FILLER = ("本假说基于宿主免疫昼夜相位与工程菌瘤内定植动力学的耦合关系展开论证"
           "并给出可在体内直接观测的量化判据与反证条件供后续实验检验其真伪")


def zh(n):
    """生成恰好 n 个 Unicode 码位的中文文本，不含空白、不以任何占位词开头。"""
    assert n >= 1
    s = (_FILLER * (n // len(_FILLER) + 1))[:n]
    assert len(s) == n
    return s


def sha256_of(path):
    with open(str(path), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_json(path):
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, obj):
    with open(str(path), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


def tmp_leftovers(map_path):
    """返回 <map>.tmp-* 残留文件列表（4.2 要求任何退出码下都不得残留）。"""
    d = os.path.dirname(str(map_path))
    base = os.path.basename(str(map_path))
    return [f for f in os.listdir(d) if f.startswith(base + ".tmp-")]


BACKUP_NAME_RE = re.compile(r"^migration_map\.\d{8}-\d{6}\.json$")


# ---------------------------------------------------------------- 数据工厂

def good_cell(**over):
    """一个各字段都恰好合格的 schema2 cell（1.3）。传关键字覆盖单个字段。

    传 None 作为值表示"删除该键"，用于构造 MISSING 场景。
    """
    cell = {
        "idea": "把宿主免疫的昼夜相位当作工程菌治疗窗口的隐藏变量，用定时给药对齐炎症低谷",
        "hypothesis": {
            "background": "肿瘤微环境的免疫细胞浸润存在明确的昼夜节律波动，既往工程菌治疗普遍忽略给药时点",
            "gap": "现有瘤内活菌治疗研究只报告绝对剂量，没有任何一项把宿主节律相位作为独立变量纳入设计",
            "design": "以固定剂量在四个相位点给药，同步记录瘤内活菌载量与中性粒细胞浸润，比较相位间差异",
            "innovation": "首次把宿主节律相位从噪声项提升为可控的治疗参数，为同一菌株提供零成本的疗效增益",
        },
        "feasibility_layers": {
            "biology": "节律相位差异在小鼠模型中可重复观测",
            "delivery_signal": "现有菌株无需改造即可用于相位对照实验",
            "safety_executability": "剂量不变，安全性风险与既有方案持平",
        },
        "falsification": "若四个相位点的瘤内活菌载量与生存期差异均不显著，则该假说被直接证伪，不需要二次解释",
        "novelty_queries": ["circadian AND engineered bacteria AND tumor colonization"],
        "closest_work": "PMID 40476548（Nano Lett 2025，报告了厌氧菌瘤内富集但未涉及节律）",
        "diff": "该工作只做了乏氧富集，没有把给药时点作为变量，本方案的相位对照是其未覆盖的维度",
        "novelty": "中-高",
        "feasibility": "高",
        "quadrant": "甜区（创新中-高×可行高）",
        "platform": "工程菌",
        "disease": "实体瘤",
        "method": "angle",
        "status": "untried",
        "user_verdict": "采纳",
    }
    for k, v in over.items():
        if v is None and k in cell:
            del cell[k]
        else:
            cell[k] = v
    return cell


def legacy_cell(idea, user_verdict="待定", extra=None):
    """一个 schema1 老格子：没有 schema 键，缺 hypothesis/falsification/feasibility_layers。"""
    cell = {
        "idea": idea,
        "novelty": "中-高",
        "feasibility": "中",
        "quadrant": "甜区",
        "platform": "工程菌",
        "disease": "结直肠癌",
        "method": "重组合 + 换角度",
        "status": "untried",
        "date": "2026-07-08",
        "notes": "历史对话直接写入，未走脚本",
    }
    if user_verdict is not _NO_VERDICT:
        cell["user_verdict"] = user_verdict
    if extra:
        cell.update(extra)
    return cell


class _NoVerdict(object):
    def __repr__(self):
        return "<无 user_verdict 键>"


_NO_VERDICT = _NoVerdict()
NO_VERDICT = _NO_VERDICT


def map_doc(cells, rejected=None, integrity=None):
    """迁移地图文件整体结构（1.1）。"""
    doc = {
        "version": 1,
        "note": "柚子的课题迁移地图，脚本只读不写 version/note/rejected_or_downgraded",
        "cells": list(cells),
        "rejected_or_downgraded": rejected if rejected is not None else [
            {"idea": "旧的被否决想法", "reason": "打不过纯肽方案"}
        ],
    }
    if integrity is not None:
        doc["_integrity"] = integrity
    return doc


# ---------------------------------------------------------------- 路径夹具

@pytest.fixture
def mapfile(tmp_path):
    """返回一个工厂：make(cells, ...) -> map 文件路径（真实写盘）。"""
    def _make(cells, rejected=None, integrity=None, name="migration_map.json"):
        p = tmp_path / name
        write_json(p, map_doc(cells, rejected, integrity))
        return p
    return _make


@pytest.fixture
def backup_dir(tmp_path):
    """备份目录路径（故意不预先创建，脚本应自建）。"""
    return tmp_path / "backups"


@pytest.fixture
def session_dir(tmp_path):
    """种子会话目录路径（故意不预先创建，脚本应自建）。"""
    return tmp_path / "session"


@pytest.fixture
def seeded(run_seed, session_dir):
    """登记若干种子并返回 seed_id 列表。默认登记 1 个，today=TODAY。"""
    def _make(n=1, today=TODAY):
        items = [{"text": "第%d个种子：把宿主节律当成工程菌治疗的隐藏变量" % (i + 1)}
                 for i in range(n)]
        r = run_seed(["register", "--session-dir", session_dir, "--today", today],
                     stdin_obj=items)
        data = r.assert_ok("register")
        return [s["seed_id"] for s in data["registered"]]
    return _make
