# 垂直切割工作流约束

> **硬性约束文件**：本文件定义切割执行的强制规则。每次执行切割操作前必须重读本文件。

---

## 一、核心原则：一步一停三验证

```
┌─────────────────────────────────────────────────────┐
│  切一步 → 停 → 验证① → 验证② → 验证③ → 用户确认 → 下一步  │
└─────────────────────────────────────────────────────┘
```

### 三验证内容

| 验证项 | 内容 | 方法 |
|--------|------|------|
| ① 后端代码检查 | 搜索被删模块的残留引用，确认无致命依赖 | `grep` + `find` |
| ② 前端代码检查 | 确认前端无硬依赖（import/API 调用） | `grep` web/ 目录 |
| ③ 用户手动验证 | 后端启动 + 前端启动 + 功能测试 | 用户执行 |

### 停止信号

- 每完成一步，**必须停止**并报告验证结果
- **不得在用户确认前继续下一步**
- 验证失败时**必须回滚**，不得带病前进

---

## 二、强制约束（不可违反）

1. **禁止批量删除**：一次只切一个模块
2. **禁止跳过验证**：每步必须完成三验证
3. **禁止跨步推进**：用户未确认不得开始下一步
4. **禁止主观推断**：遇到问题必须基于代码排查，不得猜测
5. **禁止修改保留模块**：切割过程中不得修改 Exam Sprint / Deep Solve / Deep Research 的核心逻辑
6. **进度更新强制**：每完成一步切割，必须更新本文件的进度状态和变更记录
7. **回顾前置**：执行下一步前，必须先查看上一步的进度更新和变更记录
8. **决策记录**：与原计划不符的决策必须在 `变更记录` 表格中记录，包含：决策内容、原计划、实际执行、原因

---

## 三、切割顺序（从最小到最大耦合）

```
第1步：Math Animator  ← 单文件，无前端 ← 已完成 ✅
第2步：Visualize      ← 单文件 + 小前端组件 ← 已完成 ✅
第3步：Auto           ← 有目录，无前端 ← 已完成 ✅
第4步：Deep Question  ← 完整 Pipeline + 前端组件 ← 已完成 ✅
第5步：Book           ← 独立 API 层 ← 待执行
第6步：Chat           ← 最大耦合，重写 page.tsx ← 待执行
```

---

## 四、执行 Checklist

### 第1步：Math Animator ✅

- [x] 1.1 删除 `deeptutor/capabilities/math_animator.py`
- [x] 1.2 删除 `deeptutor/capabilities/prompts/{en,zh}/math_animator.yaml`
- [x] 1.3 从 `builtin_capabilities.py` 删除 `'math_animator'` 条目
- [x] 验证①：后端无致命引用
- [x] 验证②：前端无硬依赖
- [x] 验证③：用户确认启动正常
- [x] 备份至 `useful_tools/math_animator/`

#### 变更记录（第1步）

| 决策 | 原计划 | 实际执行 | 原因 |
|------|--------|----------|------|
| 保留 agent 层 | 未明确 | 保留 `deeptutor/agents/math_animator/` | Visualize 的 `visualize.py` 第311-312行懒加载导入了 `MathAnimatorPipeline`，删除会导致 Visualize 功能受损 |
| 备份至 useful_tools | 未计划 | 用户要求备份 | 用户希望保留 Math Animator 作为独立工具备用 |
| 备份内容 | - | capability 文件 + agent 层 + prompts（capability + agent 两套） | 完整备份以便未来独立使用 |

---

### 第2步：Visualize ✅

- [x] 2.1 删除 `deeptutor/capabilities/visualize.py`
- [x] 2.2 删除 `deeptutor/capabilities/prompts/{en,zh}/visualize.yaml`
- [x] 2.3 从 `builtin_capabilities.py` 删除 `'visualize'` 条目
- [x] 验证①：后端无致命引用
- [x] 验证②：前端无硬依赖
- [x] 验证③：用户确认启动正常

#### 变更记录（第2步）

| 决策 | 原计划 | 实际执行 | 原因 |
|------|--------|----------|------|
| 保留 agent 层 | 未明确 | 保留 `deeptutor/agents/visualize/` | Book 模块的 `book/blocks/interactive.py` 和 `book/blocks/figure.py` 懒加载导入了 `VisualizePipeline` |
| 保留前端组件 | 未明确 | 保留 `web/components/visualize/` 和 `web/lib/visualize-types.ts` | 其他模块可能引用这些类型定义 |
| 不备份 | 备份 | 未备份 | 用户明确指示只需备份 Math Animator |

---

### 第3步：Auto ✅

- [x] 3.1 删除 `deeptutor/capabilities/auto.py`
- [x] 3.2 从 `builtin_capabilities.py` 删除 `'auto'` 条目
- [x] 3.3 删除 `deeptutor/agents/auto/` 目录（agent 层）
- [x] 验证①：后端无致命引用
- [x] 验证②：前端无硬依赖
- [x] 验证③：用户确认启动正常

#### 变更记录（第3步）

| 决策 | 原计划 | 实际执行 | 原因 |
|------|--------|----------|------|
| 删除 agent 层 | 未明确 | 删除 `deeptutor/agents/auto/` | 用户质疑保留原因；经检查无其他模块依赖，仅测试文件引用 |
| 无 prompts | 计划删除 prompts | 无 prompts 可删 | Auto 模块没有专属 prompts |

---

### 第4步：Deep Question ✅

- [x] 4.1 删除 `deeptutor/capabilities/deep_question.py`
- [x] 4.2 删除 `deeptutor/capabilities/prompts/{en,zh}/deep_question.yaml`
- [x] 4.3 从 `builtin_capabilities.py` 删除 `'deep_question'` 条目
- [x] 验证①：后端无致命引用
- [x] 验证②：前端无硬依赖
- [x] 验证③：用户确认启动正常

#### 变更记录（第4步）

| 决策 | 原计划 | 实际执行 | 原因 |
|------|--------|----------|------|
| 保留 agent 层 | 未明确 | **必须保留** `deeptutor/agents/question/` | Exam Sprint 的 `api/routers/exam_sprint.py` 第32-33行导入了 `QuestionPipeline` 和 `build_question_runtime_config`，删除会破坏 Exam Sprint 的题目生成功能 |
| 关键依赖发现 | - | Exam Sprint → Question Agent 层 | 这是保留模块对被删模块 agent 层的硬依赖，需要在未来 Exam Sprint 改进时解耦 |

---

### 第5步：Book ✅

- [x] 5.1 删除 `deeptutor/book/` 目录
- [x] 5.2 删除 `deeptutor/api/routers/book.py`
- [x] 5.3 从 `deeptutor/api/main.py` 删除 Book 路由
- [x] 验证①：后端无致命引用
- [x] 验证②：前端无硬依赖
- [x] 验证③：用户确认启动正常

#### 变更记录（第5步）

| 决策 | 原计划 | 实际执行 | 原因 |
|------|--------|----------|------|
| 前端 stub 文件 | 未计划 | 创建 `web/lib/book-api.ts`、`web/lib/book-types.ts`、`web/lib/book-references.ts` 空导出 | 防止其他前端模块 import 报错 |
| 前端组件清理 | 未明确 | 删除 BookReferencePicker、BookRecent 等组件 | 用户要求彻底清理 |

---

### 第6步：Chat ⏸️ 已取消

- 用户决定保留 Chat capability 作为默认能力
- Chat 是 Answer Now 的回退目标（`context.active_capability or "chat"`）

---

### 回收切割 ✅

#### 1. 记忆模块前端屏蔽 ✅

- [x] 从 `SidebarShell.tsx` 的 `PRIMARY_NAV` 删除记忆条目
- [x] 移除未使用的 `Brain` 图标导入
- [x] 后端记忆服务继续为所有能力提供上下文

#### 2. Agent Layer 回收 ✅

- [x] 删除 `deeptutor/agents/question/`（Exam Sprint 不依赖，仅依赖 core 协议）
- [x] 删除 `deeptutor/agents/math_animator/`（无剩余依赖，备份在 `useful_tools/`）
- [x] 清理 `request_contracts.py`：移除已删除能力的验证器

#### 变更记录（回收切割）

| 决策 | 原计划 | 实际执行 | 原因 |
|------|--------|----------|------|
| Question Agent 删除 | 第4步保留（因 Exam Sprint 依赖） | 删除 | 经代码分析确认 Exam Sprint 不依赖 Question Agent，只依赖 BaseCapability/UnifiedContext/StreamBus |
| Math Animator Agent 删除 | 第1步保留（因 Visualize 依赖） | 删除 | Visualize 已被切除，无剩余依赖 |
| request_contracts 清理 | 未计划 | 清理 | 移除 math_animator、visualize、auto、deep_question 的验证器 |

---

## 五、已知问题与注意事项

1. **Agent 层回收状态**：
   - Math Animator agent 层：**已回收**（备份在 `useful_tools/math_animator/`）
   - Visualize agent 层：**已回收**（随 Visualize capability 一起删除）
   - Question agent 层：**已回收**（Exam Sprint 不依赖）
   - Auto agent 层：**已回收**

2. **前端组件保留**：
   - `web/components/visualize/` — 已删除
   - `web/components/math-animator/` — 已删除
   - `web/lib/visualize-types.ts` — 已删除
   - `web/lib/math-animator-types.ts` — 已删除

3. **测试文件**：
   - 测试文件中对已删模块的引用会导致测试失败
   - 不影响主程序运行，可在最后统一清理

4. **当前保留的能力**：
   ```
   chat (默认能力，Answer Now 回退目标)
   deep_solve
   deep_research
   exam_sprint
   ```

---

## 六、紧急回滚

如果切割导致系统崩溃：

```bash
# 回滚所有改动
git checkout -- deeptutor/ web/

# 或回滚到切割前的版本
git log --oneline -5  # 找到切割前的 commit
git reset --hard <commit-hash>
```

---

*文档版本：v1.2*
*创建时间：2026-07-15*
*最后更新：2026-07-16（完成回收切割：删除 Question/MathAnimator Agent 层，清理 request_contracts，屏蔽记忆模块前端入口）*
