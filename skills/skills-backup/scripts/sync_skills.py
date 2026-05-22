import argparse
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
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Error running {' '.join(cmd)}: {e.stderr.strip()}")
        return None


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


def sync_tree(src_root: Path, dst_root: Path, specific_skills=None):
    dst_root.mkdir(parents=True, exist_ok=True)

    if specific_skills:
        for skill in specific_skills:
            src = src_root / skill
            if not src.exists():
                print(f"Warning: skill not found: {skill}")
                continue
            dst = dst_root / skill
            if dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            copy_item(src, dst)
        return

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


def sync(specific_skills=None):
    print(f"Skills source: {SKILLS_ROOT}")
    print(f"Target repo: {TARGET_REPO_URL}")
    print(f"Target subdir: {TARGET_SUBDIR}")

    if not SKILLS_ROOT.exists():
        print("Error: local skills root not found")
        return

    with tempfile.TemporaryDirectory(prefix='skills-backup-') as td:
        workdir = Path(td) / 'repo'

        if run_command(['git', 'clone', TARGET_REPO_URL, str(workdir)]) is None:
            print('Error: clone failed')
            return

        branch = run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=workdir)
        if not branch:
            branch = 'main'

        target_dir = workdir / TARGET_SUBDIR
        sync_tree(SKILLS_ROOT, target_dir, specific_skills=specific_skills)

        run_command(['git', 'add', TARGET_SUBDIR], cwd=workdir)
        status = run_command(['git', 'status', '--porcelain', '--', TARGET_SUBDIR], cwd=workdir)

        if not status:
            print('No changes to sync.')
            return

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        os_name = platform.system()
        machine = platform.node()
        if specific_skills:
            msg = f"Sync skills({', '.join(specific_skills)}) from {os_name} - {timestamp}"
        else:
            msg = f"Sync all skills from {os_name} ({machine}) - {timestamp}"

        if run_command(['git', 'commit', '-m', msg], cwd=workdir) is None:
            print('Error: commit failed')
            return

        if run_command(['git', 'push', 'origin', branch], cwd=workdir) is None:
            print('Error: push failed')
            return

        print('Backup successful.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sync OpenCode skills to wsxwj123/opencode-skills-backup')
    parser.add_argument('skills', nargs='*', help='specific skills to sync (optional)')
    args = parser.parse_args()
    sync(args.skills)
