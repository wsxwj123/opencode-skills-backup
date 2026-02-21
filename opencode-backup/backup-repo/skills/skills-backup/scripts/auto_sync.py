import os
import sys
import subprocess
import platform
import datetime

# Force UTF-8 for Windows output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Determine paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_BACKUP_DIR = os.path.dirname(SCRIPT_DIR) # Parent of scripts
SKILLS_ROOT = os.path.dirname(SKILLS_BACKUP_DIR) # Parent of skills-backup
LOG_FILE = os.path.join(SKILLS_BACKUP_DIR, 'logs', 'history.md')

def run_command(cmd, cwd=SKILLS_ROOT, check=True):
    """Run a shell command and return output, or None on error."""
    try:
        # On Windows, strictly depend on PATH to avoid file not found
        startupinfo = None
        if platform.system() == 'Windows':
             startupinfo = subprocess.STARTUPINFO()
             startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
             
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            startupinfo=startupinfo
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None
    except Exception as e:
        return None

def ensure_gitattributes():
    attr_path = os.path.join(SKILLS_ROOT, '.gitattributes')
    if not os.path.exists(attr_path):
        try:
            with open(attr_path, 'w', encoding='utf-8') as f:
                f.write("* text=auto\n")
                f.write("*.sh text eol=lf\n")
                f.write("*.bat text eol=crlf\n")
        except Exception:
            pass

def get_changed_skills():
    """
    Returns a dict of {skill_name: status_code} based on git status.
    Status codes: 'Modified', 'Added', 'Deleted'
    """
    status_output = run_command(['git', 'status', '--porcelain'])
    if not status_output:
        return {}

    changes = {}
    for line in status_output.splitlines():
        if not line.strip():
            continue
        
        # Format: XY PATH
        # X=index status, Y=worktree status
        # ?? = untracked (Added)
        # M = modified
        # D = deleted
        
        code = line[:2]
        path = line[3:]
        
        # Remove quotes if present
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
            
        # Get top-level folder (skill name)
        parts = path.split('/')
        if not parts:
            continue
            
        skill_name = parts[0]
        if skill_name == ".gitignore" or skill_name == ".gitattributes":
            continue
            
        if '??' in code:
            changes[skill_name] = 'Added'
        elif 'D' in code:
            changes[skill_name] = 'Deleted'
        else:
            if skill_name not in changes: # Prioritize Added/Deleted if mixed, or just default to Modified
                 changes[skill_name] = 'Modified'
                 
    return changes

def append_log(status, changes_dict=None, error_msg=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    hostname = platform.node()
    os_name = platform.system()
    
    log_entry = f"\n## [{timestamp}] Backup\n"
    log_entry += f"**Machine:** {hostname} ({os_name})\n"
    log_entry += f"**Status:** {status}\n"
    
    if error_msg:
        log_entry += f"**Error:** {error_msg}\n"
        
    if changes_dict:
        log_entry += "**Updated:**\n"
        for skill, change_type in changes_dict.items():
            log_entry += f"- {skill} ({change_type})\n"
            
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write log: {e}")

def main():
    # 1. Check git repo
    if not os.path.exists(os.path.join(SKILLS_ROOT, '.git')):
        append_log("Error", error_msg="Not a git repository")
        return

    # 2. Setup
    ensure_gitattributes()
    branch = run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
    if not branch:
        append_log("Error", error_msg="Could not determine git branch")
        return

    # 3. Check for local changes
    changes = get_changed_skills()
    
    if not changes:
        # Just pull/push to sync remote changes, don't spam log if nothing happened locally
        # Or maybe log "No Changes" if that's requested? The prompt says: "Status: [Success/No Changes/Error]"
        # I'll log "No Changes" but perform a pull/push sync to ensure we are up to date.
        
        run_command(['git', 'pull', '--rebase', 'origin', branch], check=False)
        run_command(['git', 'push', 'origin', branch], check=False)
        append_log("No Changes")
        return

    # 4. Commit local changes first (safer for backup)
    run_command(['git', 'add', '.'])
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = platform.node()
    os_name = platform.system()
    commit_msg = f"Auto-backup from {os_name} ({hostname}) - {timestamp}"
    
    commit_res = run_command(['git', 'commit', '-m', commit_msg], check=False)
    
    if commit_res is None:
        # Weird, we saw changes but commit failed?
        append_log("Error", changes, "Commit failed")
        return

    # 5. Pull (Rebase)
    pull_res = run_command(['git', 'pull', '--rebase', 'origin', branch], check=False)
    
    if pull_res is None:
        # Conflict or network error
        run_command(['git', 'rebase', '--abort'], check=False) # Try to cleanup
        append_log("Error", changes, "Pull/Rebase failed (conflict or network)")
        return

    # 6. Push
    push_res = run_command(['git', 'push', 'origin', branch], check=False)
    
    if push_res is not None:
        append_log("Success", changes)
    else:
        append_log("Error", changes, "Push failed")

if __name__ == "__main__":
    main()
