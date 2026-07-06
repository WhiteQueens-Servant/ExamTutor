# ExamMate 架构设计（迁移参考）

> 来源：`2026-05-22-exammate-agent-architecture-design.md`
> 清洗说明：移除 ReMe 框架代码示例，保留架构映射关系

---

## 1. 核心架构决策

### 注册式扩展 vs 继承

ExamMate 采用**注册式扩展**架构：不继承框架类，而是创建框架实例作为运行平台，将业务组件注册进去。

- 框架提供：Application 生命周期、LLM 管理、推理循环、记忆系统、Service 暴露
- ExamMate 提供：七类冲刺判断、任务包生成、状态适配

### 记忆系统选择

使用 **vector-based 记忆系统**（非 file-based）：

- 提供 CRUD API，UI 前端可通过 HTTP/MCP 调用读写状态
- 语义检索能力——"我想看看传输层薄弱点"可语义匹配
- Profile 演进能力——AbilityProfile 随时间变化

### RAG 集成

采用 **Python Import** 方式（进程内调用），同级目录结构：

- 时延最低（微秒级），成本最低
- 两个系统独立共存，零改造成本
- RAG 系统负责：文档加载、分块、向量化、混合检索、Reranker
- ExamMate 负责：调用 RAG 接口完成业务逻辑

---

## 2. 七类业务判断 → 组件映射

| 业务判断 | 组件类型 | 内部工具 | LLM 依赖度 |
|---------|---------|---------|----------|
| TimePressureState 判断 | 规则计算 | TimeCalculator, StageClassifier | 低 |
| ResourcePool 建立 | LLM 推理 | CourseAnalyzer, KnowledgeExtractor, PriorityTagger | 高 |
| 诊断内容组织 | LLM 推理 | QuestionSelector, TopicMapper, DifficultyBalancer | 中 |
| 诊断结果解释 | LLM 推理 | ScoreCalculator, ErrorClassifier, WeakSignalDetector | 高 |
| AbilityProfile 形成 | 顺序执行 | ProfileBuilder, TrendAnalyzer | 中 |
| WeakPointSnapshot 排序 | LLM 推理 | WeakPointRanker, FixTimeEstimator, InvestJudge | 高 |
| 任务包生成 | LLM 推理 | PlanBuilder, TimeAllocator, TaskPackager | 高 |
| 反馈解释与重排 | LLM 推理 | FeedbackParser, WeakPointRanker | 高 |
| 每日检查 | 规则计算 | DateCheckOp, ExecutionLogCollectorOp | 低 |

---

## 3. 四条 Flow 链路

```
# 1. 主冲刺链路 (SprintFlow)
TimePressureOp >> ResourcePoolOp >> DiagnosisOrgOp >> DiagnosisInterpOp >> AbilityProfileOp >> WeakPointOp >> PlanGenOp

# 2. 反馈重排链路 (FeedbackFlow)
FeedbackInputOp >> WeakPointUpdateOp >> ReplanOp

# 3. 冷启动链路 (ColdStartFlow)
TimePressureOp >> ResourcePoolOp >> DiagnosisOrgOp

# 4. 每日检查链路 (DailyCheckFlow)
DateCheckOp >> ExecutionLogCollectorOp >> FeedbackFlow
```

---

## 4. 六类业务状态 → 记忆映射

| 业务状态 | 记忆类型 | 存储结构 | 压缩策略 |
|---------|---------|---------|---------|
| TimePressureState | 用户维度 | 单节点：stage + remainingDays + pressureLevel | update 替换旧值 |
| ResourcePool | 用户维度 | 多节点：每章/专题一个节点 | 低优先级 delete |
| AbilityProfile | 用户维度 | 多节点：各知识点评分 + 整体评估 | update 替换评分 |
| WeakPointSnapshot | 用户维度 | 多节点：Top-N 薄弱点 | update 替换排序，超出 Top-N delete |
| PlanSnapshot | 流程维度 | 多节点：每个任务包一个节点 | 完成任务 delete，未完成保留 |
| ExecutionLog | 流程维度 | 每天一个统计节点 | 超过 7 天 delete |

### StateAdapter 翻译机制

StateAdapter 是业务对象与记忆节点的双向翻译器：

- **写入**：业务对象 → Adapter.serialize() → add_memory()/update_memory()
- **读取**：retrieve_memory()/list_memory() → Adapter.deserialize() → 业务对象

### WeakPointSnapshot 更新触发

WeakPointSnapshot 是**派生状态**：`f(AbilityProfile, TimePressureState, ResourcePool)`

| 触发对象 | 触发时机 | 更新方式 |
|---------|---------|---------|
| ExecutionFeedback | 用户完成/跳过每日任务 | 增量调整 |
| TimePressureState | 冲刺阶段切换 | 重新排序 |
| AbilityProfile | 新诊断结果 | 集合可能增减 |

### 每日定时更新机制

采用**混合方案**：
- **主路径**：Session-Triggered——每次启动时，比较 today 与 last_update_date，仅在 today > last_update_date 时触发更新
- **备选路径**：HTTP Service 模式下可配置外部 cron 补充

---

## 5. 服务暴露与部署模式

| 模式 | 适用场景 | 用户交互方式 |
|------|---------|------------|
| CLI 模式 | 开发验证、本地调试 | 终端对话 |
| HTTP API 模式 | 带 UI Shell 的本地部署 | REST API |
| MCP 模式 | 嵌入已有平台 | MCP 工具调用 |

V0 先以 CLI 模式验证，验证可行后切换 HTTP 模式。

---

## 6. V0 边界与简化

不在当前设计范围内：
- 多课程管理与跨课程全局调度
- 长期学习规划与学期全周期管理
- 教师端与组织端
- 具体 Prompt 模板内容
- API 接口详细设计
- 数据库存储结构细节
- UI Shell 的具体设计
