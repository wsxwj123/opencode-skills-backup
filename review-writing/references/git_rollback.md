# Git Rollback 指南

Because `init_project.py` runs `git init` + commits at Phase 0, every checkpoint is a full project snapshot — drafts (`drafts/section_*.md`), `state.json`, and `data/` indices all roll back together (atomic-draft rollback, no orphaned state). Run from inside the project root (`git_available: true` only):

```bash
git log --oneline                          # list checkpoints; find the [review] commit to return to
git checkout <sha> -- drafts/section_03_02.md   # restore ONE file (e.g. a bad section draft) from that checkpoint
git revert <sha>                            # undo a specific checkpoint's changes as a new commit (history-safe)
git checkout <sha> -- .                     # restore the ENTIRE project tree to that checkpoint (does not move HEAD)
```

Prefer `git checkout <sha> -- <file>` for a single bad section and `git revert` to back out a whole checkpoint. After any file restore, re-run `state_manager.py reindex` (None/EndNote) if gid alignment may have shifted. Do NOT use `git reset --hard` (destroys uncommitted work without confirmation).

## Edge Cases

| Issue | Handling |
|-------|---------|
| 需要回滚到之前某个阶段 | `git log --oneline` 查看检查点 → `git checkout <hash> -- .` 恢复文件 → `git add -A && git commit -m "[review] rollback to <phase>"` |
| 需要推倒重来（reset） | `git log --oneline` 找到 `[review] Phase 0` 的 commit → `git checkout <hash> -- .` → `git add -A && git commit -m "[review] rollback to Phase 0"` → 或直接删除项目目录重新 Phase 0 |
| Git 不可用 | 所有 checkpoint 静默跳过，不影响写作流程；建议安装 git 以获得回滚能力 |
