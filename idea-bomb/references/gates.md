# 闸门机制：完整规则与参数

本文件为闸门拒绝时的排查参考。日常流程见 SKILL.md。

## 命令速查

```bash
S=~/.claude/skills/idea-bomb/scripts

python3 $S/ib_map.py  status                      # 状态概览
python3 $S/ib_map.py  gate                        # 零积压闸门检查
python3 $S/ib_seed.py register < seeds.json       # 登记种子
python3 $S/ib_seed.py list                        # 查看当日种子
python3 $S/ib_map.py  commit --seed-id S3 < cell.json   # 写入假说
python3 $S/ib_map.py  verdict < verdicts.json     # 补充裁决（分诊用）
```

所有命令输出 JSON 对象：成功 `"ok": true`，被拒 `"ok": false` 并附 `gate` 和 `errors`。
退出码：0 = 通过，2 = 闸门拦截，3 = 输入格式错误，4 = 数据文件异常。

## 参数

| 参数 | 默认 | 用在哪 |
|---|---|---|
| `--map` | `~/.idea-bomb/migration_map.json` | ib_map.py 全部子命令 |
| `--session-dir` | `~/.idea-bomb/session` | ib_seed.py 全部；ib_map.py commit（只读） |
| `--backup-dir` | map 所在目录下的 `backups/` | ib_map.py |
| `--today YYYY-MM-DD` | 系统日期 | 测试注入用，正常流程别加。**只在 `--map` / `--session-dir` 指向默认位置之外时才生效**：对真实数据动手时它会被忽略并在 stderr 提示，否则改个日期就能把种子唯一性校验重置一遍 |
| `--seed-id S3` | 无，必填 | commit |
| `--allow-overwrite` | 关 | verdict：覆盖已有裁决时才加 |

## 闸门 1 · 种子唯一性

- `commit` 须附 `--seed-id`，且为当日登记的 ID。
- 同一种子当日仅可展开一次：`SEED_ALREADY_USED`。
- stdin 中的 `date` 一律被覆写为当日。

## 闸门 2 · 写回必填闸

commit 时逐项校验，不合格项一次性全部报出。

| 字段 | 要求 |
|---|---|
| `idea` | ≥30 字 |
| `hypothesis` | 恰好四个键 `background` / `gap` / `design` / `innovation`，每个 ≥30 字 |
| `feasibility_layers` | 对象，≥3 层，每层 ≥10 字。键名随便起 |
| `falsification` | ≥30 字。写法见 hypothesis-format.md |
| `novelty_queries` | 真跑过的检索式。`method=transfer` 至少 2 条（源领域原名得搜一遍），其余至少 1 条，每条 ≥3 字 |
| `closest_work` | ≥4 字 |
| `diff` | 条件必填，见下 |
| `novelty` / `feasibility` / `quadrant` | 只查非空，怎么写随你 |
| `platform` / `disease` | 非空 |
| `method` | `transfer` / `combine` / `angle` / `contradiction` / `problem` / `tech_mismatch` / `data_driven` / `failure` |
| `status` | `untried` / `done` / `failed` |

`diff` 条件规则：`closest_work` 含"未检索到""未见先例""无直接先例"等表述时，`diff` 可留空；填写了具体工作（PMID、文章名）时，`diff` 必填且 ≥10 字。

闸门仅校验字段形式，不校验内容质量。

## 闸门 3 · 零积压闸

`ib_map.py gate` 检查是否存在 `user_verdict` 为占位词的格子。存在则拒绝（退出码 2），并输出前 30 条清单。

- 占位词判定采用黑名单：空串、`-` `—` `–` `?` `？` `无` `空` `暂无` `N/A` `null` `None` `TODO` `TBD`，以及以 `待定` `待确认` `待柚子确认` `待议` `待补` `待填` `未定` `暂定` `搁置` `pending` 开头的字符串（前缀匹配）。
- 用户已明确下过的判断（如 `不建议作主课题`、`已否决（2026-09-15）：…`）视为有效裁决。
- 空地图放行。
- 本闸不检查新必填字段，旧格子仅需补裁决即可通过。
- `verdict` 命令不受本闸约束。

## 闸门 4 · 裁决终态闸

`user_verdict` 仅接受三个精确值：

- **采纳**：进入工作流。
- **否决**：放弃。
- **归档**：移出活跃区，须同时写 `restart_condition`（≥10 字）。

其他值（`待定`、`pending`、`搁置`、空串等）及附带说明的变体（如 `采纳：作为 2027 青基主线`）均被拒绝。

已有真实裁决的格子默认拒绝覆盖（`ALREADY_DECIDED`），需覆盖时加 `--allow-overwrite`。

## 错误码对照

| code | 意思 | 怎么办 |
|---|---|---|
| `MISSING` | 字段没有 | 补上 |
| `EMPTY` | 空串、null、空数组、空对象 | 填真东西 |
| `PLACEHOLDER` | 填的是占位词 | 同上，别拿"待补"蒙 |
| `TOO_SHORT` | 短于最小长度 | 写够。长度按字符数算，中文一个字算一个 |
| `WRONG_TYPE` | 类型不对 | 看上面的字段表 |
| `TOO_FEW` | 元素不够（可行性不足三层、检索式条数不够） | 补齐 |
| `NOT_ALLOWED` | 取值不在允许集合内 | 看枚举 |
| `BACKLOG_NOT_EMPTY` | 库里有没裁决的 | 跑分诊 |
| `UNKNOWN_SEED` | seed_id 今天没登记过 | 先 register |
| `SEED_ALREADY_USED` | 这个种子今天展开过了 | 换一个种子 |
| `INDEX_OUT_OF_RANGE` | 下标越界 | 重新跑 status 拿下标 |
| `PREFIX_MISMATCH` | 下标和 idea 前缀对不上 | 下标错位了，响应里的 `actual_prefix` 是实际内容 |
| `ALREADY_DECIDED` | 目标已有裁决 | 确认要改就加 `--allow-overwrite` |
| `BAD_JSON` | stdin 或数据文件解析不了 | 检查 JSON |
| `IO_FAILED` | 备份失败、写入失败、回读校验没过 | 看 msg，地图此时还是原样 |

## 被拒后处理

按 `errors` 提示补齐后重新执行同一命令。两条禁令：

1. 禁止以占位值（空值、`—`、`待补`等）填充缺失字段。
2. **禁止绕过脚本直接编辑 `migration_map.json`。** 地图内含 `_integrity` 指纹，外部修改将在下次脚本运行时被检出。

## 写入安全

`commit` 和 `verdict` 为仅有的两条写入路径，执行相同流程：

1. 获取写锁（`migration_map.json.lock`），超时 10 秒
2. 读取原文件并记录内容指纹，解析失败则中止
3. 备份至 `backups/migration_map.<时间戳>.json`
4. 内存修改
5. 写临时文件并 fsync
6. 回读校验 JSON 可解析且条目数正确
7. 比对内容指纹，不一致则拒绝（防并发覆盖）
8. `os.replace` 原子替换并 fsync 目录

任何步骤失败均中止，原文件不变。脚本不删除备份。
