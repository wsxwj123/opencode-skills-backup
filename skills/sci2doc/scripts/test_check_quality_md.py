#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_markdown_quality 单元测试"""

import os
import sys
import tempfile
import unittest

# 确保 scripts/ 在 sys.path 中
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from check_quality import check_markdown_quality


class TestCheckMarkdownQuality(unittest.TestCase):
    """check_markdown_quality 功能测试"""

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    def _check(self, content: str):
        """写入临时 .md 文件并运行检查，返回 (issues, stats)。"""
        fd, path = tempfile.mkstemp(suffix=".md")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            return check_markdown_quality(path)
        finally:
            os.unlink(path)

    @staticmethod
    def _has(issues, *, level=None, category=None, fragment=None):
        """判断 issues 中是否存在满足条件的条目。"""
        for iss in issues:
            if level and iss["level"] != level:
                continue
            if category and iss["category"] != category:
                continue
            if fragment and fragment not in iss["message"]:
                continue
            return True
        return False

    # ------------------------------------------------------------------
    # 1. 基本合法 Markdown
    # ------------------------------------------------------------------
    def test_basic_valid_markdown(self):
        content = (
            "# 绪论\n\n"
            "## 研究背景\n\n"
            "本研究基于前人工作[1]，探讨了纳米材料的合成方法。\n"
        )
        issues, stats = self._check(content)
        self.assertEqual(len(issues), 0, f"期望无问题，实际: {issues}")
        self.assertEqual(stats["heading_count"], 2)
        self.assertEqual(stats["citation_count"], 1)

    # ------------------------------------------------------------------
    # 2. 标题层级违规
    # ------------------------------------------------------------------
    def test_heading_too_deep(self):
        content = "# 标题\n\n#### 过深标题\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="error", category="标题层级"),
            f"应检测到 4 级标题错误: {issues}",
        )

    def test_heading_level_skip(self):
        content = "# 一级标题\n\n### 三级标题\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="warning", category="标题层级", fragment="跳"),
            f"应检测到标题层级跳跃警告: {issues}",
        )

    # ------------------------------------------------------------------
    # 3. 引用格式违规
    # ------------------------------------------------------------------
    def test_citation_chinese_comma(self):
        content = "# 标题\n\n实验结果见文献[1，2]。\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="error", category="引用格式"),
            f"应检测到中文逗号引用错误: {issues}",
        )

    def test_citation_missing_comma(self):
        content = "# 标题\n\n参考文献[1 2]中提到。\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="error", category="引用格式"),
            f"应检测到缺少逗号引用错误: {issues}",
        )

    def test_citation_unsorted(self):
        content = "# 标题\n\n如文献[2,1]所述。\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="warning", category="引用格式", fragment="升序"),
            f"应检测到引用编号未排序警告: {issues}",
        )

    # ------------------------------------------------------------------
    # 4. 写作风格违规
    # ------------------------------------------------------------------
    def test_style_em_dash(self):
        content = "# 标题\n\n这是一个测试——用于检测破折号。\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="error", category="标点规范"),
            f"应检测到破折号错误: {issues}",
        )

    def test_style_question_mark(self):
        content = "# 标题\n\n这种方法是否有效？\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="warning", category="陈述规范"),
            f"应检测到问句警告: {issues}",
        )

    def test_style_metaphor(self):
        content = "# 标题\n\n该材料如同催化剂一般发挥作用。\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="error", category="修辞规范"),
            f"应检测到比喻修辞错误: {issues}",
        )

    # ------------------------------------------------------------------
    # 5. 图表编号间断
    # ------------------------------------------------------------------
    def test_figure_numbering_gap(self):
        content = "# 标题\n\n如图1-1所示，结果良好。\n\n如图1-3所示，进一步验证。\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="warning", category="图表编号", fragment="图"),
            f"应检测到图编号不连续警告: {issues}",
        )

    def test_table_numbering_gap(self):
        content = "# 标题\n\n见表2-1的数据。\n\n表2-3列出了对比结果。\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="warning", category="图表编号", fragment="表"),
            f"应检测到表编号不连续警告: {issues}",
        )

    # ------------------------------------------------------------------
    # 6. 列表项检测
    # ------------------------------------------------------------------
    def test_list_dash(self):
        content = "# 标题\n\n- 这是一个列表项\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="warning", category="列表项"),
            f"应检测到列表项警告: {issues}",
        )

    def test_list_numbered(self):
        content = "# 标题\n\n1. 第一条内容\n"
        issues, _ = self._check(content)
        self.assertTrue(
            self._has(issues, level="warning", category="列表项"),
            f"应检测到有序列表项警告: {issues}",
        )

    def test_list_inside_code_block_ignored(self):
        content = "# 标题\n\n```\n- 代码中的列表\n1. 代码中的有序列表\n```\n"
        issues, _ = self._check(content)
        list_issues = [i for i in issues if i["category"] == "列表项"]
        self.assertEqual(
            len(list_issues), 0,
            f"代码块内的列表不应被报告: {list_issues}",
        )

    # ------------------------------------------------------------------
    # 7. 代码块排除（综合）
    # ------------------------------------------------------------------
    def test_code_block_excludes_all_violations(self):
        content = (
            "# 标题\n\n"
            "正常段落内容。\n\n"
            "```\n"
            "这里有破折号——不应报告\n"
            "引用[1，2]不应报告\n"
            "- 列表项不应报告\n"
            "```\n"
        )
        issues, _ = self._check(content)
        # 所有问题都不应来自代码块内容
        for iss in issues:
            self.assertNotIn("不应报告", iss["message"],
                             f"代码块内的违规不应被检测: {iss}")


if __name__ == "__main__":
    unittest.main()
