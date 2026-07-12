#!/usr/bin/env python3
"""共享门禁 hook 的离线自检：安装器 + 分发器 + 心跳。stdlib-only，无 fixture。
用 subprocess 跑真实脚本（连 stdin/settings.json 都真实走一遍），可跨平台。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SHARED = Path(__file__).resolve().parent
HOOK = SHARED / "academic_gate_hook.py"
INSTALLER = SHARED / "install_gate_hook.py"
PY = sys.executable or "python"


def _run_hook(payload: dict, env: dict | None = None) -> tuple[str, int]:
    p = subprocess.run([PY, str(HOOK)], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.stdout.strip(), p.returncode


SIGNOFF = SHARED / "structure_signoff_gate.py"


def _fake_project(tmp: Path, signed: bool) -> Path:
    """造一个 general-sci-writing 假项目：state 文件声明 skill；signed 决定是否
    已落结构签字。registry 现在跑共享的 structure_signoff check(粗粒度)，
    签字缺失→拦，存在→放行。managed_globs 命中 manuscripts/*.md。"""
    root = tmp / "proj"
    (root / "scripts").mkdir(parents=True)
    (root / "manuscripts").mkdir()
    (root / "writing_progress.json").write_text(
        json.dumps({"skill": "general-sci-writing", "phase": 8}), encoding="utf-8")
    if signed:
        subprocess.run([PY, str(SIGNOFF), "confirm", "--root", str(root),
                        "--note", "test"], capture_output=True, text=True)
    return root


def test_dispatcher_blocks_when_unsigned():
    with tempfile.TemporaryDirectory() as d:
        root = _fake_project(Path(d), signed=False)
        target = root / "manuscripts" / "03_3.2_Tumor.md"
        out, rc = _run_hook({"tool_name": "Write",
                             "tool_input": {"file_path": str(target)}})
        assert rc == 0, "hook 恒 exit 0"
        assert out, "结构未签字时应输出 deny JSON"
        obj = json.loads(out)
        assert obj["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "结构签字" in obj["hookSpecificOutput"]["permissionDecisionReason"]


def test_dispatcher_allows_when_signed():
    with tempfile.TemporaryDirectory() as d:
        root = _fake_project(Path(d), signed=True)
        target = root / "manuscripts" / "03_3.2_Tumor.md"
        out, rc = _run_hook({"tool_name": "Write",
                             "tool_input": {"file_path": str(target)}})
        assert rc == 0 and out == "", "已签字应放行(无输出)"


def test_dispatcher_ignores_nonmanaged_path():
    with tempfile.TemporaryDirectory() as d:
        root = _fake_project(Path(d), signed=False)
        # tmp/ 不在 managed_globs → 即便未签字也应放行
        target = root / "tmp" / "scratch.md"
        target.parent.mkdir()
        out, rc = _run_hook({"tool_name": "Write",
                             "tool_input": {"file_path": str(target)}})
        assert out == "", "非受管路径必须放行"


def test_dispatcher_ignores_non_academic_path():
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "some" / "random" / "file.md"
        target.parent.mkdir(parents=True)
        out, rc = _run_hook({"tool_name": "Edit",
                             "tool_input": {"file_path": str(target)}})
        assert out == "", "非学术项目必须放行"


def test_dispatcher_failopen_on_bad_stdin():
    p = subprocess.run([PY, str(HOOK)], input="not-json",
                       capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout.strip() == "", "坏输入必须静默放行"


def test_shared_state_file_disambiguation():
    """project_state.json 被 nsfc/sci2doc/revise/response 共用 → 靠被写文件命中谁的
    managed_globs 定技能。sections/*.md→nsfc(signoff→未签拦)；units/*.json→
    reviewer-response(无signoff→放行)。同一个项目根、同一个 state 文件，两种产物走两个技能。"""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "proj"
        (root / "sections").mkdir(parents=True)
        (root / "units").mkdir()
        (root / "project_state.json").write_text("{}", encoding="utf-8")
        # sections/*.md → nsfc(signoff) 未签字 → 拦
        out_n, _ = _run_hook({"tool_name": "Write",
                              "tool_input": {"file_path": str(root / "sections" / "P1.md")}})
        assert out_n and json.loads(out_n)["hookSpecificOutput"]["permissionDecision"] == "deny", \
            "sections/ 应被判为 nsfc 并因未签字拦下"
        # units/*.json → reviewer-response(无signoff) → 放行
        out_r, _ = _run_hook({"tool_name": "Write",
                              "tool_input": {"file_path": str(root / "units" / "001.json")}})
        assert out_r == "", "units/ 应被判为 reviewer-response(无signoff)并放行"


def test_signoff_gate_check_lifecycle():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # 未签字 → check exit 2
        r1 = subprocess.run([PY, str(SIGNOFF), "check", "--root", str(root)],
                            capture_output=True, text=True)
        assert r1.returncode == 2 and "结构签字缺失" in r1.stdout
        # confirm → check exit 0
        subprocess.run([PY, str(SIGNOFF), "confirm", "--root", str(root),
                        "--note", "用户确认了大纲"], capture_output=True, text=True)
        r2 = subprocess.run([PY, str(SIGNOFF), "check", "--root", str(root)],
                            capture_output=True, text=True)
        assert r2.returncode == 0
        # confirm 覆盖保留历史
        subprocess.run([PY, str(SIGNOFF), "confirm", "--root", str(root),
                        "--note", "大纲改了重新确认"], capture_output=True, text=True)
        data = json.loads((root / "structure_signoff.json").read_text())
        assert data["confirmed"] and len(data["history"]) == 1


def test_heartbeat_written_on_evaluation():
    with tempfile.TemporaryDirectory() as d:
        root = _fake_project(Path(d), signed=True)
        target = root / "manuscripts" / "results_1.1.md"
        hb = SHARED / "hook_heartbeat.json"
        before = hb.read_text() if hb.is_file() else None
        _run_hook({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert hb.is_file(), "评估学术产物后应写心跳"
        data = json.loads(hb.read_text())
        assert "last_fire_epoch" in data
        # 复原，避免污染真实心跳文件
        if before is not None:
            hb.write_text(before)
        else:
            hb.unlink()


def _run_installer(home: Path) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)  # Windows Path.home() 读这个
    p = subprocess.run([PY, str(INSTALLER)], capture_output=True, text=True, env=env)
    return json.loads(p.stdout.strip())


def test_installer_fresh_install():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        res = _run_installer(home)
        assert res["status"] == "installed"
        settings = json.loads((home / ".claude" / "settings.json").read_text())
        cmds = [h["command"] for e in settings["hooks"]["PreToolUse"] for h in e["hooks"]]
        assert any("academic_gate_hook.py" in c for c in cmds)


def test_installer_idempotent():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        _run_installer(home)
        res2 = _run_installer(home)
        # 第二次：已装 + 无新鲜心跳 → degraded(不透传)或 active；总之不重复安装
        settings = json.loads((home / ".claude" / "settings.json").read_text())
        entries = [h for e in settings["hooks"]["PreToolUse"] for h in e["hooks"]
                   if "academic_gate_hook.py" in h["command"]]
        assert len(entries) == 1, "不得重复安装"


def test_installer_preserves_existing_and_backs_up():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        sp = home / ".claude"
        sp.mkdir(parents=True)
        (sp / "settings.json").write_text(json.dumps(
            {"model": "sonnet", "hooks": {"PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo hi"}]}]}},
            ensure_ascii=False), encoding="utf-8")
        res = _run_installer(home)
        assert res["status"] == "installed"
        settings = json.loads((sp / "settings.json").read_text())
        assert settings["model"] == "sonnet", "既有配置必须保留"
        cmds = [h["command"] for e in settings["hooks"]["PreToolUse"] for h in e["hooks"]]
        assert "echo hi" in cmds and any("academic_gate_hook.py" in c for c in cmds)
        assert (sp / "settings.json.bak-gatehook").is_file(), "必须留备份"


def test_installer_refuses_broken_settings_without_damage():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        sp = home / ".claude"
        sp.mkdir(parents=True)
        broken = '{"model": "sonnet", oops not json'
        (sp / "settings.json").write_text(broken, encoding="utf-8")
        res = _run_installer(home)
        assert res["status"] == "degraded", "坏 settings 应跳过安装而非崩"
        assert (sp / "settings.json").read_text() == broken, "坏文件不得被改动"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"\nALL {len(fns)} PASSED")
