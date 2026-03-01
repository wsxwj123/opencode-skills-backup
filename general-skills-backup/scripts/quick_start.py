import argparse
import os
import platform
import subprocess
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
BOOTSTRAP_SCRIPT = os.path.join(SCRIPT_DIR, "bootstrap_repo.py")
SYNC_SCRIPT = os.path.join(SCRIPT_DIR, "sync_skills.py")
AUTO_BACKUP_SETUP = os.path.join(SKILL_DIR, "setup_auto_backup.py")
DEFAULT_PROXY_PORTS = ["7897", "7890"]


def run_python(script_path, extra_args=None):
    args = [sys.executable, script_path]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(args, check=False)


def ensure_git_available():
    res = subprocess.run(["git", "--version"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.returncode == 0


def ask_yes_no(prompt, default_yes=True):
    suffix = " [Y/n]: " if default_yes else " [y/N]: "
    value = input(prompt + suffix).strip().lower()
    if not value:
        return default_yes
    return value in ("y", "yes")


def normalize_repo_url(repo_url):
    return repo_url.strip()

def resolve_proxy_ports(explicit_port=None):
    if explicit_port:
        return [str(explicit_port)]

    user_port = input("请输入 Clash Verge 代理端口（直接回车将按 7897 -> 7890 自动尝试）: ").strip()
    if user_port:
        return [user_port]
    return DEFAULT_PROXY_PORTS


def main():
    parser = argparse.ArgumentParser(
        description="Quick start wizard for general-skills-backup: bootstrap repo, sync once, optional auto-backup."
    )
    parser.add_argument("--repo-url", help="GitHub repository URL for skills backup")
    parser.add_argument("--branch", default="main", help="Branch name (default: main)")
    parser.add_argument("--force-origin", action="store_true", help="Update existing origin to --repo-url")
    parser.add_argument("--proxy-port", help="Clash Verge proxy port. If omitted, asks user; empty input falls back to 7897 then 7890.")
    parser.add_argument("--setup-auto-backup", action="store_true", help="Install scheduled auto backup without prompting")
    parser.add_argument("--no-auto-backup", action="store_true", help="Skip auto backup setup without prompting")
    args = parser.parse_args()

    print("🚀 general-skills-backup quick start")

    if not ensure_git_available():
        print("❌ git is not available in PATH. Install Git first, then rerun.")
        return 1

    repo_url = normalize_repo_url(args.repo_url) if args.repo_url else ""
    if not repo_url:
        repo_url = normalize_repo_url(input("请输入你的 GitHub 仓库地址 (repo URL): ").strip())
    if not repo_url:
        print("❌ repo URL 不能为空。")
        return 1

    proxy_ports = resolve_proxy_ports(args.proxy_port)
    setup_ok = False
    used_port = None

    for idx, port in enumerate(proxy_ports):
        print(f"\n🌐 Using proxy port: {port}")
        print("\n1) 初始化仓库配置...")
        bootstrap_args = ["--repo-url", repo_url, "--branch", args.branch, "--proxy-port", port]
        if args.force_origin:
            bootstrap_args.append("--force-origin")
        bootstrap_res = run_python(BOOTSTRAP_SCRIPT, bootstrap_args)
        if bootstrap_res.returncode != 0:
            if idx < len(proxy_ports) - 1:
                print(f"⚠️ 端口 {port} 初始化失败，尝试下一个端口...")
                continue
            print("❌ 初始化失败，请先解决上面的报错。")
            return bootstrap_res.returncode

        print("\n2) 执行首次同步...")
        sync_res = run_python(SYNC_SCRIPT, ["--proxy-port", port])
        if sync_res.returncode != 0:
            if idx < len(proxy_ports) - 1:
                print(f"⚠️ 端口 {port} 同步失败，尝试下一个端口...")
                continue
            print("⚠️ 同步过程有错误，请根据输出修复后重试。")
            return sync_res.returncode

        setup_ok = True
        used_port = port
        break

    if not setup_ok:
        print("❌ 所有代理端口都失败。")
        return 1

    setup_auto = args.setup_auto_backup
    if not args.setup_auto_backup and not args.no_auto_backup:
        setup_auto = ask_yes_no("3) 是否启用每小时自动备份？", default_yes=True)

    if setup_auto:
        print("\n3) 安装自动备份任务...")
        auto_res = run_python(AUTO_BACKUP_SETUP)
        if auto_res.returncode != 0:
            print("⚠️ 自动备份安装失败，可稍后手动执行 setup_auto_backup.py。")
            return auto_res.returncode

    print(f"\n✅ 已完成开箱配置（代理端口: {used_port}），可以直接日常使用 sync_skills.py。")
    if platform.system() == "Windows":
        print("提示: 你也可以在 PowerShell 里直接运行: python scripts\\sync_skills.py")
    else:
        print("提示: 你也可以在终端里直接运行: python3 scripts/sync_skills.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
