# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

#重要注意事项：采用中文模式工作。

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
- 前端：ESLint + Prettier，作用域限于 `web/` 目录
- 提交格式：`<类型>: <简短描述>`，类型包括 `feat`、`fix`、`docs`、`style`、`refactor`、`test`、`chore`
- PR 目标分支为 `dev`（非 `main`）
- Pre-commit 钩子：Ruff、Prettier、detect-secrets、Bandit、MyPy
