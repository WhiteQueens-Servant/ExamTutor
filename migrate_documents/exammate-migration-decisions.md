# ExamMate → DeepTutor 设计迁移决策文档

> 记录每个细化阶段的讨论决策成果。按阶段编号，每个决策包含背景、方案、理由。

---

## #1 状态存储格式

**状态**：✅ 已确定
**日期**：2026-07-05

### 背景

ExamMate 有 6 个状态模型需要持久化：TimePressureState、ResourcePool、AbilityProfile、WeakPointSnapshot、PlanSnapshot、ExecutionLog。需要决定它们在 DeepTutor 记忆系统（L1/L2/L3）中的存储位置和更新机制。

### 决策

1. **存储位置**：在 L2 层新增 `"exam"` surface，6 个状态模型存放在 `L2/exam.md` 的不同 section 中
2. **不新增 L3 slot**：V0 阶段不需要跨考试周期的长期画像
3. **不启用 L1 trace**：exam 状态是快照式（覆盖写入），非追加式（事件流）
4. **状态更新方式**：exam Tool 通过 `MemoryStore.overwrite_doc("L2", "exam", markdown_content)` 直接写入 L2，绕过 L1→L2 合并流水线

### 理由

- **最小改动**：只需在 `paths.py` 的 `Surface` Literal 中加 `"exam"`，L2 基础设施自动适配
- **天然隔离**：exam 数据与 chat/quiz/book 等现有 surface 完全独立
- **复用机制**：自动获得 L2 摘要合并、前端 Memory Workbench 展示能力
- **语义匹配**：exam 状态是快照式更新，直接覆盖写入比 L1 事件流合并更自然
- **V1 扩展点**：未来可在 Tool 写入时同时 append L1 event 作为审计日志

### L2/exam.md 结构草案

```markdown
# Exam Sprint

## 时间压力
- 考试日期: 2026-08-15
- 阶段: sprintWeek
- 剩余天数: 41
- 压力等级: medium

## 课程资源
- 章节1: 高频考点 x3, 易错点 x2
- 章节2: ...

## 能力画像
- 知识点A: 掌握度 0.6
- 知识点B: 掌握度 0.8
- ...

## 薄弱点 (Top-N)
1. 知识点A — worth_investing: true
2. 知识点C — worth_investing: false
...

## 当前计划
### 今日任务
- [ ] learn: 知识点A 专题 (30min)
- [ ] practice: 章节2 练习题 (20min)
### 本周目标
- 完成 sprintWeek 第2周计划

## 执行日志
- 2026-07-05: 完成 3/4 任务, 新增错题 2 道
- 2026-07-04: 完成 2/3 任务, 跳过 1 道
```

### 涉及代码改动

- `deeptutor/services/memory/paths.py` — Surface Literal 加 `"exam"`
- `web/components/memory/MemorySection.tsx` — SURFACES 数组加 `"exam"`
- `web/components/memory/MemoryL1Workbench.tsx` — L1_NAV 加 exam 入口
- `web/app/(utility)/memory/l1/page.tsx` — VALID_SURFACES 加 `"exam"`

---

## #2 记忆 surface 命名规范

**状态**：✅ 已确定
**日期**：2026-07-05

### 决策

- Surface key 命名为 `"exam"`
- 与现有 surface 完全隔离：quiz（题库）、chat（对话）、book（教材）均不耦合
- 唯一的数据交互通过 Tool 层面实现：RAGTool 读 book KB、DeepQuestion 生成诊断题
- 不涉及记忆层的交叉读写

---

## #3 TimePressureTool 设计

**状态**：✅ 已确定
**日期**：2026-07-05

### 背景

需要一个工具根据考试日期计算当前所处的三阶段（ExamMate 核心创新）。

### 决策

**职责边界**：纯时间计算器，零 LLM 依赖，零副作用。

**输入**：

```python
{
    "exam_date": "2026-08-15",      # ISO 8601 格式
    "current_date": "2026-07-05"    # 可选，默认系统当前日期
}
```

**输出**：

```python
{
    "stage": "phasePlanning",       # phasePlanning | sprintWeek | scoreProtection
    "remaining_days": 41,
    "pressure_level": "medium"      # low | medium | high | critical
}
```

**三阶段判定规则**：

| 阶段 | 条件 | 核心行为 |
|------|------|---------|
| `phasePlanning` | remaining_days ≥ 14 | 课程资源梳理 + 诊断评估 |
| `sprintWeek` | 4 ≤ remaining_days ≤ 13 | 薄弱点攻坚 + 每日计划执行 |
| `scoreProtection` | remaining_days ≤ 3 | 保分任务 + 查漏补缺 |

**压力等级映射**：

| remaining_days | pressure_level |
|---------------|---------------|
| ≥ 21 | low |
| 14–20 | medium |
| 7–13 | high |
| ≤ 6 | critical |

**校验**：exam_date 不能是过去的日期，缺失时返回特定错误码。

**"建议"类输出不在此 Tool 职责内**：每日学习时长、本周重点等需要 LLM 读取能力画像/薄弱点/计划进度后推理，由 ExamSprintCapability 管道的 LLM 推理阶段完成。

---

## #4 WeakPointRankerTool 设计

**状态**：✅ 已确定
**日期**：2026-07-05

### 决策

**实现方案**：纯规则（零 token 消耗），与 TimePressureTool 保持一致的"纯计算器"风格。

**输入**：

```python
{
    "ability_profile": {"知识点A": 0.6, "知识点B": 0.8, ...},  # 从 L2/exam.md 读取
    "stage": "sprintWeek",        # 来自 TimePressureTool
    "remaining_days": 10
}
```

**输出**：

```python
{
    "weak_points": [
        {"name": "知识点C", "mastery": 0.3, "worth_investing": true, "priority": 1},
        {"name": "知识点A", "mastery": 0.6, "worth_investing": true, "priority": 2}
    ],
    "skipped": ["知识点B", "知识点D"]  # mastery ≥ 0.7，不需投入
}
```

**规则**：

| mastery 范围 | worth_investing | 优先级 |
|-------------|----------------|--------|
| < 0.5 | true | 高 |
| 0.5 – 0.69 | true | 中 |
| ≥ 0.7 | false | — |

**时间约束裁剪**：

| 阶段 | 保留数量 |
|------|---------|
| phasePlanning (≥14天) | 全部 |
| sprintWeek (4–13天) | Top-3 |
| scoreProtection (≤3天) | Top-1 |

**排序**：mastery 升序（越低越优先）

**选择理由**：
- 薄弱点排序的核心逻辑是确定性的（掌握度低 → 优先补）
- 考试权重信息在冷启动阶段还不准确（需要多次诊断才能建立）
- 与 TimePressureTool 保持一致的零 token 消耗
- V1 可升级为 LLM 推理，接口不变

---

## #5 PlanBuilderTool 设计

**状态**：✅ 已确定
**日期**：2026-07-05

### 决策

**实现方案**：纯规则（零 token 消耗）。

**职责**：根据薄弱点排序 + 时间压力 + 可用时间，生成结构化的任务包骨架。

**输入**：

```python
{
    "weak_points": [                          # 来自 WeakPointRankerTool
        {"name": "知识点C", "mastery": 0.3, "worth_investing": true, "priority": 1},
        {"name": "知识点A", "mastery": 0.6, "worth_investing": true, "priority": 2}
    ],
    "stage": "sprintWeek",                    # 来自 TimePressureTool
    "remaining_days": 10,
    "daily_budget_minutes": 120               # 用户设定的每日学习时长
}
```

**输出**：

```python
{
    "today_plan": [
        {"type": "learn", "target": "知识点C", "est_minutes": 40},
        {"type": "practice", "target": "知识点C", "est_minutes": 30},
        {"type": "practice", "target": "知识点A", "est_minutes": 30},
        {"type": "review", "target": "all", "est_minutes": 20}
    ],
    "week_goal": "完成 sprintWeek 第2周计划：知识点C 从 0.3 提升至 0.5+",
    "total_estimated_minutes": 120
}
```

**任务类型分配规则**：

| 条件 | 任务类型 |
|------|---------|
| mastery < 0.5 | learn + practice |
| 0.5 ≤ mastery < 0.7 | practice |
| mastery ≥ 0.7 | review only |

**固定时间估算**：

| 任务类型 | 时长 |
|---------|------|
| learn | 40min |
| practice | 30min |
| review | 20min |

**阶段行为**：

| 阶段 | 侧重点 |
|------|--------|
| phasePlanning | 练习为主，少量学习 |
| sprintWeek | 学习 + 练习混合 |
| scoreProtection | 仅复习 + 查漏补缺 |

**选择理由**：
- 任务包的"骨架"可以由规则生成（类型分配、时间估算）
- 具体的"学什么内容"（题目、解析、来源）由执行阶段的 LLM 按需生成
- 保持 Tool 层的确定性，LLM 的创造性留给 Capability 层

---

## #6 FeedbackParserTool 设计

**状态**：❌ 取消（合并入 Capability 层）
**日期**：2026-07-05

### 决策

**FeedbackParserTool 不作为独立 Tool 存在。**

### 理由

- 反馈来自上游行为收集程序（隐式收集），数据已是结构化，不需要"解析"
- 如果需要 LLM 推理（错误分类、学习建议），它是推理步骤，不是原子 Tool
- mastery 更新用纯规则（固定增量），不需要 LLM
- 保持 Tool 层只有 3 个纯规则 Tool：TimePressure、WeakPointRanker、PlanBuilder

### 替代方案

反馈处理逻辑由 ExamSprintCapability 直接完成：

```
上游程序收集作答结果 → 结构化数据
                            ↓
ExamSprintCapability 直接处理：
  1. 读取结构化作答结果（正确率、错题列表）
  2. 纯规则更新 mastery（对了 +0.05，错了 -0.03）
  3. 用 LLM 推理错误分类和学习建议（如果需要）
  4. 写入 L2/exam.md
```

---

## #7 ExamSprintCapability 骨架

**状态**：✅ 已确定
**日期**：2026-07-05

### 决策

**注册方式**：

1. 新建 `deeptutor/capabilities/exam_sprint.py`
2. 在 `builtin_capabilities.py` 添加映射：`"exam_sprint": "deeptutor.capabilities.exam_sprint:ExamSprintCapability"`

**CapabilityManifest**：

```python
manifest = CapabilityManifest(
    name="exam_sprint",
    description="Exam sprint mode — time-pressure-driven adaptive study plan.",
    stages=["cold_start", "assess", "plan", "advise"],
    tools_used=["time_pressure", "weak_point_ranker", "plan_builder", "rag"],
    cli_aliases=["exam"],
    request_schema={...},   # exam_date, daily_budget_minutes
    config_defaults={...},
)
```

**管道数据流**（方案 ②，#5 预确认）：

```
PlanBuilderTool → 任务骨架 → 直接呈现给用户（今日计划）
                                   ↓ 用户点击"开始执行"
                              LLM 按任务类型按需生成具体内容
```

- PlanBuilderTool 的输出（任务骨架）直接呈现给用户，不经过 LLM
- 题目/解析/来源在执行阶段由对应 Capability/Tool 生成
- Plan 是"目录"，LLM 结果是"内容"，分两步呈现

**循环机制**：

- 每次 `run()` 调用是一个完整的 assess→plan→advise 循环
- 循环由外部事件触发新的 `run()` 调用（不是单次 run() 内部 while 循环）
- 触发信号：用户执行完任务（反馈驱动）/ 阶段切换（时间驱动）
- 与 DeepSolve 的内部 replan 不同：ExamSprint 的循环是跨调用的

**run() 管道结构**：

```python
async def run(self, context, stream):
    exam_state = read_exam_state(context.session_id)
    
    if is_cold_start(exam_state):
        # ── cold_start stage ──
        async with stream.stage("cold_start", source="exam_sprint"):
            exam_state = await cold_start_flow(context, stream)
    
    # ── assess stage ──
    async with stream.stage("assess", source="exam_sprint"):
        tp = await time_pressure_tool(exam_state["exam_date"])
        wp = await weak_point_ranker(exam_state["ability_profile"], tp)
    
    # ── plan stage ──
    async with stream.stage("plan", source="exam_sprint"):
        plan = await plan_builder(wp, tp, daily_budget)
    
    # ── advise stage ──
    async with stream.stage("advise", source="exam_sprint"):
        advice = await llm_reason(tp, wp, plan, exam_state)
        await present_to_user(stream, plan, advice)
        write_exam_state(exam_state, tp, wp, plan)
```

### 已识别的适配点

**冷启动中调用 DeepQuestionCapability 进行诊断评估**：

- DeepQuestionCapability 不是可嵌入的"服务"，而是顶层 Capability（自己管理 stream、创建 QuestionPipeline、emit result）
- 调用路径：**直接实例化 `QuestionPipeline`**（路径 B），而非构造伪造 UnifiedContext
- 理由：ExamSprint 需要控制诊断题输出（收集结果建立能力画像，不直接发给用户）
- 具体实现细节留待 #8 冷启动流程展开

---

## #8 冷启动流程

**状态**：✅ 已确定（流程骨架见 #7）

### 预确认：冷启动完整步骤

> 在 #7 讨论中确认。

```
冷启动（exam_state 为空）
│
├─ Step 1: 收集考试信息
│   └─ AskUserTool: "你要备考什么考试？考试日期是？"
│   └─ 输出: exam_name, exam_date, daily_budget_minutes
│
├─ Step 2: RAG 课程资源检索
│   └─ RAGTool(query=exam_name, kb=...)
│   └─ 输出: 课程大纲、高频考点、易错点
│   └─ 写入 L2/exam.md → section "课程资源"
│
├─ Step 3: 诊断评估
│   └─ 直接调用 QuestionPipeline（非 DeepQuestionCapability.run()）
│   └─ 生成覆盖主要知识点的诊断题
│   └─ 用户作答（收集隐式反馈）
│   └─ 输出: 各知识点的初始 mastery 分数
│
├─ Step 4: 建立能力画像
│   └─ 基于诊断结果 → ability_profile
│   └─ 写入 L2/exam.md → section "能力画像"
│
├─ Step 5: 建立初始薄弱点
│   └─ WeakPointRankerTool(ability_profile, stage, days)
│   └─ 写入 L2/exam.md → section "薄弱点"
│
└─ Step 6: 进入标准 assess→plan→advise 循环
    └─ 冷启动完成后，run() 继续执行 assess/plan/advise stages
```

**已确定**：

- 每个知识点 3 题诊断密度
- 用户中途离开时，用已答题部分建立不完整 ability_profile
- 诊断题来源：QuestionPipeline 内置 RAG + LLM 推理生成（基于课程材料的原创题）
- 诊断结果分析（题目→知识点映射 + mastery 计算）作为 Capability 内部 LLM 调用，不作为独立 Tool

**Step 3 详细流程**：

```
3a. 从 L2/exam.md 课程资源中提取知识点列表
3b. QuestionPipeline 生成诊断题
    └─ topic = exam_name
    └─ num_questions = len(knowledge_points) * 3
    └─ question_types = []（自动选择）
    └─ 诊断题通过 stream 直接呈现给用户作答
3c. 用户作答（QuizViewer 前端交互，结果自动存入 notebook_entries 表）
3d. load_session_quiz_history(session_id) → 已答题列表
3e. Capability 内部 LLM 调用：
    └─ 输入：课程大纲 + quiz 结果（题目+对错）
    └─ LLM 推理：题目→知识点映射 + mastery 计算
    └─ 输出：ability_profile = {"知识点A": 0.6, "知识点B": 0.8, ...}
    └─ 写入 L2/exam.md → section "能力画像"
```

---

## #9 日常执行流程

**状态**：✅ 已确定
**日期**：2026-07-05

### 决策

**循环触发机制**（#7 预确认）：

- 每次 run() 是一个完整的 assess→plan→advise
- 循环由外部事件触发新的 run() 调用
- 执行阶段是独立的交互轮次（用户点击"开始" = 新请求）

**任务执行交互**：

用户看到今日计划（任务骨架）→ 点击 [开始] → 按任务类型生成内容：

| 任务类型 | 调用方式 | 输出处理 |
|---------|---------|---------|
| `learn` | RAGTool(query=知识点名称, kb=课程KB) | 直接展示 RAGTool 的 answer（已包含 LLM 整理） |
| `practice` | QuestionPipeline(topic=知识点名称, num_questions=N) | QuizViewer 前端交互 |
| `review` | 读取 L2/exam.md 中的错题记录 | 错题列表 + 解析 |
| `scoreProtect` | 混合以上 | 保分任务 |

**执行后状态更新**（纯规则）：

```
任务完成 → 收集结果（隐式） → 更新 L2/exam.md：
  1. 更新 ability_profile：对了 +0.05，错了 -0.03
  2. 更新执行日志（今日完成统计）
```

**重排触发条件**（OR 关系，满足任一即触发新 run()）：

| 条件 | 说明 |
|------|------|
| 任何知识点 mastery 变化 ≥ 0.1 | 单次任务导致显著变化 |
| 用户完成 ≥ 2 个任务 | 累积效应 |
| 阶段切换（TimePressureTool 输出变化） | 时间驱动 |

**mastery 粒度**：单个知识点级别。单次 5 道题 practice：
- 全对：+0.25
- 全错：-0.15
- 3对2错：+0.09（不触发重排）

---

## #10 反馈与重排机制

**状态**：✅ 已确定
**日期**：2026-07-05

### 决策

**反馈来源**：上游行为收集程序（隐式收集），非用户主动反馈

**mastery 更新规则**（纯规则）：
- 答对一题：该知识点 mastery += 0.05
- 答错一题：该知识点 mastery -= 0.03
- 未答：不更新

**重排触发条件**（OR 关系）：
- 任何知识点 mastery 变化 ≥ 0.1
- 用户完成 ≥ 2 个任务
- 阶段切换（TimePressureTool 输出变化）

**重排机制**：新的 run() 调用（assess→plan→advise），非单次 run() 内部循环

**Mastery 变化感知机制**（已确认）：
- mastery 数据存储在 L2 exam surface，由 Capability 直接写入（`MemoryStore.overwrite_doc()`）
- 变化检测不需要历史快照：Capability 在 run() 开头读 L2 → 拿到旧 mastery → 任务完成后计算新 mastery → 内存中比对 delta
- 跨 run() 场景：新 run() 读 L2 自然拿到上次写入的值，与新计算值比对即可
- 结论：mastery 变化感知是 Capability 内部逻辑，不需要独立 Tool 或额外存储

**FeedbackParserTool 已取消**，逻辑合并入 Capability 层（见 #6）

---

## #11 前端路由与入口

**状态**：✅ 已确定

**决策**：采用方案 B — Exam Sprint 作为侧边栏独立模块，与 Book/Knowledge 平级。

**理由**：
- Exam Sprint 有持久状态（多场考试、掌握度追踪、每日任务），在 Chat 消息流中难以有效展示
- 独立模块提供"一览全局"的仪表盘体验，与 Book/Knowledge 模式一致
- 多考试管理更自然（左侧列表切换），不需要每次重新配置 capability

**前端结构**：
```
侧边栏新增导航项：Exam Sprint（/exam-sprint）
页面布局（三栏）：
├── 左栏（320px）：考试列表 + 新建考试
├── 中栏（flex）：仪表盘（时间压力横幅 + 统计卡片 + 掌握度表格 + 任务列表 + 嵌入式问答）
└── 页签：仪表盘 | 任务列表 | 知识点图谱 | 历史记录 | 设置
```

**视觉参考**：`migrate_documents/mockup-b-sidebar-module.html` 作为初始模板/参考效果。

**嵌入式问答**：页面底部内嵌轻量 Chat 面板，用于针对当前考试的快速提问（复用 Chat 能力，但上下文限定为当前考试的 L2 exam surface）。

---

## #12 状态可视化

**状态**：✅ 已确定

**掌握度历史折线图**：
- 后端无现成 mastery history 查询接口，L2 exam surface 仅存当前状态
- 方案：在 L2 exam surface 中维护 `## Mastery History` section，记录每次变化的 timestamp/kp/old/new/trigger
- 前端：行末 `▼` 折叠按钮 → 展开后渲染轻量 SVG 折线图（最近 5 次）
- 不需要额外 API 调用：L2 整体在 run() 时已读入内存，前端通过现有 memory read 接口获取

**任务包与学习面板**：
- 任务包结构（PlanBuilderTool 输出）：task_id / knowledge_point / action(learn|practice|review) / resource_type(rag|original_question) / estimated_minutes / mastery_before
- "学习"按钮触发行为：
  - `action=learn` → RAGTool 检索学习材料 → 独立面板渲染 Markdown
  - `action=practice` → QuestionPipeline 生成练习题 → 独立面板复用 QuizViewer 组件
- 面板形式：Drawer/SlideOver 组件（类似 Book 侧边栏展开模式），lazy-loaded，数据通过 WebSocket 流式推送
- 状态管理：面板组件内部管理，与仪表盘共享 L2 exam surface 数据（React Context）
- RAG 输出格式化：V0 直接在面板中渲染 Markdown（LLM 自由文本），不做二次结构化格式化。后续迭代根据用户反馈决定是否需要结构化卡片

**任务完成反馈机制**：
- 不依赖用户主动反馈，采用行为驱动信号
- V0 信号源：作答正确率（QuizViewer 的 is_correct）+ 题目完成数（completedCount）
- V1 增强：作答耗时（前端计时器 submit_time - start_time）
- 触发链路：用户在独立面板完成作答 → QuizViewer 的 upsertNotebookEntry 持久化 → 同时触发 Capability 层 mastery 更新（纯规则） → 检测 delta ≥ 0.1 → 触发重排
- QuizViewer 的 recordQuizResults 已在所有题目完成后自动调用后端，Exam Sprint 只需在此回调中增加 mastery 更新逻辑

---

## #13 优雅降级策略

**状态**：✅ 已确定

**降级矩阵**：

| 组件 | 不可用场景 | 降级方案 |
|------|-----------|---------|
| TimePressureTool | 纯规则，永不失败 | 无需降级 |
| WeakPointRankerTool | 纯规则，永不失败 | 无需降级 |
| PlanBuilderTool | 纯规则，永不失败 | 无需降级 |
| RAGTool | KB 未索引 / 网络异常 | Capability 层 catch → fallback 到推理 LLM 直接生成学习材料 |
| QuestionPipeline | LLM 超时 / 限流 | Capability 层 catch → 返回"题目生成失败，请重试"，保留任务进度 |
| L2 exam surface 读写 | 文件系统异常 | 返回错误提示，不更新 mastery |

**RAG fallback 实现**（已确认）：
- 不修改 RAGService 本身，在 ExamSprintCapability 内部 try/catch
- RAG 失败时调用 `llm.complete()` 生成学习材料（注入知识点名称 + system prompt）
- 零风险：RAGService / rag_tool 完全不动，fallback 逻辑封装在新写的 Capability 内部

**阶段自动切换 — 惰性钩子**（已确认）：
- 不做实时推送通知（用户可能几天不登录，定时推送无意义）
- 实现为惰性计算：用户每次访问 Exam Sprint 页面或点击"开始"时，自动调用 TimePressureTool 计算当前阶段
- 如果 `current_phase != stored_phase`，自动写入 L2 并触发 replan
- 零成本：TimePressureTool 已是纯规则函数，阶段比较是简单字符串比较

**总体原则**：跳过失败 + 保留进度。单个任务失败不影响整个冲刺计划，用户可手动重试。不新增自动重试或回滚机制。

---

## #14 V0 边界

**状态**：✅ 已确定

**V0 做什么**：

| 模块 | 内容 |
|------|------|
| 后端注册 | BUILTIN_CAPABILITY_CLASSES 新增 `exam_sprint` → `ExamSprintCapability` |
| Surface | L2 新增 `exam` surface + L3 新增 `exam_profile` slot |
| 3 个纯规则 Tool | TimePressureTool / WeakPointRankerTool / PlanBuilderTool |
| ExamSprintCapability | 4 stages: cold_start → assess → plan → advise |
| 冷启动 | 考试信息收集 + RAG 检索 + 诊断评估（复用 QuestionPipeline） |
| 日常执行 | assess→plan→advise 单次 run()，行为驱动 mastery 更新 |
| 前端页面 | 侧边栏独立模块 `/exam-sprint`，三栏布局（考试列表 + 仪表盘 + 嵌入式问答） |
| 掌握度表格 | 当前值展示（无历史折线图） |
| 任务展示 | PlanBuilderTool 输出的任务列表 + 独立面板（learn/practice） |
| 进度显示 | 复用 StreamBus + StreamPanel，不新增基础设施 |
| RAG fallback | Capability 层 catch → LLM 兜底（不修改 RAGService） |
| 阶段钩子 | 惰性计算，用户访问时自动检测阶段切换 |

**V0 不做什么**（明确排除）：

| 排除项 | 原因 |
|--------|------|
| 修改 RAGService 增加 fallback | 影响 12 个 caller，风险高 |
| 修改 QuestionPipeline 增加 exam 逻辑 | 影响 deep_question 能力 |
| 修改 StreamBus 新增事件类型 | 影响所有消费者 |
| 自动定时推送 | 惰性钩子已覆盖，无需后台任务 |
| 任务完成计时器 | V1 增强，V0 仅用作答正确率 + 完成数 |
| 掌握度历史折线图 | V1 增强，V0 仅展示当前值 |
| 错题本导出 | V1 功能 |
| 跨考试知识点关联 | V1 功能 |
| 独立 Chat session | 嵌入式问答面板已足够 |

**风险控制原则**：新代码包裹旧接口，不碰旧代码。所有 Exam Sprint 逻辑封装在新增文件中，不修改任何现有模块。
