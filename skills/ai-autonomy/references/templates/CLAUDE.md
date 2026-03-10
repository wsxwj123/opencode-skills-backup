# AI 自治开发协议 v2.0

> 你是一个自治开发 Agent。每次启动时，你是全新的，不需要知道上一个 Agent 做了什么。
> 你只需要看交接文档，然后继续工作。

## 核心工作流

每次启动时，**必须严格按顺序执行**：

1. **环境自检**：运行 `python3 init.py`，确认环境就绪。
2. **状态同步**：读取 `feature_list.json` 和 `progress.txt`，了解当前进度。
3. **任务选择**：选择 `priority` 最小且 `status: "pending"` 的任务。
4. **执行开发**：按照任务的 `acceptance_criteria` 逐条实现。
5. **严格验证**：
   - 修改后端逻辑 → 必须跑通相关测试
   - 修改前端 UI → 必须截图验证
   - 修改配置 → 必须验证服务能正常启动
6. **更新状态**：
   - 任务完成 → 更新 `feature_list.json` 中该任务的 `status: "done"`, `passes: true`
   - 任务失败 → 保持 `status: "pending"`，在 `notes` 中记录失败原因
7. **写交接日志**：在 `progress.txt` 末尾追加本次工作记录。
8. **Git 提交**：`git add -A && git commit -m "feat(F-XXX): 简要描述"`

## 行为准则

- **不要猜测**：不确定的事情，查文档或读代码确认。
- **不要跳步**：严格按工作流执行，不要跳过验证。
- **不要过度修改**：只改当前任务相关的代码，不要"顺手"重构其他模块。
- **失败时回滚**：如果改坏了东西，`git checkout .` 回滚，记录原因，继续下一个任务。
- **保持上下文干净**：每个任务独立，完成后清理临时文件。

## 文件说明

| 文件 | 用途 |
|------|------|
| `feature_list.json` | 工单系统，你的任务清单 |
| `progress.txt` | 交接日志，记录决策和进度 |
| `CLAUDE.md` | 就是本文件，你的行为准则 |
| `init.py` | 跨平台环境初始化脚本 |
| `.autonomy/config/providers.json` | 模型提供商配置 |
| `.autonomy/config/.env` | API Key 配置 |
| `.autonomy/scripts/switch_provider.py` | 一键切换模型 |

## 模型配置

当前系统支持多模型提供商，配置在 `.autonomy/config/providers.json`。
通过 `python3 .autonomy/scripts/switch_provider.py <provider>` 一键切换。
