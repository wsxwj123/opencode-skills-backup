#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
abbreviation_registry.py 端到端测试套件

覆盖：
- 注册/批量注册/查询/删除/更新（含 TOCTOU 安全）
- 提取（含大写验证、前缀修剪）
- 剥离冗余展开（含章节归一化）
- 交叉引用验证
- 一体化 process_section_markdown
- CLI 子命令
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# 确保 scripts 目录在 sys.path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from abbreviation_registry import (
    register,
    register_batch,
    is_known,
    get_all,
    get_info,
    unregister,
    update_entry,
    extract_abbreviations,
    strip_redundant_expansions,
    process_section_markdown,
    generate_abbreviation_table_markdown,
    validate_cross_references,
    load_registry,
    save_registry,
    _trim_cn_prefix,
    _normalize_chapter,
)


class TempProjectMixin:
    """为每个测试创建临时项目目录"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="sci2doc_test_")
        self.project_root = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


# =========================================================================
# 1. 基础注册/查询/删除/更新
# =========================================================================


class TestRegister(TempProjectMixin, unittest.TestCase):

    def test_register_new(self):
        r = register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                     full_en="Polymerase Chain Reaction", chapter="2", section="2.1")
        self.assertTrue(r["registered"])
        self.assertFalse(r["already_known"])

    def test_register_duplicate(self):
        register(self.project_root, "PCR", full_cn="聚合酶链式反应")
        r = register(self.project_root, "PCR", full_cn="不同全称")
        self.assertFalse(r["registered"])
        self.assertTrue(r["already_known"])
        # 首次注册的全称不被覆盖
        info = get_info(self.project_root, "PCR")
        self.assertEqual(info["full_cn"], "聚合酶链式反应")

    def test_register_empty(self):
        r = register(self.project_root, "  ")
        self.assertFalse(r["registered"])
        self.assertIn("error", r)

    def test_is_known(self):
        register(self.project_root, "HPLC")
        self.assertTrue(is_known(self.project_root, "HPLC"))
        self.assertFalse(is_known(self.project_root, "GC"))

    def test_get_all_sorted(self):
        register(self.project_root, "PCR")
        register(self.project_root, "HPLC")
        register(self.project_root, "ABC")
        items = get_all(self.project_root)
        keys = [k for k, _ in items]
        self.assertEqual(keys, ["ABC", "HPLC", "PCR"])

    def test_get_info_not_found(self):
        self.assertIsNone(get_info(self.project_root, "NOPE"))

    def test_unregister(self):
        register(self.project_root, "PCR")
        r = unregister(self.project_root, "PCR")
        self.assertTrue(r["removed"])
        self.assertFalse(is_known(self.project_root, "PCR"))

    def test_unregister_not_found(self):
        r = unregister(self.project_root, "NOPE")
        self.assertFalse(r["removed"])

    def test_update_entry(self):
        register(self.project_root, "PCR", full_cn="旧名称")
        r = update_entry(self.project_root, "PCR", full_cn="聚合酶链式反应")
        self.assertTrue(r["updated"])
        self.assertIn("full_cn", r["fields"])
        info = get_info(self.project_root, "PCR")
        self.assertEqual(info["full_cn"], "聚合酶链式反应")

    def test_update_entry_not_found(self):
        r = update_entry(self.project_root, "NOPE", full_cn="x")
        self.assertFalse(r["updated"])

    def test_update_no_fields_skips_write(self):
        register(self.project_root, "PCR")
        r = update_entry(self.project_root, "PCR")
        self.assertTrue(r["updated"])
        self.assertEqual(r["fields"], [])


# =========================================================================
# 2. 批量注册
# =========================================================================


class TestRegisterBatch(TempProjectMixin, unittest.TestCase):

    def test_batch_register(self):
        items = [
            {"abbr": "PCR", "full_cn": "聚合酶链式反应", "chapter": "2", "section": "2.1"},
            {"abbr": "HPLC", "full_cn": "高效液相色谱", "chapter": "3", "section": "3.1"},
        ]
        r = register_batch(self.project_root, items)
        self.assertEqual(r["registered_count"], 2)
        self.assertEqual(r["skipped_count"], 0)

    def test_batch_skip_existing(self):
        register(self.project_root, "PCR")
        items = [
            {"abbr": "PCR"},
            {"abbr": "HPLC", "full_cn": "高效液相色谱"},
        ]
        r = register_batch(self.project_root, items)
        self.assertEqual(r["registered_count"], 1)
        self.assertEqual(r["skipped_count"], 1)

    def test_batch_skip_empty(self):
        items = [{"abbr": ""}, {"abbr": "  "}]
        r = register_batch(self.project_root, items)
        self.assertEqual(r["registered_count"], 0)
        self.assertEqual(r["skipped_count"], 2)

    def test_batch_no_new_skips_write(self):
        """P4: 无新条目时不写入文件"""
        register(self.project_root, "PCR")
        from abbreviation_registry import registry_path
        path = registry_path(self.project_root)
        mtime_before = os.path.getmtime(path)

        import time
        time.sleep(0.05)

        items = [{"abbr": "PCR"}]
        r = register_batch(self.project_root, items)
        self.assertEqual(r["registered_count"], 0)

        mtime_after = os.path.getmtime(path)
        self.assertEqual(mtime_before, mtime_after)


# =========================================================================
# 3. 提取缩略语
# =========================================================================


class TestExtract(unittest.TestCase):

    def test_cn_pattern(self):
        text = "本研究采用聚合酶链式反应（PCR）进行检测"
        result = extract_abbreviations(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["abbr"], "PCR")
        # 前缀修剪后应为纯术语
        self.assertEqual(result[0]["full_cn"], "聚合酶链式反应")

    def test_en_pattern(self):
        text = "Polymerase Chain Reaction (PCR) is widely used."
        result = extract_abbreviations(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["abbr"], "PCR")
        self.assertEqual(result[0]["full_en"], "Polymerase Chain Reaction")

    def test_mixed_pattern(self):
        text = "聚合酶链式反应（Polymerase Chain Reaction, PCR）"
        result = extract_abbreviations(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["abbr"], "PCR")
        self.assertEqual(result[0]["full_cn"], "聚合酶链式反应")
        self.assertEqual(result[0]["full_en"], "Polymerase Chain Reaction")

    def test_lowercase_prefix_mRNA(self):
        text = "信使核糖核酸（mRNA）在基因表达中起关键作用"
        result = extract_abbreviations(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["abbr"], "mRNA")

    def test_uppercase_validation_rejects_all_lowercase(self):
        """P2: 纯小写不应被提取"""
        text = "某种技术（abc）不是缩略语"
        result = extract_abbreviations(text)
        self.assertEqual(len(result), 0)

    def test_uppercase_validation_accepts_mixed(self):
        """siRNA 有大写 R/N/A"""
        text = "小干扰核糖核酸（siRNA）用于基因沉默"
        result = extract_abbreviations(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["abbr"], "siRNA")

    def test_multiple_extractions(self):
        text = (
            "聚合酶链式反应（PCR）和高效液相色谱（HPLC）"
            "以及酶联免疫吸附测定（Enzyme Linked Immunosorbent Assay, ELISA）"
        )
        result = extract_abbreviations(text)
        abbrs = {r["abbr"] for r in result}
        self.assertIn("PCR", abbrs)
        self.assertIn("HPLC", abbrs)
        self.assertIn("ELISA", abbrs)

    def test_no_lookbehind_restriction(self):
        """P1: 去掉 lookbehind 后，句中任意位置都能匹配"""
        text = "实验中聚合酶链式反应（PCR）的灵敏度很高"
        result = extract_abbreviations(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["abbr"], "PCR")


# =========================================================================
# 4. 前缀修剪
# =========================================================================


class TestTrimPrefix(unittest.TestCase):

    def test_trim_verb_prefix(self):
        self.assertEqual(_trim_cn_prefix("采用聚合酶链式反应"), "聚合酶链式反应")
        self.assertEqual(_trim_cn_prefix("本研究使用高效液相色谱"), "高效液相色谱")

    def test_no_trim_short_result(self):
        """修剪后太短则保留原文"""
        self.assertEqual(_trim_cn_prefix("采用"), "采用")

    def test_no_trim_clean_text(self):
        self.assertEqual(_trim_cn_prefix("聚合酶链式反应"), "聚合酶链式反应")

    def test_single_char_not_trimmed(self):
        """P1: 单字（以/用/对/在/为/是/的/与/和）不再被修剪"""
        self.assertEqual(_trim_cn_prefix("以聚合酶链式反应"), "以聚合酶链式反应")
        self.assertEqual(_trim_cn_prefix("用高效液相色谱"), "用高效液相色谱")
        self.assertEqual(_trim_cn_prefix("对免疫印迹法"), "对免疫印迹法")

    def test_empty_input(self):
        self.assertEqual(_trim_cn_prefix(""), "")
        self.assertEqual(_trim_cn_prefix(None), None)


# =========================================================================
# 5. 章节归一化
# =========================================================================


class TestNormalizeChapter(unittest.TestCase):

    def test_strip_leading_zeros(self):
        self.assertEqual(_normalize_chapter("02"), "2")
        self.assertEqual(_normalize_chapter("002"), "2")

    def test_normal_number(self):
        self.assertEqual(_normalize_chapter("2"), "2")
        self.assertEqual(_normalize_chapter("10"), "10")

    def test_whitespace(self):
        self.assertEqual(_normalize_chapter(" 3 "), "3")

    def test_non_numeric(self):
        self.assertEqual(_normalize_chapter("二"), "二")

    def test_empty(self):
        self.assertEqual(_normalize_chapter(""), "")


# =========================================================================
# 6. 剥离冗余展开
# =========================================================================


class TestStripRedundant(TempProjectMixin, unittest.TestCase):

    def test_strip_cn_pattern(self):
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="2", section="2.1")
        text = "本章使用聚合酶链式反应（PCR）进行验证"
        cleaned, report = strip_redundant_expansions(
            self.project_root, text, chapter="3", section="3.1"
        )
        self.assertIn("PCR", cleaned)
        self.assertNotIn("聚合酶链式反应（PCR）", cleaned)
        self.assertEqual(report["stripped_count"], 1)

    def test_no_strip_first_occurrence(self):
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="2", section="2.1")
        text = "聚合酶链式反应（PCR）首次出现"
        cleaned, report = strip_redundant_expansions(
            self.project_root, text, chapter="2", section="2.1"
        )
        self.assertIn("聚合酶链式反应（PCR）", cleaned)
        self.assertEqual(report["stripped_count"], 0)

    def test_chapter_normalization(self):
        """P2: "02" 和 "2" 应视为同一章"""
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="02", section="2.1")
        text = "聚合酶链式反应（PCR）首次出现"
        cleaned, report = strip_redundant_expansions(
            self.project_root, text, chapter="2", section="2.1"
        )
        # 应保留（首次出现章节匹配）
        self.assertIn("聚合酶链式反应（PCR）", cleaned)
        self.assertEqual(report["stripped_count"], 0)

    def test_strip_en_pattern(self):
        register(self.project_root, "PCR", full_en="Polymerase Chain Reaction",
                 chapter="1", section="1.1")
        text = "We used Polymerase Chain Reaction (PCR) for detection."
        cleaned, report = strip_redundant_expansions(
            self.project_root, text, chapter="3"
        )
        self.assertIn("PCR", cleaned)
        self.assertNotIn("Polymerase Chain Reaction (PCR)", cleaned)

    def test_strip_mixed_pattern(self):
        register(self.project_root, "ELISA",
                 full_cn="酶联免疫吸附测定",
                 full_en="Enzyme Linked Immunosorbent Assay",
                 chapter="2", section="2.1")
        text = "酶联免疫吸附测定（Enzyme Linked Immunosorbent Assay, ELISA）"
        cleaned, report = strip_redundant_expansions(
            self.project_root, text, chapter="4"
        )
        self.assertEqual(cleaned.strip(), "ELISA")

    def test_empty_registry(self):
        text = "聚合酶链式反应（PCR）"
        cleaned, report = strip_redundant_expansions(
            self.project_root, text, chapter="3"
        )
        self.assertEqual(cleaned, text)
        self.assertEqual(report["stripped_count"], 0)


# =========================================================================
# 7. 一体化处理
# =========================================================================


class TestProcessSection(TempProjectMixin, unittest.TestCase):

    def test_process_extracts_and_registers(self):
        text = "聚合酶链式反应（PCR）是常用技术"
        cleaned, report = process_section_markdown(
            self.project_root, text, chapter="2", section="2.1"
        )
        self.assertEqual(report["extracted_count"], 1)
        self.assertEqual(report["registration"]["registered_count"], 1)
        self.assertTrue(is_known(self.project_root, "PCR"))

    def test_process_strips_in_later_chapter(self):
        # 先注册
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="2", section="2.1")
        text = "本章使用聚合酶链式反应（PCR）进行验证"
        cleaned, report = process_section_markdown(
            self.project_root, text, chapter="3", section="3.1"
        )
        self.assertNotIn("聚合酶链式反应（PCR）", cleaned)
        self.assertIn("PCR", cleaned)


# =========================================================================
# 8. 缩略语对照表生成
# =========================================================================


class TestGenerateTable(TempProjectMixin, unittest.TestCase):

    def test_generate_table(self):
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 full_en="Polymerase Chain Reaction")
        register(self.project_root, "HPLC", full_cn="高效液相色谱",
                 full_en="High Performance Liquid Chromatography")
        md = generate_abbreviation_table_markdown(self.project_root)
        self.assertIn("| PCR |", md)
        self.assertIn("| HPLC |", md)
        self.assertIn("主要缩略语对照表", md)

    def test_empty_table(self):
        md = generate_abbreviation_table_markdown(self.project_root)
        self.assertEqual(md, "")


# =========================================================================
# 9. 交叉引用验证
# =========================================================================


class TestCrossReferenceValidation(TempProjectMixin, unittest.TestCase):

    def _setup_chapter_md(self, chapter, section, content):
        chapter_dir = Path(self.project_root) / "atomic_md" / f"第{chapter}章"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        md_file = chapter_dir / f"{section}_test.md"
        md_file.write_text(content, encoding="utf-8")
        return md_file

    def test_valid_cross_reference(self):
        self._setup_chapter_md("2", "2.1", "聚合酶链式反应（PCR）是常用技术")
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="2", section="2.1")
        result = validate_cross_references(self.project_root)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 0)

    def test_valid_cross_reference_with_prefix(self):
        """测试带前缀的引用格式：(Full Name, ABBR)"""
        self._setup_chapter_md("2", "2.1", "全文...（Tumor Microenvironment, TME）...")
        register(self.project_root, "TME", full_cn="肿瘤微环境", full_en="Tumor Microenvironment",
                 chapter="2", section="2.1")
        result = validate_cross_references(self.project_root)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 0)

    def test_valid_cross_reference_cn_prefix(self):
        """测试带中文前缀的引用格式：(肿瘤微环境，TME)"""
        self._setup_chapter_md("2", "2.1", "全文...（肿瘤微环境，TME）...")
        register(self.project_root, "TME", full_cn="肿瘤微环境", full_en="Tumor Microenvironment",
                 chapter="2", section="2.1")
        result = validate_cross_references(self.project_root)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 0)

    def test_invalid_cross_reference_no_expansion(self):
        self._setup_chapter_md("2", "2.1", "本章使用PCR进行检测")
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="2", section="2.1")
        result = validate_cross_references(self.project_root)
        self.assertEqual(result["invalid_count"], 1)
        detail = result["details"][0]
        self.assertEqual(detail["status"], "invalid")

    def test_invalid_cross_reference_missing_chapter_dir(self):
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="99", section="99.1")
        result = validate_cross_references(self.project_root)
        self.assertEqual(result["invalid_count"], 1)

    def test_invalid_missing_first_chapter(self):
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="", section="")
        result = validate_cross_references(self.project_root)
        self.assertEqual(result["invalid_count"], 1)
        self.assertIn("missing first_chapter", result["details"][0]["reason"])

    def test_chapter_normalization_in_validation(self):
        """注册时 chapter="02"，目录名为 第2章"""
        self._setup_chapter_md("2", "2.1", "聚合酶链式反应（PCR）")
        register(self.project_root, "PCR", full_cn="聚合酶链式反应",
                 chapter="02", section="2.1")
        result = validate_cross_references(self.project_root)
        self.assertEqual(result["valid_count"], 1)

    def test_empty_registry(self):
        result = validate_cross_references(self.project_root)
        self.assertEqual(result["valid_count"], 0)
        self.assertEqual(result["invalid_count"], 0)


# =========================================================================
# 10. CLI 冒烟测试
# =========================================================================


class TestCLI(TempProjectMixin, unittest.TestCase):

    def _run_cli(self, *args):
        import subprocess
        cmd = [sys.executable, os.path.join(_SCRIPT_DIR, "abbreviation_registry.py"),
               "--project-root", self.project_root] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result

    def test_cli_register_and_query(self):
        r = self._run_cli("register", "--abbr", "PCR", "--full-cn", "聚合酶链式反应")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertTrue(data["registered"])

        r = self._run_cli("query", "--abbr", "PCR")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertTrue(data["found"])

    def test_cli_list(self):
        self._run_cli("register", "--abbr", "PCR")
        r = self._run_cli("list")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["count"], 1)

    def test_cli_unregister(self):
        self._run_cli("register", "--abbr", "PCR")
        r = self._run_cli("unregister", "--abbr", "PCR")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertTrue(data["removed"])

    def test_cli_update(self):
        self._run_cli("register", "--abbr", "PCR")
        r = self._run_cli("update", "--abbr", "PCR", "--full-cn", "新名称")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertTrue(data["updated"])

    def test_cli_table_empty(self):
        r = self._run_cli("table")
        self.assertEqual(r.returncode, 0)
        self.assertIn("无已注册缩略语", r.stdout)

    def test_cli_validate(self):
        r = self._run_cli("validate")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIn("valid_count", data)

    def test_cli_extract(self):
        md_file = Path(self.project_root) / "test_input.md"
        md_file.write_text("聚合酶链式反应（PCR）", encoding="utf-8")
        r = self._run_cli("extract", "--file", str(md_file))
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(len(data["extracted"]), 1)

    def test_cli_process_in_place(self):
        # 先注册一个缩略语
        self._run_cli("register", "--abbr", "PCR", "--full-cn", "聚合酶链式反应",
                       "--chapter", "1", "--section", "1.1")
        md_file = Path(self.project_root) / "test_process.md"
        md_file.write_text("本章使用聚合酶链式反应（PCR）验证", encoding="utf-8")
        r = self._run_cli("process", "--file", str(md_file),
                          "--chapter", "3", "--section", "3.1", "--in-place")
        self.assertEqual(r.returncode, 0)
        content = md_file.read_text(encoding="utf-8")
        self.assertNotIn("聚合酶链式反应（PCR）", content)
        self.assertIn("PCR", content)


if __name__ == "__main__":
    unittest.main()
