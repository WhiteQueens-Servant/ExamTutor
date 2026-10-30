# DeepTutor 简历项目解读文档索引

> 本文档汇总了 DeepTutor 项目的核心模块解读，帮助你在面试中清晰表达技术细节。

---

## 📚 文档列表

| 序号 | 模块 | 文档 | 核心亮点 |
|------|------|------|---------|
| 00 | 系统全貌 | [00_系统全貌.md](00_系统全貌.md) | 五阶段生命周期、分层架构、组件协作 |
| 01 | RAG Pipeline | [01_RAG_Pipeline详解.md](01_RAG_Pipeline详解.md) | 混合检索、版本化索引、异步处理 |
| 02 | Prompt Engineering | [见下方速览](#-速览-prompt-engineering)（原 README_RESUME.md 并入） | 多语言支持、语言回退、全局缓存 |
| 03 | Exam Sprint | [见下方速览](#-速览-exam-sprint-sse-流式诊断)（原 README_RESUME.md 并入） | SSE 流式诊断、时间压力驱动、自适应学习 |
| 04 | Agentic Loop | [04_Agentic_Loop详解.md](04_Agentic_Loop详解.md) | 标签驱动、并行工具调用、自动修复 |
| 05 | 两层插件架构 | [05_两层插件架构详解.md](05_两层插件架构详解.md) | Tools + Capabilities、插件化、组合性 |
| 08 | 三层记忆系统 | [08_三层记忆系统详解.md](08_三层记忆系统详解.md) | L1/L2/L3 分层、LLM 驱动整合、增量去重 |

---

## 🎯 面试准备指南

### 1. 项目介绍（1-2 分钟）

"我负责的 DeepTutor 是一个 Agent-Native 个性化学习伴侣系统，核心采用两层插件架构：L1 Tools 提供原子操作，L2 Capabilities 提供多步骤流程。系统集成了 RAG（检索增强生成）、Prompt Engineering、SSE 流式诊断等核心技术。"

### 2. 技术深度（3-5 分钟）

根据面试官的问题，选择对应模块深入：

- **问整体架构** → 参考 [00_系统全貌.md](00_系统全貌.md)
- **问 RAG** → 参考 [01_RAG_Pipeline详解.md](01_RAG_Pipeline详解.md)
- **问推理引擎** → 参考 [04_Agentic_Loop详解.md](04_Agentic_Loop详解.md)
- **问架构设计** → 参考 [05_两层插件架构详解.md](05_两层插件架构详解.md)
- **问记忆系统** → 参考 [08_三层记忆系统详解.md](08_三层记忆系统详解.md)

### 3. 亮点总结

**架构设计亮点：**
- 两层插件架构：Tools + Capabilities
- 标签驱动的 Agentic Loop
- 统一的 PromptManager

**工程实现亮点：**
- 混合检索（向量 + BM25）
- SSE 流式诊断
- 并行工具调用

**业务价值亮点：**
- 时间压力驱动的任务优先级
- 自适应学习材料生成
- 多语言支持

---

## 📊 技术栈总结

| 层次 | 技术 | 说明 |
|------|------|------|
| **前端** | Next.js 16 + React 19 | App Router, Tailwind CSS |
| **后端** | Python 3.11+ + FastAPI | WebSocket, SSE, RESTful API |
| **RAG** | LlamaIndex | 向量检索 + BM25 混合检索 |
| **LLM** | OpenAI / Anthropic / DashScope | 多 Provider 支持 |
| **Embedding** | OpenAI / DashScope / 本地模型 | 向量化服务 |
| **存储** | JSON + SQLite | 配置 + 会话持久化 |
| **Prompt** | YAML + PromptManager | 多语言管理 |

---

## 🏛️ 速览：系统架构（原 README_RESUME.md 并入）

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户入口层                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   CLI    │  │ WebSocket│  │ Python   │  │ Exam     │       │
│  │  (Typer) │  │   API    │  │   SDK    │  │ Sprint   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
├───────┴──────────────┴──────────────┴──────────────┴─────────────┤
│                      核心运行时                                   │
│           ChatOrchestrator (统一路由) ← UnifiedContext           │
│         ┌─────────────────┴─────────────────┐                  │
│         ▼                                   ▼                  │
│  ┌──────────────┐                    ┌──────────────┐          │
│  │ ToolRegistry │                    │CapabilityReg │          │
│  │    (L1)      │                    │    (L2)      │          │
│  ├──────────────┤                    ├──────────────┤          │
│  │ • rag        │                    │ • chat       │          │
│  │ • web_search │                    │ • deep_solve │          │
│  │ • code_exec  │                    │ • exam_sprint│          │
│  │ • ...        │                    │ • deep_research │       │
│  └──────────────┘                    └──────────────┘          │
├──────────────────────────────────────────────────────────────────┤
│  服务层：LLM / Embedding / RAG / Memory / PromptManager          │
└─────────────────────────────────────────────────────────────────┘
```

核心设计模式：
- **两层插件架构**：`BaseTool.execute()`（L1 单功能）+ `BaseCapability.run(context, stream)`（L2 多阶段管道）
- **Agentic Loop**：THINK → TOOL → FINISH → REPLAN 四阶段循环（详解见 [04]）
- **SSE 流式响应**：逐题生成，解决 LLM 多题 JSON 不可靠问题（见下方速览）

---

## 📝 速览：Prompt Engineering

原"02 待补"要点（详解文档尚未单列，面试可按此展开）：

- **PromptManager**（`deeptutor/services/prompt/manager.py`）：单例 + 全局缓存，避免重复加载 YAML
- **语言回退链**：`zh → cn → en`，缺失语言自动降级
- **组织方式**：`deeptutor/**/prompts/{en,zh}/*.yaml`，按模块/Agent 分目录；字段含 system_prompt / user_prompt 模板
- **工具引导两层设计**：Tool schema description（给 function-calling）+ Prompt Hints YAML（`hints/{en,zh}/{tool}.yaml`，渲染进 system prompt，含 short_description / when_to_use / guideline / phase）

---

## 🎯 速览：Exam Sprint SSE 流式诊断

原"03 待补"要点：

- **问题背景**：LLM 一次生成多题 JSON 不可靠（格式错误、知识点缺失）→ 诊断失败
- **方案**：`POST /diagnosis/stream`，逐题单独调用 LLM，SSE 事件流式返回（`event: question\ndata: {...}`）
- **Prompt 关键约束**：强制 `knowledge_point` 为非空中文核心考点字符串（Phase 5.4/5.5 两轮优化产出）
- **解析容错**：多层 fallback 的 JSON 解析
- **业务链**：冷启动向导（考试信息 → 知识库 → SSE 诊断）→ 诊断持久化 → 动态任务生成 → 练习/掌握度追踪（数据架构见 `migrate_documents/exam-sprint-data-architecture.md`）

---

## 🔗 相关资源

- **项目仓库**：`D:\AgentProject\DeepTutor-main`
- **原始 README**：`README.md`
- **垂直切割/视频工具 spec**：`docs/superpowers/specs/`
- **Exam Sprint 迁移记录**：`migrate_documents/exam-sprint-task-list.md`

---

## 📝 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-07-07 | v1.0 | 初始版本，包含 5 个核心模块解读 |
| 2026-07-30 | v1.1 | 补充 00 系统全貌 + 08 三层记忆系统索引；标注 02/03 待补 |
| 2026-10-30 | v1.2 | 文档瘦身：README_RESUME.md 去重并入本文（架构/Prompt/SSE 三个速览，填补 02/03 坑），删除原根目录文件；能力清单更新为切割后 4 能力 |

---

**维护者**：DeepTutor Dev
**最后更新**：2026-10-30
