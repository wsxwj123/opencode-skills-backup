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


def main():
    parser = argparse.ArgumentParser(
        description="Quick start wizard for general-skills-backup: bootstrap repo, sync once, optional auto-backup."
    )
    parser.add_argument("--repo-url", help="GitHub repository URL for skills backup")
    parser.add_argument("--branch", default="main", help="Branch name (default: main)")
    parser.add_argument("--force-origin", action="store_true", help="Update existing origin to --repo-url")
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

    print("\n1) 初始化仓库配置...")
    bootstrap_args = ["--repo-url", repo_url, "--branch", args.branch]
    if args.force_origin:
        bootstrap_args.append("--force-origin")
    bootstrap_res = run_python(BOOTSTRAP_SCRIPT, bootstrap_args)
    if bootstrap_res.returncode != 0:
        print("❌ 初始化失败，请先解决上面的报错。")
        return bootstrap_res.returncode

    print("\n2) 执行首次同步...")
    sync_res = run_python(SYNC_SCRIPT)
    if sync_res.returncode != 0:
        print("⚠️ 同步过程有错误，请根据输出修复后重试。")
        return sync_res.returncode

    setup_auto = args.setup_auto_backup
    if not args.setup_auto_backup and not args.no_auto_backup:
        setup_auto = ask_yes_no("3) 是否启用每小时自动备份？", default_yes=True)

    if setup_auto:
        print("\n3) 安装自动备份任务...")
        auto_res = run_python(AUTO_BACKUP_SETUP)
        if auto_res.returncode != 0:
            print("⚠️ 自动备份安装失败，可稍后手动执行 setup_auto_backup.py。")
            return auto_res.returncode

    print("\n✅ 已完成开箱配置，可以直接日常使用 sync_skills.py。")
    if platform.system() == "Windows":
        print("提示: 你也可以在 PowerShell 里直接运行: python scripts\\sync_skills.py")
    else:
        print("提示: 你也可以在终端里直接运行: python3 scripts/sync_skills.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
