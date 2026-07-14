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


def _hook_env(extra: dict | None = None) -> dict:
    """分发器测试直接测 _shared 本文件逻辑:关闭转发(否则本机已部署
    academic-gate 时会转去测部署副本,开发期改了真源测的却是旧副本)。"""
    env = dict(os.environ)
    env["ACADEMIC_GATE_NO_FORWARD"] = "1"
    if extra:
        env.update(extra)
    return env


def _run_hook(payload: dict, env: dict | None = None) -> tuple[str, int]:
    p = subprocess.run([PY, str(HOOK)], input=json.dumps(payload),
                       capture_output=True, text=True, env=env or _hook_env())
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
                       capture_output=True, text=True, env=_hook_env())
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


BUNDLE = ("structure_signoff_gate.py", "academic_gate_hook.py",
          "install_gate_hook.py", "gate_registry.json")


def _run_installer(home: Path, installer: Path | None = None,
                   args: list[str] | None = None) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)  # Windows Path.home() 读这个
    p = subprocess.run([PY, str(installer or INSTALLER)] + (args or []),
                       capture_output=True, text=True, env=env)
    return json.loads(p.stdout.strip())


def _entry_cmds(home: Path) -> list[str]:
    settings = json.loads((home / ".claude" / "settings.json").read_text())
    return [h["command"] for e in settings["hooks"]["PreToolUse"] for h in e["hooks"]
            if "academic_gate_hook.py" in h["command"]]


def test_installer_fresh_install():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        res = _run_installer(home)
        assert res["status"] == "installed"
        cmds = _entry_cmds(home)
        assert len(cmds) == 1 and "academic-gate" in cmds[0], \
            "entry 必须指向 ~/.claude/academic-gate/ 稳定位置"
        gate = home / ".claude" / "academic-gate"
        for name in BUNDLE:
            assert (gate / name).is_file(), f"四件套须部署到 academic-gate: 缺 {name}"
        assert not (gate / "hook_heartbeat.json").is_file(), "心跳是运行时产物,不得随部署复制"


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


def test_installer_migrates_old_shared_entry():
    """旧 _shared 路径的 entry 必须被替换为 academic-gate 路径,且收敛为恰好一条。"""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        sp = home / ".claude"
        sp.mkdir(parents=True)
        old_cmd = f'python "{SHARED / "academic_gate_hook.py"}"'
        (sp / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
            {"matcher": "Write|Edit",
             "hooks": [{"type": "command", "command": old_cmd, "timeout": 60}]}]}},
            ensure_ascii=False), encoding="utf-8")
        res = _run_installer(home)
        assert res["action"] == "migrated", f"旧 entry 应触发迁移,得到 {res['action']}"
        cmds = _entry_cmds(home)
        assert len(cmds) == 1 and "academic-gate" in cmds[0] and str(SHARED) not in cmds[0], \
            "迁移后应只剩一条指向 academic-gate 的 entry"


def test_installer_converges_duplicate_entries():
    """新旧并存/重复 entry → 收敛为一条;同 entry 里用户自己的其它 hook 保留。"""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        sp = home / ".claude"
        sp.mkdir(parents=True)
        gate_cmd = f'python "{home / ".claude" / "academic-gate" / "academic_gate_hook.py"}"'
        old_cmd = f'python "/old/path/_shared/academic_gate_hook.py"'
        (sp / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": old_cmd, "timeout": 60},
                {"type": "command", "command": "echo user-own"}]},
            {"matcher": "Write|Edit",
             "hooks": [{"type": "command", "command": gate_cmd, "timeout": 60}]}]}},
            ensure_ascii=False), encoding="utf-8")
        _run_installer(home)
        cmds = _entry_cmds(home)
        assert len(cmds) == 1 and "academic-gate" in cmds[0], "必须收敛为一条指向 academic-gate"
        settings = json.loads((sp / "settings.json").read_text())
        all_cmds = [h["command"] for e in settings["hooks"]["PreToolUse"] for h in e["hooks"]]
        assert "echo user-own" in all_cmds, "用户自己的 hook 不得被误删"


def _deployed_version(home: Path) -> int:
    reg = home / ".claude" / "academic-gate" / "gate_registry.json"
    return int(json.loads(reg.read_text(encoding="utf-8")).get("version", 0))


def test_deploy_version_compare_and_force():
    """目标更新→不覆盖;更旧→覆盖;--force→同版重刷。"""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        _run_installer(home)
        gate = home / ".claude" / "academic-gate"
        hook_file = gate / "academic_gate_hook.py"
        marker = "\n# LOCAL-MARK\n"
        # ① 目标版更高 → 不覆盖(改动保留)
        reg = json.loads((gate / "gate_registry.json").read_text(encoding="utf-8"))
        src_ver = reg["version"]
        reg["version"] = src_ver + 99
        (gate / "gate_registry.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
        hook_file.write_text(hook_file.read_text(encoding="utf-8") + marker, encoding="utf-8")
        _run_installer(home)
        assert marker in hook_file.read_text(encoding="utf-8"), "目标更新时不得覆盖"
        # ② 目标版更旧 → 覆盖(改动被刷掉)
        reg["version"] = 1
        (gate / "gate_registry.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
        _run_installer(home)
        assert marker not in hook_file.read_text(encoding="utf-8"), "目标更旧时必须覆盖"
        assert _deployed_version(home) == src_ver
        # ③ 同版 + 改动 + --force → 重刷
        hook_file.write_text(hook_file.read_text(encoding="utf-8") + marker, encoding="utf-8")
        _run_installer(home)
        assert marker in hook_file.read_text(encoding="utf-8"), "同版默认不重刷"
        _run_installer(home, args=["--force"])
        assert marker not in hook_file.read_text(encoding="utf-8"), "--force 应同版重刷"


def test_signoff_cross_copy_contract():
    """契约冻结:真源副本 confirm 落盘的文件,必须通过部署副本的 check(v1 只看 confirmed)。"""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        _run_installer(home)
        deployed_signoff = home / ".claude" / "academic-gate" / "structure_signoff_gate.py"
        root = Path(d) / "proj"
        root.mkdir()
        subprocess.run([PY, str(SIGNOFF), "confirm", "--root", str(root),
                        "--note", "契约测试"], capture_output=True, text=True)
        r = subprocess.run([PY, str(deployed_signoff), "check", "--root", str(root)],
                           capture_output=True, text=True)
        assert r.returncode == 0, "真源 confirm 的落盘必须过部署副本 check"


def test_vendored_installer_full_chain():
    """模拟单技能分发:installer+四件套只存在于技能 scripts/(无 _shared),
    从那里跑安装 → 部署到临时 HOME 的 academic-gate + entry 指部署位。"""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d) / "home"
        skill_scripts = Path(d) / "skills" / "some-skill" / "scripts"
        skill_scripts.mkdir(parents=True)
        for name in BUNDLE:
            (skill_scripts / name).write_bytes((SHARED / name).read_bytes())
        res = _run_installer(home, installer=skill_scripts / "install_gate_hook.py")
        assert res["status"] == "installed", f"vendored 全链应装成功,得到 {res}"
        cmds = _entry_cmds(home)
        assert len(cmds) == 1 and "academic-gate" in cmds[0] and "some-skill" not in cmds[0], \
            "entry 必须指部署位,绝不指技能目录(否则删技能=悬空)"
        for name in BUNDLE:
            assert (home / ".claude" / "academic-gate" / name).is_file()


def test_interpreter_probe_and_command_runs():
    """entry 的解释器必须是 PATH 上真实存在的(全新 macOS 无 python 只有 python3,
    裸写 python → exit 127,物理锁静默失效);且写完的命令 shell 真跑得起来。"""
    import shutil as _sh
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        res = _run_installer(home)
        assert res["status"] == "installed", f"命令可跑时应 installed,得到 {res}"
        cmd = _entry_cmds(home)[0]
        interp = cmd.split(' "', 1)[0].strip('"')
        assert _sh.which(interp) or Path(interp).is_file(), \
            f"解释器 {interp!r} 必须在 PATH 或为存在的绝对路径"
        p = subprocess.run(cmd, shell=True, input="{}",
                           capture_output=True, text=True, timeout=15,
                           env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)})
        assert p.returncode == 0, f"写进 settings 的命令必须真跑得通,rc={p.returncode}"


def test_stale_interpreter_selfheals():
    """解释器变了(如 pyenv 卸载留下 python 裸名 entry)→ 下次安装按新探测迁移命令。"""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        _run_installer(home)  # 部署四件套
        sp = home / ".claude" / "settings.json"
        gate_hook = home / ".claude" / "academic-gate" / "academic_gate_hook.py"
        stale = json.loads(sp.read_text())
        stale["hooks"]["PreToolUse"] = [{"matcher": "Write|Edit", "hooks": [
            {"type": "command", "command": f'no-such-python "{gate_hook}"', "timeout": 60}]}]
        sp.write_text(json.dumps(stale, ensure_ascii=False), encoding="utf-8")
        res = _run_installer(home)
        assert res["action"] == "migrated", f"过期解释器 entry 应被迁移,得到 {res}"
        cmds = _entry_cmds(home)
        assert len(cmds) == 1 and not cmds[0].startswith("no-such-python"), \
            "命令应被改写为当前探测到的解释器"


def test_installer_tolerates_null_hooks():
    """hooks/PreToolUse 被其它工具写成显式 null → 应 coerce 安装,不得退化成 error。"""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        sp = home / ".claude"
        sp.mkdir(parents=True)
        (sp / "settings.json").write_text(json.dumps({"hooks": None}), encoding="utf-8")
        res = _run_installer(home)
        assert res["status"] == "installed", f"null hooks 应被 coerce 后安装,得到 {res}"
        assert len(_entry_cmds(home)) == 1
        (sp / "settings.json").write_text(
            json.dumps({"hooks": {"PreToolUse": None}}), encoding="utf-8")
        res2 = _run_installer(home)
        assert res2["status"] == "installed", f"null PreToolUse 同理,得到 {res2}"
        assert len(_entry_cmds(home)) == 1


def test_shared_hook_forwards_to_deployed():
    """悬空防护:_shared 的 hook 被旧 entry 调起时,若部署副本存在应转发执行它。"""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        gate = home / ".claude" / "academic-gate"
        gate.mkdir(parents=True)
        (gate / "academic_gate_hook.py").write_text(
            "import sys; sys.stdout.write('FORWARDED-MARK')", encoding="utf-8")
        env = dict(os.environ)
        env["HOME"] = str(home)
        env["USERPROFILE"] = str(home)
        env.pop("ACADEMIC_GATE_NO_FORWARD", None)
        p = subprocess.run([PY, str(HOOK)], input="{}",
                           capture_output=True, text=True, env=env)
        assert "FORWARDED-MARK" in p.stdout, "_shared hook 应转发到部署副本"
        # NO_FORWARD=1 时不转发(测试逃生口)
        env["ACADEMIC_GATE_NO_FORWARD"] = "1"
        p2 = subprocess.run([PY, str(HOOK)], input="{}",
                            capture_output=True, text=True, env=env)
        assert "FORWARDED-MARK" not in p2.stdout, "NO_FORWARD 应关闭转发"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"\nALL {len(fns)} PASSED")
