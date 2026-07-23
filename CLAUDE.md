# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

#重要注意事项：采用中文模式工作。

## 工作原则

- **CodeGraph 优先**：探索代码结构/项目架构时，优先使用 `codegraph_explore`（MCP）或 `codegraph explore`（Shell），避免 Grep/Read 循环浪费 tokens。仅在 CodeGraph 未覆盖或需要精确行号确认时才直接读文件。

## 增量点停开发模式（Incremental Point-Stop Mode）

**强制执行，不可跳过。** 当前项目处于 Exam Sprint 迁移的增量验证式开发阶段。

### 核心规则

1. **每完成一个小模块，必须停下来做浏览器实时调试**
   - 使用 Playwright MCP 工具（`browser_navigate` / `browser_snapshot` / `browser_take_screenshot`）或 Chrome DevTools MCP 工具进行浏览器验证
   - 不依赖频繁修改测试脚本来验收——浏览器可视化验证优先
   - 后端纯逻辑模块可用 pytest 验证，但前端/交互模块必须浏览器验证

2. **双层验证节奏**
   - 第一层：我自己通过浏览器调试确认功能正常
   - 第二层：向用户报告验证结果，等待用户手动确认后再推进下一步
   - **禁止未经验证就连续推进多个任务**

3. **停止信号**
   - 每完成一个任务，必须在输出中明确标注 `[点停] 任务 X 完成，等待验证` 或类似标记
   - 用户确认后才能开始下一个任务

4. **浏览器调试强制约束**
   - 前端相关改动必须调用 Playwright 或 Chrome DevTools MCP 工具进行浏览器验证
   - 前端开发服务器启动命令：`cd web && npm run dev`（端口 3000）
   - 后端服务器启动命令：`deeptutor serve --port 8001`

5. **开发顺序**
   - 前端优先：先实现前端 UI 骨架，用 mock 数据驱动，后端逐步填充真实逻辑
   - 原因：尽快在浏览器中实操验证，减少"写完后端才发现前端接不上"的返工

### 硬性原则（不可违反）

6. **前端报错优先排查接口一致性**
   - 前端出错时，先检查前端接收数据的接口/渲染方式是否符合后端返回格式
   - 确认接口一致后，优先在前端修改解决问题

7. **禁止主观推断，基于代码排查**
   - 遇到问题时，根据实际代码实现排查链路哪个环节出了问题
   - 可使用 CodeGraph、code-reviews 等 skills 排查项目结构/代码链路
   - 禁止并行分发 agent 探索

8. **问题记录在任务下方**
   - 每个任务执行中遇到的问题、修改变更，记录在该任务的 `### 变更记录` 子节
   - 下一个任务开始前，必须先阅读上一个任务的变更记录

9. **每完成一个任务必须 git push 保存版本**
   - 确认任务无误后，执行 git commit + push 再推进下一个任务
   - 推到 git 上的版本必须是正确无误的版本，方便回滚

10. **讨论达成共识前禁止开发**
    - 在用户明确同意方案之前，不得直接开始编写代码或执行开发任务
    - 必须先完成：方案设计 → 用户确认 → 再执行开发
    - 适用于所有新功能、架构改动、集成方案等非 trivial 任务

## 项目概述

DeepTutor 是一个原生智能代理学习伴侣，后端基于 Python 3.11+，前端基于 Next.js 16 / React 19。采用两层插件模型——单次调用的 **Tools（工具）** 和多阶段的 **Capabilities（能力）**——通过 CLI、WebSocket API 和 Python SDK 三种入口暴露。

## 开发命令

### Python 后端

```bash
# 开发安装（源码检出）
pip install -e ".[all]"          # 全部：服务器 + tutorbot + matrix + math-animator + 开发工具
pip install -e ".[dev]"          # 服务器 + 测试/lint 工具
pip install -e ".[tutorbot]"     # 服务器 + TutorBot 代理引擎

# 首次设置（交互式）
deeptutor init

# 运行后端服务器
deeptutor serve --port 8001

# CLI 用法
deeptutor chat                                   # 交互式 REPL
deeptutor run chat "解释傅里叶变换"               # 单次能力调用
deeptutor run deep_solve "求解 x^2=4" -t rag --kb my-kb
```

### 测试

```bash
pytest                                          # 运行所有测试
pytest tests/core/                              # 运行指定测试目录
pytest tests/core/test_context.py               # 运行单个测试文件
pytest -k "test_name"                           # 按名称运行特定测试
pytest -x                                       # 首次失败即停止
```

测试配置位于 `pyproject.toml` 的 `[tool.pytest.ini_options]` 下。测试目录：`tests/`。

### 前端 (web/)

```bash
cd web
npm install
npm run dev              # 开发服务器
npm run build            # 生产构建
npm run lint             # ESLint 检查
npm run test:node        # Node 测试
npm run i18n:check       # 国际化一致性 + 审计
npm run audit            # Playwright UI 审计
```

### 代码质量与 Lint

```bash
# Pre-commit（运行所有检查）
pre-commit install               # 仅首次
pre-commit run --all-files       # 运行所有钩子

# 单独工具
ruff check . --fix               # Python lint 并自动修复
ruff format .                    # Python 格式化
```

Ruff 配置位于 `pyproject.toml` 的 `[tool.ruff]` 下。行长度：100。目标版本：Python 3.11。

## 架构

### 入口点

- **CLI**：`deeptutor_cli/main.py`（Typer）
- **WebSocket API**：`deeptutor/api/routers/unified_ws.py`
- **Python SDK**：`deeptutor/app/`
- **前端**：`web/`（Next.js 16，app router）

### 核心运行时

```
入口点 → ChatOrchestrator → ToolRegistry (L1) + CapabilityRegistry (L2)
```

- `deeptutor/runtime/orchestrator.py` — ChatOrchestrator，统一入口，将 UnifiedContext 路由到选定的 Capability（默认为 `chat`）
- `deeptutor/runtime/registry/` — 工具 + 能力注册中心
- `deeptutor/core/context.py` — `UnifiedContext` 数据类
- `deeptutor/core/stream.py` + `stream_bus.py` — StreamEvent 协议 + 异步扇出
- `deeptutor/core/tool_protocol.py` — `BaseTool` + `ToolDefinition`
- `deeptutor/core/capability_protocol.py` — `BaseCapability` + `CapabilityManifest`

### 第一层 — Tools（工具）

LLM 按需选取的单功能工具。内置包装器位于 `deeptutor/tools/builtin/`。

上下文自动挂载工具（始终启用）：`rag`、`read_source`、`read_memory`、`write_memory`、`web_fetch`、`list_notebook`、`write_note`、`github`、`ask_user`。

用户可切换工具：`brainstorm`、`web_search`、`paper_search`、`code_execution`、`reason`。

### 第二层 — Capabilities（能力）

拥有一轮对话的多阶段管道。实现位于 `deeptutor/capabilities/`。

主要能力：`chat`（代理循环，默认）、`auto`（路由到其他能力）、`deep_solve`、`deep_question`、`deep_research`、`visualize`、`math_animator`。所有能力最终汇聚于 `deeptutor/capabilities/_shared.py` 中的 `emit_capability_result()`。

### 服务层

- `deeptutor/services/llm/` — LLM 提供商抽象（OpenAI、Anthropic、DashScope 等）
- `deeptutor/services/embedding/` — 嵌入适配器与注册中心
- `deeptutor/services/rag/` — RAG 管道（基于 LlamaIndex）
- `deeptutor/services/memory/` — 三层记忆系统（L1/L2/L3）
- `deeptutor/services/config/runtime_settings.py` — JSON 设置 + 进程环境变量覆盖（非 `.env` 文件）
- `deeptutor/services/prompt/` — PromptManager，从 `prompts/` 目录加载 YAML 提示词
- `deeptutor/services/session/` — 会话持久化
- `deeptutor/services/knowledge/` — 知识库管理

### TutorBot

位于 `deeptutor/tutorbot/` 的持久化自治 AI 代理引擎。支持多渠道集成（Telegram、Slack、Discord、钉钉、Zulip、Matrix 等）。安装命令：`pip install -e ".[tutorbot]"`。

### 前端 (web/)

Next.js 16 + React 19 + Tailwind CSS。通过 WebSocket（`/api/v1/ws`）与后端通信。前端作为静态资源打包在 `deeptutor` wheel 中。

### 配置

- 运行时设置位于 `data/user/settings/*.json`——项目根目录的 `.env` 文件被有意忽略
- 提示词为 YAML 文件，由 PromptManager 从 `deeptutor/**/prompts/*.yaml` 加载
- 能力国际化：`deeptutor/capabilities/prompts/{en,zh}/<name>.yaml`

## 编码规范

- Python：所有函数签名使用类型提示，使用 f-string，遵循 PEP 8（Ruff 强制执行），Google 风格文档字符串
- 行长度：100（Ruff 和 Black 一致）
- **代码必须加中文注释**：当前二开模式下，所有新增/修改代码需用中文注释说明意图（类、关键方法、复杂逻辑、非显而易见的分支）。注释解释"为什么"，而不是复述代码。
- **import 语句集中在文件顶端**：禁止将 import 包/类语句与逻辑代码混写。所有 import 提前放在文件顶部（标准库 → 第三方 → 本项目，分组排列），避免杂糅。仅当存在循环依赖需要延迟导入时，才允许函数内部 import 并注明原因。
- 前端：ESLint + Prettier，作用域限于 `web/` 目录
- 提交格式：`<类型>: <简短描述>`，类型包括 `feat`、`fix`、`docs`、`style`、`refactor`、`test`、`chore`
- PR 目标分支为 `dev`（非 `main`）
- Pre-commit 钩子：Ruff、Prettier、detect-secrets、Bandit、MyPy
