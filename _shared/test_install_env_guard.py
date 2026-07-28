#!/usr/bin/env python3
"""install_gate_hook 的"这台机器在不在用 Claude Code"判据自检。stdlib-only,无 fixture。

背景:8 家技能同时被镜像到 ~/.codex/skills 与 ~/.config/opencode/skills,而那两个运行端
从不读 ~/.claude/settings.json。安装器若无脑照装,会在纯 Codex 机器上凭空创建 ~/.claude/
塞一堆没人读的文件。判据必须满足:①不能拿安装器自己的产物当证据(否则装过一次就永远为真);
②宁可误判成"装了"也不能把真 Claude Code 用户的门禁关掉。

每个场景都在**假 HOME + 洗干净的 PATH/环境变量**里跑真安装器,绝不碰真实 ~/.claude。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SHARED = Path(__file__).resolve().parent
INSTALLER = SHARED / "install_gate_hook.py"
PY = sys.executable or "python3"
HOOK_TAG = "academic_gate_hook.py"


def _fake_bin(root: Path) -> Path:
    """只放 python3 的 PATH:安装器要靠它探解释器,但不能让它探到真机上的 claude 命令。"""
    d = root / "fakebin"
    d.mkdir(parents=True, exist_ok=True)
    link = d / "python3"
    if not link.exists():
        link.symlink_to(PY)
    return d


def _run(home: Path, bindir: Path) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("CLAUDE") and k != "PATH"}
    env.update(HOME=str(home), USERPROFILE=str(home), PATH=str(bindir))
    p = subprocess.run([PY, str(INSTALLER)], capture_output=True, text=True, env=env)
    return json.loads(p.stdout.strip().splitlines()[-1])


def _our_settings(home: Path) -> None:
    """伪造"上一版安装器已经装过一次"的状态:settings.json 里只有我们自己写的 entry。"""
    (home / ".claude" / "academic-gate").mkdir(parents=True, exist_ok=True)
    (home / ".claude" / "settings.json").write_text(json.dumps(
        {"hooks": {"PreToolUse": [{"matcher": "Write|Edit", "hooks": [
            {"type": "command", "command": f'python3 "{home}/.claude/academic-gate/{HOOK_TAG}"'}]}]}}
    ), encoding="utf-8")


def test_pure_codex_machine_skips_and_writes_nothing():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        home = root / "home"
        home.mkdir()
        res = _run(home, _fake_bin(root))
        assert res["action"] == "skipped-no-claude-code", res
        assert res["status"] == "degraded", res
        assert "不生效" in res["message"], res
        assert not (home / ".claude").exists(), "跳过时不得凭空创建 ~/.claude/"


def test_skip_is_not_self_fulfilling():
    """装过一次之后(~/.claude 里只有安装器自己的产物)必须仍然跳过——否则判据等于没判。"""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        home = root / "home"
        home.mkdir()
        _our_settings(home)
        res = _run(home, _fake_bin(root))
        assert res["action"] == "skipped-no-claude-code", res


def test_real_claude_user_still_installs():
    """~/.claude/settings.json 里有用户自己的配置 = 真 Claude Code 用户,必须照常安装。"""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        home = root / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text(
            json.dumps({"model": "opusplan", "hooks": {"PostToolUse": []}}), encoding="utf-8")
        res = _run(home, _fake_bin(root))
        assert res["status"] == "installed", res
        settings = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
        assert settings["model"] == "opusplan", "用户原有配置必须原样保留"
        cmds = [h["command"] for e in settings["hooks"]["PreToolUse"] for h in e["hooks"]]
        assert len(cmds) == 1 and HOOK_TAG in cmds[0], cmds


def test_other_claude_artifacts_are_evidence():
    """~/.claude/ 下任何不是安装器造的东西(projects/ 等)都算证据。"""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        home = root / "home"
        (home / ".claude" / "projects").mkdir(parents=True)
        res = _run(home, _fake_bin(root))
        assert res["status"] == "installed", res


def test_plugin_branch_wins_over_env_guard():
    """插件在场:优先级不变,照走 plugin 让位分支(且不部署 academic-gate/)。"""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        home = root / "home"
        plug = home / ".claude" / "skills" / "academic-gate"
        (plug / ".claude-plugin").mkdir(parents=True)
        (plug / "scripts").mkdir(parents=True)
        (plug / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
        (plug / "scripts" / HOOK_TAG).write_text("", encoding="utf-8")
        (home / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
        res = _run(home, _fake_bin(root))
        assert res["action"] == "plugin", res
        assert not (home / ".claude" / "academic-gate").exists(), "插件在场不得部署 legacy 四件套"


def test_claude_env_var_alone_is_evidence():
    """空 HOME + 只有 CLAUDECODE=1(正跑在 Claude Code 里)→ 必须装,不能误判成没装。"""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        home = root / "home"
        home.mkdir()
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("CLAUDE") and k != "PATH"}
        env.update(HOME=str(home), USERPROFILE=str(home),
                   PATH=str(_fake_bin(root)), CLAUDECODE="1")
        p = subprocess.run([PY, str(INSTALLER)], capture_output=True, text=True, env=env)
        res = json.loads(p.stdout.strip().splitlines()[-1])
        assert res["status"] == "installed", res


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("ALL PASS")
