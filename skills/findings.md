# Findings & Decisions

## Requirements
- 备份所有 skills 到远端仓库
- 输出“哪些更新了”
- 输出“更新了什么内容”

## Research Findings
- 当前仓库路径：`/Users/wsxwj/.config/opencode/skills`
- 当前分支：`main`
- 远端：`origin -> https://github.com/wsxwj123/opencode-skills-backup`
- 变更集中在多个 `SKILL.md` 与 `sci2doc` 子目录文件
- 已新增全局 skill：`pua`（来源：`https://github.com/tanweai/pua`，安装路径：`/Users/wsxwj/.config/opencode/skills/pua`）

## Installation Notes
- `pua` 已按 OpenCode 全局 skill 方式安装到 `~/.config/opencode/skills/pua`
- 已同步 `SKILL.md` 及其 `references/` 依赖文件
- 使用方式：在对话中直接提到“用 pua skill 继续处理/排查这个问题”即可增强主动性与闭环排查

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 `skills-backup/scripts/sync_skills.py` 做全量同步 | 与 skill 文档推荐流程一致 |
| 先记录变更清单再同步 | 便于给出准确更新报告 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| session-catchup 输出为空 | 不中断流程，继续手动建计划文件并执行 |

## Resources
- `/Users/wsxwj/.config/opencode/skills/skills-backup/SKILL.md`
- `/Users/wsxwj/.config/opencode/skills/skills-backup/scripts/sync_skills.py`

## Visual/Browser Findings
- 无
