import datetime
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_BACKUP_DIR = SCRIPT_DIR.parent
SKILLS_ROOT = SKILLS_BACKUP_DIR.parent
LOG_FILE = SKILLS_BACKUP_DIR / 'logs' / 'history.md'

TARGET_REPO_URL = os.environ.get('SKILLS_BACKUP_REPO_URL', 'https://github.com/wsxwj123/opencode-skills-backup.git')
TARGET_SUBDIR = os.environ.get('SKILLS_BACKUP_TARGET_SUBDIR', 'skills')

EXCLUDE_NAMES = {'.git', '.DS_Store', '__pycache__', '.pytest_cache', 'node_modules'}
EXCLUDE_SUFFIXES = {'.pyc'}


def run_command(cmd, cwd=None, check=True):
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def append_log(status, note=None):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    host = platform.node()
    os_name = platform.system()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(f"\n## [{ts}] Backup\n")
        f.write(f"**Machine:** {host} ({os_name})\n")
        f.write(f"**Status:** {status}\n")
        if note:
            f.write(f"**Note:** {note}\n")


def should_exclude(name: str) -> bool:
    if name in EXCLUDE_NAMES:
        return True
    for suf in EXCLUDE_SUFFIXES:
        if name.endswith(suf):
            return True
    return False


def copy_item(src: Path, dst: Path):
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def sync_tree(src_root: Path, dst_root: Path):
    dst_root.mkdir(parents=True, exist_ok=True)
    src_entries = [p for p in src_root.iterdir() if not should_exclude(p.name)]
    src_names = {p.name for p in src_entries}

    for dst in list(dst_root.iterdir()):
        if dst.name == '.git':
            continue
        if dst.name not in src_names:
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()

    for src in src_entries:
        copy_item(src, dst_root / src.name)


def main():
    if not SKILLS_ROOT.exists():
        append_log('Error', 'Local skills root missing')
        return

    with tempfile.TemporaryDirectory(prefix='skills-auto-sync-') as td:
        workdir = Path(td) / 'repo'

        if run_command(['git', 'clone', TARGET_REPO_URL, str(workdir)]) is None:
            append_log('Error', 'Clone failed')
            return

        branch = run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=workdir) or 'main'

        target_dir = workdir / TARGET_SUBDIR
        sync_tree(SKILLS_ROOT, target_dir)

        run_command(['git', 'add', TARGET_SUBDIR], cwd=workdir)
        status = run_command(['git', 'status', '--porcelain', '--', TARGET_SUBDIR], cwd=workdir)

        if not status:
            append_log('No Changes', 'skills/ is up to date')
            return

        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        host = platform.node()
        os_name = platform.system()
        msg = f"Auto-sync skills from {os_name} ({host}) - {ts}"

        if run_command(['git', 'commit', '-m', msg], cwd=workdir) is None:
            append_log('Error', 'Commit failed')
            return

        if run_command(['git', 'push', 'origin', branch], cwd=workdir) is None:
            append_log('Error', 'Push failed')
            return

        append_log('Success', 'Synced to opencode-skills-backup/skills')


if __name__ == '__main__':
    main()
