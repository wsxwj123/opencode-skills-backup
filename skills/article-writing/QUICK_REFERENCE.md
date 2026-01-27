# Article Writing Skill - 快速参考卡片

## 🚀 快速开始（3步）

```
1. /init              → 初始化项目
2. /preview           → 预审模式（3000词报告）
3. /storyline         → 构建故事脉络
4. /literature phase1 → 检索核心文献
5. /write abstract    → 开始撰写
```

---

## 📋 核心命令

| 命令 | 功能 | 使用时机 |
|------|------|----------|
| `/init` | 初始化项目 | 首次使用 |
| `/resume` | 恢复写作 | 对话中断后 |
| `/preview` | 预审报告 | 开始写作前 |
| `/storyline` | 构建提纲 | 预审后 |
| `/literature [phase]` | 文献检索 | storyline后/写作时 |
| `/write [section]` | 撰写章节 | 按顺序撰写 |
| `/check` | 质量检查 | 完成章节后 |
| `/reviewer [mode]` | 审稿人模拟 | storyline后/完稿后 |
| `/snapshot [desc]` | 手动快照 | 重大修改前 |
| `/rollback` | 版本回滚 | 需要恢复时 |
| `/stats` | 进度仪表盘 | 随时查看 |
| `/merge` | 最终合并 | 全部完成后 |

---

## 📊 核心标准

### 字数限制
- **Abstract**: ≤250词（严格）
- **Introduction**: 800-1500词
- **Main Text**: 5000-7000词
- **参考文献**: 30-50篇

### 文献时间窗口
- **背景统计**: ≤2年
- **Gap/创新**: ≤5年（IF>10）
- **机制**: ≤10年
- **方法**: 不限

### 引用密度
- **Introduction**: 论点1-2篇，讨论3-4篇
- **Results**: 不引用
- **Discussion**: 论点1-2篇，展望3-4篇
- **Methods**: 仅方法学原始论文

---

## 🔄 工作流程

```
初始化 → 预审 → storyline → Phase 1文献 → 撰写各章节 → 质量检查 → 审稿人模拟 → 合并
  ↓        ↓        ↓           ↓              ↓            ↓          ↓           ↓
/init   /preview /storyline /literature   /write xxx   /check   /reviewer   /merge
```

---

## 🗂️ 核心文件（必读优先级）

### 🔴 P0级（绝对必读）
1. `project_config.json` - 项目配置
2. `storyline.json` - 故事脉络（选项B粒度）
3. `writing_progress.json` - 实时进度
4. `context_memory.md` - 上下文快照（3版本）
5. `literature_index.json` - 文献数据库（防止重复引用）
6. `figures_database.json` - Figure元数据

### 🟡 P1级（高优先级）
7. `reviewer_concerns.json` - 审稿人质疑库
8. `version_history.json` - 版本历史

---

## ⚡ 自动触发机制

### 自动快照触发点
- ✅ storyline确认后
- ✅ Phase 1文献检索完成后
- ✅ 每个章节完成后
- ✅ 最终合并前

### context_memory更新触发点
- ✅ 完成任何一个小节
- ✅ 完成文献检索
- ✅ 用户提供Figure数据
- ✅ 关键决策讨论后
- ✅ 质量检查发现问题
- ✅ 执行rollback

---

## 🛡️ 质量检查项

- ✅ 字数控制
- ✅ 引用密度
- ✅ Figure编号连续性
- ✅ AI高频词自动替换
- ✅ 数据冲突检测
- ✅ 统计显著性表达（P值）

---

## 🚨 常见问题速查

### Q: 对话中断怎么办？
**A**: 使用`/resume`，AI会自动加载所有上下文

### Q: 如何避免重复引用？
**A**: AI自动检查`literature_index.json`中的DOI和标题

### Q: 如何回滚到之前版本？
**A**: 使用`/rollback`，选择快照版本

### Q: Figure编号混乱怎么办？
**A**: AI会提醒但不自动修正（防止遗漏），需用户确认

### Q: 如何查看当前进度？
**A**: 使用`/stats`查看进度条、字数、文献统计

---

## 📝 写作禁忌

### 严禁AI表达
❌ "delve into" → ✅ "investigate"
❌ "comprehensive landscape" → ✅ "overview"
❌ "pivotal role" → ✅ "important role"
❌ "It is well known that..." → ✅ 直接陈述

### 严禁模糊量词
❌ "significant effect" → ✅ "5-fold increase (P=0.0023)"
❌ "considerable improvement" → ✅ "tumor volume reduced by 60%"

---

## 🎯 成功标准

一篇成功的论文应该：
- ✅ Storyline逻辑严密
- ✅ 创新性清晰，差异化明确
- ✅ 数据完整，逻辑链无断裂
- ✅ 写作简练，无AI味
- ✅ 预见并预防审稿人质疑
- ✅ Limitation诚实且有解决方案
- ✅ 参考文献新颖权威

---

## 💡 专家建议

### 提高创新性
1. 在Introduction中明确与竞争工作的差异
2. 强调您独有的数据（定量 vs 定性）
3. 突出工业化/临床转化潜力

### 强化逻辑链
1. 补充非响应对照组
2. 增加体内penetration depth数据
3. 机制验证实验（抑制剂阻断）

### 预防致命质疑
1. EPR争议：在Discussion中引用临床试验数据
2. 批次稳定性：Methods中说明3批次验证
3. 长期毒性：SI中补充H&E和血生化

---

## 📞 技术支持

- 遇到问题先查看`USAGE_GUIDE.md`中的完整示例
- 使用`/check`进行自动质量检查
- 使用`/reviewer storyline`提前发现问题

---

**版本**: 1.0.0  
**最后更新**: 2024-01-27  
**适用期刊**: Nature/Science/Cell及其子刊
