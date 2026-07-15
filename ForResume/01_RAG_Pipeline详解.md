# RAG Pipeline 详解 — 面试解读

> 本文档从面试角度解读 DeepTutor 的 RAG（检索增强生成）实现，帮助你在面试中清晰表达技术细节。
> **v4.1** — 新增签名机制、增量更新、异步执行深度讲解；新增跨版本局限性分析。

---

## 一、模块总览

### 1.1 这个模块解决什么问题？

RAG Pipeline 是 DeepTutor 的**知识库检索引擎**，解决的核心问题是：

**如何将用户上传的文档变成可检索的知识，并在对话时精准召回相关内容？**

在教育场景中，学生上传课件、论文、教材后，DeepTutor 需要：
- 将文档拆分成语义完整的片段（Chunking）
- 将片段转为向量并存储（Embedding + Indexing）
- 对话时同时用语义检索和关键词检索找到最相关的内容（Hybrid Retrieval）
- 处理 Embedding 模型切换导致的索引不兼容问题（Versioning）

### 1.2 核心设计理念

采用**四层架构 + 混合检索 + 版本化索引**的设计，核心思想是：

> 上层应用不关心检索细节，只通过统一入口调用；底层支持向量检索与 BM25 关键词检索的融合，通过倒数排名策略取长补短。

这种设计的好处是：
- **解耦**：应用层（Chat/Solve/ExamSprint）只调用 RAGService，不直接接触 LlamaIndex
- **可替换**：管道层可以替换不同的 RAG 后端
- **混合检索**：向量检索擅长语义理解，BM25 擅长精确匹配，融合后覆盖面更广
- **版本安全**：Embedding 模型切换时，旧索引不会被误用

---

## 二、内部分层架构

### 2.1 组件组成

```
┌─────────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                     │
│                                                                 │
│   RAGAdapterTool     SmartRetriever     ExamSprint               │
│   (Agent工具调用)     (多查询检索)       (考试冲刺)               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    服务层 (Service Layer)                         │
│                                                                 │
│   RAGService（统一入口）                                         │
│   - 懒加载 Pipeline：首次调用时才初始化                           │
│   - 结果标准化：统一 answer/content 字段                          │
│   - 事件通知：通过回调推送检索状态到前端                          │
│   - 记忆追踪：将检索事件写入 L1 Memory Trace                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    管道层 (Pipeline Layer)                        │
│                                                                 │
│   LlamaIndexPipeline（核心管道）                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │  Ingestion   │  │   Storage    │  │  Retrievers  │         │
│   │  文档摄入     │  │   存储管理    │  │  检索器组合   │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    基础层 (Infrastructure Layer)                  │
│                                                                 │
│   EmbeddingAdapter    IndexVersioning    BM25Retriever           │
│   (向量化服务)         (版本管理)         (关键词检索)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 各层职责

| 层级 | 职责 | 核心组件 | 关键文件 |
|------|------|---------|---------|
| **应用层** | 通过 RAGService 调用检索 | RAGAdapterTool, SmartRetriever | `deeptutor/agent/tools/deeptutor_tools.py` |
| **服务层** | 统一入口，结果标准化，事件通知 | RAGService | `deeptutor/services/rag/service.py` |
| **管道层** | 索引创建、检索执行、存储管理 | LlamaIndexPipeline | `deeptutor/services/rag/pipelines/llamaindex/pipeline.py` |
| **基础层** | 向量化、版本管理、BM25 | EmbeddingAdapter, IndexVersioning | `deeptutor/services/rag/index_versioning.py` |

### 2.3 组件关系图

```
应用层
  │
  │  调用 search(query, kb_name)
  ▼
RAGService（服务层）
  │
  │  懒加载获取 Pipeline
  │  调用 pipeline.search()
  ▼
LlamaIndexPipeline（管道层）
  │
  │  1. resolve_storage_dir_for_read() → 找到匹配的索引目录
  │  2. run_in_executor(storage.retrieve_nodes()) → 线程池执行检索
  │  3. _nodes_to_result() → 转换结果格式
  ▼
Storage（存储层）
  │
  │  1. load_index_from_storage() → 加载 LlamaIndex 索引
  │  2. _validate_persisted_embeddings() → 验证向量有效性
  │  3. build_retriever() → 构建检索器
  │  4. retriever.retrieve(query) → 执行检索
  ▼
Retrievers（检索器层）
  │
  ├─── Vector Retriever（向量检索）──→ index.as_retriever()
  │
  └─── BM25 Retriever（关键词检索）──→ BM25Retriever.from_persist_dir()
          │
          │  两者通过 QueryFusionRetriever 融合
          ▼
      RRF（倒数排名融合）→ 返回 Top-K 结果
```

---

## 三、核心机制详解

### 3.1 签名机制（EmbeddingSignature）

**所在文件**：`deeptutor/services/rag/index_versioning.py:47`、`deeptutor/services/rag/embedding_signature.py`

#### 签名是什么？

签名是 **Embedding 配置的指纹**，由 5 个字段组成：

| 字段 | 含义 | 示例 |
|------|------|------|
| `binding` | Embedding 提供商 | `"dashscope"`, `"openai"` |
| `model` | 模型名 | `"text-embedding-v3"`, `"text-embedding-ada-002"` |
| `dimension` | 向量维度 | `1024`, `1536` |
| `base_url` | API 地址 | `"https://dashscope.aliyuncs.com"` |
| `api_version` | API 版本 | `"2024-01-01"` |

签名的哈希值计算方式：将 5 个字段序列化为 JSON → SHA256 → 取前 16 位十六进制。

#### 签名如何产生？

`signature_from_config()` 从当前 Embedding 配置中提取 5 个字段，构建 `EmbeddingSignature` 对象。每次索引或查询时都会调用。

#### 签名如何匹配？

**索引时**（写入路径）：
1. 计算当前配置的签名哈希
2. `resolve_storage_dir_for_write()` 查找是否已有相同签名的 flat 版本
3. 有 → 复用该版本目录（增量写入）；没有 → 创建新的 `version-N/` 目录
4. 在目录下写入 `meta.json`，记录签名哈希和完整配置

**查询时**（读取路径）：
1. 计算当前配置的签名哈希
2. `resolve_storage_dir_for_read()` 遍历所有版本，查找签名匹配且状态为 ready 的版本
3. 找到 → 使用该版本的索引；找不到 → 返回 `needs_reindex: True`

#### 签名机制解决什么问题？

**场景**：用户先用 DashScope（1024 维）索引了文档，后来切换到 OpenAI（1536 维）。

- DashScope 索引签名：`hash("dashscope" + "text-embedding-v3" + 1024 + ...) = "a1b2c3..."`
- OpenAI 索引签名：`hash("openai" + "text-embedding-ada-002" + 1536 + ...) = "x9y8z7..."`

两个签名不同，系统会创建新版本 `version-2/` 存储 OpenAI 向量，旧版本 `version-1/` 保留。查询时自动匹配当前配置对应的版本。

**如果没有签名机制**：切换 Embedding 模型后，旧索引的向量维度不匹配，查询会报错或返回垃圾结果。

---

### 3.2 版本化索引的读写分离

**所在文件**：`deeptutor/services/rag/index_versioning.py`

#### 三种存储布局

| 布局 | 目录结构 | 特点 |
|------|---------|------|
| **flat（新版）** | `kb_dir/version-N/` | 结构简单，新索引默认使用 |
| **nested_legacy** | `kb_dir/versions/<id>/storage/` | 旧版嵌套结构 |
| **root_legacy** | `kb_dir/storage/` | 最早期的结构 |

#### 读写分离策略

**读取**（`resolve_storage_dir_for_read()`）：
1. 如果有签名 → 查找签名匹配的就绪版本（优先 flat）
2. 如果没有签名 → 使用最新的就绪 flat 版本
3. 都没有 → 尝试 root_legacy 作为兜底
4. 都没有 → 返回 None（触发 `needs_reindex`）

**写入**（`resolve_storage_dir_for_write()`）：
1. 如果有签名 → 查找签名匹配的 flat 版本，复用
2. 如果没有匹配 → 创建新的 `version-N/` 目录
3. **永远不写入 legacy 布局** → 系统自然向 flat 布局收敛

#### 版本元数据

每个版本目录下有 `meta.json`，记录：
- `version`：版本号（如 `"version-2"`）
- `signature`：签名哈希
- `binding`、`model`、`dimension` 等完整配置
- `layout`：布局类型（`"flat"` 或 `"nested_legacy"`）
- `created_at`：创建时间

---

### 3.3 增量更新 vs 全量重建

**所在文件**：`deeptutor/services/rag/pipelines/llamaindex/storage.py`

#### 两种操作模式

| 操作 | 触发条件 | 行为 |
|------|---------|------|
| **增量更新** | `add_documents()` | 加载已有索引 → 插入新节点 → 持久化 |
| **全量重建** | `initialize()` | 从零创建索引 → 分块所有文档 → 向量化 → 持久化 |

#### 增量更新的执行流程

`insert_documents()` 的具体步骤：

1. **加载已有索引**：`StorageContext.from_defaults(persist_dir=existing_storage)` → `load_index_from_storage()`
2. **验证向量有效性**：`_validate_persisted_embeddings()` 检查已有索引的向量是否可用
3. **分块 + 向量化新文档**：`ingestion.insert_documents_into_index()` → `documents_to_nodes()` → `pipeline.run()`
4. **插入新节点**：`index.insert_nodes(nodes)` 将新向量插入已有索引
5. **持久化**：`index.storage_context.persist()` 保存到磁盘
6. **更新 BM25**：`persist_bm25_retriever()` 重建 BM25 索引（因为 BM25 需要全局词频统计）

#### 增量更新的工程细节

- **签名复用**：`resolve_storage_dir_for_write()` 会找到已有签名匹配的 flat 版本，直接写入
- **失败清理**：`cleanup_failed_version_dir()` 清理空的版本目录（索引失败时可能产生）
- **BM25 全量重建**：每次增量更新都会重建 BM25 索引，因为 BM25 依赖全局词频统计，无法增量更新

---

### 3.4 混合检索与 RRF 融合

**所在文件**：`deeptutor/services/rag/pipelines/llamaindex/retrievers.py`

#### 双检索器架构

| 检索器 | 创建方式 | 擅长场景 |
|--------|---------|---------|
| **向量检索器** | `index.as_retriever()` | 语义理解（"机器学习"匹配"ML"） |
| **BM25 检索器** | `BM25Retriever.from_persist_dir()` | 精确匹配（"BERT"命中包含"BERT"的文档） |

#### 倒数排名融合（RRF）

使用 LlamaIndex 的 `QueryFusionRetriever`，采用 `RECIPROCAL_RANK` 模式：

1. 向量检索返回 Top-K1 个结果（候选数量通过 `candidate_top_k()` 放大，默认 2 倍）
2. BM25 检索返回 Top-K2 个结果（同样放大）
3. 根据排名计算融合分数：`score = Σ 1/(k + rank_i)`，k=60 是平滑参数
4. 按融合分数排序，返回最终 Top-K

#### BM25 持久化

`persist_bm25_retriever()` 将 BM25 索引存储在 `bm25_retriever/` 子目录，避免每次查询时重建。BM25 索引**按版本隔离**，每个 `version-N/` 下有独立的 `bm25_retriever/`。

#### 优雅降级

如果 BM25 依赖未安装（`_import_bm25_retriever()` 返回 None），自动降级到纯向量检索，不报错。

---

### 3.5 异步执行机制

**所在文件**：`deeptutor/services/rag/pipelines/llamaindex/pipeline.py:155`

#### 为什么需要异步执行？

检索操作是 **CPU 密集型**的（加载索引、计算相似度、排序结果）。如果在主事件循环中同步执行，会阻塞整个服务器，其他用户请求无法处理。

#### 异步执行的实现

`LlamaIndexPipeline.search()` 中的关键逻辑：

```
loop = asyncio.get_running_loop()
nodes = await loop.run_in_executor(
    None,                           # 使用默认线程池
    lambda: storage.retrieve_nodes(storage_dir, query, top_k=top_k)
)
```

**执行流程**：
1. 获取当前事件循环 `loop`
2. 将 `storage.retrieve_nodes()` 放入线程池执行
3. `await` 等待线程池返回结果
4. 期间事件循环可以处理其他请求

**关键理解**：`run_in_executor()` 不是并行执行多个检索，而是**不阻塞事件循环**。单个检索仍然在独立线程中顺序执行。

#### 好处

- **非阻塞**：检索操作不阻塞主事件循环，服务器可以同时处理多个用户请求
- **兼容性**：LlamaIndex 的检索 API 是同步的，通过 `run_in_executor()` 包装为异步
- **线程池复用**：使用默认线程池，不需要手动管理线程生命周期

---

### 3.6 SmartRetriever — 多查询检索

**所在文件**：`deeptutor/services/rag/smart_retriever.py`

#### 设计思路

当用户的查询比较复杂（如"请总结 RAG 的检索和排序策略"），单次检索可能无法覆盖所有相关内容。SmartRetriever 通过**生成多个查询变体**来提升召回率。

#### 执行流程

1. **查询生成**：`_generate_queries()` 使用 LLM 将用户上下文生成 N 个多样化的搜索查询
2. **并行检索**：使用 `asyncio.gather()` 并行执行多个查询，每个查询独立调用 `RAGService.search()`
3. **结果聚合**：`_aggregate()` 使用 LLM 将多个检索结果综合成一个连贯的摘要
4. **容错设计**：单个查询失败不影响其他查询，异常被 `return_exceptions=True` 捕获后跳过

---

## 四、组件如何协同工作

### 4.1 离线索引流程

```
用户上传文档
    │
    ▼
RAGService.initialize(kb_name, file_paths)
    │
    ▼
LlamaIndexPipeline.initialize()
    │
    ├── 1. _current_signature() → 获取当前 Embedding 配置签名
    ├── 2. resolve_storage_dir_for_write() → 确定索引存储目录
    ├── 3. _verify_embedding_connectivity() → 测试 Embedding 服务
    │
    ▼
storage.create_index(documents, storage_dir)
    │
    ├── 4. ingestion.documents_to_nodes(documents)
    │       ├── _has_precomputed_embedding() → 过滤预向量化节点
    │       ├── build_ingestion_pipeline() → 构建分块+向量化流水线
    │       └── pipeline.run(documents) → 执行分块和向量化
    │
    ├── 5. VectorStoreIndex(nodes) → 创建向量索引
    ├── 6. index.storage_context.persist() → 持久化到磁盘
    └── 7. retrievers.persist_bm25_retriever() → 持久化 BM25 索引
```

### 4.2 在线检索流程

```
用户提问："什么是反向传播？"
    │
    ▼
RAGAdapterTool.execute(query, kb_name)
    │
    ▼
RAGService.search(query, kb_name)
    │
    ├── 1. _get_pipeline() → 懒加载 LlamaIndexPipeline
    │
    ▼
LlamaIndexPipeline.search(query, kb_name)
    │
    ├── 2. _current_signature() → 获取当前 Embedding 签名
    ├── 3. resolve_storage_dir_for_read(kb_dir, signature) → 找到匹配版本
    ├── 4. run_in_executor(storage.retrieve_nodes()) → 线程池执行检索
    │       │
    │       ▼
    │   storage.retrieve_nodes()
    │       ├── load_index_from_storage() → 加载索引
    │       ├── _validate_persisted_embeddings() → 验证向量
    │       ├── build_retriever() → 构建混合检索器（向量+BM25+RRF）
    │       └── retriever.retrieve(query) → 执行检索
    │
    ├── 5. _nodes_to_result() → 转换结果格式
    └── 6. 返回 {query, answer, content, provider}
```

---

## 五、关键设计决策与局限性

### 5.1 版本化索引的核心局限：一次查询只搜一个版本

**源码证据**：

- `resolve_storage_dir_for_read()` 返回**单个**目录（`index_versioning.py:280`）
- `LlamaIndexPipeline.search()` 只调用**一次** `storage.retrieve_nodes()`（`pipeline.py:157`）
- `storage.retrieve_nodes()` 从**单个**目录加载索引（`storage.py:175`）

整条链路没有"遍历所有版本"或"跨版本合并"的逻辑。

#### 场景分析

假设：
- `version-1/`：DashScope（1024 维），存了 Reranker 策略文档
- `version-2/`：OpenAI（1536 维），存了 Hybrid 策略文档
- 当前 Embedding 配置：OpenAI

用户提问："请总结 RAG 流程"→ 需要同时召回 Reranker 和 Hybrid 的内容。

**实际发生的事**：
1. `signature = self._current_signature()` → OpenAI 签名
2. `resolve_storage_dir_for_read()` → 匹配到 `version-2/`
3. `retrieve_nodes(version-2/)` → 只检索 OpenAI 索引
4. **Reranker 策略文档（存在 version-1/ 中）完全不可见**
5. 返回的结果只有 Hybrid 策略的内容，Reranker 部分缺失

**系统不会报错**，用户也不会收到任何警告。只是结果不完整。

#### 为什么设计成这样？

这是一个**有意的工程权衡**，不是 bug。核心原因是**向量空间不可比**：

DashScope 生成的 1024 维向量和 OpenAI 生成的 1536 维向量，存在于完全不同的向量空间。它们的余弦相似度没有任何数学意义——就像用摄氏度和华氏度做加法一样。即使把两个版本的向量放在一起检索，计算出的相似度分数也是垃圾。

#### BM25 也无法跨版本

虽然 BM25（关键词检索）不依赖 Embedding 模型，但源码中 BM25 索引也是**按版本隔离**的（`retrievers.py:30`：`_bm25_persist_dir()` 返回 `storage_dir / "bm25_retriever"`）。所以 BM25 也无法跨版本。

#### 现实中的解决方案

| 方案 | 描述 | 代价 |
|------|------|------|
| **重新索引**（最常见） | 切换模型后，用新模型重新索引所有文档到同一个版本 | 需要重新处理所有文档 |
| **跨版本检索**（需自研） | 遍历所有版本执行检索，用 RRF 融合排名 | 工程量大，相似度分数不可比只能用排名融合 |
| **BM25 全局索引**（部分解决） | 将 BM25 从版本隔离改为全局共享 | 只解决精确匹配，语义检索仍无法跨版本 |

**面试回答**：切换 Embedding 模型后，旧索引的文档需要重新索引到新版本。系统通过 `_embedding_mismatch_warning()` 提醒用户当前配置与索引不匹配。如果要支持跨版本检索，可以考虑遍历所有版本执行检索并用 RRF 融合排名，但不同版本的相似度分数不可比，只能用排名融合。

---

### 5.2 增量更新的 BM25 代价

增量更新虽然不需要重新处理已有文档，但 **BM25 索引需要全量重建**。原因是 BM25 依赖全局词频统计（IDF），新增文档会改变整个词频分布，无法增量更新。

**工程影响**：如果知识库很大（如 10 万文档），增量更新的 BM25 重建可能成为瓶颈。

---

### 5.3 异步执行的线程安全

`run_in_executor()` 将检索操作放到线程池，但 LlamaIndex 的索引加载和检索不是线程安全的。当前设计通过**每个查询独立加载索引**来规避线程安全问题，代价是每次查询都有加载索引的开销。

---

## 六、面试题与参考答案

### 面试题 1：请描述 RAG 系统的整体架构

**参考答案：**

DeepTutor 的 RAG 系统采用**四层架构**：

1. **应用层**：RAGAdapterTool 和 SmartRetriever 通过 RAGService 调用检索
2. **服务层**：RAGService 作为统一入口，负责懒加载 Pipeline、结果标准化、事件通知
3. **管道层**：LlamaIndexPipeline 基于 LlamaIndex 实现索引创建和检索
4. **基础层**：EmbeddingAdapter 提供向量化，IndexVersioning 管理多版本索引

这种分层的好处是**解耦**——上层应用不需要关心 LlamaIndex 的实现细节，管道层可以替换不同的 RAG 后端。

---

### 面试题 2：向量检索和关键词检索如何融合？

**参考答案：**

我们实现了**混合检索（Hybrid Retrieval）**，结合两种检索方式的优势：

| 检索方式 | 优势 | 劣势 |
|---------|------|------|
| **向量检索** | 语义理解强，"机器学习"能匹配"ML" | 对精确术语不敏感 |
| **BM25** | 精确匹配强，速度快 | 无法理解同义词 |

**融合策略**：使用 LlamaIndex 的 `QueryFusionRetriever`，采用**倒数排名融合（RRF）**：

1. 向量检索返回 Top-K1 个结果（候选数量放大 2 倍）
2. BM25 检索返回 Top-K2 个结果（同样放大）
3. 根据排名计算融合分数：`score = Σ 1/(k + rank_i)`，k=60
4. 按融合分数排序，返回最终 Top-K

**工程亮点**：BM25 索引被持久化到 `bm25_retriever/` 子目录，避免每次重建；如果 BM25 依赖未安装，优雅降级到纯向量检索。

---

### 面试题 3：如何处理 Embedding 模型不匹配问题？

**参考答案：**

我们实现了**版本化索引**机制，核心是**签名匹配**：

1. **EmbeddingSignature**：每次索引时记录 Embedding 配置（provider + model + dimensions + base_url + api_version）的 SHA256 哈希值
2. **版本目录**：每个索引版本存储在独立的 `version-N/` 目录，目录下有 `meta.json` 记录签名
3. **查询时匹配**：`resolve_storage_dir_for_read()` 根据当前签名查找匹配的就绪版本

**局限性**：一次查询只搜一个版本。如果文档分散在不同版本中，切换模型后需要重新索引所有文档到新版本。系统通过 `_embedding_mismatch_warning()` 提醒用户。

**面试加分回答**：如果要支持跨版本检索，可以遍历所有版本执行检索，用 RRF 融合排名。但不同版本的向量空间不可比，相似度分数没有意义，只能用排名融合。

---

### 面试题 4：文档分块策略是什么？

**参考答案：**

我们使用 LlamaIndex 的 `SentenceSplitter` 进行分块，核心参数：
- `chunk_size`：默认 1024 字符
- `chunk_overlap`：默认 200 字符，保证上下文连贯性

**分块策略是语义感知的**：优先在句子边界处分割，保持段落完整性，重叠区域确保跨块语义不丢失。预向量化节点（如 ImageNode）跳过分块，直接进入索引。

---

### 面试题 5：如何保证检索质量？

**参考答案：**

| 维度 | 策略 |
|------|------|
| **分块质量** | 语义感知分块，保持上下文连贯 |
| **检索策略** | 混合检索（向量+BM25），取长补短 |
| **结果排序** | 倒数排名融合，综合考虑两种检索结果 |
| **质量验证** | 检索前验证 embedding 有效性 |
| **错误处理** | 优雅降级，提示用户重新索引 |

---

### 面试题 6：RAG 系统有哪些工程亮点？

**参考答案：**

1. **版本化索引**：签名机制解决 Embedding 模型切换问题，支持多版本共存
2. **混合检索 + RRF**：向量检索和 BM25 的融合，覆盖面更广
3. **异步执行**：CPU 密集型的检索操作通过 `run_in_executor()` 放到线程池，不阻塞主循环
4. **增量更新**：新增文档插入已有索引，不需要重建（但 BM25 需要全量重建）
5. **SmartRetriever**：多查询检索 + LLM 聚合，提升复杂问题的召回率

---

## 七、面试话术模板

### 开场白

"我负责的 RAG 系统采用四层架构设计，核心是基于 LlamaIndex 的混合检索管道。支持向量检索和 BM25 关键词检索的融合，通过倒数排名策略提升检索质量。系统还实现了版本化索引，通过签名机制解决 Embedding 模型切换导致的索引不兼容问题。"

### 技术细节

"签名机制将 Embedding 配置的 5 个字段（provider、model、dimension、base_url、api_version）哈希为 16 位十六进制字符串，作为版本标识。查询时自动匹配签名对应的版本。检索采用混合策略，向量检索和 BM25 各返回放大后的候选集，通过 RRF 融合排名。检索操作通过 `run_in_executor()` 放到线程池执行，不阻塞主事件循环。"

### 局限性（如果被追问）

"版本化索引的一个局限是每次查询只搜一个版本。如果文档分散在不同版本中，切换模型后需要重新索引。这是因为不同 Embedding 模型产生的向量空间不可比，混用会产生垃圾结果。如果要支持跨版本检索，可以遍历所有版本执行检索并用 RRF 融合排名，但只能用排名融合，不能用分数融合。"

---

## 八、相关文件索引

| 文件 | 说明 |
|------|------|
| `deeptutor/services/rag/service.py` | RAGService 统一入口 |
| `deeptutor/services/rag/pipelines/llamaindex/pipeline.py` | LlamaIndexPipeline 核心管道 |
| `deeptutor/services/rag/pipelines/llamaindex/ingestion.py` | 文档摄入（分块+向量化）|
| `deeptutor/services/rag/pipelines/llamaindex/retrievers.py` | 检索器组合（向量+BM25+RRF）|
| `deeptutor/services/rag/pipelines/llamaindex/storage.py` | 存储操作（索引加载+验证+增量插入）|
| `deeptutor/services/rag/pipelines/llamaindex/config.py` | 检索配置（profile+top_k）|
| `deeptutor/services/rag/index_versioning.py` | 版本化索引管理（签名+读写分离）|
| `deeptutor/services/rag/embedding_signature.py` | 签名构建（signature_from_config）|
| `deeptutor/services/rag/smart_retriever.py` | 多查询检索+LLM聚合 |
| `deeptutor/services/embedding/adapters/` | Embedding 适配器（OpenAI/DashScope/Cohere/Jina）|
| `deeptutor/tutorbot/agent/tools/deeptutor_tools.py` | RAGAdapterTool（Agent 工具调用）|

---

**文档版本**：v4.1（新增签名机制、增量更新、异步执行深度讲解；新增跨版本局限性分析；删除 event_sink 细节）
**更新日期**：2026-07-11
**作者**：DeepTutor Dev
