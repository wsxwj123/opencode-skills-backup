# Task Plan: 备份全部 Skills 并输出更新说明

## Goal
完成 `~/.config/opencode/skills` 全量备份到远端仓库，并明确说明哪些技能有更新以及更新内容摘要。

## Current Phase
Phase 1

## Phases
### Phase 1: 需求与现状确认
- [x] 确认用户目标（全量备份 + 更新说明）
- [x] 确认仓库状态与远端信息
- [x] 记录关键上下文
- **Status:** complete

### Phase 2: 计划与执行准备
- [x] 检查 `skills-backup` 脚本行为
- [x] 确认备份路径与分支
- [ ] 确认将要提交的变更范围
- **Status:** in_progress

### Phase 3: 执行备份
- [ ] 执行全量同步脚本
- [ ] 验证提交与推送结果
- **Status:** pending

### Phase 4: 变更分析与汇总
- [ ] 统计更新的 skill 列表
- [ ] 提炼每类更新内容
- [ ] 输出给用户
- **Status:** pending

## Key Questions
1. 本次需要提交的修改是否全部属于 skills 目录且可安全备份？
2. 如何按“技能维度”汇总大量文件变化，便于用户阅读？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用 `skills-backup` 官方脚本执行同步 | 与用户需求和技能规范一致 |
| 先采集变更清单再执行同步 | 便于输出准确的“更新了什么” |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| session-catchup 无输出 | 1 | 继续手动创建规划文件并执行后续流程 |
