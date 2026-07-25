"""Built-in tool implementations and metadata."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
from typing import Any

from deeptutor.core.tool_protocol import BaseTool, ToolDefinition, ToolParameter, ToolResult
from deeptutor.exam.tools import PlanBuilderTool, TimePressureTool, WeakPointRankerTool
from deeptutor.tools.prompting import load_prompt_hints

logger = logging.getLogger(__name__)


class _PromptHintsMixin:
    """Shared prompt-hint loader for built-in tools."""

    def get_prompt_hints(self, language: str = "en"):
        return load_prompt_hints(self.name, language=language)


class BrainstormTool(_PromptHintsMixin, BaseTool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="brainstorm",
            description="Broadly explore multiple possibilities for a topic and give a short rationale for each.",
            parameters=[
                ToolParameter(
                    name="topic",
                    type="string",
                    description="The topic, goal, or problem to brainstorm about.",
                ),
                ToolParameter(
                    name="context",
                    type="string",
                    description="Optional supporting context, constraints, or background.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.brainstorm import brainstorm

        result = await brainstorm(
            topic=kwargs.get("topic", ""),
            context=kwargs.get("context", ""),
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            model=kwargs.get("model"),
            max_tokens=kwargs.get("max_tokens"),
            temperature=kwargs.get("temperature"),
        )
        return ToolResult(content=result.get("answer", ""), metadata=result)


class RAGTool(_PromptHintsMixin, BaseTool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="rag",
            description=(
                "Retrieve relevant passages from one of the knowledge bases the "
                "user attached to this turn. Call once per knowledge base you "
                "want to consult; the system runs them in parallel."
            ),
            parameters=[
                ToolParameter(name="query", type="string", description="Search query."),
                ToolParameter(
                    name="kb_name",
                    type="string",
                    description="Knowledge base to search. Must be one of the attached knowledge bases.",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.rag_tool import rag_search

        query = str(kwargs.get("query") or "").strip()
        if not query:
            raise ValueError("RAG query must be a non-empty string.")
        kb_name = str(kwargs.get("kb_name") or "").strip()
        if not kb_name:
            raise ValueError("RAG requires an explicit kb_name.")
        event_sink = kwargs.get("event_sink")
        extra_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key not in {"query", "kb_name", "event_sink"}
        }

        result = await rag_search(
            query=query,
            kb_name=kb_name,
            event_sink=event_sink,
            **extra_kwargs,
        )
        content = result.get("answer") or result.get("content", "")
        return ToolResult(
            content=content,
            sources=[{"type": "rag", "query": query, "kb_name": kb_name}],
            metadata=result,
        )


class WebSearchTool(_PromptHintsMixin, BaseTool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Search the web and return summarised results with citations.",
            parameters=[
                ToolParameter(name="query", type="string", description="Search query."),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.web_search import web_search

        query = kwargs.get("query", "")
        output_dir = kwargs.get("output_dir")
        verbose = kwargs.get("verbose", False)
        result = await asyncio.to_thread(
            web_search,
            query=query,
            output_dir=output_dir,
            verbose=verbose,
        )

        if isinstance(result, dict):
            answer = result.get("answer", "")
            citations = result.get("citations", [])
        else:
            answer = str(result)
            citations = []

        return ToolResult(
            content=answer,
            sources=[
                {"type": "web", "url": citation.get("url", ""), "title": citation.get("title", "")}
                for citation in citations
            ],
            metadata=result if isinstance(result, dict) else {"raw": answer},
        )


class CodeExecutionTool(_PromptHintsMixin, BaseTool):
    _CODEGEN_SYSTEM_PROMPT = """You are a Python code generator.

Convert the user's natural-language request into executable Python code only.

Rules:
- Output only Python code, with no markdown fences or explanation.
- Prefer standard library plus these common packages when useful: math, numpy, pandas, matplotlib, scipy, sympy.
- Print the final answer to stdout.
- Save plots or generated files to the current working directory.
- Keep the code focused on the requested computation or verification task.
"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code_execution",
            description="Turn a natural-language computation request into Python, run it in a restricted Python worker, and return the result.",
            parameters=[
                ToolParameter(
                    name="intent",
                    type="string",
                    description="Natural-language description of the computation or verification task.",
                ),
                ToolParameter(
                    name="code",
                    type="string",
                    description="Optional raw Python code to execute directly.",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Max execution time in seconds.",
                    required=False,
                    default=30,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.code_executor import run_code

        code = str(kwargs.get("code") or "").strip()
        intent = str(kwargs.get("intent") or kwargs.get("query") or "").strip()
        timeout = int(kwargs.get("timeout", 30) or 30)
        workspace_dir = kwargs.get("workspace_dir")
        feature = kwargs.get("feature")
        task_id = kwargs.get("task_id")
        session_id = kwargs.get("session_id")
        turn_id = kwargs.get("turn_id")

        if not code:
            if not intent:
                raise ValueError("code_execution requires either 'intent' or 'code'")
            code = await self._generate_code(intent)

        result = await run_code(
            language="python",
            code=code,
            timeout=timeout,
            workspace_dir=workspace_dir,
            feature=feature,
            task_id=task_id,
            session_id=session_id,
            turn_id=turn_id,
        )
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", 1)
        artifacts = result.get("artifacts", [])

        parts: list[str] = []
        if stdout:
            parts.append(stdout.strip())
        if stderr:
            label = "Error" if exit_code else "Stderr"
            parts.append(f"{label}:\n{stderr.strip()}")
        if artifacts:
            parts.append(f"Artifacts: {', '.join(str(item) for item in artifacts)}")
        if not parts:
            parts.append("Execution completed with no output.")

        metadata = {**result, "code": code, "intent": intent}
        return ToolResult(
            content="\n\n".join(parts),
            success=exit_code == 0,
            sources=[{"type": "code", "file": artifact} for artifact in artifacts],
            metadata=metadata,
        )

    async def _generate_code(self, intent: str) -> str:
        from deeptutor.services.llm import complete, get_token_limit_kwargs
        from deeptutor.services.llm.config import get_llm_config

        llm_config = get_llm_config()
        completion_kwargs: dict[str, Any] = {"temperature": 0.0}
        if getattr(llm_config, "model", None):
            completion_kwargs.update(get_token_limit_kwargs(llm_config.model, 1200))

        response = await complete(
            prompt=intent,
            system_prompt=self._CODEGEN_SYSTEM_PROMPT,
            model=llm_config.model,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            api_version=getattr(llm_config, "api_version", None),
            binding=getattr(llm_config, "binding", None),
            **completion_kwargs,
        )
        code = self._strip_markdown_fences(response)
        if not code.strip():
            raise ValueError("LLM returned empty code for code_execution")
        return code

    @staticmethod
    def _strip_markdown_fences(content: str) -> str:
        cleaned = content.strip()
        if not cleaned.startswith("```"):
            return cleaned

        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()


class ReasonTool(_PromptHintsMixin, BaseTool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="reason",
            description=(
                "Perform deep reasoning on a complex sub-problem using a dedicated LLM call. "
                "Use when the current context is insufficient for a confident answer."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The sub-problem to reason about.",
                ),
                ToolParameter(
                    name="context",
                    type="string",
                    description="Supporting context for reasoning.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.reason import reason

        result = await reason(
            query=kwargs.get("query", ""),
            context=kwargs.get("context", ""),
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            model=kwargs.get("model"),
            max_tokens=kwargs.get("max_tokens"),
            temperature=kwargs.get("temperature"),
        )
        return ToolResult(content=result.get("answer", ""), metadata=result)


class PaperSearchToolWrapper(_PromptHintsMixin, BaseTool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="paper_search",
            description="Search arXiv preprints by keyword and return concise metadata.",
            parameters=[
                ToolParameter(name="query", type="string", description="Search query."),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum papers to return.",
                    required=False,
                    default=3,
                ),
                ToolParameter(
                    name="years_limit",
                    type="integer",
                    description="Only include preprints from the last N years.",
                    required=False,
                    default=3,
                ),
                ToolParameter(
                    name="sort_by",
                    type="string",
                    description="Sort by relevance or submission date.",
                    required=False,
                    default="relevance",
                    enum=["relevance", "date"],
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.paper_search_tool import ArxivSearchTool

        try:
            papers = await ArxivSearchTool().search_papers(
                query=kwargs.get("query", ""),
                max_results=kwargs.get("max_results", 3),
                years_limit=kwargs.get("years_limit", 3),
                sort_by=kwargs.get("sort_by", "relevance"),
            )
        except Exception:
            return ToolResult(
                content="arXiv search is temporarily unavailable (rate-limited or network error). Please try again later.",
                sources=[],
                metadata={"provider": "arxiv", "papers": [], "error": True},
            )
        if not papers:
            return ToolResult(
                content="No arXiv preprints found for this query.",
                sources=[],
                metadata={"provider": "arxiv", "papers": []},
            )

        lines: list[str] = []
        for paper in papers:
            lines.append(f"**{paper['title']}** ({paper.get('year', '?')})")
            lines.append(f"Authors: {', '.join(paper.get('authors', []))}")
            lines.append(f"arXiv: {paper.get('arxiv_id', '')}")
            lines.append(f"URL: {paper.get('url', '')}")
            lines.append(f"Abstract: {paper.get('abstract', '')[:400]}")
            lines.append("")

        return ToolResult(
            content="\n".join(lines),
            sources=[
                {
                    "type": "paper",
                    "provider": "arxiv",
                    "url": paper.get("url", ""),
                    "title": paper.get("title", ""),
                    "arxiv_id": paper.get("arxiv_id", ""),
                }
                for paper in papers
            ],
            metadata={"provider": "arxiv", "papers": papers},
        )


class GeoGebraAnalysisTool(_PromptHintsMixin, BaseTool):
    """Analyze a math-problem image and generate GeoGebra visualization commands."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="geogebra_analysis",
            description=(
                "Analyze a math problem image, detect geometric elements, "
                "and generate validated GeoGebra commands for visualization. "
                "Requires an attached image."
            ),
            parameters=[
                ToolParameter(
                    name="question",
                    type="string",
                    description="The math problem text to analyze.",
                ),
                ToolParameter(
                    name="image_base64",
                    type="string",
                    description="Base64-encoded image (data URI or raw). Injected from attachments when called via function-calling.",
                    required=False,
                    default="",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.agents.vision_solver.vision_solver_agent import VisionSolverAgent
        from deeptutor.services.llm.config import get_llm_config

        question = kwargs.get("question", "")
        image_base64 = kwargs.get("image_base64", "")
        # language is server-injected from the user's session setting by the
        # chat pipeline; never accept an LLM-provided override.
        language = kwargs.get("language") or "zh"

        if not image_base64:
            return ToolResult(
                content="No image provided. This tool requires an image attachment.",
                success=False,
            )

        # VisionSolverAgent expects a fully-qualified ``data:image/<fmt>;base64,…``
        # URI for the OpenAI image_url shape. The chat pipeline injects this
        # form already, but defensively normalize for any other caller (or a
        # hallucinated kwarg) so we don't silently fall through 4 empty stages.
        if not image_base64.startswith("data:"):
            image_base64 = f"data:image/png;base64,{image_base64}"

        llm_config = get_llm_config()
        agent = VisionSolverAgent(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            language=language,
        )

        try:
            result = await agent.process(
                question_text=question,
                image_base64=image_base64,
            )
        except Exception as exc:
            logger.exception("GeoGebra analysis pipeline failed")
            return ToolResult(content=f"Analysis pipeline error: {exc}", success=False)

        if not result.get("has_image"):
            return ToolResult(content="No image was processed.", success=False)

        final_commands = result.get("final_ggb_commands", [])
        ggb_block = agent.format_ggb_block(final_commands)

        analysis = result.get("analysis_output") or {}
        constraints = analysis.get("constraints", [])
        relations = analysis.get("geometric_relations", [])
        summary_parts: list[str] = []
        if constraints:
            summary_parts.append(
                f"Constraints ({len(constraints)}): {json.dumps(constraints[:5], ensure_ascii=False)}"
            )
        if relations:
            relation_descriptions = [
                relation.get("description", str(relation))
                if isinstance(relation, dict)
                else str(relation)
                for relation in relations[:5]
            ]
            summary_parts.append(
                f"Relations ({len(relations)}): {json.dumps(relation_descriptions, ensure_ascii=False)}"
            )

        content_parts: list[str] = []
        if summary_parts:
            content_parts.append("\n".join(summary_parts))
        content_parts.append(ggb_block or "(No GeoGebra commands generated.)")

        return ToolResult(
            content="\n\n".join(content_parts),
            metadata={
                "has_image": True,
                "commands_count": len(final_commands),
                "final_ggb_commands": final_commands,
                "image_is_reference": result.get("image_is_reference", False),
                "bbox_elements": len((result.get("bbox_output") or {}).get("elements", [])),
                "constraints_count": len(constraints),
                "relations_count": len(relations),
                "reflection_issues": len(
                    (result.get("reflection_output") or {}).get("issues_found", [])
                ),
            },
        )


class ReadSourceTool(_PromptHintsMixin, BaseTool):
    """Load the full text of an attached Space source by its manifest id.

    The chat pipeline auto-enables this tool whenever a turn has any non-image
    attached source (notebook record, book reference, history session,
    question-bank entry, or document attachment). The per-turn full-text
    payload is carried in ``context.metadata["source_index"]`` as
    ``{source_id: str}`` and injected into the tool call by
    ``_augment_tool_kwargs``. The tool itself stays stateless.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_source",
            description=(
                "Load the full text of one attached source by id. Use ONLY when "
                "the preview shown in the Attached Sources manifest is "
                "insufficient to answer the user's question. The id must be "
                "copied verbatim from the manifest — do not invent ids. Do not "
                "call this on every source 'just in case'."
            ),
            parameters=[
                ToolParameter(
                    name="source_id",
                    type="string",
                    description=(
                        "The source identifier from the Attached Sources "
                        "manifest. Begins with one of: nb- (notebook record), "
                        "bk- (book reference), hs- (history session), qb- "
                        "(question-bank entry), at- (document attachment)."
                    ),
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        source_id = str(kwargs.get("source_id") or "").strip()
        if not source_id:
            return ToolResult(
                content="Error: source_id is required.",
                success=False,
            )
        source_index = kwargs.get("source_index")
        if not isinstance(source_index, dict) or not source_index:
            return ToolResult(
                content=("Error: no attached sources are available for this turn."),
                success=False,
            )
        full_text = source_index.get(source_id)
        if not full_text:
            available = ", ".join(sorted(source_index.keys()))
            return ToolResult(
                content=(
                    f"Error: unknown source_id {source_id!r}. "
                    f"Valid ids for this turn: {available or '(none)'}."
                ),
                success=False,
            )
        return ToolResult(
            content=str(full_text),
            metadata={"source_id": source_id, "char_count": len(str(full_text))},
        )


class ReadMemoryTool(_PromptHintsMixin, BaseTool):
    """Read the current user's L3 cross-surface Memory.

    Returns the concatenation of the four L3 markdown documents
    (recent / profile / scope / preferences). Multi-user-safe: paths
    resolve to the active user via the runtime's ContextVars.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_memory",
            description=(
                "Read the user's persistent memory: recent learning summary, "
                "user profile, knowledge scope, and explicit preferences. "
                "Use to personalise tone, depth, and examples — not on "
                "every turn, not for purely factual questions."
            ),
            parameters=[],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.services.memory import get_memory_store

        text = get_memory_store().read_l3_concat()
        return ToolResult(
            content=text,
            metadata={"char_count": len(text)},
        )


class WriteMemoryTool(_PromptHintsMixin, BaseTool):
    """Persist an explicit user preference into the L3 ``preferences.md``.

    The only chat-mode write into memory. Other memory docs are updated
    through the Memory workbench by the user manually. This tool is for
    moments when the user *explicitly* states a preference — speak it
    back to them only if natural, then call this with the substance.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_memory",
            description=(
                "Save an explicit user preference (writing style, language "
                "choice, depth, format) to long-term memory. Call ONLY when "
                "the user clearly states a preference — never speculate."
            ),
            parameters=[
                ToolParameter(
                    name="op",
                    type="string",
                    description="`add` for a new preference, `edit` to revise an existing one.",
                    enum=["add", "edit"],
                    required=True,
                ),
                ToolParameter(
                    name="text",
                    type="string",
                    description="The preference, in the user's own words where possible. ≤ 240 chars.",
                    required=True,
                ),
                ToolParameter(
                    name="target_id",
                    type="string",
                    description="Existing entry id (form `m_xxx`). Required for `edit`.",
                    required=False,
                ),
                ToolParameter(
                    name="reason",
                    type="string",
                    description="Optional one-line note shown in the Memory workbench.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.services.memory import get_memory_store
        from deeptutor.services.memory.trace import TraceEvent

        op = str(kwargs.get("op") or "").strip().lower()
        text = str(kwargs.get("text") or "").strip()
        target_id = kwargs.get("target_id")
        reason = kwargs.get("reason")

        if op not in {"add", "edit"}:
            return ToolResult(
                content=f"Error: op must be 'add' or 'edit', got {op!r}.", success=False
            )
        if not text:
            return ToolResult(
                content="Error: text is required and must be non-empty.", success=False
            )

        store = get_memory_store()
        # Emit an L1 trace so the preference's footnote points at a real event.
        event = TraceEvent.new(
            "chat",
            "preference_stated",
            {"op": op, "text": text, "target_id": target_id, "reason": reason},
        )
        await store.emit(event)

        report = await store.write_preference(
            op=op,  # type: ignore[arg-type]
            text=text,
            target_id=str(target_id).strip() if target_id else None,
            reason=str(reason).strip() if reason else None,
            trace_id=event.id,
        )
        if not report.accepted:
            return ToolResult(
                content=f"write_memory rejected: {report.reason}",
                success=False,
                metadata={"op": op},
            )
        entry_id = report.results[0].entry_id if report.results else None
        return ToolResult(
            content=f"preference {op}ed (entry={entry_id or target_id}).",
            metadata={"op": op, "entry_id": entry_id or target_id},
        )


class WebFetchTool(_PromptHintsMixin, BaseTool):
    """Fetch a specific URL and return readable markdown.

    The actual fetch / extract / safety logic lives in
    ``deeptutor.tools.web_fetch`` so this wrapper stays free of network
    code — easier to unit-test the BaseTool boilerplate without spinning
    up an httpx mock.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_fetch",
            description=(
                "Fetch a specific URL and extract readable content as "
                "markdown. Use this when the user shares a specific link; "
                "use `web_search` for general topic searches."
            ),
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="Full http:// or https:// URL.",
                ),
                ToolParameter(
                    name="max_chars",
                    type="integer",
                    description="Cap on the extracted text length; defaults to 50000.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.web_fetch import (
            DEFAULT_MAX_CHARS,
            fetch_url_as_markdown,
        )

        url = str(kwargs.get("url") or "").strip()
        if not url:
            return ToolResult(content="Error: url is required.", success=False)
        try:
            max_chars = int(kwargs.get("max_chars") or DEFAULT_MAX_CHARS)
        except (TypeError, ValueError):
            max_chars = DEFAULT_MAX_CHARS
        outcome = await fetch_url_as_markdown(url, max_chars=max_chars)
        if not outcome.ok:
            return ToolResult(
                content=outcome.error or "Fetch failed.",
                success=False,
                metadata={"url": url},
            )
        return ToolResult(
            content=outcome.markdown,
            sources=[{"type": "web", "url": outcome.url, "title": outcome.title}],
            metadata={
                "url": outcome.url,
                "title": outcome.title,
                "char_count": len(outcome.markdown),
                "truncated": outcome.truncated,
            },
        )


class ListNotebookTool(_PromptHintsMixin, BaseTool):
    """List the user's notebooks, or list the records inside one notebook.

    Two-mode discovery tool. Auto-mounted by the chat pipeline iff the
    user has at least one notebook. The tool itself is stateless; the
    chat pipeline supplies no extra context — list calls go straight
    against the per-user notebook manager.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_notebook",
            description=(
                "Discover the user's notebooks and the records inside "
                "them. Call with no arguments to list every notebook "
                "the user owns (id + name + record count). Call with a "
                "specific `notebook_id` to drill in and list its "
                "records (record_id + title + summary + timestamp). "
                "Use this BEFORE `write_note` in edit mode so you have "
                "valid record ids."
            ),
            parameters=[
                ToolParameter(
                    name="notebook_id",
                    type="string",
                    description=(
                        "Optional. When omitted, returns the notebook "
                        "index. When supplied, returns the records in "
                        "that notebook. Must be a valid id from the "
                        "notebook index — do not invent ids."
                    ),
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.list_notebook import list_notebooks_or_records

        outcome = list_notebooks_or_records(
            notebook_id=str(kwargs.get("notebook_id") or ""),
        )
        if not outcome.ok:
            return ToolResult(content=outcome.error, success=False)
        return ToolResult(
            content=outcome.text,
            metadata=outcome.summary or {},
        )


class WriteNoteTool(_PromptHintsMixin, BaseTool):
    """Create OR edit a notebook record from the chat agent.

    Two modes mirror what a human sees in the notebook UI:

    * ``append`` — create a new record in a notebook (the model picks
      a title; the body defaults to the actual chat transcript built
      from injected conversation history, or to an agent-authored
      markdown body if ``content`` is explicitly provided).
    * ``edit`` — patch an existing record's title / body / summary.
      Requires a known ``record_id`` (obtained via ``list_notebook``).

    Auto-mounted only when the user has at least one notebook. The
    pipeline injects ``conversation_history`` + ``current_user_message``
    so the model never has to fabricate the saved chat.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_note",
            description=(
                "Save or edit a notebook record. mode='append' creates "
                "a NEW record (default body = the actual recent chat "
                "transcript built by the tool; pass `content` instead "
                "to save an agent-authored markdown body). "
                "mode='edit' patches an existing record's title / body "
                "/ summary — `record_id` is required (call `list_notebook` "
                "first to discover valid ids)."
            ),
            parameters=[
                ToolParameter(
                    name="mode",
                    type="string",
                    description="'append' (new record) or 'edit' (patch existing).",
                    enum=["append", "edit"],
                ),
                ToolParameter(
                    name="notebook_id",
                    type="string",
                    description=(
                        "Id of the target notebook from the schema enum (do not invent ids)."
                    ),
                ),
                ToolParameter(
                    name="record_id",
                    type="string",
                    description=("Required for mode='edit'. Discover with `list_notebook` first."),
                    required=False,
                ),
                ToolParameter(
                    name="title",
                    type="string",
                    description=(
                        "For append: required, short descriptive title. "
                        "For edit: optional new title (leave empty to "
                        "keep the existing one)."
                    ),
                    required=False,
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description=(
                        "For append: optional agent-authored markdown body "
                        "(when omitted the tool inserts the real Q&A "
                        "transcript itself, the recommended default). "
                        "For edit: replacement body (leave empty to keep "
                        "the existing body)."
                    ),
                    required=False,
                ),
                ToolParameter(
                    name="turns_to_include",
                    type="string",
                    description=(
                        "Append mode only. Number of recent user+assistant "
                        "turns to render into the transcript body. Pass an "
                        "integer as a string (e.g. '3') or 'all' to include "
                        "every turn currently in scope. Ignored when "
                        "`content` is provided. Default '3'."
                    ),
                    required=False,
                ),
                ToolParameter(
                    name="note",
                    type="string",
                    description=(
                        "Optional one-paragraph commentary. In append "
                        "mode it's prepended above the transcript; in "
                        "edit mode it replaces the record's summary."
                    ),
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.write_note import write_note

        outcome = write_note(
            mode=str(kwargs.get("mode") or ""),
            notebook_id=str(kwargs.get("notebook_id") or ""),
            record_id=str(kwargs.get("record_id") or ""),
            title=str(kwargs.get("title") or ""),
            content=str(kwargs.get("content") or ""),
            turns_to_include=kwargs.get("turns_to_include") or 3,
            note=str(kwargs.get("note") or ""),
            conversation_history=kwargs.get("conversation_history") or [],
            current_user_message=str(kwargs.get("current_user_message") or ""),
        )
        if not outcome.ok:
            return ToolResult(content=outcome.error, success=False)
        action = "Saved new record" if outcome.mode == "append" else "Updated record"
        return ToolResult(
            content=(
                f"{action} in notebook {outcome.notebook_name!r} (record id: {outcome.record_id})."
            ),
            metadata={
                "mode": outcome.mode,
                "record_id": outcome.record_id,
                "notebook_id": outcome.notebook_id,
                "notebook_name": outcome.notebook_name,
            },
        )


class GithubTool(_PromptHintsMixin, BaseTool):
    """Read-only GitHub queries via `gh`. Always auto-mounted; the
    underlying call gracefully reports "gh unavailable" when the CLI
    isn't installed on the server."""

    _ALLOWED_QUERY_TYPES = ("pr", "issue", "run", "repo", "api")

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github",
            description=(
                "Read-only queries against GitHub PRs / issues / repos / "
                "CI runs via the gh CLI. This tool cannot write — no "
                "comments, no closes, no merges."
            ),
            parameters=[
                ToolParameter(
                    name="query_type",
                    type="string",
                    description=("One of 'pr', 'issue', 'run', 'repo', 'api'."),
                    enum=list(_ALLOWED_QUERY_TYPES := ("pr", "issue", "run", "repo", "api")),
                ),
                ToolParameter(
                    name="target",
                    type="string",
                    description=(
                        "owner/repo[#number] or full URL for pr/issue; "
                        "owner/repo for run/repo; gh-api relative path "
                        "for api."
                    ),
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.github_query import run_github_query

        outcome = await run_github_query(
            query_type=str(kwargs.get("query_type") or ""),
            target=str(kwargs.get("target") or ""),
        )
        if not outcome.ok:
            return ToolResult(
                content=outcome.error,
                success=False,
                metadata={"query_type": outcome.query_type, "target": outcome.target},
            )
        return ToolResult(
            content=outcome.output,
            sources=[
                {
                    "type": "github",
                    "query_type": outcome.query_type,
                    "target": outcome.target,
                }
            ],
            metadata={
                "query_type": outcome.query_type,
                "target": outcome.target,
            },
        )


class AskUserTool(_PromptHintsMixin, BaseTool):
    """Pause the turn mid-loop to ask the user a clarifying question.

    Returns ``pause_for_user`` carrying the structured question payload.
    The chat pipeline halts the agentic loop after this call, surfaces
    the question + options as a card in the chat UI, and **waits for
    the user's reply on the same turn**. When the reply arrives the
    loop resumes with the user's answer substituted into this tool's
    result body — so subsequent iterations see "User answered: <text>"
    as the matching ``role=tool`` content and can act on it. The user
    can also abort the wait at any time via the composer's stop button
    (which cancels the whole turn).
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="ask_user",
            description=(
                "Pause the conversation to ask the user 1-3 clarifying "
                "questions in one batch. The frontend renders all "
                "questions on a single card with tabs the user can "
                "switch between; the user answers each, then submits "
                "once. The turn does NOT end — when the answers arrive "
                "the agentic loop resumes with them as this tool's "
                "result. Use sparingly: only when intent is genuinely "
                "ambiguous and progress without clarification is unsafe."
            ),
            parameters=[
                ToolParameter(
                    name="questions",
                    type="array",
                    description=(
                        "1-3 questions to ask in one card. Each item: "
                        "{prompt: 'question text', options?: ['A','B'], "
                        "id?: 'stable-id', allow_free_text?: true, "
                        "placeholder?: 'hint for free input'}. Each "
                        "question may have its own option chips; the "
                        "user can also type freely."
                    ),
                    required=False,
                    items={
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "options": {"type": "array", "items": {"type": "string"}},
                            "id": {"type": "string"},
                            "allow_free_text": {"type": "boolean"},
                            "placeholder": {"type": "string"},
                        },
                    },
                ),
                ToolParameter(
                    name="intro",
                    type="string",
                    description=(
                        "Optional one-line lead-in shown above the "
                        "questions (e.g. 'To tailor the research, please "
                        "answer:')."
                    ),
                    required=False,
                ),
                # Legacy single-question shape — still accepted; the tool
                # auto-wraps it into a one-element ``questions`` list so
                # older prompts keep working unchanged.
                ToolParameter(
                    name="question",
                    type="string",
                    description=(
                        "Legacy single-question shorthand. Prefer "
                        "``questions``. If supplied alone, wrapped into "
                        "one question with ``options``."
                    ),
                    required=False,
                ),
                ToolParameter(
                    name="options",
                    type="array",
                    description=(
                        "Legacy option list paired with ``question``. "
                        "Ignored when ``questions`` is provided."
                    ),
                    required=False,
                    items={"type": "string"},
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        from deeptutor.tools.ask_user import build_ask_user_payload

        payload, err = build_ask_user_payload(
            questions=kwargs.get("questions"),
            intro=kwargs.get("intro"),
            question=kwargs.get("question"),
            options=kwargs.get("options"),
        )
        if payload is None:
            return ToolResult(content=err or "Invalid ask_user arguments.", success=False)

        payload_dict = payload.to_dict()
        prompts = ", ".join(q.prompt for q in payload.questions)
        return ToolResult(
            # The placeholder content is overwritten by the pipeline
            # once the user's reply arrives; the model never sees this
            # literal string on a normal flow. It only surfaces if the
            # runtime crashes mid-pause (in which case the LLM at least
            # gets a coherent log entry).
            content=f"[awaiting user reply to: {prompts}]",
            metadata={"ask_user": payload_dict},
            pause_for_user=payload_dict,
        )


class VideoUnderstandTool(_PromptHintsMixin, BaseTool):
    """视频理解工具：提取关键帧 + 转录语音，再用多模态 LLM 图文结合分析。

    架构共识（详见 docs/superpowers/specs/2026-07-22-video-understand-tool-design.md）：

    * 工具内部调用 claude-real-video 抽取关键帧 + Whisper 转录文本，
      再把两者喂给可配置的多模态 LLM。
    * 多模态 LLM 返回「自然语言 + JSON」分析结果，这段文本就是
      调用方 Agent_Loop 消费的 ToolResult.content。
    * tool 消息体是纯文本（tool_dispatch 把 content 塞进 role=tool 的
      字符串），因此图片永远不会回传给调用方——它们只在本工具内部的
      多模态调用里存活。

    本骨架阶段只把工具挂进注册表、execute 留空，目的是先验证注册 +
    prompt-hint 渲染。真实管线（claude-real-video 抽取、多模态分析、
    临时文件管理）由后续任务填充。
    """

    def get_definition(self) -> ToolDefinition:
        # schema 的 description 面向 LLM function-calling，保持英文以与
        # 项目其他内置工具一致（zh/en 细化引导放在 hints YAML）。
        return ToolDefinition(
            name="video_understand",
            description=(
                "Understand a video's content: extract key frames and "
                "transcribe speech, then analyse them together with a "
                "multimodal LLM (corrects transcription term errors from "
                "the on-screen text). Use when the user uploads a video or "
                "asks to understand / summarise / analyse a video."
            ),
            parameters=[
                ToolParameter(
                    name="video_path",
                    type="string",
                    description="Path to the video file to understand.",
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Transcription language hint (default 'zh').",
                    required=False,
                    default="zh",
                ),
                ToolParameter(
                    name="max_frames",
                    type="integer",
                    description="Maximum number of key frames to extract (default 72).",
                    required=False,
                    default=72,
                ),
                ToolParameter(
                    name="analysis_prompt",
                    type="string",
                    description="Optional custom analysis prompt.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        # —— 参数解析（language/max_frames 有默认值，video_path 必填）——
        video_path = str(kwargs.get("video_path") or "").strip()
        if not video_path:
            # 缺少必填的视频路径，直接返回失败。
            return ToolResult(
                content="Error: video_path is required.",
                success=False,
            )
        language = str(kwargs.get("language") or "zh").strip() or "zh"
        try:
            max_frames = int(kwargs.get("max_frames") or 72)
        except (TypeError, ValueError):
            max_frames = 72

        # —— 临时目录：基于视频绝对路径的哈希（任务2 策略）——
        # 任务4 会升级为会话级 {session_id}/（需改 chat pipeline 注入 session_id）。
        # 延迟 import get_runtime_data_root：顶端 import 会触发
        # runtime.__init__ → orchestrator → tool_registry → tools.builtin 的循环导入。
        from deeptutor.runtime.home import get_runtime_data_root

        abs_path = os.path.abspath(video_path)
        path_hash = hashlib.md5(abs_path.encode("utf-8")).hexdigest()[:12]
        out_dir = str(get_runtime_data_root() / "temp" / "video_understand" / path_hash)

        # —— 延迟 import：claude_real_video 是可选外部依赖 ——
        # 放顶端会导致未安装时整个 tools 模块 import 失败（连带 rag/web_search 全挂），
        # 故按"可选依赖"豁免条款放在函数内部，未安装时本工具优雅降级。
        try:
            from claude_real_video import process
        except ImportError as exc:
            return ToolResult(
                content=f"claude-real-video 未安装，无法处理视频：{exc}",
                success=False,
                metadata={"video_path": video_path, "error": "missing_dependency"},
            )

        # —— 调用 process()：同步阻塞函数（内部 subprocess），用 to_thread 不阻塞事件循环 ——
        try:
            result = await asyncio.to_thread(
                process,
                src=video_path,
                out_dir=out_dir,
                max_frames=max_frames,
                lang=language,
                do_transcribe=True,
                overwrite=True,
            )
        except Exception as exc:
            # 缺少 ffmpeg/whisper、视频损坏等情况都会在这里抛出，统一降级不崩溃。
            logger.exception("video_understand 提取失败")
            return ToolResult(
                content=f"视频处理失败：{exc}",
                success=False,
                metadata={"video_path": video_path, "out_dir": out_dir, "error": str(exc)},
            )

        # —— 删除 process() 复制的源视频副本，节省磁盘（用户持有原始文件）——
        source_copy = os.path.join(result.out_dir, "source.mp4")
        if os.path.exists(source_copy):
            try:
                os.remove(source_copy)
            except OSError:
                logger.warning("无法删除源视频副本：%s", source_copy)

        # —— 读取转录文本，拼装 content ——
        # 任务2 只做提取；任务3 会用多模态 LLM 分析关键帧，替换这段 content。
        transcript_text = ""
        if result.transcript_path and os.path.exists(result.transcript_path):
            try:
                with open(result.transcript_path, encoding="utf-8") as f:
                    transcript_text = f.read().strip()
            except OSError:
                logger.warning("无法读取转录文件：%s", result.transcript_path)

        content_parts: list[str] = [
            "[video_understand] 提取完成",
            f"- 时长：{result.duration}秒 | 关键帧：{result.frame_count}张",
            f"- 产物目录：{result.out_dir}",
        ]
        if transcript_text:
            content_parts.append(
                f"\n--- 转录文本（{len(transcript_text)}字符）---\n{transcript_text}"
            )
        else:
            content_parts.append("\n（无转录文本——视频可能无音轨，或 whisper 未安装）")

        return ToolResult(
            content="\n".join(content_parts),
            metadata={
                "video_path": video_path,
                "out_dir": result.out_dir,
                "frames_dir": result.frames_dir,
                "frame_count": result.frame_count,
                "duration": result.duration,
                "transcript_path": result.transcript_path,
                "frames_json_path": result.frames_json_path,
                "has_transcript": bool(transcript_text),
            },
        )

    def _build_multimodal_content(self, out_dir: str) -> list[dict[str, Any]]:
        """时间对齐 + 组装多模态图文流（共识10：按视频时间顺序交错排列图文）。

        读 out_dir 下的 frames.json（每帧 timestamp_sec）与 transcript.json
        （每段 start/end），用双指针 O(F+S) 为每帧匹配时间上最近的转录段，
        再按视频时间顺序交错输出「时间标注 + 帧图(base64) + 对应转录」，
        让多模态 LLM 看到一条贴近人类"边看画面边听讲解"学习顺序的图文流。

        Args:
            out_dir: 任务2 产物目录（含 frames/、frames.json、transcript.json）

        Returns:
            OpenAI 多模态 content parts 数组，元素形如
            ``{"type": "text", ...}`` / ``{"type": "image_url", ...}``。
        """
        # —— 读取帧时间戳（frames.json 已按时间排序）——
        frames_path = os.path.join(out_dir, "frames.json")
        frames: list[dict[str, Any]] = []
        if os.path.exists(frames_path):
            with open(frames_path, encoding="utf-8") as f:
                frames = (json.load(f) or {}).get("frames", [])

        # —— 读取转录段（transcript.json 的 segments 带 start/end）——
        transcript_json_path = os.path.join(out_dir, "transcript.json")
        segments: list[dict[str, Any]] = []
        if os.path.exists(transcript_json_path):
            with open(transcript_json_path, encoding="utf-8") as f:
                segments = (json.load(f) or {}).get("segments", [])

        content_parts: list[dict[str, Any]] = []
        # —— 双指针对齐：seg_idx 单调推进，总推进次数 <= len(segments)，整体 O(F+S) ——
        # 思路：frames 与 segments 都按时间排序；对每帧 t，把 seg_idx 推进到
        # "start <= t 的最后一段"，该段即时间上最接近 t 的转录段（覆盖或最近前段）。
        seg_idx = 0
        for frame in frames:
            t = float(frame.get("timestamp_sec", 0) or 0)
            while (
                seg_idx < len(segments) - 1
                and float(segments[seg_idx + 1].get("start", float("inf"))) <= t
            ):
                seg_idx += 1
            matched_text = ""
            if segments:
                matched_text = str(segments[seg_idx].get("text", "") or "")

            # —— 时间标注 ——
            ts = str(frame.get("timestamp", "") or "")
            if ts:
                content_parts.append({"type": "text", "text": f"⏱ [{ts}]"})

            # —— 帧图 base64（OpenAI image_url 格式）——
            frame_file = str(frame.get("file", "") or "")
            frame_path = os.path.join(out_dir, "frames", frame_file)
            if frame_file and os.path.exists(frame_path):
                with open(frame_path, "rb") as fp:
                    img_b64 = base64.b64encode(fp.read()).decode("ascii")
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    }
                )

            # —— 对应转录 ——
            if matched_text:
                content_parts.append({"type": "text", "text": f"📝 {matched_text}"})

        return content_parts


BUILTIN_TOOL_TYPES: tuple[type[BaseTool], ...] = (
    BrainstormTool,
    RAGTool,
    WebSearchTool,
    CodeExecutionTool,
    ReasonTool,
    PaperSearchToolWrapper,
    ReadSourceTool,
    ReadMemoryTool,
    WriteMemoryTool,
    WebFetchTool,
    ListNotebookTool,
    WriteNoteTool,
    GithubTool,
    AskUserTool,
    VideoUnderstandTool,
    TimePressureTool,
    WeakPointRankerTool,
    PlanBuilderTool,
)

# Tools whose implementation is parked while we redesign them. NOT loaded
# into the runtime registry — the chat agent cannot invoke these — but the
# settings page surfaces them with a "Coming soon" badge so users see the
# capability is on the roadmap. Re-add to ``BUILTIN_TOOL_TYPES`` when ready
# to ship.
COMING_SOON_TOOL_TYPES: tuple[type[BaseTool], ...] = (GeoGebraAnalysisTool,)

BUILTIN_TOOL_NAMES: tuple[str, ...] = tuple(tool_type().name for tool_type in BUILTIN_TOOL_TYPES)

COMING_SOON_TOOL_NAMES: tuple[str, ...] = tuple(
    tool_type().name for tool_type in COMING_SOON_TOOL_TYPES
)

# Tools the user can switch on/off from /settings/tools ("体验增强" /
# Experience Enhancement). Everything else in BUILTIN_TOOL_NAMES is mounted
# automatically by the chat pipeline under per-tool context gates and is
# locked-on from the user's perspective. Ordering here is the canonical
# display order for the settings page.
USER_TOGGLEABLE_TOOL_NAMES: tuple[str, ...] = (
    "brainstorm",
    "web_search",
    "paper_search",
    "code_execution",
    "reason",
)

TOOL_ALIASES: dict[str, tuple[str, dict[str, Any]]] = {
    "rag_hybrid": ("rag", {"mode": "hybrid"}),
    "rag_naive": ("rag", {"mode": "naive"}),
    "rag_search": ("rag", {}),
    "code_execute": ("code_execution", {}),
    "run_code": ("code_execution", {}),
}

__all__ = [
    "BUILTIN_TOOL_NAMES",
    "BUILTIN_TOOL_TYPES",
    "COMING_SOON_TOOL_NAMES",
    "COMING_SOON_TOOL_TYPES",
    "TOOL_ALIASES",
    "USER_TOGGLEABLE_TOOL_NAMES",
    "AskUserTool",
    "BrainstormTool",
    "CodeExecutionTool",
    "GeoGebraAnalysisTool",
    "GithubTool",
    "ListNotebookTool",
    "PaperSearchToolWrapper",
    "RAGTool",
    "ReadMemoryTool",
    "ReadSourceTool",
    "ReasonTool",
    "WebFetchTool",
    "WebSearchTool",
    "WriteMemoryTool",
    "WriteNoteTool",
    "VideoUnderstandTool",
]
