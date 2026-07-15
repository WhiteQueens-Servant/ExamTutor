# DeepTutor 简历项目解读文档索引

> 本文档汇总了 DeepTutor 项目的核心模块解读，帮助你在面试中清晰表达技术细节。

---

## 📚 文档列表

| 序号 | 模块 | 文档 | 核心亮点 |
|------|------|------|---------|
| 01 | RAG Pipeline | [01_RAG_Pipeline详解.md](01_RAG_Pipeline详解.md) | 混合检索、版本化索引、异步处理 |
| 02 | Prompt Engineering | [02_Prompt_Engineering详解.md](02_Prompt_Engineering详解.md) | 多语言支持、语言回退、全局缓存 |
| 03 | Exam Sprint | [03_Exam_Sprint详解.md](03_Exam_Sprint详解.md) | SSE 流式诊断、时间压力驱动、自适应学习 |
| 04 | Agentic Loop | [04_Agentic_Loop详解.md](04_Agentic_Loop详解.md) | 标签驱动、并行工具调用、自动修复 |
| 05 | 两层插件架构 | [05_两层插件架构详解.md](05_两层插件架构详解.md) | Tools + Capabilities、插件化、组合性 |

---

## 🎯 面试准备指南

### 1. 项目介绍（1-2 分钟）

"我负责的 DeepTutor 是一个 Agent-Native 个性化学习伴侣系统，核心采用两层插件架构：L1 Tools 提供原子操作，L2 Capabilities 提供多步骤流程。系统集成了 RAG（检索增强生成）、Prompt Engineering、SSE 流式诊断等核心技术。"

### 2. 技术深度（3-5 分钟）

根据面试官的问题，选择对应模块深入：

- **问 RAG** → 参考 [01_RAG_Pipeline详解.md](01_RAG_Pipeline详解.md)
- **问 Prompt** → 参考 [02_Prompt_Engineering详解.md](02_Prompt_Engineering详解.md)
- **问 Exam Sprint** → 参考 [03_Exam_Sprint详解.md](03_Exam_Sprint详解.md)
- **问推理引擎** → 参考 [04_Agentic_Loop详解.md](04_Agentic_Loop详解.md)
- **问架构设计** → 参考 [05_两层插件架构详解.md](05_两层插件架构详解.md)

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

## 🔗 相关资源

- **项目仓库**：`D:\AgentProject\DeepTutor-main`
- **简历 README**：`README_RESUME.md`
- **原始 README**：`README.md`

---

## 📝 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-07-07 | v1.0 | 初始版本，包含 5 个核心模块解读 |

---

**维护者**：DeepTutor Dev
**最后更新**：2026-07-07
