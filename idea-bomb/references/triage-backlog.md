# 存量分诊操作手册

一次性操作，用于清除迁移地图中历史积压的未裁决格子。零积压闸启用后，积压未清则后续流程全部阻塞。

## 前提

分诊仅修改 `user_verdict` / `restart_condition` / `archived` / `verdict_date` 四个键，不触碰旧格子的其他字段，亦不要求补充 `hypothesis`、`falsification` 等新字段。

`verdict` 命令不受零积压闸约束。

## 第一步：获取积压清单

```bash
python3 ~/.claude/skills/idea-bomb/scripts/ib_map.py status
```

关注 `undecided` 和 `undecided_items`。每条含 `index`、`idea_prefix`、原 `user_verdict`、`date`，下标为后续裁决的寻址依据。

已有真实裁决的格子不在清单内，分诊不触碰。

## 第二步：排序

按以下优先级排列未裁决格子：

1. 甜区（创新性高 × 可行性高）排最前。
2. 与 profile 主攻方向直接相关者优先于边缘探索。
3. 同主题聚簇，便于批量判断。
4. 元件级、工具级（非课题级）排后。

须向用户说明排序依据。

## 第三步：逐条精读前 10–15 个

逐个呈现：想法内容、原有判断、当前评估。每次一个，等待用户表态。

裁决仅限三个值：

- **采纳** — 进入工作流
- **否决** — 放弃
- **归档** — 移出活跃区，须同时给出重启条件

**禁止替用户否决任何想法。** 可提供评估意见（如可行性瓶颈、已有先例），最终裁决权归用户。用户未明确表态时，引导归档并请其拟定重启条件。

## 第四步：其余批量归档

前 15 个之外的格子整批归档，每条须写明具体重启条件。重启条件须指向可验证的具体事件或证据，泛泛表述（如"若有新数据则重新考虑"）不合格。示例：

> 若能论证 VE-cadherin 连接可逆自恢复，且给出微出血定量数据，则重新评估

批量执行前须将完整清单提交用户确认。脚本无自动裁决模式，`user_verdict` 仅接受显式传入。

## 第五步：执行

通过 stdin 传入数组。`expect` 为目标格子 `idea` 前缀（≥6 字），用于防止下标错位。

```bash
python3 ~/.claude/skills/idea-bomb/scripts/ib_map.py verdict <<'JSON'
[{"index": 12, "expect": "让定植菌持续分泌信号", "user_verdict": "归档",
  "restart_condition": "若能论证 VE-cadherin 连接可逆自恢复，且给出微出血定量数据"},
 {"index": 13, "expect": "把蛋白酶从降解ECM", "user_verdict": "采纳"}]
JSON
```

原子性：任一条不合格则整批拒绝，无部分写入。每次写入自动备份至 `~/.idea-bomb/backups/`。归档格子在 `cells` 原位打标，下标保持稳定。

## 第六步：验收

```bash
python3 ~/.claude/skills/idea-bomb/scripts/ib_map.py status   # undecided 应为 0
python3 ~/.claude/skills/idea-bomb/scripts/ib_map.py gate     # 退出码 0 方为通过
```

`gate` 放行即分诊完成。后续日常流程中新格子入库时即携带终态裁决，不再产生积压。

## 错误处理

- `INDEX_OUT_OF_RANGE`：下标越界，重新执行 `status` 获取最新清单。
- `PREFIX_MISMATCH`：下标与内容不匹配，`actual_prefix` 为该位置的实际内容。通常由中途插入新格子导致错位，须重新获取下标。
- `ALREADY_DECIDED`：该格子已有真实裁决。确认需覆盖时加 `--allow-overwrite`。
- `IO_FAILED`：地图未变，查看 `msg` 中的具体原因。
