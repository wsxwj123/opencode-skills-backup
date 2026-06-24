#!/usr/bin/env python3
"""回归测试：固化两类已修 bug 的契约。

纯 assert、无 pytest、自包含（输入用 tempfile/字符串现造，不依赖真稿）。
直接运行：失败抛 AssertionError，全过打印 OK。

    python3 test_format_contract.py

覆盖契约：
  契约 1 —— citation_validator.extract_citation_numbers 复合角标解析
            （bug: 旧版只识别单角标 [7]，复合 [4,5] / 区间 [4-6] / 全角逗号失效）
  契约 2 —— 三个 CLI 的 fail-closed 退出码
            （bug: ERROR 级 FAIL 未映射为非零退出码，CI 误判通过）
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from citation_validator import extract_citation_numbers  # noqa: E402
from humanizer_zh import scan_text  # noqa: E402


# ---------------------------------------------------------------------------
# 契约 1：复合角标解析
# bug 复现：复合/区间/全角逗号角标必须全部展开，单角标不得退化。
# ---------------------------------------------------------------------------
def test_extract_citation_numbers() -> None:
    # 复合（半角逗号）
    nums = extract_citation_numbers("[4,5]")
    assert 4 in nums and 5 in nums, f"[4,5] 应含 4,5，实得 {nums}"

    # 区间展开
    nums = extract_citation_numbers("[4-6]")
    assert 4 in nums and 5 in nums and 6 in nums, f"[4-6] 应含 4,5,6，实得 {nums}"

    # 句中混合复合 + 单角标
    nums = extract_citation_numbers("文献[2,3]和[7]")
    assert 2 in nums and 3 in nums and 7 in nums, f"文献[2,3]和[7] 应含 2,3,7，实得 {nums}"

    # 全角逗号
    nums = extract_citation_numbers("[4，5]")
    assert 4 in nums and 5 in nums, f"全角 [4，5] 应含 4,5，实得 {nums}"

    # 单角标不退化
    nums = extract_citation_numbers("[7]")
    assert nums == [7], f"单角标 [7] 应仍为 [7]，实得 {nums}"

    print("契约 1 (复合角标解析) OK")


# ---------------------------------------------------------------------------
# 契约 2：fail-closed 退出码
# 每个命令在独立 tempdir 中运行，所有输入/输出路径显式指向 tempdir，
# 不污染 skill 目录，退出即随 tempdir 一并清理。
# ---------------------------------------------------------------------------
def _run(script: str, args: list[str], cwd: Path) -> int:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return proc.returncode


def test_consistency_mapper_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # ERROR FAIL：研究内容缺 mapped_to_method → V-03(ERROR) 失败 → rc=1
        err_map = d / "cm_err.json"
        err_map.write_text(
            json.dumps({"research_contents": [{"id": "RC-1", "mapped_to_method": []}]}),
            encoding="utf-8",
        )
        rc = _run("consistency_mapper.py",
                  ["--path", str(err_map), "validate", "--rules", "V-03"], d)
        assert rc == 1, f"consistency ERROR FAIL 应 rc=1，实得 {rc}"

        # 全 pass：空 map，所有规则空集合 vacuously 通过 → rc=0
        pass_map = d / "cm_pass.json"
        pass_map.write_text("{}", encoding="utf-8")
        rc = _run("consistency_mapper.py",
                  ["--path", str(pass_map), "validate"], d)
        assert rc == 0, f"consistency 全 pass 应 rc=0，实得 {rc}"

        # 仅 WARNING：研究内容有 method 但缺 annual_plan_year → V-04(WARNING) 失败 → rc=0
        warn_map = d / "cm_warn.json"
        warn_map.write_text(
            json.dumps({"research_contents": [{"id": "RC-1", "mapped_to_method": ["M-1"]}]}),
            encoding="utf-8",
        )
        rc = _run("consistency_mapper.py",
                  ["--path", str(warn_map), "validate", "--rules", "V-04"], d)
        assert rc == 0, f"consistency 仅 WARNING 应 rc=0，实得 {rc}"

    print("契约 2a (consistency_mapper: ERROR→1 / pass→0 / WARNING→0) OK")


def test_citation_validator_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        ref = d / "none.md"          # 不存在的 p1，validator 容忍
        mrq = d / "mrq.json"
        log = d / "log.json"
        base = ["--offline", "--mcp-ttl-days", "0",
                "--p1", str(ref),
                "--manual-review", str(mrq), "--log", str(log)]

        # verification_status=failed：DOI 非法 + 无 MCP 记录 → 硬失败 → rc=1
        idx_fail = d / "idx_fail.json"
        idx_fail.write_text(json.dumps({
            "metadata": {},
            "entries": [{"ref_number": 1, "title": "Some Title",
                         "doi": "NOT_A_DOI", "search_source": "pubmed"}],
        }), encoding="utf-8")
        mcp_empty = d / "mcp_empty.json"
        mcp_empty.write_text(json.dumps({"entries": []}), encoding="utf-8")
        rc = _run("citation_validator.py",
                  ["verify-all", "--index", str(idx_fail),
                   "--mcp-cache", str(mcp_empty), *base], d)
        assert rc == 1, f"citation verification failed 应 rc=1，实得 {rc}"

        # 全 pass：合法 DOI + MCP 命中（ttl=0 跳过时效）+ offline → verified → rc=0
        idx_pass = d / "idx_pass.json"
        idx_pass.write_text(json.dumps({
            "metadata": {},
            "entries": [{"ref_number": 1, "title": "Some Title",
                         "doi": "10.1000/abc123", "search_source": "pubmed"}],
        }), encoding="utf-8")
        mcp_pass = d / "mcp_pass.json"
        mcp_pass.write_text(json.dumps({
            "metadata": {"schema_version": "1.0"},
            "entries": [{"doi": "10.1000/abc123"}],
        }), encoding="utf-8")
        rc = _run("citation_validator.py",
                  ["verify-all", "--index", str(idx_pass),
                   "--mcp-cache", str(mcp_pass), *base], d)
        assert rc == 0, f"citation 全 pass 应 rc=0，实得 {rc}"

    print("契约 2b (citation_validator: failed→1 / pass→0) OK")


def test_diagnosis_engine_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        idx = d / "idx.json"
        idx.write_text(json.dumps({"metadata": {}, "entries": []}), encoding="utf-8")
        ref = d / "ref.md"
        ref.write_text("", encoding="utf-8")
        empty_cm = d / "cm_empty.json"
        empty_cm.write_text("{}", encoding="utf-8")

        # blocked：空 sections 目录 → P1 缺失 → D-01 评 "D" → 任一维 D → blocked → rc=1
        blocked_dir = d / "sections_blocked"
        blocked_dir.mkdir()
        rep_blocked = d / "rep_blocked.json"
        p1_missing = d / "p1_missing.md"
        p1_missing.write_text("", encoding="utf-8")
        rc = _run("diagnosis_engine.py", [
            "full-review",
            "--sections-dir", str(blocked_dir),
            "--consistency", str(empty_cm),
            "--index", str(idx), "--p1", str(p1_missing), "--ref", str(ref),
            "--output", str(rep_blocked),
        ], d)
        assert rc == 1, f"diagnosis blocked 应 rc=1，实得 {rc}"

        # pass：构造无任何 "D" 维度的最小合法稿
        #   D-01: P1 非空(≥8 角标) ; D-04: cm 含 1 条 feasibility_evidence(合法节)
        #   D-09: B1/B2/B3 齐全 ; D-07: 各节文本清洁(无风格/节奏告警)
        pass_dir = d / "sections_pass"
        pass_dir.mkdir()
        p1 = ("本研究关注糖代谢调控的分子机制[1]。前期工作发现某蛋白在肝细胞中表达升高[2]。"
              "我们推测它参与葡萄糖摄取[3]。实验采用细胞培养与小鼠模型相结合的方式开展[4]。"
              "数据来自三批独立重复[5]。统计方法选用方差分析[6]。"
              "结果显示该蛋白敲低后糖摄取下降约四成[7]。这一现象在两种细胞系中均可观察到[8]。"
              "后续将进一步验证其下游通路[9]。")
        (pass_dir / "P1_立项依据.md").write_text(p1, encoding="utf-8")
        (pass_dir / "B1_预算说明_直接费用.md").write_text(
            "直接费用涵盖设备与材料两类。设备购置依照实验需要列支。", encoding="utf-8")
        (pass_dir / "B2_预算说明_合作外拨.md").write_text(
            "合作外拨主要用于委托测序服务。金额依据对方报价确定。", encoding="utf-8")
        (pass_dir / "B3_预算说明_其他来源.md").write_text(
            "其他来源经费来自单位配套支持。用途与本项目保持一致。", encoding="utf-8")
        pass_cm = d / "cm_pass.json"
        pass_cm.write_text(json.dumps({
            "feasibility_evidence": [
                {"id": "F-1", "source_section": "P3_1_研究基础与可行性分析"}
            ]
        }), encoding="utf-8")
        rep_pass = d / "rep_pass.json"
        rc = _run("diagnosis_engine.py", [
            "full-review",
            "--sections-dir", str(pass_dir),
            "--consistency", str(pass_cm),
            "--index", str(idx),
            "--p1", str(pass_dir / "P1_立项依据.md"), "--ref", str(ref),
            "--output", str(rep_pass),
        ], d)
        assert rc == 0, f"diagnosis pass 应 rc=0，实得 {rc}"

    print("契约 2c (diagnosis_engine: blocked→1 / pass→0) OK")


# ---------------------------------------------------------------------------
# 契约 3：check-gates 引用门禁（J4 fail-closed / J5,J7 WARN）
# J4 著录不完整 → exit 2；J5 自引 / J7 时效仅告警，不改退出码 → exit 0。
# ---------------------------------------------------------------------------
def _codes(text: str) -> set[str]:
    return {i["code"] for i in scan_text(text)["issues"]}


def test_check_gates_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        profile = d / "proposal_profile.json"
        profile.write_text(json.dumps({"applicant_authors": ["张三"]}), encoding="utf-8")

        # J4 fail-closed：某条无 title 且无 DOI/PMID/raw → incomplete → rc=2
        idx_bad = d / "idx_bad.json"
        idx_bad.write_text(json.dumps({"metadata": {}, "entries": [
            {"ref_number": 1, "doi": "", "pmid": "", "title": ""},
        ]}), encoding="utf-8")
        rc = _run("citation_validator.py",
                  ["check-gates", "--index", str(idx_bad),
                   "--profile", str(profile), "--current-year", "2026"], d)
        assert rc == 2, f"J4 著录不完整应 fail-closed rc=2，实得 {rc}"

        # 全 pass：J4 完整（有 title+DOI）；J5 自引超阈/J7 时效偏旧 仅 WARN → rc=0
        idx_warn = d / "idx_warn.json"
        idx_warn.write_text(json.dumps({"metadata": {}, "entries": [
            {"ref_number": 1, "title": "T1", "doi": "10.1/a",
             "authors": ["张三"], "year": 2008},
            {"ref_number": 2, "title": "T2", "doi": "10.1/b",
             "authors": ["张三"], "year": 2009},
        ]}), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "citation_validator.py"),
             "check-gates", "--index", str(idx_warn),
             "--profile", str(profile), "--current-year", "2026"],
            cwd=str(d), capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"J5/J7 仅 WARN 应 rc=0，实得 {proc.returncode}"
        report = json.loads(proc.stdout)
        assert report["j5_self_citation"]["status"] == "warn", "J5 应触发 warn（自引比例=1）"
        assert report["j7_recency"]["status"] == "warn", "J7 应触发 warn（无近 5 年文献）"
        assert report["j4_completeness"]["strength"] == "fail-closed"
        assert report["j5_self_citation"]["strength"] == "warn"
        assert report["j7_recency"]["strength"] == "warn"

        # J5 skip：profile 无 applicant_authors → 不报错、status=skipped → rc=0
        empty_profile = d / "empty_profile.json"
        empty_profile.write_text("{}", encoding="utf-8")
        proc2 = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "citation_validator.py"),
             "check-gates", "--index", str(idx_warn),
             "--profile", str(empty_profile), "--current-year", "2026"],
            cwd=str(d), capture_output=True, text=True,
        )
        assert proc2.returncode == 0, "无 authors 时 check-gates 应 rc=0"
        assert json.loads(proc2.stdout)["j5_self_citation"]["status"] == "skipped", \
            "无 applicant_authors → J5 应 skip"

    print("契约 3 (check-gates: J4→2 / J5,J7 warn→0 / J5 skip) OK")


# ---------------------------------------------------------------------------
# 契约 4：字符级检查双向断言（D1 半角 / D2 上下标裸写 / F1 错别字，全 WARN）
# 正例必报对应 code；反例（干净/已正确标注）不得误报。
# ---------------------------------------------------------------------------
def test_charlevel_bidirectional() -> None:
    # D1 正例：中文句内夹半角逗号
    assert "halfwidth_punct_in_cn" in _codes("本实验,采用细胞模型。"), "D1 应报中文句内半角逗号"
    # D1 反例：全角逗号干净
    assert "halfwidth_punct_in_cn" not in _codes("本实验，采用细胞模型。"), "D1 不应误报全角逗号"
    # D1 反例：数字间半角不触发（非汉字两侧）
    assert "halfwidth_punct_in_cn" not in _codes("剂量为 1,000 mg。"), "D1 不应误报数字千分位"

    # D2 正例：裸写 H2O
    assert "subsup_bare" in _codes("反应生成 H2O 和热量。"), "D2 应报裸写 H2O"
    # D2 正例：中文紧邻（无空格），ASCII 边界须在汉字-字母间成立
    assert "subsup_bare" in _codes("影响H2O代谢的关键酶。"), "D2 应报中文紧邻裸写 H2O"
    # D2 正例：IC50 中文紧邻
    assert "subsup_bare" in _codes("测得IC50值约为 10 μM。"), "D2 应报中文紧邻裸写 IC50"
    # D2 反例：已用 markdown 下标标注
    assert "subsup_bare" not in _codes("反应生成 H~2~O 和热量。"), "D2 不应误报已标注上下标"
    # D2 反例：英文上下文不退化（XH2OY 前后接字母数字时不报）
    assert "subsup_bare" not in _codes("the XH2OY level is high."), "D2 不应误报英文嵌字母的 XH2OY"

    # F1 正例：错别字"登陆"
    assert "chinese_typo" in _codes("用户需要登陆系统后操作。"), "F1 应报错别字'登陆'"
    # F1 反例：正确写法"登录"
    assert "chinese_typo" not in _codes("用户需要登录系统后操作。"), "F1 不应误报'登录'"

    # 全 WARN：字符级 issue 不得出现 ERROR 级
    issues = scan_text("本实验,生成 H2O，用户登陆系统。")["issues"]
    charlevel = [i for i in issues
                 if i["code"] in {"halfwidth_punct_in_cn", "subsup_bare", "chinese_typo"}]
    assert charlevel and all(i["severity"] == "WARNING" for i in charlevel), \
        "字符级检查必须全为 WARNING 级"

    print("契约 4 (字符级 D1/D2/F1 双向断言, 全 WARN) OK")


# ---------------------------------------------------------------------------
# 契约 5：consistency_mapper 字段名契约（防"字段名错配静默全 PASS=假绿"）
# 实测背景：consistency_map 顶层键名为 hypotheses/research_contents 等非直觉名，
# 调用方易写成 h_nodes/reseach_contents。旧行为下 load_map 把错键当未知数据丢弃、
# 正确键 setdefault 成空集合，validate 便 vacuously 全 PASS、rc=0 —— 假绿。
#   - 正例：标准键名的最小合法全链 → validate PASS（rc=0）。
#   - 反例：所有顶层键错配（real data 落在未知键上，集合全空）→ 必须 fail-closed
#           （rc≠0），不得返回"全 PASS / rc=0"。固化 unknown_top_level_keys 守卫行为。
# ---------------------------------------------------------------------------
def test_consistency_mapper_field_name_contract() -> None:
    # 标准键名最小全链：Phase 2 规则全过，且无未知键 → rc=0
    correct_map = {
        "scientific_questions": [{"id": "SQ-1"}],
        "hypotheses": [{"id": "H-1", "mapped_from_sq": ["SQ-1"],
                        "mapped_to_objective": "O-1", "mapped_to_rc": "RC-1",
                        "mapped_to_ksq": "KSQ-1"}],
        "objectives": [{"id": "O-1"}],
        "key_scientific_problems": [{"id": "KSQ-1", "mapped_from_sq": ["SQ-1"]}],
        "research_contents": [{"id": "RC-1", "mapped_to_method": ["M-1"],
                               "annual_plan_year": 1}],
        "methodologies": [{"id": "M-1"}],
        "innovations": [{"id": "IN-1", "mapped_from_rc": ["RC-1"],
                         "mapped_from_method": ["M-1"]}],
        "feasibility_evidence": [],
        "keywords_trace": {},
    }
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        ok = d / "cm_correct.json"
        ok.write_text(json.dumps(correct_map), encoding="utf-8")
        rc = _run("consistency_mapper.py",
                  ["--path", str(ok), "validate", "--phase", "2"], d)
        assert rc == 0, f"标准键名最小全链应 PASS rc=0，实得 {rc}"

        # 错配键名：把整张图的键全写错（hypotheses→h_nodes 等）。
        # real data 落到未知键、标准集合全空 —— 旧行为会假绿 rc=0；守卫后必须 rc!=0。
        wrong_map = {
            "scientific_questions_": correct_map["scientific_questions"],  # 拼错
            "h_nodes": correct_map["hypotheses"],                          # hypotheses 错配
            "objs": correct_map["objectives"],
            "ksqs": correct_map["key_scientific_problems"],
            "reseach_contents": correct_map["research_contents"],          # research 拼错
            "methods": correct_map["methodologies"],
        }
        bad = d / "cm_wrong.json"
        bad.write_text(json.dumps(wrong_map), encoding="utf-8")
        # phase 7（全量规则）下尤其危险：若守卫缺失，空集合令所有规则 vacuously PASS。
        rc7 = _run("consistency_mapper.py",
                   ["--path", str(bad), "validate", "--phase", "7"], d)
        assert rc7 != 0, f"字段名全错配不得假绿（phase7 应 rc!=0），实得 {rc7}"
        rc2 = _run("consistency_mapper.py",
                   ["--path", str(bad), "validate", "--phase", "2"], d)
        assert rc2 != 0, f"字段名全错配不得假绿（phase2 应 rc!=0），实得 {rc2}"

        # 部分错配（hypotheses→h_nodes，其余正确键名存在并引用缺失 ID）同样不得假绿。
        partial = {
            "scientific_questions": [{"id": "SQ-1"}],
            "h_nodes": correct_map["hypotheses"],
            "objectives": correct_map["objectives"],
            "key_scientific_problems": correct_map["key_scientific_problems"],
            "research_contents": correct_map["research_contents"],
            "methodologies": correct_map["methodologies"],
        }
        pbad = d / "cm_partial.json"
        pbad.write_text(json.dumps(partial), encoding="utf-8")
        rcp = _run("consistency_mapper.py",
                   ["--path", str(pbad), "validate", "--phase", "2"], d)
        assert rcp != 0, f"部分字段名错配不得假绿，实得 {rcp}"

    print("契约 5 (consistency_mapper 字段名契约：标准名 PASS / 错配名不假绿) OK")


if __name__ == "__main__":
    test_extract_citation_numbers()
    test_consistency_mapper_exit_codes()
    test_consistency_mapper_field_name_contract()
    test_citation_validator_exit_codes()
    test_diagnosis_engine_exit_codes()
    test_check_gates_exit_codes()
    test_charlevel_bidirectional()
    print("ALL OK")
