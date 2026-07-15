# DeepTutor: Agent-Native Personalized Learning System

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LlamaIndex](https://img.shields.io/badge/LlamaIndex-RAG-009688?style=flat-square)](https://docs.llamaindex.ai/)

## 📋 项目简介

DeepTutor 是一个 **Agent-Native 个性化学习伴侣系统**，基于两层插件架构（Tools + Capabilities）构建。系统集成了 **RAG（检索增强生成）**、**多 Provider LLM 路由**、**Prompt Engineering**、**SSE 流式诊断**等核心技术，支持从冷启动到个性化学习的完整用户旅程。

**核心亮点：**
- 🏗️ 两层插件架构：Tools (L1) 单功能工具 + Capabilities (L2) 多步骤管道
- 🔍 RAG Pipeline：LlamaIndex 驱动的向量检索 + LLM 合成
- 📝 Prompt Engineering：YAML 管理 + 多语言支持 + 语言回退链
- 🎯 SSE 流式诊断：逐题生成，解决 LLM 多题 JSON 不可靠问题
- 🧠 三层记忆系统：L1 追踪 → L2 摘要 → L3 综合

---

## 🏛️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户入口层                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   CLI    │  │ WebSocket│  │ Python   │  │ Exam     │       │
│  │  (Typer) │  │   API    │  │   SDK    │  │ Sprint   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │             │
├───────┴──────────────┴──────────────┴──────────────┴─────────────┤
│                      核心运行时                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              ChatOrchestrator (统一路由)                   │   │
│  │  ┌──────────────────────────────────────────────────┐    │   │
│  │  │         UnifiedContext (上下文传递)                │    │   │
│  │  └──────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│         ┌─────────────────┴─────────────────┐                  │
│         ▼                                   ▼                  │
│  ┌──────────────┐                    ┌──────────────┐          │
│  │ ToolRegistry │                    │CapabilityReg │          │
│  │    (L1)      │                    │    (L2)      │          │
│  ├──────────────┤                    ├──────────────┤          │
│  │ • rag        │                    │ • chat       │          │
│  │ • web_search │                    │ • deep_solve │          │
│  │ • code_exec  │                    │ • exam_sprint│          │
│  │ • reason     │                    │ • visualize  │          │
│  │ • ...        │                    │ • ...        │          │
│  └──────────────┘                    └──────────────┘          │
│                           │                                      │
├───────────────────────────┴──────────────────────────────────────┤
│                      服务层                                       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │  LLM   │ │Embedding│ │  RAG   │ │ Memory │ │Prompt  │       │
│  │Service │ │ Service │ │Service │ │Service │ │Manager │       │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 RAG Pipeline 详解

### 数据流

```
用户查询
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Tool (入口)                           │
│  rag_search(query, kb_name) → RAGService                    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                  RAGService (服务层)                         │
│  • 解析查询意图                                              │
│  • 调用 LlamaIndexPipeline                                  │
│  • 结果后处理 + 格式化                                       │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│               LlamaIndexPipeline (核心)                     │
│  1. Query Expansion (查询扩展)                              │
│  2. Vector Search (向量检索)                                │
│  3. Rerank (重排序)                                         │
│  4. LLM Synthesis (LLM 合成答案)                           │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                  结果返回                                    │
│  • answer: 合成答案                                         │
│  • sources: 引用来源                                        │
│  • score: 相关度分数                                        │
└─────────────────────────────────────────────────────────────┘
```

### 关键代码

```python
# deeptutor/services/rag/service.py
class RAGService:
    """Unified RAG service backed by the LlamaIndex pipeline."""

    async def search(self, query: str, kb_name: str, event_sink=None):
        """向量检索 + LLM 合成"""
        pipeline = self._get_pipeline()
        result = await pipeline.search(query=query, kb_name=kb_name)
        return result

# deeptutor/tools/rag_tool.py
async def rag_search(query: str, kb_name: str, ...):
    """RAG 工具入口"""
    service = RAGService(kb_base_dir=kb_base_dir)
    return await service.search(query=query, kb_name=kb_name)
```

---

## 📝 Prompt Engineering 实现

### PromptManager 架构

```python
# deeptutor/services/prompt/manager.py
class PromptManager:
    """Unified prompt manager with singleton pattern and global caching."""

    # 语言回退链
    LANGUAGE_FALLBACKS = {
        "zh": ["zh", "cn", "en"],  # 中文 → 英文
        "en": ["en", "zh", "cn"],  # 英文 → 中文
    }

    def load_prompts(self, module_name, agent_name, language="zh"):
        """加载 YAML prompt，支持语言回退"""
        # 1. 检查缓存
        # 2. 查找 prompt 文件 (en/zh 双语)
        # 3. 语言回退 (zh → en)
        # 4. 缓存结果
```

### YAML 文件组织

```
deeptutor/
├── agents/
│   ├── solve/prompts/
│   │   ├── en/pipeline.yaml      # Solve Pipeline (英文)
│   │   └── zh/pipeline.yaml      # Solve Pipeline (中文)
│   ├── chat/prompts/
│   │   ├── en/chat_agent.yaml
│   │   └── zh/chat_agent.yaml
│   └── ...
├── capabilities/prompts/
│   ├── en/deep_question.yaml
│   └── zh/deep_question.yaml
└── book/prompts/
    ├── en/section.yaml
    └── zh/section.yaml
```

### Agent Prompt 示例

```yaml
# deeptutor/agents/solve/prompts/zh/pipeline.yaml
system_prompt: |
  你是一个多步骤问题解决助手。
  
  Phase 1: 规划
  - 分析问题
  - 制定解决步骤
  
  Phase 2: 执行
  - 逐步执行
  - 调用工具验证
  
  Phase 3: 综合
  - 总结答案
  - 提供引用

user_prompt: |
  问题：{question}
  知识库上下文：{retrieved_context}
```

---

## 🎯 SSE 流式诊断

### 问题背景

LLM 一次生成多题 JSON 不可靠（格式错误、知识点缺失），导致诊断失败。

### 解决方案

**逐题生成**：每道题单独调用 LLM，通过 SSE 流式返回。

### 实现代码

```python
# deeptutor/api/routers/exam_sprint.py
@router.post("/diagnosis/stream")
async def stream_diagnosis(req: DiagnosisGenerateRequest):
    """Stream diagnostic questions one-by-one via Server-Sent Events."""

    async def event_generator():
        llm = get_llm_client()
        
        for i in range(total_questions):
            # 1. 构建 system_prompt (明确要求 knowledge_point 字段)
            system_prompt = (
                "You are an exam diagnostic question generator. "
                "Generate exactly ONE diagnostic question in Chinese. "
                "Return a JSON object with these EXACT fields:\n"
                "- knowledge_point: string (REQUIRED! The specific topic name)\n"
                "..."
            )
            
            # 2. 单次 LLM 调用
            raw_response = await llm.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )
            
            # 3. 解析 JSON (支持多层 fallback)
            question = parse_json_response(raw_response)
            
            # 4. SSE 流式返回
            yield f"event: question\ndata: {json.dumps(question)}\n\n"
```

### Prompt Engineering 优化

```python
# system_prompt 关键要求
"CRITICAL REQUIREMENTS for knowledge_point:\n"
"1. MUST be a non-empty Chinese string (e.g., 'TCP拥塞控制')\n"
"2. Must describe the CORE knowledge point being tested\n"
"3. NEVER leave knowledge_point empty or as an English abbreviation\n"
```

---

## 🧠 三层记忆系统

```
┌─────────────────────────────────────────────────────────────┐
│                    L3 · 跨表面综合                           │
│  • profile (用户画像)                                       │
│  • recent (近期时间线)                                      │
│  • scope (知识范围)                                         │
│  • preferences (偏好)                                       │
└─────────────────────────────────────────────────────────────┘
                          ▲
                          │ LLM 综合
┌─────────────────────────────────────────────────────────────┐
│                    L2 · 表面摘要                             │
│  • 每个表面 (chat, notebook, quiz, kb) 独立摘要              │
│  • 带引用的事实提取                                          │
│  • 支持 Update/Audit/Dedup 运行                             │
└─────────────────────────────────────────────────────────────┘
                          ▲
                          │ LLM 提取
┌─────────────────────────────────────────────────────────────┐
│                    L1 · 追踪记录                             │
│  • 追加式日志 (JSONL)                                       │
│  • 每个交互事件的无损记录                                    │
│  • trace/<surface>/<YYYY-MM-DD>.jsonl                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| **前端** | Next.js 16 + React 19 | App Router, Tailwind CSS |
| **后端** | Python 3.11+ + FastAPI | WebSocket, SSE, RESTful API |
| **RAG** | LlamaIndex | 向量检索 + LLM 合成 |
| **LLM** | OpenAI / Anthropic / DashScope | 多 Provider 支持 |
| **Embedding** | OpenAI / DashScope / 本地模型 | 向量化服务 |
| **存储** | JSON + SQLite | 配置 + 会话持久化 |
| **Prompt** | YAML + PromptManager | 多语言管理 |

---

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -e ".[dev]"

# 4. 初始化配置
deeptutor init

# 5. 启动服务
deeptutor start
```

---

## 📊 项目结构

```
DeepTutor/
├── deeptutor/
│   ├── core/                    # 核心协议
│   │   ├── capability_protocol.py  # BaseCapability
│   │   ├── tool_protocol.py        # BaseTool
│   │   ├── context.py              # UnifiedContext
│   │   └── stream_bus.py           # StreamBus
│   ├── capabilities/            # L2 能力实现
│   │   ├── exam_sprint.py       # 考试冲刺
│   │   ├── deep_solve.py        # 多步骤解题
│   │   └── ...
│   ├── tools/                   # L1 工具实现
│   │   ├── rag_tool.py          # RAG 检索
│   │   └── builtin/             # 内置工具
│   ├── services/                # 服务层
│   │   ├── llm/                 # LLM 提供商
│   │   ├── rag/                 # RAG Pipeline
│   │   ├── prompt/              # PromptManager
│   │   └── memory/              # 三层记忆
│   ├── agents/                  # Agent 实现
│   │   ├── solve/               # Solve Pipeline
│   │   ├── auto/                # Auto Router
│   │   └── ...
│   └── api/                     # API 路由
│       └── routers/
│           ├── exam_sprint.py   # 考试冲刺 API
│           └── ...
├── web/                         # Next.js 前端
├── tests/                       # 测试
└── data/                        # 运行时数据
```

---

## 💡 核心设计模式

### 1. 两层插件架构

```python
# L1: Tools - 单功能工具
class BaseTool(ABC):
    @abstractmethod
    async def execute(self, **kwargs) -> dict: ...

# L2: Capabilities - 多步骤管道
class BaseCapability(ABC):
    @abstractmethod
    async def run(self, context: UnifiedContext, stream: StreamBus): ...
```

### 2. Agentic Loop

```python
# 四阶段循环: THINK → TOOL → FINISH → REPLAN
async def run_agentic_loop(...):
    while True:
        # THINK: LLM 分析
        # TOOL: 调用工具
        # FINISH: 输出结果
        # REPLAN: 重新规划 (如需要)
```

### 3. SSE 流式响应

```python
# 逐题生成，解决 LLM 多题 JSON 不可靠问题
async def event_generator():
    for i in range(total_questions):
        question = await llm.complete(...)  # 单次调用
        yield f"event: question\ndata: {json.dumps(question)}\n\n"
```

---

## 📈 性能优化

1. **Prompt 缓存**：PromptManager 全局缓存，避免重复加载
2. **并行检索**：RAG Pipeline 支持多查询并行
3. **SSE 流式**：逐题生成，减少等待时间
4. **语言回退**：自动 fallback 到备选语言

---

## 🔒 安全设计

1. **多用户隔离**：per-user workspace 隔离
2. **JWT 认证**：可选的 token 认证
3. **API Key 保护**：credentials 不跨用户边界
4. **输入验证**：Pydantic 模型验证

---

## 🎓 学习价值

本项目展示了以下核心技能：

1. **系统架构设计**：两层插件架构 + 服务层抽象
2. **RAG 实现**：向量检索 + LLM 合成的完整链路
3. **Prompt Engineering**：YAML 管理 + 多语言支持 + 语言回退
4. **流式处理**：SSE 实现 + 逐题生成策略
5. **异步编程**：asyncio + 并行检索
6. **前后端分离**：Next.js + FastAPI + WebSocket

---

## 📄 License

Apache License 2.0

---

**Author**: DeepTutor Dev
**Date**: 2026-07-07
