# 四个闸门：完整规则与参数

被脚本拒了再来查这一份。日常流程看 SKILL.md 就够。

## 命令速查

```bash
S=~/.claude/skills/idea-bomb/scripts

python3 $S/ib_map.py  status                      # 体检：多少格、多少没裁决、备份占多大
python3 $S/ib_map.py  gate                        # 开工前的零积压闸
python3 $S/ib_seed.py register < seeds.json       # 第一段：登记种子，拿 seed_id
python3 $S/ib_seed.py list                        # 看今天登记了哪些种子
python3 $S/ib_map.py  commit --seed-id S3 < cell.json   # 第二段：写入一条假说
python3 $S/ib_map.py  verdict < verdicts.json     # 给已有格子补裁决（分诊用）
```

所有命令的 stdout 都是一个 JSON 对象，成功 `"ok": true`，被拒 `"ok": false` 并给出 `gate` 和 `errors`。
退出码：0 放行，2 被闸门拦下，3 输入格式错，4 数据文件出问题。

## 参数

| 参数 | 默认 | 用在哪 |
|---|---|---|
| `--map` | `~/.idea-bomb/migration_map.json` | ib_map.py 全部子命令 |
| `--session-dir` | `~/.idea-bomb/session` | ib_seed.py 全部；ib_map.py commit（只读） |
| `--backup-dir` | map 所在目录下的 `backups/` | ib_map.py |
| `--today YYYY-MM-DD` | 系统日期 | 测试注入用，正常流程别加。**只在 `--map` / `--session-dir` 指向默认位置之外时才生效**：对真实数据动手时它会被忽略并在 stderr 提示，否则改个日期就能把日上限重置一遍 |
| `--seed-id S3` | 无，必填 | commit |
| `--allow-overwrite` | 关 | verdict：覆盖已有裁决时才加 |

## 闸门 1 · 数量闸

种子每天最多 8 个，深度假说每天最多 3 个。上限是脚本里的常量，没有 `--force`。留后门等于没闸门。

- 第一段登记第 9 个种子：拒，`gate=seed_cap`，`CAP_EXCEEDED`。整批拒绝，一条都不落盘。
- 当天第 4 次 commit：拒，`gate=hypothesis_cap`，`CAP_EXCEEDED`。
- commit 必须带 `--seed-id`，且该 ID 得是当天登记过的。这条把"第二段只展开用户点选的种子"变成硬约束。
- 同一个种子当天只能展开一次：`SEED_ALREADY_USED`。
- 老格子（schema 1）不算进日上限，哪怕它的 date 是今天。
- stdin 里的 `date` 一律被脚本覆写成当天，伪造日期绕不开上限。

配额按自然日算。跨午夜工作会被当成两天，这是已知代价，不修。

## 闸门 2 · 写回必填闸

commit 时逐项校验，不合格的全部一次性报出来，不是报一条让你补一条。

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
| `method` | `transfer` / `combine` / `angle` |
| `status` | `untried` / `done` / `failed` |

`diff` 的条件规则：`closest_work` 里出现"未检索到""未见先例""无直接先例"这类话，算查新做了但没撞车，`diff` 可以留空。写了具体工作（PMID、文章名）的，`diff` 必填且 ≥10 字。一刀切的长度门槛会把合法的"没找到先例"和敷衍的"—"一起砍，所以拆成两种情况。

脚本查的是字段的形，不是内容的实。四段 30 字的空话照样能过闸。闸门只保证你没跳过这些环节。

## 闸门 3 · 零积压闸

`ib_map.py gate` 只看一件事：还有没有 `user_verdict` 是占位词的格子。有就拒，退出码 2，并给出前 30 条清单。

- 判定用黑名单：占位词表里的才算没裁决。`不建议作主课题`、`已否决（2026-09-15）：…` 这类你本人下过的判断算已裁决，不会被要求重做。
- 占位词表：空串、`-` `—` `–` `?` `？` `无` `空` `暂无` `N/A` `null` `None` `TODO` `TBD`，以及以 `待定` `待确认` `待柚子确认` `待议` `待补` `待填` `未定` `暂定` `搁置` `pending` 开头的任何字符串。
- `待定：拟作 2027 青基主线方案 A` 这种带补充说明的照样算没裁决——前缀匹配就是为它准备的。
- 空地图放行。
- 这一闸不看任何新必填字段，所以 103 个老格子只要补上裁决就能让它通过，不用回填 hypothesis。
- 分诊命令 `verdict` 不受这一闸约束。它是解药，不能被病挡住。

这是四个闸门里最弱的一个：脚本能判定，但拦不住 AI 跳过这条命令直接开始想点子。所以它在 SKILL.md 里被写成 Step 0 的第一条。

## 闸门 4 · 裁决终态闸

`user_verdict` 只收三个值，精确相等，不做前缀匹配：

- **采纳**：进工作流。
- **否决**：不做了。
- **归档**：移出活跃区但留在库里，必须同时写 `restart_condition`（≥10 字，写清楚什么条件下把它捞回来）。

`待定`、`待柚子确认`、`pending`、`搁置`、空串一律拒。`采纳：作为 2027 青基主线` 也拒——补充说明写到别的字段去，裁决值本身要干净。

归档是给"现在不想定，但不舍得毙"准备的出口。没有它，零积压闸就会逼着你把好想法当场毙掉，那就违反红线了。

分诊时如果目标格子已经有真实裁决，默认拒绝覆盖（`ALREADY_DECIDED`），确实要改再加 `--allow-overwrite`。

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
| `CAP_EXCEEDED` | 超日上限 | 今天到顶了，明天再来，或者先清积压 |
| `BACKLOG_NOT_EMPTY` | 库里有没裁决的 | 跑分诊 |
| `UNKNOWN_SEED` | seed_id 今天没登记过 | 先 register |
| `SEED_ALREADY_USED` | 这个种子今天展开过了 | 换一个种子 |
| `INDEX_OUT_OF_RANGE` | 下标越界 | 重新跑 status 拿下标 |
| `PREFIX_MISMATCH` | 下标和 idea 前缀对不上 | 下标错位了，响应里的 `actual_prefix` 是实际内容 |
| `ALREADY_DECIDED` | 目标已有裁决 | 确认要改就加 `--allow-overwrite` |
| `BAD_JSON` | stdin 或数据文件解析不了 | 检查 JSON |
| `IO_FAILED` | 备份失败、写入失败、回读校验没过 | 看 msg，地图此时还是原样 |

## 被拒了怎么办

照 `errors` 里说的补，然后重跑同一条命令。三件事不许做：

1. 不许把缺的字段填成空值、`—`、`待补` 蒙混过关——占位词表就是拦这个的。
2. 不许改脚本里的上限常量来让自己过闸。要放宽是用户的决定，不是你的。
3. **不许绕过脚本直接编辑 `migration_map.json`。** 这是所有闸门唯一的窟窿，堵不上，只能靠不碰。地图里有个 `_integrity` 字段记着上次写入后的内容指纹，下次任何命令跑起来都会核对，对不上会在 stderr 报"疑似被外部编辑"。那是事后发现，不是事前阻止——真绕过去了，损失的是用户对这套闸门的信任。

## 写入安全

`commit` 和 `verdict` 是仅有的两条写入路径，走同一套流程：

1. 拿写锁（`migration_map.json.lock`，同目录多出来的那个空文件就是它），等不到就 10 秒后放弃
2. 读原文件，解析失败就停，原文件一个字节不动；顺便记下此刻的内容指纹
3. 备份到 `backups/migration_map.<时间戳>.json`，校验备份体积和原文件一致
4. 内存里改
5. 写临时文件，fsync
6. 回读临时文件，校验 JSON 能解析且条目数是预期的
7. 替换前再比一次内容指纹，和第 2 步不一样就拒绝——绝不拿旧快照盖掉别人的改动
8. `os.replace` 原子替换，再 fsync 目录

任何一步失败都中止，原文件保持原样，临时文件清掉。

第 1 和第 7 步是防并发的：没有它们，两个进程同时跑 `verdict`（比如把存量分诊拆成两批并行），后完成的那个会用旧快照整体覆盖，**两边都返回 `ok: true`，改动静默消失，备份也救不回来**（两份备份都是同一个旧版本）。

**脚本永远不会删除任何备份**，攒多了 `status` 会提示，自己清。
