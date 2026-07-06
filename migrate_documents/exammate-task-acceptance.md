# ExamMate 任务验收与用户旅程（迁移参考）

> 来源：`task_plan.md`
> 清洗说明：移除 ReMe 框架代码、测试用例、审查规则，保留验收标准和用户旅程

---

## 1. 模块定义

| 模块 | 任务 | 描述 |
|------|------|------|
| M1 项目骨架 | T1 | 项目目录结构 + 框架依赖 |
| M2 数据模型 | T2 | 6 类业务状态 Pydantic 模型 + 诊断模型 |
| M3 记忆适配 | T3 | StateAdapter 基类 + 6 类状态适配器 |
| M4 规则 Op | T4 | TimePressureOp, DateCheckOp, ExecutionLogCollectorOp |
| M5 记忆工具 | T5 | StateReaderTool + StateWriterTool |
| M6 LLM 工具 | T6 | CourseAnalyzer, QuestionSelector, WeakPointRanker, PlanBuilder, FeedbackParser, ImageAnalyzer |
| M7 ReAct Op | T7 | 9 个 BaseReactOp（ResourcePoolOp ~ ReplanOp） |
| M8 Flow 定义 | T8 | SprintFlow, FeedbackFlow, ColdStartFlow, DailyCheckFlow |
| M9 配置集成 | T9 | 配置文件 + 启动入口 + 全量注册 |
| M10 RAG 集成 | T11 | RAG 系统集成 + CourseAnalyzer/QuestionSelector 更新 |

---

## 2. 模块验收标准

### M2 数据模型验收

- TimePressureState 能正确表示三阶段 + 三压力等级
- ResourcePool 能表示课程章节、高频考点、高风险易错点
- AbilityProfile 能表示各知识点掌握度评分 + 整体评估
- WeakPointSnapshot 能表示薄弱点优先级排序 + 是否值得投入判断
- PlanSnapshot 能表示任务包列表 + 状态追踪
- ExecutionLog 能表示每日完成/跳过/部分完成统计
- DiagnosisResult 能表示各知识点正确率 + 错因分类

### M3 记忆适配验收

- StateAdapter 基类定义 serialize/deserialize 抽象方法
- 6 类状态全部往返正确（serialize → 节点 → deserialize → 字段一致）
- ResourcePool 多节点序列化后章节列表完整
- WeakPointSnapshot 反序列化后按 priority_rank 正确排序

### M4 规则 Op 验收

- TimePressureOp：remaining_days ≥ 14 → phasePlanning, 4-13 → sprintWeek, ≤3 → scoreProtection
- TimePressureOp：daily_hours < 1.5 时 pressure_level 强制升级为 high
- DateCheckOp：today == last_update_date → 不触发更新
- DateCheckOp：today > last_update_date → 触发更新
- ExecutionLogCollectorOp：能从 context 接收执行统计数据

### M7 ReAct Op 验收

- 9 个 Op 全部继承 BaseReact
- 每个 Op 指定正确的工具列表和 max_steps
- 满足七类业务判断 → Op/Tool 映射表的全部对应关系

### M8 Flow 验收

- SprintFlow 链路：TPS >> RP >> DiagOrg >> DiagInterp >> AP >> WP >> Plan
- FeedbackFlow 链路：FeedbackInput >> WeakPointUpdate >> Replan
- ColdStartFlow 链路：TPS >> RP >> DiagOrg
- DailyCheckFlow 链路：DateCheck >> ExecLog >> FeedbackFlow

---

## 3. P0 用户旅程（14 条）

### J01：首次完整冷启动

**场景**：用户首次使用，输入考试日期和课程名称，从未有过诊断或冲刺记录。

**路径**：
```
用户输入 → TimePressureOp → ResourcePoolOp → DiagnosisOrgOp → 用户作答 → DiagnosisInterpOp → AbilityProfileOp → WeakPointOp → PlanGenOp → 输出任务包
```

**验收**：
1. 用户从零输入到获得可执行任务包，全程无中断
2. 每一步状态正确写入记忆
3. PlanSnapshot 中任务类型包含 learn/practice/review

### J05：阶段规划期完整冲刺

**场景**：考试还有 14+ 天，阶段规划期，粗粒度规划。

**验收**：
1. 任务包粒度为章节/专题级
2. learn + practice 占比 > 60%

### J06：高压冲刺期完整冲刺

**场景**：考试还有 4-13 天，高压冲刺期，天级计划。

**验收**：
1. 任务包粒度为天级
2. practice + review 占比 > 50%

### J07：临考保分期完整冲刺

**场景**：考试还有 1-3 天，临考保分期。

**验收**：
1. scoreProtect + review 占比 > 70%
2. 无 learn 新知识任务
3. 输出可放弃内容建议

### J08：纯文本诊断

**场景**：用户通过文本输入完成诊断题。

**验收**：
1. DiagnosisResult 包含各知识点正确率
2. 错因分类覆盖：概念不清/方法不会/题型识别错误/粗心
3. weak_candidates 列表非空

### J11：全部完成反馈

**场景**：用户完成了当天所有任务。

**验收**：
1. 已修复薄弱点优先级下降
2. 新暴露薄弱点被插入
3. ReplanOp 输出重排原因

### J12：部分完成反馈

**场景**：用户只完成了部分任务。

**验收**：
1. PlanSnapshot 标记 completed/skipped/partial
2. 跳过任务不丢弃

### J13：新增错题反馈

**场景**：用户在执行过程中发现了新的错误类型。

**验收**：
1. 新增薄弱点插入 WeakPointSnapshot
2. 新 PlanSnapshot 包含修复任务

### J16：同日多次启动

**场景**：用户在一天内多次启动。

**验收**：
1. DateCheckOp 判断不需更新
2. 第二次启动读取已有 PlanSnapshot

### J17：次日首次启动

**场景**：用户第二天首次启动。

**验收**：
1. DateCheckOp 判断需更新
2. ExecutionLogCollectorOp 收集前日统计
3. 进入新 SprintFlow，不复用旧计划

### J19：阶段自动切换

**场景**：时间推移导致冲刺阶段自然变化。

**验收**：
1. 三阶段切换正确判定
2. 每次切换后 PlanSnapshot 粒度和类型比例符合特征

### J22：状态持久化与恢复

**场景**：用户退出后次日重新进入。

**验收**：
1. 五类状态全部从记忆正确恢复
2. 恢复后 Pydantic 对象字段一致

### J23：StateAdapter 序列化往返

**场景**：验证每个 StateAdapter 的 serialize → 写入 → 读取 → deserialize 往返。

**验收**：
1. 六类状态全部往返正确
2. ResourcePool 多节点序列化后章节完整
3. WeakPointSnapshot 反序列化后按 priority_rank 排序

### J30：7 天完整冲刺闭环

**场景**：模拟完整 7 天冲刺。

**验收**：
1. 7 天全程无中断
2. 阶段切换自动发生
3. 薄弱点持续追踪
4. 最终输出保分方案

---

## 4. P1 用户旅程（15 条）

### J02：冷启动 + 用户自有课程资料

CourseAnalyzer 能融合预置结构和用户补充资料。

### J03：冷启动 + 用户已有错题

诊断题选取受用户自述弱信号影响。

### J04：紧急进入（考试极近）

stage 正确判定为 scoreProtection；PlanSnapshot 中 scoreProtect 占比 > 50%。

### J09：图片作答诊断

ImageAnalyzerTool 能读取图片并提取答题内容。

### J10：复测诊断

复测范围限定在指定知识点；AbilityProfile 中评分有更新。

### J14：图片反馈

ImageAnalyzerTool 能从图片中提取完成/错误信息。

### J15：反馈导致阶段切换

TimePressureState 正确重新判定；PlanSnapshot 粒度切换。

### J18：连续多日未启动

DateCheckOp 正确计算多日间隔；ReplanOp 输出大面积调整。

### J20：每日时长变化导致压力升级

daily_hours < 1.5 时 pressure_level 升级为 high。

### J21：WeakPointSnapshot 三触发联动

三种触发机制各自独立工作。

### J24：WeakPointSnapshot 更新不累积

向量存储中只有最新版节点。

### J26：极低每日时长

daily_hours < 1.5 时 pressure_level 强制升级为 high。

### J27：无课程资料输入

ResourcePool 结构完整，不因缺少 course_content 报错。

### J31：薄弱点修复有效性验证

复测后薄弱点 accuracy 提升；优先级下降。

### J32：RAG 降级容错验证

RAG 不可用时自动降级到 Mock 模式；用户无感知。
