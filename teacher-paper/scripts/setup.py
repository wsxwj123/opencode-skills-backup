#!/usr/bin/env python3
"""
环境自检与准备 —— teacher-paper skill 启动第一步（跨 agent / 跨平台通用）

为什么需要它：本 skill 可能被任意 AI agent 在任意电脑上调用，
不能假设脚本装在某个固定目录，也不能假设依赖都已就绪。
启动时先跑本脚本：① 定位 skill 自身路径 ② 检查 Python 依赖 ③ 全盘探测可选外部工具
④ 给出"缺什么、装什么"的明确清单，必要处自动安装。

用法：
    python3 <本脚本所在目录>/setup.py            # 只体检，不自动装
    python3 <本脚本所在目录>/setup.py --install   # 体检并自动 pip 安装缺失的必需依赖
    python3 <本脚本所在目录>/setup.py --json       # 机器可读输出，供 agent 解析

设计要点：
- skill 路径用本文件的 __file__ 自解析，**不写死任何绝对路径**。
- 全盘扫描可选外部工具（如内容抓取增强工具），有就用、没有不强求。
- 只把"生成 Word 必需"的依赖列为必需；识图/抓取增强类列为可选。
"""
import sys
import os
import json
import shutil
import subprocess

# —— skill 自身路径：本文件在 <SKILL_DIR>/scripts/setup.py ——
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)

# 必需依赖：缺了核心功能（生成 Word / 组卷）就跑不动
REQUIRED = [
    ("docx", "python-docx", "生成 Word 试卷与答案、读取 .docx 素材"),
]
# 可选依赖：按素材类型/模型能力按需，缺了只影响对应分支
OPTIONAL = [
    ("pdfplumber", "pdfplumber", "读取 PDF 素材（含表格）"),
    ("pptx", "python-pptx", "读取 PPT 课件素材"),
    ("openpyxl", "openpyxl", "读取 Excel 表格素材"),
    ("readability", "readability-lxml", "网页正文提取（抓取第2策略）"),
    ("rapidocr_onnxruntime", "rapidocr-onnxruntime",
     "图片OCR兜底（仅当模型不能直接识图时需要）"),
]
# 本 skill 自带的脚本，逐个核对是否齐全（防止文件缺失）
SELF_SCRIPTS = ["read_material.py", "fetch_web.py", "ocr_image.py",
                "assemble.py", "make_paper.py"]
# 可选的外部命令行工具（增强能力，全盘探测，有就用没有不强求）
EXTERNAL_TOOLS = ["pandoc", "soffice", "tesseract"]


def _importable(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def _pip_install(pkgs):
    cmd = [sys.executable, "-m", "pip", "install", *pkgs]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode == 0, (r.stdout + r.stderr)[-800:]
    except Exception as e:
        return False, str(e)


def _scan_disk_for(names, max_hits=3):
    """全盘探测某个可执行文件名（优先 PATH，再有限度扫常见根目录）。
    返回找到的绝对路径列表。先用 which，命中即返回；否则浅扫常见安装根。"""
    hits = []
    for n in names:
        p = shutil.which(n)
        if p:
            hits.append(p)
    if hits:
        return hits
    # PATH 没有 → 在常见安装根做有限深度扫描（避免真的遍历整盘耗时）
    roots = [os.path.expanduser("~"), "/usr/local", "/opt", "/Applications",
             "/usr/bin", "C:\\Program Files", "C:\\Program Files (x86)"]
    targets = set()
    for n in names:
        targets.add(n)
        targets.add(n + ".exe")
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # 控制深度，最多向下 4 层，跳过隐藏/缓存目录
            depth = dirpath[len(root):].count(os.sep)
            if depth > 4:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".") and
                           d not in ("node_modules", "__pycache__", "Library")]
            for fn in filenames:
                if fn in targets:
                    hits.append(os.path.join(dirpath, fn))
                    if len(hits) >= max_hits:
                        return hits
    return hits


def _detect_desktop():
    """跨平台探测桌面（与 assemble.py 同逻辑，便于报告默认工程位置）。"""
    home = os.path.expanduser("~")
    if os.name == "nt":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            val, _ = winreg.QueryValueEx(key, "Desktop")
            winreg.CloseKey(key)
            val = os.path.expandvars(val)
            if os.path.isdir(val):
                return val
        except Exception:
            pass
    for c in (os.path.join(home, "Desktop"), os.path.join(home, "桌面"),
              os.path.join(home, "OneDrive", "Desktop"),
              os.path.join(home, "OneDrive", "桌面")):
        if os.path.isdir(c):
            return c
    return None


def run(install=False):
    report = {"skill_dir": SKILL_DIR, "scripts_dir": SCRIPTS_DIR,
              "python": sys.version.split()[0],
              "desktop": _detect_desktop() or "(未探测到，将回退当前目录)",
              "required": [], "optional": [], "self_scripts": [],
              "external_tools": [], "missing_required": [], "actions": []}

    # 1) 自带脚本齐全性
    for s in SELF_SCRIPTS:
        ok = os.path.exists(os.path.join(SCRIPTS_DIR, s))
        report["self_scripts"].append({"name": s, "present": ok})

    # 2) 必需依赖
    missing_req_pkgs = []
    for mod, pkg, desc in REQUIRED:
        ok = _importable(mod)
        report["required"].append({"module": mod, "package": pkg,
                                   "desc": desc, "installed": ok})
        if not ok:
            missing_req_pkgs.append(pkg)
            report["missing_required"].append(pkg)

    # 3) 可选依赖
    for mod, pkg, desc in OPTIONAL:
        ok = _importable(mod)
        report["optional"].append({"module": mod, "package": pkg,
                                   "desc": desc, "installed": ok})

    # 4) 全盘探测外部工具
    for tool in EXTERNAL_TOOLS:
        found = _scan_disk_for([tool])
        report["external_tools"].append(
            {"name": tool, "found": bool(found),
             "path": found[0] if found else ""})

    # 5) 自动安装必需依赖
    if install and missing_req_pkgs:
        ok, log = _pip_install(missing_req_pkgs)
        report["actions"].append(
            {"action": "pip install", "packages": missing_req_pkgs,
             "success": ok, "log_tail": log})
        if ok:
            # pip 刚装的包在本进程 import 缓存里可能仍显示缺失，需失效缓存后复测；
            # 用子进程做权威验证，避免同进程缓存假阴性。
            import importlib
            importlib.invalidate_caches()
            still_missing = []
            for p in report["missing_required"]:
                mod = next(m for m, pk, _ in REQUIRED if pk == p)
                check = subprocess.run(
                    [sys.executable, "-c", f"import {mod}"],
                    capture_output=True)
                if check.returncode != 0:
                    still_missing.append(p)
            report["missing_required"] = still_missing

    return report


def _print_human(rep):
    print(f"# teacher-paper 环境自检")
    print(f"skill 目录：{rep['skill_dir']}")
    print(f"Python：{rep['python']}")
    print(f"默认工程位置（未指定时建在此桌面下）：{rep['desktop']}\n")

    print("自带脚本：")
    for s in rep["self_scripts"]:
        print(f"  [{'✓' if s['present'] else '✗ 缺失'}] {s['name']}")

    print("\n必需依赖（生成试卷必须）：")
    for r in rep["required"]:
        print(f"  [{'✓' if r['installed'] else '✗'}] {r['package']}　{r['desc']}")

    print("\n可选依赖（按需）：")
    for o in rep["optional"]:
        print(f"  [{'✓' if o['installed'] else '·'}] {o['package']}　{o['desc']}")

    print("\n外部工具（全盘探测，有则增强）：")
    for t in rep["external_tools"]:
        loc = t["path"] if t["found"] else "未找到（可不装）"
        print(f"  [{'✓' if t['found'] else '·'}] {t['name']}　{loc}")

    if rep["actions"]:
        for a in rep["actions"]:
            tag = "成功" if a["success"] else "失败"
            print(f"\n[自动安装 {tag}] {' '.join(a['packages'])}")

    if rep["missing_required"]:
        print("\n🔴 必需依赖未就绪：" + ", ".join(rep["missing_required"]))
        print("   运行：python3 \"%s\" --install  自动安装；"
              % os.path.join(rep["scripts_dir"], "setup.py"))
        print("   或手动：pip3 install " + " ".join(rep["missing_required"]))
    else:
        print("\n✅ 必需依赖齐全，可以开始出卷。")
    # 缺失的自带脚本提示
    miss_self = [s["name"] for s in rep["self_scripts"] if not s["present"]]
    if miss_self:
        print("🔴 自带脚本缺失：" + ", ".join(miss_self) + "（请重新获取完整 skill）")


def main():
    install = "--install" in sys.argv
    as_json = "--json" in sys.argv
    rep = run(install=install)
    if as_json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        _print_human(rep)
    # 必需依赖或脚本缺失 → 非零退出，便于 agent 判断
    bad = rep["missing_required"] or [
        s for s in rep["self_scripts"] if not s["present"]]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
