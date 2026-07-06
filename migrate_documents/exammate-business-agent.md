# ExamMate 业务智能体层设计（迁移参考）

> 来源：`ExamMate_V0业务智能体层设计说明.md`
> 清洗说明：移除框架实现细节，保留业务判断定义和输入输出规范

---

## 1. 定位

业务智能体层是 ExamMate 的**主动决策层**，不是开放式问答，也不是简单总结课程资料。

核心职责：围绕考前冲刺场景，将用户输入、课程内容、诊断作答、历史错题和执行反馈转化为**可执行、可调整的冲刺决策**。

持续回答三个问题：
1. 当前时间压力下，用户最应该学什么
2. 当前能力状态下，用户最应该补什么
3. 当前执行偏差下，后续计划应该如何调整

---

## 2. 七类业务判断

### 判断 1：冲刺阶段判断

**输入**：考试日期、当前日期、每日可投入时长
**输出**：TimePressureState（stage + remaining_days + pressure_level）

**判定规则**：
- remaining_days ≥ 14 → phasePlanning, pressure=low
- remaining_days 4-13 → sprintWeek, pressure=medium
- remaining_days ≤ 3 → scoreProtection, pressure=high
- daily_hours < 1.5 时，pressure 强制升级为 high

**设计要点**：
- 纯规则计算，不依赖 LLM
- 阶段切换是自动的，用户无需手动选择

### 判断 2：课程资源分析

**输入**：课程名称、课程资料（可选）
**输出**：ResourcePool（章节列表 + 高频考点 + 高风险易错点）

**设计要点**：
- 优先使用预置课程结构
- 用户补充资料可融合进 ResourcePool
- 无用户资料时，LLM 基于课程名称生成基础结构

### 判断 3：诊断内容组织

**输入**：ResourcePool、冲刺阶段、用户自述弱信号（可选）
**输出**：诊断题列表（15 题，覆盖重点知识点）

**设计要点**：
- 每章至少 2 题
- 用户自述弱信号影响题目选取权重
- 临考保分期精简为 5 题

### 判断 4：诊断结果解释

**输入**：用户作答结果、ResourcePool
**输出**：DiagnosisResult（各知识点正确率 + 错因分类 + 弱候选列表）

**错因分类**：
- 概念不清
- 方法不会
- 题型识别错误
- 粗心

### 判断 5：能力画像构建

**输入**：DiagnosisResult、ResourcePool 优先级
**输出**：AbilityProfile（各知识点掌握度评分 + 整体评估 + 高风险薄弱点）

**设计要点**：
- 诊断结果转化为数值评分（0-1）
- 每个评分附带置信度（high/medium/low）

### 判断 6：薄弱点排序

**输入**：AbilityProfile、TimePressureState、课程高频考点
**输出**：WeakPointSnapshot（Top-N 薄弱点 + 修复建议 + 是否值得投入）

**排序维度**：
- 当前正确率（越低越优先）
- 高频考点权重（高频优先）
- 修复时间估算（时间紧迫时跳过高耗时项）
- 值得投入判断（worth_investing: bool）

### 判断 7：任务包生成

**输入**：WeakPointSnapshot、TimePressureState、每日可用时长
**输出**：PlanSnapshot（任务列表 + 总预计耗时）

**任务类型**：
- learn：学习新知识
- practice：做题巩固
- review：复习已学
- scoreProtect：保分冲刺

**阶段特征**：
- phasePlanning：learn + practice 为主
- sprintWeek：practice + review 为主
- scoreProtection：scoreProtect + review 为主，输出可放弃清单

---

## 3. 反馈与重排机制

### 执行反馈解析

**输入**：用户反馈文本（完成/跳过/新增错题）
**输出**：结构化反馈（completed/skipped/partial 列表 + 新增错题信息）

### 薄弱点更新

**触发条件**：
- 用户完成任务 → 对应薄弱点降级或移除
- 用户跳过任务 → 薄弱点维持或升级
- 新增错题 → 插入新的薄弱点

### 计划重排

**基于**：更新后的 WeakPointSnapshot + TimePressureState
**输出**：新 PlanSnapshot + 重排原因说明

**重排策略**：
- 已修复薄弱点 → 轻量 review
- 新增薄弱点 → 插入修复任务
- 时间压力变化 → 压缩或顺延部分任务

---

## 4. 每日检查机制

**触发**：每次启动时自动执行
**逻辑**：
1. 比较 today 与 last_update_date
2. 同一天内多次启动 → 跳过更新，读取已有计划
3. 次日首次启动 → 收集昨日执行统计 → 触发 FeedbackFlow → 生成新日计划
4. 连续多日未启动 → 收集多日统计 → 大面积调整计划

---

## 5. 多模态输入

V0 支持文本 + 图片两种输入方式：
- 开放性作答题目：文本输入 / 图片上传
- CLI 模式下通过文件路径提交图片
- 记忆系统只存分析结果文本，不存原始图片
