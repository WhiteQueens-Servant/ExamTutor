# Exam Sprint 增量开发任务列表

## 开发模式

**增量点停式开发验证**——每完成一个任务，浏览器调试 + 用户确认后才能推进下一步。

详细规则见 `CLAUDE.md`「增量点停开发模式」章节。

## 任务列表

### Phase 0: 持久化约束 ✅

- [x] 写入 CLAUDE.md：点停模式规则 + Playwright 强制调用
- [x] 写入 memory：point-stop-dev-mode.md

### Phase 1: 前端骨架

- [x] **1.1 Sidebar 入口**
  - `PRIMARY_NAV` 添加 Exam Sprint（图标 + 路由 `/exam-sprint`）
  - 文件：`web/components/sidebar/SidebarShell.tsx`

- [x] **1.2 页面路由 + 空壳**
  - 创建 `web/app/(workspace)/exam-sprint/page.tsx`
  - 基础布局：标题 + 占位区域

- [x] ⬆ **[点停] 浏览器验证**：Sidebar 显示 Exam Sprint 入口，点击跳转正确，空壳页面渲染正常

#### 变更记录
- 修改文件：`web/components/sidebar/SidebarShell.tsx`（添加 Target 图标 import + PRIMARY_NAV 新增条目）
- 新建文件：`web/app/(workspace)/exam-sprint/page.tsx`（空壳页面）
- 修改文件：`web/locales/en/app.json` + `web/locales/zh/app.json`（添加 Exam Sprint i18n 条目）
- 问题：无（Console 报错为预存的 session API 未连接问题，与本次改动无关）

### Phase 2: 后端 Capability 注册 ✅

- [x] **2.1 注册空 Capability**
  - 创建 `deeptutor/capabilities/exam_sprint.py`（manifest only，run() 直接返回）
  - 注册到 `builtin_capabilities.py` 的 `BUILTIN_CAPABILITY_CLASSES`

- [x] **2.2 ExamStream 包装**
  - 复用 BookStream 模式，创建 `deeptutor/exam/streaming.py`

- [x] ⬆ **[点停] 验证**：pytest 通过，前端 Console 无报错，Capability 列表中出现 exam_sprint

#### 变更记录
- 新建 `deeptutor/capabilities/exam_sprint.py`（ExamSprintCapability，manifest + 空 run()）
- 新建 `deeptutor/exam/__init__.py`（空包）
- 新建 `deeptutor/exam/streaming.py`（ExamStream，SOURCE="exam_sprint"，阶段常量 + emit 方法）
- 修改 `deeptutor/runtime/bootstrap/builtin_capabilities.py`（BUILTIN_CAPABILITY_CLASSES 添加 "exam_sprint" 入口）

### Phase 3: 前端 Dashboard 逐步填充

- [x] **3.1 掌握度表格 + 进度条**
  - ExamMasteryTable 组件（静态 mock 数据先）
  - 进度条复用 BookProgressRing 样式

- [x] **3.2 统计卡片行**
  - 今日任务 / 预估提分 / 连续天数 / 剩余天数

- [x] **3.3 时间压力横幅**
  - TopWeakBanner 组件（红色置顶）

- [x] **3.4 任务列表**
  - SprintTaskList 组件，任务卡片含「学习」「练题」按钮

- [x] **3.5 嵌入 QuizViewer**
  - Drawer/SlideOver 中复用现有 QuizViewer 组件

- [x] ⬆ **[点停] 浏览器验证**：每一步截图确认 UI 渲染正确

#### 变更记录
- 新建 `web/components/exam-sprint/types.ts`（类型定义 + mock 数据）
- 新建 `web/components/exam-sprint/ExamMasteryTable.tsx`（掌握度表格 + 彩色进度条）
- 新建 `web/components/exam-sprint/StatCards.tsx`（4 张统计卡片）
- 新建 `web/components/exam-sprint/TopWeakBanner.tsx`（时间压力红色横幅）
- 新建 `web/components/exam-sprint/SprintTaskList.tsx`（任务列表 + Learn/Practice 按钮）
- 新建 `web/components/exam-sprint/QuizPreview.tsx`（轻量答题组件，无后端依赖）
- 新建 `web/components/exam-sprint/QuizDrawer.tsx`（右侧抽屉容器）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（组装完整 Dashboard）
- 修改 `web/locales/en/app.json` + `web/locales/zh/app.json`（新增 i18n 条目）
- 问题：QuizViewer 有大量后端 API 依赖（notebook/session），无后端时崩溃。解决方案：创建轻量 QuizPreview 替代，V0 阶段不依赖后端

### Phase 4: 后端真实逻辑接入

- [x] **4.1 纯规则工具**
  - TimePressureTool / WeakPointRankerTool / PlanBuilderTool
  - 零 token 消耗，pytest 验证

- [x] **4.2 QuestionPipeline 打通**
  - 后端 REST 端点 `POST /api/v1/exam-sprint/generate-questions` 调用 QuestionPipeline 生成真实题目
  - 前端 QuizDrawer 接入真实 API，显示 loading/error 状态
  - Practice 按钮触发真实题目生成，QuizPreview 渲染 + 答题交互正常

- [x] **4.3 RAG + LLM 降级 + 知识库选择器**
  - 后端：ExamSprintCapability 接收 `kb_name` 参数，调用 `rag_service.search(query, kb_name)` 做精确范围检索
  - 后端：RAG 不可用时降级到 `llm.complete()` 直接生成
  - 前端：Dashboard 顶部增加知识库选择器（从已有 KB 列表选择，复用 `useKnowledgeBases` hook）
  - 注意：Phase 4 仅做选择器，上传功能放在 Phase 5

- [x] **4.4 掌握度读写**
  - Capability 内读 L2（old mastery）→ 计算 → 对比 → 写回
  - 前端替换 mock 数据为真实 mastery

- [ ] ⬆ **[点停] 浏览器验证**：端到端流程跑通（冷启动 → 任务执行 → 分数更新）

#### 变更记录

##### Phase 4.1
- 新建 `deeptutor/exam/tools.py`（3 个纯规则工具：TimePressureTool / WeakPointRankerTool / PlanBuilderTool）
- 新建 `tests/exam/__init__.py`
- 新建 `tests/exam/test_tools.py`（12 个测试用例，全部通过）
- 问题：IEEE 754 浮点精度 — `0.9 - 0.8 = 0.09999...` 导致 gap=0.1 的优先级判定为 "low"。修复：在 `_rank_weak_points` 中先 `round(gap, 3)` 再传入 `_priority_from_gap`

##### Phase 4.2
- 新建 `deeptutor/api/routers/exam_sprint.py`（REST 端点 `POST /api/v1/exam-sprint/generate-questions`）
- 修改 `deeptutor/api/main.py`（注册 exam_sprint router）
- 新建 `web/lib/exam-sprint-api.ts`（前端 API 客户端 `generateExamQuestions`）
- 修改 `web/components/exam-sprint/QuizDrawer.tsx`（添加 loading/error 状态）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（Practice 按钮接入真实 API）
- 验证：浏览器端到端流程跑通 — 点击 Practice → loading → 真实 LLM 题目生成 → 答题 → 正确性判定 → 解析显示
- 注意：QuestionPipeline 三阶段（explore→plan→quiz）耗时约 60-120 秒，取决于 LLM 响应速度

##### Phase 4.3
- 修改 `deeptutor/api/routers/exam_sprint.py`（新增 `kb_name` 字段，RAG 检索 + LLM 降级逻辑）
- 修改 `web/lib/exam-sprint-api.ts`（`GenerateQuestionsParams` 新增 `kb_name`）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（引入 `useKnowledgeBases` hook，header 添加 KB 选择器）
- 修改 `web/locales/en/app.json` + `web/locales/zh/app.json`（新增 "No knowledge base (LLM only)" i18n key）
- 验证：TypeScript 编译通过，浏览器渲染正常，KB 选择器显示在 header 右侧
- 注意：RAG 检索失败时自动降级为纯 LLM 生成，不影响原有流程

##### Phase 4.4
- 新建 `deeptutor/exam/mastery.py`（掌握度存储模块：load_mastery / save_mastery / update_mastery_score，指数移动平均混合）
- 修改 `deeptutor/api/routers/exam_sprint.py`（新增 GET /mastery + POST /mastery/update 端点）
- 新建 `web/lib/exam-sprint-mastery-api.ts`（前端掌握度 API 客户端）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（引入 fetchMastery，替换 MOCK_MASTERY 为真实数据）
- 验证：浏览器端到端流程跑通 — 页面加载时自动拉取掌握度，TopWeakBanner 正确显示最弱知识点，MasteryOverview 显示全部知识点进度
- 注意：掌握度存储在 `data/exam_sprint/mastery.json`，不依赖 L2 记忆系统（L2 是 markdown 文档，不适合结构化分数）

### Phase 4.5: Learn 链路

- [x] **4.5 Learn 学习材料生成**
  - 后端：`POST /api/v1/exam-sprint/learn` 端点
  - Prompt 工程：注入 Stage 约束 + 记忆对象（mastery/ability_profile）+ RAG 结果 → LLM 生成学习材料
  - RAG 检索（有 KB 时）→ LLM 整理 → Markdown 输出；RAG 失败/无 KB → fallback 到 LLM 直接生成
  - 前端：`LearnDrawer.tsx` 组件（MarkdownRenderer 渲染学习材料）
  - 前端：Learn 按钮绑定事件，打开 Drawer 展示学习内容
  - 与 Practice 对称：Learn 生成"学什么"，Practice 生成"练什么"

- [x] ⬆ **[点停] 浏览器验证**：Learn 按钮点击 → Drawer 打开 → 学习材料正确渲染

##### Phase 4.5
- 修改 `deeptutor/api/routers/exam_sprint.py`（新增 POST /learn 端点：mastery 读取 + RAG 检索 + Prompt 工程 + LLM 生成）
- 修改 `web/lib/exam-sprint-api.ts`（新增 generateLearnContent API）
- 新建 `web/components/exam-sprint/LearnDrawer.tsx`（Markdown 阅读面板组件）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（Learn 按钮绑定事件，LearnDrawer 集成）
- 修改 `web/locales/en/app.json` + `web/locales/zh/app.json`（新增 Learn 相关 i18n key）
- 验证：浏览器端到端流程跑通 — 点击 Learn → Drawer 打开 → loading → LLM 生成学习材料 → Markdown + LaTeX 正确渲染
- 注意：LLM 生成耗时约 60-120 秒，内容包含概念解释、核心公式、典型例题、要点总结

### Phase 5: 业务闭环（V0 核心链路）

> V0 目标：完整业务闭环——冷启动全链路（考试信息 → 资料上传 → 诊断测评 → 初始掌握度 → 每日循环）跑通。
> 数据架构设计见 `migrate_documents/exam-sprint-data-architecture.md`。
> V1 目标：底层性能调优（RAG 检索策略、Reranking、文档切分参数、LLM 推理速度、Prompt Engineering）。

#### 当前进度（2026-07-08）
- Phase 5.1 ✅ 数据层重构（profile.json 统一数据源）
- Phase 5.2 ✅ 冷启动向导（SetupModal 多步骤，SSE 流式诊断）
- Phase 5.3.1 ✅ 学习材料持久化（用户按需保存 + 学习历史入口）
- Phase 5.3.2 ✅ 练习错题持久化（practice_history.json + 错题本入口）
- Phase 5.3.3 ❌ 诊断报告持久化
- Phase 5.4 ❌ Dashboard 增强（诊断报告入口 / 重置按钮）
- Phase 5.5 ❌ 最终验证（完整用户旅程浏览器跑一遍）

#### 5.1 数据层重构（profile.json 统一数据源）

> 将 mastery.json 合并进 profile.json，建立统一的用户画像数据结构。

- [ ] **5.1.1 重构 profile 模块**
  - 新建 `deeptutor/exam/profile.py`（替代 mastery.py）
  - 数据结构：`profile.json`（knowledge_points 数组 + diagnosis 对象）
  - API：`load_profile()` / `save_profile()` / `update_score()` / `init_from_diagnosis()`
  - 首次诊断初始化时直接写入原始正确率（非 EMA），后续练习用 EMA 更新

- [ ] **5.1.2 API 适配**
  - `GET /mastery` → 从 profile.json 读 knowledge_points
  - `POST /mastery/update` → 更新 profile.json
  - 新增 `GET /profile` → 返回完整画像
  - 去掉 mastery.json 依赖

- [ ] **5.1.3 state.py 扩展**
  - 新增字段：`onboarding_completed`、`diagnosis_completed`、`kb_name`
  - 新增 `is_cold_start()` 逻辑：检查 exam_name/exam_date 为空
  - 新增 `reset_state()` → 清空全部数据（state + profile + history）

- [ ] ⬆ **[点停] pytest 验证**：profile 读写 + state 扩展 + mastery API 兼容

#### 5.2 冷启动向导（SetupModal 多步骤）

> 将当前单步 SetupModal 改为四步向导。

**Step 1: 考试信息（已完成 ✅）**
- [x] 考试名称、考试日期、每日可用时间
- [x] 写入 state.json

**Step 2: 创建知识库（已完成 ✅）**
- [x] KB 名称输入（默认用考试名称填充）
- [x] 上传课程资料文档（可选，可为空）
  - 复用 `createKnowledgeBase` + `uploadKnowledgeBaseFiles` API
  - 上传完成后自动索引 + 写入 state.json.kb_name
- [x] 跳过提示："跳过后学习材料将基于通用知识生成，建议上传课程资料以获得更精准的内容"

**Step 3: 诊断测评（已完成 ✅）**
- [x] 后端：`POST /diagnosis/generate` 端点
  - 有 KB → RAG 检索 → LLM 出题；无 KB → LLM 直接出题
  - 题数由 LLM 根据 KB 内容/考试范围动态决定（不硬编码）
- [x] 后端：`POST /diagnosis/stream` 端点（SSE 流式生成，解决超时问题）
- [x] 前端：SSE 流式解析 + 增量渲染诊断题目
- [x] 后端：`POST /diagnosis/submit` 端点
  - 接收作答结果 → 按知识点汇总 → 初始化 profile.json
  - 首次写入直接用原始正确率，不走 EMA

**Step 4: 完成（已完成 ✅）**
- [x] 展示诊断结果概览（分数 + 薄弱点）
- [x] 写入 state.json.onboarding_completed = true

- [x] ⬆ **[点停] 浏览器验证**：完整冷启动流程跑通（SSE 流式诊断 + 增量渲染）

#### 5.3 内容持久化

> 解决"生成内容无落点"问题。

**5.3.1 学习材料持久化**
- [x] 后端：`POST /learn/save` 手动保存端点
  - 生成的 Markdown 保存到 `data/exam_sprint/learn_history/YYYY-MM-DD_HH-MM_<知识点>.md`
- [x] 后端：`GET /learn/history` → 列出已保存的学习材料
- [x] 前端：LearnDrawer 增加"保存"按钮 + "已保存"提示

**5.3.2 练习错题持久化**
- [x] 后端：`POST /diagnosis/submit` 时，错题写入 `practice_history.json`
- [x] 后端：`GET /practice/history` → 读取错题历史
- [x] 前端：Dashboard 增加"错题本"入口（查看历史错题）

**5.3.3 诊断报告持久化**
- [ ] 诊断结果保存到 profile.json 的 diagnosis 对象
- [ ] 前端：Dashboard 增加"诊断报告"入口（查看完整诊断：每题解析+错因）

- [ ] ⬆ **[点停] 浏览器验证**：Learn/Practice 后内容可回看，诊断报告可查看

#### 5.4 Dashboard 增强

> 将真实数据接入 Dashboard 组件。

- [ ] **掌握度表格**：数据来自 profile.json（已有，适配新数据源）
- [ ] **TopWeakBanner**：数据来自 profile.json.weak_points（已有）
- [ ] **新增：诊断报告入口** → 展示 diagnosis 对象内容
- [x] **新增：错题本入口** → 展示 practice_history.json 内容
- [x] **新增：学习历史入口** → 列出 learn_history/ 文件
- [ ] **新增：重置按钮**（含确认弹窗）→ 调用 POST /state/reset

- [ ] ⬆ **[点停] 浏览器验证**：Dashboard 各入口功能正常

#### 5.5 最终验证

- [ ] 完整用户旅程浏览器跑一遍：冷启动 → 上传资料 → 诊断 → Dashboard → Learn → Practice → 错题回看 → 重置

#### 变更记录

##### Phase 5.1（已完成——考试信息收集）
- 新建 `deeptutor/exam/state.py`（考试状态存储模块：load_state / save_state / is_cold_start / update_state）
- 修改 `deeptutor/api/routers/exam_sprint.py`（新增 GET /state + POST /state 端点）
- 修改 `web/lib/exam-sprint-api.ts`（新增 fetchExamState / saveExamState API）
- 新建 `web/components/exam-sprint/SetupModal.tsx`（冷启动引导表单组件）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（集成 SetupModal，替换 MOCK_META 为真实 exam state，自动计算 phase/days_remaining）
- 修改 `web/locales/en/app.json` + `web/locales/zh/app.json`（新增 Setup 相关 i18n key）
- 验证：浏览器端到端流程跑通 — 首次访问弹出 SetupModal → 填写考试信息 → 提交 → Dashboard 显示真实考试名称和剩余天数

##### Phase 5 架构重构
- 新建 `migrate_documents/exam-sprint-data-architecture.md`（数据架构设计文档）
- 任务列表重构：Phase 5 拆分为 5.1-5.5，覆盖数据层/冷启动/持久化/Dashboard/验证
- mastery.json 合并进 profile.json（统一用户画像数据源）
- 新增内容持久化：learn_history/ + practice_history.json + diagnosis 存储
- 新增用户状态机：onboarding_completed / diagnosis_completed / reset

##### Phase 5.1 数据层重构
- 新建 `deeptutor/exam/profile.py`（替代 mastery.py，统一用户画像+掌握度数据源）
  - `load_profile()` / `save_profile()` — 完整 profile 读写
  - `load_mastery()` — 兼容层，从 profile.json 读取 legacy 格式
  - `update_mastery_score()` — EMA 更新（已有知识点）/ 直接写入（新知识点）
  - `init_from_diagnosis()` — 诊断结果初始化 profile
  - `reset_profile()` — 清空 profile 文件
- 修改 `deeptutor/exam/state.py` — 新增 `onboarding_completed`、`diagnosis_completed`、`kb_name` 字段 + `reset_state()` 函数
- 修改 `deeptutor/api/routers/exam_sprint.py` — mastery 端点改用 profile.py；新增 `GET /profile`、`POST /state/reset` 端点；`POST /state` 接收新字段
- 修改 `web/lib/exam-sprint-api.ts` — ExamState 新增字段；新增 KnowledgePoint/DiagnosisReport/UserProfile 类型；新增 fetchProfile/resetExamState API
- 新建 `tests/exam/test_profile.py`（10 个测试用例，全部通过）
- 验证：pytest 22/22 通过，TypeScript 编译通过
- 注意：mastery.py 保留但不再被 API 使用（向后兼容），后续可清理

##### Phase 5.2 冷启动向导多步骤（已完成）
- 修改 `deeptutor/api/routers/exam_sprint.py`（新增 POST /diagnosis/generate + POST /diagnosis/submit + POST /diagnosis/stream 端点）
- 重写 `web/components/exam-sprint/SetupModal.tsx`（四步向导：考试信息 → 创建KB → 诊断测评 → 完成）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（适配新 SetupModal onComplete 接口，诊断结果驱动 mastery）
- 修改 `web/lib/exam-sprint-api.ts`（新增 generateDiagnosis/submitDiagnosis/streamDiagnosis API + 类型定义）
- 修改 `web/components/exam-sprint/types.ts`（MasteryEntry.surface 新增 "diagnosis"）
- 修改 `web/components/exam-sprint/ExamMasteryTable.tsx`（SURFACE_LABELS 新增 "Diagnosis"）
- 修改 `web/locales/en/app.json` + `web/locales/zh/app.json`（新增向导步骤 i18n key）
- 验证：浏览器端到端流程跑通 — 四步向导正确切换，诊断数据正确流入 Dashboard
- 注意：诊断题目生成改为 SSE 流式方案（POST /diagnosis/stream），解决单次 LLM 调用生成多题 JSON 不可靠的超时问题
- 注意：SSE 解析逻辑修复 — currentEventType 变量需在 for 循环外部声明以保持跨行状态
- 注意：冷启动检测改为检查 `onboarding_completed` 字段

##### Phase 5.3.1 学习材料持久化（已完成）
- 新建 `deeptutor/exam/learn_history.py`（学习历史存储模块）
- 修改 `deeptutor/api/routers/exam_sprint.py`（POST /learn 不再自动保存；新增 POST /learn/save 手动保存端点；新增 GET /learn/history + GET/DELETE /learn/history/{filename}）
- 修改 `web/lib/exam-sprint-api.ts`（新增 saveLearnContent + fetchLearnHistory + fetchLearnContent + deleteLearnContent API）
- 修改 `web/components/exam-sprint/LearnDrawer.tsx`（新增保存按钮 + saved 状态显示）
- 新建 `web/components/exam-sprint/LearnHistoryDrawer.tsx`（学习历史查看组件：左侧列表 + 右侧内容预览）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（集成 LearnHistoryDrawer，Dashboard 添加"学习历史"入口按钮）
- 修改 `web/locales/en/app.json` + `web/locales/zh/app.json`（新增 Learn History 相关 i18n key）
- 验证：浏览器端到端流程跑通 — 生成学习材料 → 点击保存 → 显示已保存提示 → 学习历史入口查看内容
- 注意：改为用户按需保存（非自动生成即保存），提升用户体验

##### Phase 5.3.2 练习错题持久化（已完成）
- 新建 `deeptutor/exam/practice_history.py`（错题历史存储模块）
- 修改 `deeptutor/api/routers/exam_sprint.py`（POST /diagnosis/submit 保存错题；新增 GET/DELETE /practice/history + /practice/history/{id}）
- 修改 `web/lib/exam-sprint-api.ts`（新增 fetchPracticeHistory + fetchPracticeRecord + deletePracticeRecord API）
- 新建 `web/components/exam-sprint/PracticeHistoryDrawer.tsx`（错题本查看组件：左侧列表 + 右侧详情）
- 修改 `web/app/(workspace)/exam-sprint/page.tsx`（集成 PracticeHistoryDrawer，Dashboard 添加"错题本"入口按钮）
- 修改 `web/locales/en/app.json` + `web/locales/zh/app.json`（新增 Practice History 相关 i18n key）
- 验证：浏览器端到端流程跑通 — 诊断提交 → 错题自动保存 → 错题本入口查看 → 显示题目/答案对比/错误类型
- 注意：诊断提交返回 `wrong_saved` 字段显示保存的错题数量

（执行中遇到的问题和修改记录在此）

---

## 硬性原则（不可违反）

1. **前端报错优先排查接口一致性**
   - 前端出错时，先检查前端接收数据的接口/渲染方式是否符合后端返回格式
   - 确认接口一致后，优先在前端修改解决问题（不要轻易改后端）

2. **禁止主观推断，基于代码排查**
   - 遇到问题时，根据实际代码实现排查链路哪个环节出了问题
   - 可使用 CodeGraph、code-reviews 等 skills 排查项目结构/代码链路
   - 禁止并行分发 agent 探索（token 浪费且容易跑偏）

3. **问题记录在任务下方**
   - 每个任务执行中遇到的问题、修改变更，记录在该任务的 `### 变更记录` 子节
   - 下一个任务开始前，必须先阅读上一个任务的变更记录
   - 确保推进时能看到已出现的问题和修改内容

4. **每完成一个任务必须 git push 保存版本**
   - 确认任务无误后，执行 git commit + push 再推进下一个任务
   - 推到 git 上的版本必须是正确无误的版本，方便回滚
   - commit 格式：`feat(exam-sprint): <任务描述>`

## 关键注意事项

1. **前端优先**：先用 mock 数据做 UI，后端逐步替换真实逻辑
2. **不修改现有模块**：exam_sprint 是纯增量，所有现有代码不改动
3. **QuizViewer 复用**：不重写，通过 Drawer 嵌入。Phase 4.2 后切回 QuizViewer（替换 QuizPreview）
4. **记忆系统**：复用 L1/L2/L3，exam 作为新 surface type
5. **StreamBus 复用**：ExamStream 包装，不改 StreamBus 本身
6. **Git 推送方式**：始终使用 `git -c http.proxy="" -c https.proxy="" push`（绕过本地代理）
7. **知识库隔离**：RAG 查询通过 `kb_name` 参数限定范围，不跨 KB 检索。Exam Sprint 支持用户选择/创建专属知识库
8. **验证方式**：全部采用 web 模式（后端 `deeptutor serve` + 前端 `npm run dev` + Playwright + 手动实操），不使用 deeptutor CLI
9. **数据架构**：数据持久化方案见 `migrate_documents/exam-sprint-data-architecture.md`，实现前必须阅读
