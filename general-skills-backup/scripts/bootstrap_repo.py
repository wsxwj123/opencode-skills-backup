import argparse
import os
import platform
import subprocess
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_BACKUP_DIR = os.path.dirname(SCRIPT_DIR)
SKILLS_ROOT = os.path.dirname(SKILLS_BACKUP_DIR)


def run_command(cmd, cwd=SKILLS_ROOT, check=True):
    try:
        startupinfo = None
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=startupinfo,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running '{' '.join(cmd)}': {e.stderr.strip()}")
        return None
    except Exception as e:
        print(f"Execution error: {e}")
        return None


def has_origin_remote():
    remotes = run_command(["git", "remote"], check=False) or ""
    return "origin" in remotes.split()

def get_origin_url():
    return run_command(["git", "remote", "get-url", "origin"], check=False)


def has_commit():
    head = run_command(["git", "rev-parse", "--verify", "HEAD"], check=False)
    return bool(head)


def bootstrap(repo_url, branch, force_origin=False):
    print(f"📂 Skills Directory: {SKILLS_ROOT}")

    if not os.path.exists(os.path.join(SKILLS_ROOT, ".git")):
        print("🔧 Initializing git repository...")
        if run_command(["git", "init"]) is None:
            return 1
    else:
        print("✅ Git repository already exists.")

    print(f"🌿 Ensuring branch: {branch}")
    if run_command(["git", "branch", "-M", branch], check=False) is None:
        return 1

    if not has_origin_remote():
        print(f"🔗 Adding remote origin: {repo_url}")
        if run_command(["git", "remote", "add", "origin", repo_url]) is None:
            return 1
    else:
        existing = get_origin_url() or "<unknown>"
        if force_origin and existing != repo_url:
            print(f"🔁 Updating remote origin: {existing} -> {repo_url}")
            if run_command(["git", "remote", "set-url", "origin", repo_url]) is None:
                return 1
        else:
            print(f"✅ Remote origin already configured: {existing}")

    if not has_commit():
        print("📝 Creating initial commit...")
        run_command(["git", "add", "."])
        status = run_command(["git", "status", "--porcelain"], check=False)
        if status:
            if run_command(["git", "commit", "-m", "Initialize skills backup repository"], check=False) is None:
                return 1
        else:
            # Empty repository with no tracked files.
            print("ℹ️ No files to commit yet. Initial push may fail until first change.")

    print("⬆️ Pushing and setting upstream...")
    pushed = run_command(["git", "push", "-u", "origin", branch], check=False)
    if pushed is None:
        print("⚠️ Push failed. Verify repo URL and GitHub credentials, then retry.")
        return 1

    print("✅ Repository bootstrap completed.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap skills git repository")
    parser.add_argument("--repo-url", required=True, help="Git remote URL for origin")
    parser.add_argument("--branch", default="main", help="Branch name (default: main)")
    parser.add_argument("--force-origin", action="store_true", help="Update existing origin URL to --repo-url")
    args = parser.parse_args()

    raise SystemExit(bootstrap(args.repo_url, args.branch, args.force_origin))
