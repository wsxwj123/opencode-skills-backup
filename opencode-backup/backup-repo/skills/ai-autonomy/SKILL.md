---
name: ai-autonomy
description: >
  AI 自治开发系统。在任何项目中启动 AI 自动化开发，支持两种模式：
  嵌入式（每个 session 自动读取任务继续开发）和脚本循环（终端无人值守批量执行）。
  触发词：自治开发、自动化开发、autonomous dev、初始化自治、启动自治、
  添加任务、写工单、agent team、多智能体协作、接着干活、继续开发。
---

# AI 自治开发系统

> 在任何项目文件夹中注入自治能力，让 AI 像轮班工人一样连续开发。

## 两种使用模式

### 模式 A：嵌入式（推荐日常使用）
用户在 OpenCode 中打开项目 → 说"初始化自治" → 注入文件 → 之后每个 session 说"接着干活"即可。
AI 读取 feature_list.json 找 pending 任务，干完更新状态，写交接日志。

### 模式 B：脚本自动循环（批量赶工）
终端运行 `python3 .autonomy/run_autonomy.py`，无限循环调用 AI CLI，完全无人值守。

---

## 工作流

### 1. 初始化（用户说"初始化自治"）

在**当前项目目录**创建 `.autonomy/` 子目录 + 根目录注入 CLAUDE.md：

```
用户的项目/（已有代码）
├── src/、package.json 等（用户已有的文件）
│
├── CLAUDE.md                    ← 注入：AI 行为准则（根目录，AI 自动读取）
├── feature_list.json            ← 注入：任务工单
├── progress.txt                 ← 注入：交接日志
└── .autonomy/                   ← 注入：自治系统文件
    ├── config/
    │   ├── providers.json       ← 多模型提供商配置
    │   ├── agent_team_config.json
    │   └── .env                 ← API Keys（gitignore）
    ├── scripts/
    │   ├── run_autonomy.py      ← 2.0 无限循环驱动
    │   ├── run_team.py          ← 3.0 多 Agent 驱动
    │   └── switch_provider.py   ← 切换模型
    └── agents/                  ← Agent 角色定义
        ├── lead-cto.md
        ├── backend-integrator.md
        ├── frontend-polisher.md
        └── qa-engineer.md
```

步骤：
1. 确认当前目录是用户的项目（不要创建新目录）
2. 创建 `.autonomy/` 子目录
3. 从 skill 的 `references/templates/` 复制所有模板文件
4. 在根目录创建 CLAUDE.md、feature_list.json、progress.txt
5. 在 .gitignore 中追加 `.autonomy/config/.env`
6. 询问用户有哪些 API 提供商，写入 providers.json 和 .env
7. 提示用户编写第一批任务工单

### 2. 接着干活（用户说"接着干活"/"继续开发"/"下一个任务"）

这是嵌入式模式的核心。每次新 session 执行：

1. 读取 `feature_list.json`，找 `status: "pending"` 且 `priority` 最小的任务
2. 读取 `progress.txt` 最后 20 行，了解上次交接内容
3. 如果没有 pending 任务，告诉用户"全部完成"
4. 如果有任务：
   a. 宣布当前要做的任务
   b. 按 `acceptance_criteria` 逐条实现
   c. 验证（跑测试/检查语法）
   d. 更新 feature_list.json：`status: "done"`, `passes: true`
   e. 在 progress.txt 追加交接日志
   f. Git commit：`feat(任务ID): 简要描述`
   g. 问用户"继续下一个？"或自动继续

### 3. 添加任务（用户说"添加任务"/"写工单"）

交互式询问：
- 任务描述
- 类别（backend/frontend/testing/fullstack/setup）
- 优先级（数字越小越优先）
- 验收标准（逐条输入）

写入 feature_list.json，格式：
```json
{
  "id": "F-XXX",
  "description": "...",
  "category": "backend",
  "priority": 1,
  "status": "pending",
  "acceptance_criteria": ["...", "..."],
  "notes": ""
}
```

### 4. 配置模型（用户说"配置模型"/"切换模型"/"添加提供商"）

- 读取 `.autonomy/config/providers.json`
- 用户提供 base_url + API Key + 模型名 → 写入配置
- 运行 `python3 .autonomy/scripts/switch_provider.py` 验证
- 支持自动查询 `/v1/models` 获取可用模型列表

### 5. 启动脚本循环（用户说"启动自动循环"/"无人值守"）

**不要在对话中运行！** 告诉用户在终端执行：

```bash
# 2.0 单 Agent 循环
python3 .autonomy/scripts/run_autonomy.py

# 3.0 多 Agent 团队
python3 .autonomy/scripts/run_team.py

# Ctrl+C 优雅停止
```

## 行为准则（嵌入式模式）

当 AI 在 session 中"接着干活"时，必须遵守：

- **不要猜测**：不确定的事情，查文档或读代码确认
- **不要跳步**：严格按工作流执行，不要跳过验证
- **不要过度修改**：只改当前任务相关的代码
- **失败时记录**：改坏了就 `git checkout .` 回滚，在 notes 记录原因
- **保持交接**：每个任务完成后必须更新 feature_list.json 和 progress.txt

## 文件参考

- Agent 角色定义：[references/agents/](references/agents/)
- 配置模板：[references/templates/](references/templates/)
- 脚本源码：[scripts/](scripts/)
