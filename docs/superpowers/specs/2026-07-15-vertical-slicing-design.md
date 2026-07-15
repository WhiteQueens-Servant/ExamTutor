# DeepTutor 垂直切割设计方案

> 日期：2026-07-15
> 状态：待执行

---

## 1. 目标

将 DeepTutor 从"全功能 AI 学习伴侣"精简为"Exam Sprint + Deep Solve + Deep Research"三模块系统，实现：

- **项目聚焦**：面试时只讲 3 个核心模块，故事线清晰
- **体积缩减**：删除无用代码，降低维护成本
- **为改进做准备**：干净的代码库更容易做 Exam Sprint 改进

## 2. 保留模块

| 模块 | 面试定位 | 技术亮点 |
|------|---------|---------|
| **Exam Sprint** | 业务创新 | SSE 流式诊断、时间压力驱动、自适应学习 |
| **Deep Solve** | 基础 Agentic Loop | THINK→TOOL→FINISH→REPLAN 标签驱动循环 |
| **Deep Research** | 高级 Agentic Loop | 并行研究、动态话题队列、引用管理 |

## 3. 删除模块

| 模块 | 后端文件 | 前端文件 | 工作量 |
|------|---------|---------|--------|
| Math Animator | `capabilities/math_animator.py` | 无独立前端 | 小 |
| Visualize | `capabilities/visualize.py` | `components/visualize/` | 小 |
| Auto | `capabilities/auto.py` | 无 | 小 |
| Deep Question | `capabilities/deep_question.py` + `agents/question/` | `components/quiz/` | 中 |
| Book | `book/` 目录 + API routes | `lib/book-api.ts` + book 组件 | 大 |
| Chat | `capabilities/chat.py` + `agents/chat/` | page.tsx 大量逻辑 | 大 |

## 4. 保留的基础设施

- `BaseCapability` + `CapabilityRegistry` + 插件加载机制
- `ToolRegistry`（工具注册中心）
- `StreamBus`（事件流）
- `UnifiedContext`（上下文）
- `run_agentic_loop`（循环引擎）
- `PromptManager`（提示词管理）
- `LLM Client`（LLM 客户端）
- RAG Pipeline（知识检索）
- Memory 模块（记忆系统）

## 5. 执行顺序

```
第1步：切 Math Animator + Visualize + Auto（小模块，快速验证流程）
  ↓
第2步：切 Deep Question（中等模块）
  ↓
第3步：切 Book（大模块，有独立 API 和前端）
  ↓
第4步：切 Chat（最大模块，需要重写 page.tsx）
  ↓
第5步：更新 BUILTIN_CAPABILITY_CLASSES（只保留 3 条）
  ↓
第6步：验证 Exam Sprint + Deep Solve + Deep Research 正常工作
```

## 6. 每步详细操作

### 第1步：切 Math Animator + Visualize + Auto

**后端：**
- 删除 `deeptutor/capabilities/math_animator.py`
- 删除 `deeptutor/capabilities/visualize.py`
- 删除 `deeptutor/capabilities/auto.py`
- 从 `BUILTIN_CAPABILITY_CLASSES` 删除 3 条

**前端：**
- 删除 `web/components/visualize/` 目录
- 从 page.tsx 的 `CAPABILITIES` 数组删除对应条目
- 删除 page.tsx 中对应的 dynamic import（VisualizeConfigPanel）

### 第2步：切 Deep Question

**后端：**
- 删除 `deeptutor/capabilities/deep_question.py`
- 删除 `deeptutor/agents/question/` 目录
- 删除对应 prompts 目录

**前端：**
- 删除 `web/components/quiz/` 目录
- 从 page.tsx 中删除 Quiz 相关逻辑（QuizConfigPanel import、配置面板逻辑）

### 第3步：切 Book

**后端：**
- 删除 `deeptutor/book/` 目录
- 删除 book 相关 API 路由

**前端：**
- 删除 `web/lib/book-api.ts`、`web/lib/book-types.ts`
- 删除 `web/components/book/` 目录
- 从 page.tsx 中删除 Book 相关逻辑

### 第4步：切 Chat

**后端：**
- 删除 `deeptutor/capabilities/chat.py`
- 删除 `deeptutor/agents/chat/` 目录
- 删除对应 prompts 目录

**前端：**
- **重写 page.tsx**：移除 Chat 相关逻辑，保留 Exam Sprint + Deep Solve + Deep Research 的入口
- 删除 Chat 相关的 dynamic import

### 第5步：更新注册表

`deeptutor/runtime/bootstrap/builtin_capabilities.py` 只保留 3 条：

```python
BUILTIN_CAPABILITY_CLASSES: dict[str, str] = {
    "deep_solve": "deeptutor.capabilities.deep_solve:DeepSolveCapability",
    "deep_research": "deeptutor.capabilities.deep_research:DeepResearchCapability",
    "exam_sprint": "deeptutor.capabilities.exam_sprint:ExamSprintCapability",
}
```

### 第6步：验证

- 启动后端 `deeptutor serve --port 8001`，确认 3 个 Capability 正常注册
- 启动前端 `cd web && npm run dev`，确认页面正常加载
- 测试 Exam Sprint / Deep Solve / Deep Research 功能正常

## 7. 注意事项

1. **page.tsx 是最大耦合点**：所有模块的逻辑都在这个文件里，切割时需要仔细处理
2. **ToolRegistry 不要误删**：Chat、Deep Question、Deep Research 共享工具注册中心
3. **StreamBus 不要破坏**：所有模块共用事件流
4. **PromptManager 的 prompt 文件**：每个模块的 prompt 在 `deeptutor/**/prompts/` 下，切割时要删除对应目录
5. **Memory 模块保留**：Exam Sprint 可能用到记忆系统
6. **每步完成后验证**：不要一次性删除所有模块，逐步删除逐步验证

## 8. 面试话术（切割后）

"DeepTutor 是一个 Agent-Native 的 AI 学习伴侣系统。我在这个底座上做了三个核心模块：

1. **Exam Sprint**：考试冲刺模块，通过 SSE 流式诊断识别薄弱点，基于时间压力驱动生成个性化学习任务，根据掌握度自适应调整学习材料深度。

2. **Deep Solve**：多步推理模块，展示完整的 Agentic Loop 架构——标签驱动循环（THINK→TOOL→FINISH→REPLAN）、并行工具调用、协议违规自动修复。

3. **Deep Research**：深度研究模块，展示 Agentic Loop 的高级用法——多阶段 Pipeline（改写→分解→研究→报告）、并行研究块、动态话题队列、引用管理系统。"
