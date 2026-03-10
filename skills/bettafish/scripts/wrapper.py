import argparse
import shlex
import subprocess
import sys
from pathlib import Path

GITHUB_URL = "https://github.com/666ghj/BettaFish"
PINNED_HASH = "ec733a9c0febe9ddbfb4add757613a0ac59e0df9"
DEFAULT_REPO_DIR = Path.home() / ".cache" / "opencode-skills" / "bettafish-repo"


def run(cmd, cwd=None):
    print("[bettafish-skill] $", " ".join(shlex.quote(str(c)) for c in cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_repo(repo_dir: Path):
    if not repo_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", GITHUB_URL, str(repo_dir)])


def checkout_pinned(repo_dir: Path):
    run(["git", "fetch", "--all", "--tags"], cwd=repo_dir)
    run(["git", "checkout", PINNED_HASH], cwd=repo_dir)


def cmd_init(repo_dir: Path):
    ensure_repo(repo_dir)
    checkout_pinned(repo_dir)
    print(f"[bettafish-skill] 仓库已就绪: {repo_dir}")


def cmd_update(repo_dir: Path):
    ensure_repo(repo_dir)
    run(["git", "pull", "--ff-only"], cwd=repo_dir)
    checkout_pinned(repo_dir)
    print(f"[bettafish-skill] 仓库已更新并检出固定版本: {PINNED_HASH}")


def cmd_install(repo_dir: Path):
    ensure_repo(repo_dir)
    req = repo_dir / "requirements.txt"
    if not req.exists():
        raise FileNotFoundError(f"requirements.txt 不存在: {req}")
    run([sys.executable, "-m", "pip", "install", "-r", str(req)], cwd=repo_dir)


def cmd_playwright_install(repo_dir: Path):
    ensure_repo(repo_dir)
    run([sys.executable, "-m", "playwright", "install"], cwd=repo_dir)


def cmd_run_app(repo_dir: Path):
    ensure_repo(repo_dir)
    run([sys.executable, "app.py"], cwd=repo_dir)


def cmd_run_report_engine(repo_dir: Path, passthrough):
    ensure_repo(repo_dir)
    run([sys.executable, "report_engine_only.py", *passthrough], cwd=repo_dir)


def cmd_run_mindspider(repo_dir: Path, passthrough):
    ensure_repo(repo_dir)
    run([sys.executable, "main.py", *passthrough], cwd=repo_dir / "MindSpider")


def cmd_exec(repo_dir: Path, passthrough):
    ensure_repo(repo_dir)
    if not passthrough:
        raise ValueError("exec 需要通过 -- 传入要执行的命令")
    run(passthrough, cwd=repo_dir)


def build_parser():
    parser = argparse.ArgumentParser(description="BettaFish skill wrapper")
    parser.add_argument("command", choices=[
        "init",
        "update",
        "install",
        "playwright-install",
        "run-app",
        "run-report-engine",
        "run-mindspider",
        "exec",
    ])
    parser.add_argument("--repo-dir", default=str(DEFAULT_REPO_DIR), help="BettaFish 本地仓库路径")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="透传参数（请使用 -- 分隔）")
    return parser


def strip_leading_double_dash(args):
    if args and args[0] == "--":
        return args[1:]
    return args


def main():
    parser = build_parser()
    ns = parser.parse_args()
    repo_dir = Path(ns.repo_dir).expanduser().resolve()
    passthrough = strip_leading_double_dash(ns.args)

    if ns.command == "init":
        cmd_init(repo_dir)
    elif ns.command == "update":
        cmd_update(repo_dir)
    elif ns.command == "install":
        cmd_install(repo_dir)
    elif ns.command == "playwright-install":
        cmd_playwright_install(repo_dir)
    elif ns.command == "run-app":
        cmd_run_app(repo_dir)
    elif ns.command == "run-report-engine":
        cmd_run_report_engine(repo_dir, passthrough)
    elif ns.command == "run-mindspider":
        cmd_run_mindspider(repo_dir, passthrough)
    elif ns.command == "exec":
        cmd_exec(repo_dir, passthrough)


if __name__ == "__main__":
    main()
