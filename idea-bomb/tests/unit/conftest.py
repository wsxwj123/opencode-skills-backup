"""只放 fixture。共享工具在 unit_helpers.py——不放这里是为了避免和
tests/acceptance/conftest.py 抢 "conftest" 这个模块名。"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unit_helpers import IB_MAP, IB_SEED, TODAY, run, write_map  # noqa: E402


@pytest.fixture
def env(tmp_path):
    """一套隔离的运行环境：地图、会话目录、备份目录全在 tmp_path 里。"""

    class Env:
        map_path = str(tmp_path / "migration_map.json")
        session_dir = str(tmp_path / "session")
        backup_dir = str(tmp_path / "backups")
        root = tmp_path

        def map_args(self):
            return ["--map", self.map_path, "--backup-dir", self.backup_dir]

        def seed(self, *args, stdin=None):
            return run(IB_SEED, *args, "--session-dir", self.session_dir, stdin=stdin)

        def register(self, texts, today=TODAY):
            payload = json.dumps([{"text": t} for t in texts], ensure_ascii=False)
            return self.seed("register", "--today", today, stdin=payload)

        def commit(self, cell, seed_id="S1", today=TODAY, extra=()):
            return run(IB_MAP, "commit", *self.map_args(), "--seed-id", seed_id,
                       "--session-dir", self.session_dir, "--today", today, *extra,
                       stdin=json.dumps(cell, ensure_ascii=False))

        def verdict(self, items, today=TODAY, extra=()):
            return run(IB_MAP, "verdict", *self.map_args(), "--today", today, *extra,
                       stdin=json.dumps(items, ensure_ascii=False))

        def status(self):
            return run(IB_MAP, "status", *self.map_args())

        def gate(self):
            return run(IB_MAP, "gate", *self.map_args())

        def backup_count(self):
            if not os.path.isdir(self.backup_dir):
                return 0
            return len([n for n in os.listdir(self.backup_dir) if n.startswith("migration_map.")])

    env = Env()
    write_map(env.map_path, [])
    return env
