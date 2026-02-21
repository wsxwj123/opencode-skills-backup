#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci2Doc thesis profile helpers.

统一维护论文目标参数，避免文档规范与脚本阈值冲突。
"""

import json
import os
import tempfile


DEFAULT_PROFILE = {
    "schema_version": "1.0",
    "language": "zh-CN",
    "targets": {
        "body_target_chars": 80000,
        "abstract_min_chars": 1500,
        "abstract_max_chars": 2500,
        "review_in_scope": False,
        "review_target_chars": 0,
        "references_min_count": 80,
        "min_chapters": 5,
    },
    "chapter_targets": {},
    "structure": {
        "pattern": "intro + research_chapters + conclusion",
        "research_chapter_required_sections": [
            "引言",
            "材料与方法",
            "结果与讨论",
            "实验结论",
            "小结",
        ],
    },
    "rules": {
        "references_at_end": True,
        "atomic_md_required": True,
        "experiment_one_figure_or_table": True,
        "result_discussion_linked_to_methods": True,
        "self_check_after_chapter": True,
        "snapshot_after_section_summary": True,
        "humanizer_required": True,
    },
}


def resolve_profile_path(project_root, profile_path=None):
    if profile_path:
        return profile_path if os.path.isabs(profile_path) else os.path.abspath(os.path.join(project_root, profile_path))
    return os.path.abspath(os.path.join(project_root, "thesis_profile.json"))


def deep_merge(base, override):
    if not isinstance(base, dict):
        return override
    if not isinstance(override, dict):
        return base
    merged = dict(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_profile(project_root, profile_path=None):
    path = resolve_profile_path(project_root, profile_path)
    if not os.path.exists(path):
        return deep_merge(DEFAULT_PROFILE, {}), path
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return deep_merge(DEFAULT_PROFILE, payload), path


def save_profile(path, profile):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_profile_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def parse_chapter_target_spec(spec):
    """
    Parse '2:12000' -> ('2', 12000).
    """
    if ":" not in spec:
        raise ValueError("chapter target must use '<chapter>:<chars>' format")
    chapter, value = spec.split(":", 1)
    chapter = str(chapter).strip()
    chars = int(value)
    if chars <= 0:
        raise ValueError("chapter target chars must be positive")
    return chapter, chars

