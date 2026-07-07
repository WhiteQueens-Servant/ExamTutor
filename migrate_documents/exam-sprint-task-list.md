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

### Phase 2: 后端 Capability 注册

- [ ] **2.1 注册空 Capability**
  - 创建 `deeptutor/capabilities/exam_sprint.py`（manifest only，run() 直接返回）
  - 注册到 `builtin_capabilities.py` 的 `BUILTIN_CAPABILITY_CLASSES`

- [ ] **2.2 ExamStream 包装**
  - 复用 BookStream 模式，创建 `deeptutor/exam/streaming.py`

- [ ] ⬆ **[点停] 验证**：pytest 通过，前端 Console 无报错，Capability 列表中出现 exam_sprint

#### 变更记录
（执行中遇到的问题和修改记录在此）

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

- [ ] **4.1 纯规则工具**
  - TimePressureTool / WeakPointRankerTool / PlanBuilderTool
  - 零 token 消耗，pytest 验证

- [ ] **4.2 QuestionPipeline 打通**
  - 前端 QuizViewer 接真实后端数据（替换 mock）
  - 记忆回写（capability_results + mastery 更新）

- [ ] **4.3 RAG + LLM 降级**
  - RAGTool 学习模式 + try/catch 降级到 llm.complete()

- [ ] **4.4 掌握度读写**
  - Capability 内读 L2（old mastery）→ 计算 → 对比 → 写回
  - 前端替换 mock 数据为真实 mastery

- [ ] ⬆ **[点停] 浏览器验证**：端到端流程跑通（冷启动 → 任务执行 → 分数更新）

#### 变更记录
（执行中遇到的问题和修改记录在此）

### Phase 5: 收尾

- [ ] **5.1 冷启动流程**
  - 首次使用引导（选科目 → 设考试日期 → RAG 入库 → 初始化 mastery）

- [ ] **5.2 阶段自动切换（lazy hook）**
  - 用户访问时计算当前阶段 vs 存储阶段，差异则触发 replan

- [ ] **5.3 连续天数追踪**
  - `## Sprint` 字段记录 streak + last_active

- [ ] ⬆ **[点停] 最终验证**：完整用户旅程浏览器跑一遍

#### 变更记录
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
3. **QuizViewer 复用**：不重写，通过 Drawer 嵌入
4. **记忆系统**：复用 L1/L2/L3，exam 作为新 surface type
5. **StreamBus 复用**：ExamStream 包装，不改 StreamBus 本身
6. **Git 推送方式**：始终使用 `git -c http.proxy="" -c https.proxy="" push`（绕过本地代理）
