#!/usr/bin/env python3
"""统一开工前环境预检（全部学术技能共用，字节一致分发）。

软门禁语义：检测 OS / Python / git（+ 技能可选工具），写 <root>/env_status.json，
末行打印机器可读状态 `PRECHECK: OK | ASK | BLOCKED`。
- 必需缺失（Python 过低）          -> BLOCKED，exit 1，引导升级。
- 可选缺失（git / 技能传入的工具） -> ASK，  exit 0，列出缺项 + 安装指引（由 SKILL 逐项问用户）。
- 全齐                              -> OK，   exit 0。

用法:
  python3 env_preflight.py [root]                      # 仅 Python+git
  python3 env_preflight.py [root] --cli esearch,blastn # 额外检 CLI（shutil.which）
  python3 env_preflight.py [root] --py pyzotero,docx   # 额外检 Python 模块（可导入）
"""
import sys
import json
import shutil
import platform
import importlib.util
from pathlib import Path

MIN_PY = (3, 7)

INSTALL_HINT = {
    "git": {"Darwin": "brew install git", "Linux": "sudo apt install git", "Windows": "winget install Git.Git"},
    "esearch": {"_": 'sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"（Windows 需 WSL）'},
    "pyzotero": {"_": "pip install pyzotero"},
    "docx": {"_": "pip install python-docx"},
}


def hint(tool: str, osname: str) -> str:
    h = INSTALL_HINT.get(tool, {})
    return h.get(osname) or h.get("_") or f"自行安装 {tool}"


def parse_list(flag: str, argv) -> list:
    if flag in argv:
        raw = argv[argv.index(flag) + 1]
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def main():
    argv = sys.argv[1:]
    root = Path(argv[0]).expanduser() if argv and not argv[0].startswith("--") else Path.cwd()
    cli_tools = parse_list("--cli", argv)
    py_mods = parse_list("--py", argv)

    ver = sys.version_info
    osname = platform.system()
    git_available = shutil.which("git") is not None

    missing = []  # (tool, hint)
    if not git_available:
        missing.append(("git", hint("git", osname)))
    for t in cli_tools:
        if shutil.which(t) is None:
            missing.append((t, hint(t, osname)))
    for m in py_mods:
        if importlib.util.find_spec(m) is None:
            missing.append((m, hint(m, osname)))

    root.mkdir(parents=True, exist_ok=True)
    (root / "env_status.json").write_text(
        json.dumps(
            {
                "os": osname,
                "python": f"{ver.major}.{ver.minor}.{ver.micro}",
                "git_available": git_available,
                "missing_optional": [t for t, _ in missing],
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    print(f"OS: {osname} | Python {ver.major}.{ver.minor}.{ver.micro}")
    if ver < MIN_PY:
        print(f"❌ 需要 Python {MIN_PY[0]}.{MIN_PY[1]}+ — 升级: python.org / brew install python / winget install Python.Python.3")
        print("PRECHECK: BLOCKED")
        return 1
    print("✅ Python OK")

    for tool, h in missing:
        print(f"⚠️ 缺 {tool} — 安装: {h}")
    if missing:
        print("PRECHECK: ASK " + ",".join(t for t, _ in missing))
    else:
        print("PRECHECK: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
