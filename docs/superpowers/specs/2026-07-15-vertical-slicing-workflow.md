# DeepTutor 垂直切割工作流

> 本文件是切割执行的工作流约束文件。每次执行切割操作前，必须先读取本文件。

---

## 核心原则：一步一停三验证

### 执行规则

1. **逐级切割**：每次只切割一个模块，按粒度从小到大排序
2. **三次强制验证**：每步切割完成后，必须做三次验证：
   - **验证1 — 后端启动**：`deeptutor serve --port 8001`，确认无报错
   - **验证2 — 前端启动**：`cd web && npm run dev`，Playwright 打开浏览器确认页面正常
   - **验证3 — 用户手工确认**：向用户报告验证结果，等待用户确认后再继续
3. **停止信号**：每次验证后输出 `[点停] 切割步骤 N 完成，等待验证`
4. **回滚机制**：验证失败时 `git checkout .` 回滚，分析原因后重新切割

### 切割顺序（从小到大）

| 步骤 | 模块 | 后端操作 | 前端操作 | 影响度 |
|------|------|---------|---------|--------|
| 第1步 | Math Animator | 删除 `capabilities/math_animator.py` | 无 | 最小 |
| 第2步 | Visualize | 删除 `capabilities/visualize.py` | 删除 `components/visualize/` | 小 |
| 第3步 | Auto | 删除 `capabilities/auto.py` + `agents/auto/` | 无 | 小 |
| 第4步 | Deep Question | 删除 `capabilities/deep_question.py` + `agents/question/` | 删除 `components/quiz/` + page.tsx 逻辑 | 中 |
| 第5步 | Book | 删除 `book/` 目录 + API routes | 删除 `book-api.ts` + book 组件 | 大 |
| 第6步 | Chat | 删除 `capabilities/chat.py` + `agents/chat/` | 重写 page.tsx | 最大 |

### 每步详细操作

#### 第1步：Math Animator
- [ ] 删除 `deeptutor/capabilities/math_animator.py`
- [ ] 从 `deeptutor/runtime/bootstrap/builtin_capabilities.py` 删除 `"math_animator"` 条目
- [ ] 验证1：后端启动
- [ ] 验证2：前端启动
- [ ] 验证3：用户确认

#### 第2步：Visualize
- [ ] 删除 `deeptutor/capabilities/visualize.py`
- [ ] 从 `builtin_capabilities.py` 删除 `"visualize"` 条目
- [ ] 删除 `web/components/visualize/` 目录
- [ ] 从 page.tsx 删除 Visualize 相关 import 和 CAPABILITIES 条目
- [ ] 验证1：后端启动
- [ ] 验证2：前端启动
- [ ] 验证3：用户确认

#### 第3步：Auto
- [ ] 删除 `deeptutor/capabilities/auto.py`
- [ ] 删除 `deeptutor/agents/auto/` 目录
- [ ] 从 `builtin_capabilities.py` 删除 `"auto"` 条目
- [ ] 验证1：后端启动
- [ ] 验证2：前端启动
- [ ] 验证3：用户确认

#### 第4步：Deep Question
- [ ] 删除 `deeptutor/capabilities/deep_question.py`
- [ ] 删除 `deeptutor/agents/question/` 目录
- [ ] 从 `builtin_capabilities.py` 删除 `"deep_question"` 条目
- [ ] 删除 `web/components/quiz/` 目录
- [ ] 从 page.tsx 删除 Quiz 相关 import 和逻辑
- [ ] 验证1：后端启动
- [ ] 验证2：前端启动
- [ ] 验证3：用户确认

#### 第5步：Book
- [ ] 删除 `deeptutor/book/` 目录
- [ ] 删除 book 相关 API 路由
- [ ] 删除 `web/lib/book-api.ts`、`web/lib/book-types.ts`
- [ ] 删除 `web/components/book/` 目录（如有）
- [ ] 从 page.tsx 删除 Book 相关逻辑
- [ ] 验证1：后端启动
- [ ] 验证2：前端启动
- [ ] 验证3：用户确认

#### 第6步：Chat
- [ ] 删除 `deeptutor/capabilities/chat.py`
- [ ] 删除 `deeptutor/agents/chat/` 目录
- [ ] 从 `builtin_capabilities.py` 删除 `"chat"` 条目
- [ ] 重写 page.tsx：移除 Chat 逻辑，保留 Exam Sprint + Deep Solve + Deep Research
- [ ] 验证1：后端启动
- [ ] 验证2：前端启动
- [ ] 验证3：用户确认

### 最终状态

切割完成后，`builtin_capabilities.py` 应该只有 3 条：

```python
BUILTIN_CAPABILITY_CLASSES: dict[str, str] = {
    "deep_solve": "deeptutor.capabilities.deep_solve:DeepSolveCapability",
    "deep_research": "deeptutor.capabilities.deep_research:DeepResearchCapability",
    "exam_sprint": "deeptutor.capabilities.exam_sprint:ExamSprintCapability",
}
```

### 禁止事项

- ❌ 禁止一次性删除多个模块
- ❌ 禁止跳过验证步骤
- ❌ 禁止在验证失败后继续切割
- ❌ 禁止不读本文件就执行切割操作
