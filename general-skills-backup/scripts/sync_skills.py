import os
import sys
import subprocess
import platform
import datetime
import argparse

# Force UTF-8 for Windows output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Determine paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_BACKUP_DIR = os.path.dirname(SCRIPT_DIR) # Parent of scripts
SKILLS_ROOT = os.path.dirname(SKILLS_BACKUP_DIR) # Parent of skills-backup

def run_command(cmd, cwd=SKILLS_ROOT):
    """Run a shell command and return output, or None on error."""
    try:
        # On Windows, we need shell=True for some commands to work properly, 
        # but for git simple calls it's usually fine without.
        # However, to avoid 'system cannot find the file specified', strictly depend on PATH.
        startupinfo = None
        if platform.system() == 'Windows':
             startupinfo = subprocess.STARTUPINFO()
             startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
             
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8', # Force encoding for git output
            errors='replace',
            startupinfo=startupinfo,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Don't print error for basic checks that are expected to fail (like stash check)
        if "stash" not in cmd and "rev-parse" not in cmd:
             print(f"Error running '{' '.join(cmd)}': {e.stderr.strip()}")
        return None
    except Exception as e:
        print(f"Execution error: {e}")
        return None

def get_current_branch():
    return run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])

def has_origin_remote():
    remotes = run_command(['git', 'remote']) or ""
    return 'origin' in remotes.split()

def ensure_gitattributes():
    attr_path = os.path.join(SKILLS_ROOT, '.gitattributes')
    if not os.path.exists(attr_path):
        print("🔧 Creating .gitattributes for cross-platform compatibility...")
        try:
            with open(attr_path, 'w', encoding='utf-8') as f:
                f.write("* text=auto\n")
                f.write("*.sh text eol=lf\n")
                f.write("*.bat text eol=crlf\n")
        except Exception as e:
            print(f"Warning: Could not write .gitattributes: {e}")

def sync(specific_skills=None):
    print(f"📂 Skills Directory: {SKILLS_ROOT}")
    
    py_cmd = "python" if platform.system() == "Windows" else "python3"

    if run_command(['git', '--version']) is None:
        print("❌ Error: git is not available in PATH.")
        return

    # 1. Check if git repo exists
    if not os.path.exists(os.path.join(SKILLS_ROOT, '.git')):
        print("❌ Error: Not a git repository.")
        print("Run this one-time setup command first:")
        print(f"{py_cmd} {os.path.join(SCRIPT_DIR, 'bootstrap_repo.py')} --repo-url <your-repo-url>")
        return

    if not has_origin_remote():
        print("❌ Error: Git remote 'origin' is not configured.")
        print("Run this one-time setup command first:")
        print(f"{py_cmd} {os.path.join(SCRIPT_DIR, 'bootstrap_repo.py')} --repo-url <your-repo-url>")
        return

    # 2. Setup cross-platform config
    ensure_gitattributes()
    
    branch = get_current_branch()
    if not branch:
        print("❌ Could not detect current branch. Is the repo corrupt?")
        return

    print(f"🌿 Current Branch: {branch}")
    machine = platform.node()
    os_name = platform.system()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3. Pull Changes
    print("\n⬇️  Pulling remote changes...")
    stash_output = run_command(['git', 'stash'])
    stashed = stash_output and "No local changes to save" not in stash_output

    pull_res = run_command(['git', 'pull', '--rebase', 'origin', branch])
    
    if stashed:
        print("📦 Restoring local changes...")
        run_command(['git', 'stash', 'pop'])

    if pull_res is None:
        print("⚠️  Pull failed. You might need to resolve conflicts manually.")
        return

    # 4. Add and Commit
    print("\n💾 Checking for local changes...")
    
    if specific_skills:
        print(f"🎯 Syncing specific skills: {', '.join(specific_skills)}")
        for skill in specific_skills:
            skill_path = os.path.join(SKILLS_ROOT, skill)
            if os.path.exists(skill_path):
                run_command(['git', 'add', skill])
            else:
                print(f"⚠️ Warning: Skill '{skill}' not found in {SKILLS_ROOT}")
    else:
        run_command(['git', 'add', '.'])
    
    status = run_command(['git', 'status', '--porcelain'])
    if status:
        if specific_skills:
             commit_msg = f"Sync skills: {', '.join(specific_skills)} from {os_name}"
        else:
             commit_msg = f"Sync from {os_name} ({machine}) - {timestamp}"
             
        print(f"📝 Committing: {commit_msg}")
        commit_res = run_command(['git', 'commit', '-m', commit_msg])
        if commit_res is None:
            print("❌ Commit failed. Configure git user/email and retry.")
            return
        
        # 5. Push
        print("⬆️  Pushing to remote...")
        push_res = run_command(['git', 'push', 'origin', branch])
        if push_res is not None:
            print("✅ Backup successful!")
        else:
            print("❌ Push failed. Check your internet or credentials.")
    else:
        print("✨ No local changes to commit.")
        push_res = run_command(['git', 'push', 'origin', branch])
        if push_res is not None:
            print("✅ Sync complete.")
        else:
            print("❌ Push failed. Check your internet or credentials.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync OpenCode Skills")
    parser.add_argument("skills", nargs="*", help="Specific skills to sync (optional)")
    args = parser.parse_args()
    
    sync(args.skills)
