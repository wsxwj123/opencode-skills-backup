#!/usr/bin/env python3
"""可移植的解释器解析：让裸 `python3` 自动落到"playwright 能用且浏览器齐"的解释器。

背景：一台机器可能装了多套各自 pin 不同 chromium build 的 playwright/patchright，
共用一个浏览器缓存目录。裸 `python3` 命中谁取决于 PATH，于是"这边能跑那边报找不到"。
本模块在脚本入口调一次 ensure_resolved()，按优先级挑一个"就绪"的解释器并 os.execv 重入，
从此 PATH 谁在前都无所谓。对没配 venv/环境变量的机器完全透明（自动跳过，兜底裸 python3）。

候选优先级（命中即停）：
  1. 环境变量 FETCH_PY 指定的解释器（显式覆盖，存在即用，不做就绪判定）
  2. 约定 venv ~/.venvs/fetch/bin/python（存在且就绪才用；别人机器上不存在→自动跳过）
  3. [sys.executable, which(python3), which(python)] 去重后逐个测"就绪"
  4. 兜底 sys.executable（即裸 python3 现状，至少不比现在差）

"就绪"判据 = 该解释器能 import playwright 且其 browsers.json 里 pin 的 chromium build
目录在浏览器缓存中真实存在（纯文件判断，不启动浏览器）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

SENTINEL = "FETCH_PY_RESOLVED"  # 哨兵：重入后置 1，防 execv 死循环
VENV_PYTHON = os.path.expanduser("~/.venvs/fetch/bin/python")  # 约定路径，存在才用

# 在候选解释器里运行的就绪探针：读 playwright 的 browsers.json 取 chromium revision，
# 再查各标准缓存目录是否有 chromium-<rev>。返回码 0=就绪，非 0=不就绪。
_READY_PROBE = r"""
import json, os, sys
try:
    import playwright
except Exception:
    sys.exit(1)
pkg = os.path.dirname(playwright.__file__)
try:
    with open(os.path.join(pkg, "driver", "package", "browsers.json")) as f:
        data = json.load(f)
except Exception:
    sys.exit(1)
rev = next((b.get("revision") for b in data.get("browsers", [])
            if b.get("name") == "chromium"), None)
if not rev:
    sys.exit(1)
bases = []
if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    bases.append(os.environ["PLAYWRIGHT_BROWSERS_PATH"])
bases += [
    os.path.expanduser("~/Library/Caches/ms-playwright"),   # macOS
    os.path.expanduser("~/.cache/ms-playwright"),           # Linux
    os.path.expandvars(r"%USERPROFILE%\AppData\Local\ms-playwright"),  # Windows
]
sys.exit(0 if any(os.path.isdir(os.path.join(b, "chromium-" + str(rev)))
                  for b in bases) else 2)
"""


def _is_ready(python_exe: str) -> bool:
    try:
        r = subprocess.run([python_exe, "-c", _READY_PROBE],
                           capture_output=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


def candidates() -> list:
    """按优先级返回候选解释器路径（去重，不做就绪过滤，便于自检断言顺序）。"""
    out, seen = [], set()

    def add(p):
        if not p:
            return
        rp = os.path.realpath(p)
        if rp in seen or not os.path.exists(p):
            return
        seen.add(rp)
        out.append(p)

    add(os.environ.get("FETCH_PY"))
    add(VENV_PYTHON)
    add(sys.executable)
    add(shutil.which("python3"))
    add(shutil.which("python"))
    return out


def resolve() -> str:
    """返回一个就绪的解释器路径；全不就绪则兜底 sys.executable。

    FETCH_PY 为显式覆盖：只要设置且存在就直接用（信任用户，不做就绪判定）。
    其余候选逐个测就绪，命中即停。
    """
    fetch_py = os.environ.get("FETCH_PY")
    if fetch_py and os.path.exists(fetch_py):
        return fetch_py
    for c in candidates():
        if _is_ready(c):
            return c
    return sys.executable


def ensure_resolved() -> None:
    """在脚本入口调一次：若当前解释器不是选中的就绪解释器，os.execv 重入。
    幂等，靠 FETCH_PY_RESOLVED 哨兵防重入死循环。"""
    if os.environ.get(SENTINEL):
        return
    chosen = resolve()
    os.environ[SENTINEL] = "1"
    if os.path.realpath(chosen) != os.path.realpath(sys.executable):
        os.execv(chosen, [chosen] + sys.argv)


def _selftest() -> None:
    """自检：候选顺序 + 哨兵防重入。不依赖真实 venv/浏览器。"""
    # 1) 哨兵已置位 → ensure_resolved 立即返回（不 execv、不抛异常）
    saved = dict(os.environ)
    try:
        os.environ[SENTINEL] = "1"
        ensure_resolved()  # 不应重入，能返回即通过
        # 2) FETCH_PY 存在时 resolve 无条件优先返回它
        os.environ.pop(SENTINEL, None)
        os.environ["FETCH_PY"] = sys.executable
        assert resolve() == sys.executable, "FETCH_PY 显式覆盖未生效"
        assert candidates()[0] == sys.executable, "FETCH_PY 未排在候选首位"
        # 3) 不存在的 FETCH_PY 不被采纳，且不进候选
        os.environ["FETCH_PY"] = "/no/such/python-xyz"
        assert "/no/such/python-xyz" not in candidates(), "不存在路径不应进候选"
        # 4) 未设约定 venv 时兜底 sys.executable（当前机器若装了 playwright 也可能返回自身，二者都可接受）
        os.environ.pop("FETCH_PY", None)
        r = resolve()
        assert os.path.exists(r), "resolve 返回了不存在的解释器"
    finally:
        os.environ.clear()
        os.environ.update(saved)
    print("SELFTEST_OK resolved=" + resolve())


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(resolve())
