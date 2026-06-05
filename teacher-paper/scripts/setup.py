#!/usr/bin/env python3
"""
环境自检与准备 —— teacher-paper skill 启动第一步（跨 agent / 跨平台通用）

为什么需要它：本 skill 可能被任意 AI agent 在任意电脑上调用，
不能假设脚本装在某个固定目录，也不能假设依赖都已就绪。
启动时先跑本脚本：① 定位 skill 自身路径 ② 扫描多个 Python 解释器
③ 探测本机 CLI / Office / OCR 工具 ④ 推荐当前电脑最稳的 Word 生成后端。

用法：
    python3 <本脚本所在目录>/setup.py            # 只体检，不自动装
    python3 <本脚本所在目录>/setup.py --install   # 仅当没有稳定后端时安装兜底依赖
    python3 <本脚本所在目录>/setup.py --json       # 机器可读输出，供 agent 解析

设计要点：
- skill 路径用本文件的 __file__ 自解析，**不写死任何绝对路径**。
- MCP / 插件属于当前 AI agent 的会话能力，Python 脚本无法可靠枚举；
  这些能力由 SKILL.md 指挥 agent 在脚本外检查。
- python-docx 是最小稳定兜底，不是唯一 Word 方案；已有 Pandoc / Office
  转换工具时先报告可用路径，不抢先安装。
"""
import sys
import os
import json
import shutil
import subprocess
import platform
import glob

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
# 可选的外部命令行工具（增强能力，有就用没有不强求）
CLI_TOOL_GROUPS = [
    ("pandoc", ["pandoc"], "Markdown/HTML 转 DOCX，可配 reference.docx 模板"),
    ("libreoffice", ["soffice", "libreoffice"], "Office 格式转换、DOCX/PDF 渲染校验"),
    ("tesseract", ["tesseract"], "OCR 兜底"),
    ("textutil", ["textutil"], "macOS 自带文本/RTF/DOCX 转换兜底"),
    ("qlmanage", ["qlmanage"], "macOS 快速预览/导出辅助"),
    ("powershell", ["pwsh", "powershell"], "Windows 脚本/Office COM 兜底"),
]


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


def _dedupe(seq):
    seen = set()
    out = []
    for item in seq:
        key = tuple(item) if isinstance(item, list) else item
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _python_candidates():
    """Return executable command lists for Python interpreters worth probing."""
    candidates = [[sys.executable]]
    for name in ("python3", "python"):
        p = shutil.which(name)
        if p:
            candidates.append([p])
    if os.name == "nt":
        py = shutil.which("py")
        if py:
            candidates.append([py, "-3"])
    env_python = os.environ.get("PYTHON")
    if env_python:
        candidates.append([env_python])
    return _dedupe([c for c in candidates if c and c[0]])


def _probe_python(cmd):
    mods = [m for m, _, _ in REQUIRED + OPTIONAL]
    code = (
        "import json, sys\n"
        f"mods = {mods!r}\n"
        "data = {'executable': sys.executable, "
        "'version': sys.version.split()[0], 'modules': {}}\n"
        "for mod in mods:\n"
        "    try:\n"
        "        __import__(mod)\n"
        "        data['modules'][mod] = True\n"
        "    except Exception:\n"
        "        data['modules'][mod] = False\n"
        "print(json.dumps(data, ensure_ascii=False))\n"
    )
    try:
        r = subprocess.run(cmd + ["-c", code], capture_output=True, text=True,
                           timeout=12)
    except Exception as e:
        return {"command": " ".join(cmd), "available": False, "error": str(e)}
    if r.returncode != 0:
        return {"command": " ".join(cmd), "available": False,
                "error": (r.stderr or r.stdout).strip()[-300:]}
    try:
        data = json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"command": " ".join(cmd), "available": False,
                "error": "无法解析 Python 探测输出"}
    data["command"] = " ".join(cmd)
    data["available"] = True
    data["has_docx"] = bool(data["modules"].get("docx"))
    return data


def _scan_cli_tools():
    tools = []
    for name, aliases, desc in CLI_TOOL_GROUPS:
        found = []
        for alias in aliases:
            p = shutil.which(alias)
            if p:
                found.append({"name": alias, "path": p})
        tools.append({"name": name, "aliases": aliases, "desc": desc,
                      "found": bool(found), "matches": found,
                      "path": found[0]["path"] if found else ""})
    return tools


def _detect_office_apps():
    """Best-effort Office app detection. These apps are enhancement paths."""
    apps = []
    system = platform.system().lower()
    if system == "darwin":
        checks = [
            ("microsoft_word", ["/Applications/Microsoft Word.app"]),
            ("libreoffice", ["/Applications/LibreOffice.app"]),
            ("wps_office", ["/Applications/wpsoffice.app",
                            "/Applications/WPS Office.app"]),
            ("pages", ["/Applications/Pages.app"]),
        ]
    elif system == "windows":
        roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("LOCALAPPDATA", "")]
        checks = [
            ("microsoft_word", ["Microsoft Office/root/Office*/WINWORD.EXE",
                                "Microsoft Office/Office*/WINWORD.EXE"]),
            ("libreoffice", ["LibreOffice/program/soffice.exe"]),
            ("wps_office", ["Kingsoft/WPS Office/*/office6/wps.exe",
                            "WPS Office/*/office6/wps.exe"]),
        ]
        expanded = []
        for name, rels in checks:
            paths = []
            for root in roots:
                if not root:
                    continue
                for rel in rels:
                    paths.extend(glob.glob(os.path.join(root, rel)))
            expanded.append((name, paths))
        checks = expanded
    else:
        checks = [
            ("libreoffice", [shutil.which("soffice") or "",
                             shutil.which("libreoffice") or ""]),
            ("wps_office", [shutil.which("wps") or ""]),
        ]
    for name, paths in checks:
        hits = [p for p in paths if p and os.path.exists(p)]
        apps.append({"name": name, "found": bool(hits),
                     "path": hits[0] if hits else ""})
    return apps


def _tool_found(tools, name):
    return any(t["name"] == name and t["found"] for t in tools)


def _recommend_backend(pythons, cli_tools, office_apps):
    docx_python = next((p for p in pythons if p.get("available")
                        and p.get("has_docx")), None)
    if docx_python:
        return {
            "name": "python-docx",
            "status": "ready",
            "reason": "已有 Python 解释器可 import docx，使用自带 make_paper.py 最稳定。",
            "command": docx_python["command"],
            "install_required": False,
        }
    if _tool_found(cli_tools, "pandoc"):
        return {
            "name": "pandoc-docx",
            "status": "fallback-ready",
            "reason": "未发现 python-docx，但已发现 Pandoc，可由 Markdown 中间产物转 DOCX。",
            "command": "pandoc",
            "install_required": False,
        }
    if _tool_found(cli_tools, "textutil"):
        return {
            "name": "macos-textutil-docx",
            "status": "low-fidelity-ready",
            "reason": "未发现 python-docx/Pandoc，但 macOS textutil 可做低保真 DOCX 兜底。",
            "command": "textutil",
            "install_required": False,
        }
    office = next((a for a in office_apps if a["found"]), None)
    if office:
        return {
            "name": "office-app-assisted",
            "status": "manual-or-agent-assisted",
            "reason": f"发现 {office['name']}，可用于转换/后处理，但不作为唯一自动生成路径。",
            "command": office["path"],
            "install_required": False,
        }
    return {
        "name": "install-python-docx",
        "status": "install-needed",
        "reason": "未发现稳定 DOCX 生成后端，建议安装最小兜底依赖 python-docx。",
        "command": sys.executable,
        "install_required": True,
    }


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
              "os": {"name": platform.system(), "platform": platform.platform()},
              "python": sys.version.split()[0],
              "desktop": _detect_desktop() or "(未探测到，将回退当前目录)",
              "required": [], "optional": [], "self_scripts": [],
              "python_backends": [], "external_tools": [], "office_apps": [],
              "recommended_backend": {}, "install_plan": [],
              "missing_required": [], "actions": []}

    # 1) 自带脚本齐全性
    for s in SELF_SCRIPTS:
        ok = os.path.exists(os.path.join(SCRIPTS_DIR, s))
        report["self_scripts"].append({"name": s, "present": ok})

    # 2) 扫描多个 Python 解释器，避免把"当前 python 缺包"误判为"整机缺包"
    probed = []
    seen_exec = set()
    for cmd in _python_candidates():
        info = _probe_python(cmd)
        key = info.get("executable") or info.get("command")
        if key in seen_exec:
            continue
        seen_exec.add(key)
        probed.append(info)
    report["python_backends"] = probed
    current_modules = next((p.get("modules", {}) for p in probed
                            if p.get("executable") == sys.executable), {})

    # 3) 必需/可选依赖：这里报告当前解释器状态；后端推荐会看所有解释器
    for mod, pkg, desc in REQUIRED:
        ok = bool(current_modules.get(mod)) if current_modules else _importable(mod)
        report["required"].append({"module": mod, "package": pkg,
                                   "desc": desc, "installed": ok})

    for mod, pkg, desc in OPTIONAL:
        ok = bool(current_modules.get(mod)) if current_modules else _importable(mod)
        report["optional"].append({"module": mod, "package": pkg,
                                   "desc": desc, "installed": ok})

    # 4) 探测 CLI / Office 应用
    report["external_tools"] = _scan_cli_tools()
    report["office_apps"] = _detect_office_apps()
    report["recommended_backend"] = _recommend_backend(
        report["python_backends"], report["external_tools"], report["office_apps"])
    if report["recommended_backend"].get("install_required"):
        report["missing_required"].append("python-docx")
        report["install_plan"].append({
            "command": f"{sys.executable} -m pip install python-docx",
            "reason": "没有发现可直接使用的稳定 DOCX 生成后端",
        })

    # 5) 自动安装兜底依赖：只有推荐后端明确要求安装时才执行
    if install and report["recommended_backend"].get("install_required"):
        ok, log = _pip_install(["python-docx"])
        report["actions"].append(
            {"action": "pip install", "packages": ["python-docx"],
             "success": ok, "log_tail": log})
        if ok:
            # pip 刚装的包在本进程 import 缓存里可能仍显示缺失，需子进程复测。
            import importlib
            importlib.invalidate_caches()
            check = subprocess.run([sys.executable, "-c", "import docx"],
                                   capture_output=True)
            if check.returncode == 0:
                report["missing_required"] = []
                report["recommended_backend"] = {
                    "name": "python-docx",
                    "status": "ready",
                    "reason": "已安装 python-docx，可使用 make_paper.py。",
                    "command": sys.executable,
                    "install_required": False,
                }

    return report


def _print_human(rep):
    print(f"# teacher-paper 环境自检")
    print(f"skill 目录：{rep['skill_dir']}")
    print(f"系统：{rep['os']['platform']}")
    print(f"当前 Python：{rep['python']}")
    print(f"默认工程位置（未指定时建在此桌面下）：{rep['desktop']}\n")

    print("自带脚本：")
    for s in rep["self_scripts"]:
        print(f"  [{'✓' if s['present'] else '✗ 缺失'}] {s['name']}")

    print("\nPython 解释器扫描：")
    for p in rep["python_backends"]:
        if not p.get("available"):
            print(f"  [·] {p.get('command')}　不可用：{p.get('error', '')}")
            continue
        mods = p.get("modules", {})
        marks = []
        for mod, pkg, _ in REQUIRED + OPTIONAL:
            marks.append(f"{pkg}:{'✓' if mods.get(mod) else '·'}")
        print(f"  [{'✓' if p.get('has_docx') else '·'}] {p['command']} "
              f"({p['version']})　" + " ".join(marks))

    print("\n当前 Python 依赖状态（仅代表当前解释器）：")
    for r in rep["required"]:
        print(f"  [{'✓' if r['installed'] else '✗'}] {r['package']}　{r['desc']}")

    print("\n可选依赖（按需）：")
    for o in rep["optional"]:
        print(f"  [{'✓' if o['installed'] else '·'}] {o['package']}　{o['desc']}")

    print("\nCLI 工具（有则增强，不强求）：")
    for t in rep["external_tools"]:
        loc = t["path"] if t["found"] else "未找到"
        print(f"  [{'✓' if t['found'] else '·'}] {t['name']}　{loc}　{t['desc']}")

    print("\nOffice 应用（转换/后处理增强）：")
    for a in rep["office_apps"]:
        loc = a["path"] if a["found"] else "未找到"
        print(f"  [{'✓' if a['found'] else '·'}] {a['name']}　{loc}")

    backend = rep.get("recommended_backend", {})
    print("\n推荐后端：")
    print(f"  {backend.get('name', 'unknown')} [{backend.get('status', 'unknown')}]")
    print(f"  {backend.get('reason', '')}")
    if backend.get("command"):
        print(f"  command: {backend['command']}")

    if rep["actions"]:
        for a in rep["actions"]:
            tag = "成功" if a["success"] else "失败"
            print(f"\n[自动安装 {tag}] {' '.join(a['packages'])}")

    if rep["missing_required"]:
        print("\n🔴 未发现稳定 DOCX 生成后端，建议安装兜底依赖："
              + ", ".join(rep["missing_required"]))
        print("   经用户确认后运行：python3 \"%s\" --install"
              % os.path.join(rep["scripts_dir"], "setup.py"))
        print("   或手动：" + rep["install_plan"][0]["command"])
    else:
        print("\n✅ 已找到可用出卷后端，可以开始出卷。")
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
