"""Parallel research agent using Claude Agent SDK.

Uses the official Claude Agent SDK for parallel subagent orchestration.
Each subagent specializes in a different knowledge source (RAG, AWS, web).

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import anyio

from vector_rag_gui.core.agent import (
    OBSIDIAN_KNOWLEDGE_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    ResearchResult,
    Source,
    TokenUsage,
)


class SDKModelChoice(Enum):
    """Available model choices for SDK agent."""

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


# System prompts for specialized subagents
RAG_SUBAGENT_PROMPT = """You are a local knowledge specialist. Your job is to:
1. Search the local vector stores for relevant information
2. Extract the most pertinent findings
3. Return a concise summary with source references

Focus on internal documentation, notes, and code examples.
Be factual and cite specific sources."""

AWS_SUBAGENT_PROMPT = """You are an AWS documentation specialist. Your job is to:
1. Search AWS documentation for official guidance
2. Extract best practices and recommendations
3. Return a concise summary with documentation references

Focus on authoritative AWS guidance and official best practices."""

WEB_SUBAGENT_PROMPT = """You are a web research specialist. Your job is to:
1. Search the web for current information
2. Identify credible and relevant sources
3. Return a concise summary with source citations

Focus on recent, authoritative sources."""

FILE_SUBAGENT_PROMPT = """You are a codebase specialist. Your job is to:
1. Search through files for relevant code and documentation
2. Extract pertinent code snippets and patterns
3. Return a concise summary with file references

Focus on actual code implementations and inline documentation."""


@dataclass
class SubagentResult:
    """Result from a specialized subagent."""

    source_type: str  # "local", "aws", "web", "file"
    query: str
    findings: str
    error: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


class SDKResearchAgent:
    """Research agent using Claude Agent SDK with parallel subagent execution.

    Implements map-reduce pattern:
    - MAP: Parallel execution of specialized subagents
    - REDUCE: Synthesis into structured research document
    """

    def __init__(
        self,
        model_choice: SDKModelChoice = SDKModelChoice.SONNET,
        custom_prompt: str = "",
        obsidian_mode: bool = False,
    ) -> None:
        """Initialize SDK research agent.

        Args:
            model_choice: Model to use for final synthesis (HAIKU, SONNET, OPUS)
            custom_prompt: Optional custom instructions to append to system prompt
            obsidian_mode: Enable Obsidian-aware behavior with vault knowledge
        """
        self.model_choice = model_choice
        self.custom_prompt = custom_prompt
        self.obsidian_mode = obsidian_mode
        self._local_stores: list[str] = []

    async def research(
        self,
        query: str,
        use_local: bool = True,
        use_aws: bool = False,
        use_web: bool = False,
        local_stores: list[str] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> ResearchResult:
        """Execute parallel research using SDK subagents.

        Core tools (always enabled):
        - glob_files, grep_files, read_file (file search)
        - todo_read, todo_write (task tracking)

        Optional tools:
        - use_local: Local RAG vector store search (default: True)
        - use_aws: AWS documentation search (default: False)
        - use_web: Web tools - web_search, web_fetch, extended web (default: False)

        Args:
            query: Research question or topic
            use_local: Enable local vector store search (default True)
            use_aws: Enable AWS documentation search (default False)
            use_web: Enable web tools (web_search, web_fetch, web) (default False)
            local_stores: List of local vector store names to query
            on_progress: Optional callback for progress updates

        Returns:
            ResearchResult with synthesized document and metadata
        """
        if local_stores is None:
            local_stores = ["obsidian-knowledge-base"]

        self._local_stores = local_stores

        def emit_progress(message: str) -> None:
            if on_progress:
                on_progress(message)

        emit_progress("Initializing parallel research agents...")

        # === MAP PHASE: Execute subagents in parallel ===
        tasks: list[tuple[str, Any]] = []

        # CORE: File search (glob, grep, read) - always enabled
        emit_progress("Spawning file search agent...")
        tasks.append(("file", self._run_file_subagent(query)))

        # OPTIONAL: Local RAG (default enabled)
        if use_local:
            for store in local_stores:
                emit_progress(f"Spawning RAG agent for {store}...")
                tasks.append(("local", self._run_rag_subagent(query, store)))

        # OPTIONAL: AWS documentation
        if use_aws:
            emit_progress("Spawning AWS documentation agent...")
            tasks.append(("aws", self._run_aws_subagent(query)))

        # OPTIONAL: Web tools (web_search, web_fetch, extended web research)
        if use_web:
            emit_progress("Spawning web search agent...")
            tasks.append(("websearch", self._run_websearch_subagent(query)))
            emit_progress("Spawning extended web research agent...")
            tasks.append(("web", self._run_web_subagent(query)))

        emit_progress(f"Running {len(tasks)} agents in parallel...")

        # Execute all subagents concurrently
        results: list[SubagentResult] = []
        async with anyio.create_task_group() as tg:
            result_queue: list[SubagentResult] = []

            async def run_and_collect(source_type: str, coro: Any, idx: int) -> None:
                result = await coro
                result_queue.append(result)
                emit_progress(f"Agent {source_type} completed ({idx + 1}/{len(tasks)})")

            for idx, (source_type, coro) in enumerate(tasks):
                tg.start_soon(run_and_collect, source_type, coro, idx)

            # Wait for all to complete (implicit via task group context)

        results = result_queue

        # Build sources from results
        sources = self._build_sources(results)

        # === REDUCE PHASE: Synthesize findings ===
        emit_progress("Synthesizing findings...")

        synthesis_result = await self._synthesize(query, results, emit_progress)

        return ResearchResult(
            document=synthesis_result["document"],
            sources=sources,
            usage=synthesis_result["usage"],
            model=self.model_choice,  # type: ignore
            model_id=synthesis_result["model_id"],
            query=query,
        )

    async def _run_rag_subagent(self, query: str, store: str) -> SubagentResult:
        """Run RAG subagent to search local vector store.

        Args:
            query: Search query
            store: Vector store name

        Returns:
            SubagentResult with findings
        """
        try:
            from vector_rag_gui.tools.vector_rag import search_local_knowledge

            # Run sync tool in thread pool
            result = await anyio.to_thread.run_sync(
                lambda: search_local_knowledge(query=query, store=store, top_k=5)
            )

            return SubagentResult(
                source_type="local",
                query=query,
                findings=result,
                raw_data={"store": store},
            )
        except Exception as e:
            return SubagentResult(
                source_type="local",
                query=query,
                findings=json.dumps({"error": str(e), "results": []}),
                error=str(e),
                raw_data={"store": store},
            )

    async def _run_aws_subagent(self, query: str) -> SubagentResult:
        """Run AWS documentation subagent.

        Args:
            query: Search query

        Returns:
            SubagentResult with findings
        """
        try:
            from vector_rag_gui.tools.aws_knowledge import search_aws_docs

            result = await anyio.to_thread.run_sync(lambda: search_aws_docs(query=query))

            return SubagentResult(
                source_type="aws",
                query=query,
                findings=result,
            )
        except Exception as e:
            return SubagentResult(
                source_type="aws",
                query=query,
                findings=json.dumps({"error": str(e), "results": []}),
                error=str(e),
            )

    async def _run_websearch_subagent(self, query: str) -> SubagentResult:
        """Run core web search subagent (always enabled).

        Uses search_web for Google search results.

        Args:
            query: Search query

        Returns:
            SubagentResult with findings
        """
        try:
            from vector_rag_gui.tools.web_search import search_web

            findings: list[dict[str, Any]] = []

            # Web search
            search_result = await anyio.to_thread.run_sync(lambda: search_web(query=query))
            try:
                search_data = json.loads(search_result)
                findings.append(
                    {
                        "type": "web_search",
                        "query": query,
                        "data": search_data,
                    }
                )
            except json.JSONDecodeError:
                findings.append(
                    {
                        "type": "web_search",
                        "query": query,
                        "data": {"raw": search_result},
                    }
                )

            return SubagentResult(
                source_type="websearch",
                query=query,
                findings=json.dumps({"results": findings}),
            )
        except Exception as e:
            return SubagentResult(
                source_type="websearch",
                query=query,
                findings=json.dumps({"error": str(e), "results": []}),
                error=str(e),
            )

    async def _run_web_subagent(self, query: str) -> SubagentResult:
        """Run extended web research subagent (optional).

        Performs deeper web research with URL fetching.

        Args:
            query: Search query

        Returns:
            SubagentResult with findings
        """
        try:
            from vector_rag_gui.tools.web_fetch import web_fetch
            from vector_rag_gui.tools.web_search import search_web

            # Extended web search with URL fetching
            search_result = await anyio.to_thread.run_sync(lambda: search_web(query=query))

            findings = []
            try:
                search_data = json.loads(search_result)
                findings.append(
                    {
                        "type": "extended_web_search",
                        "query": query,
                        "data": search_data,
                    }
                )

                # Fetch top URLs if available
                urls_to_fetch = []
                if isinstance(search_data, dict) and "results" in search_data:
                    for result in search_data["results"][:3]:
                        if isinstance(result, dict) and "url" in result:
                            urls_to_fetch.append(result["url"])

                for url in urls_to_fetch[:2]:  # Limit to 2 URLs

                    def _fetch(u: str = url) -> str:
                        return web_fetch(url=u)

                    fetch_result = await anyio.to_thread.run_sync(_fetch)
                    try:
                        fetch_data = json.loads(fetch_result)
                        if fetch_data.get("content"):
                            findings.append(
                                {
                                    "type": "web_fetch",
                                    "url": url,
                                    "content": fetch_data["content"][:3000],
                                }
                            )
                    except json.JSONDecodeError:
                        pass

            except json.JSONDecodeError:
                findings.append(
                    {
                        "type": "extended_web_search",
                        "query": query,
                        "data": {"raw": search_result},
                    }
                )

            return SubagentResult(
                source_type="web",
                query=query,
                findings=json.dumps({"results": findings}),
            )
        except Exception as e:
            return SubagentResult(
                source_type="web",
                query=query,
                findings=json.dumps({"error": str(e), "results": []}),
                error=str(e),
            )

    async def _run_file_subagent(self, query: str) -> SubagentResult:
        """Run file search subagent using glob, grep, and read.

        Searches for relevant files in the current working directory
        based on the query, then reads content from matching files.

        Args:
            query: Search query

        Returns:
            SubagentResult with findings from file search
        """
        try:
            from vector_rag_gui.tools.file_tools import glob_files, grep_files, read_file

            findings: list[dict[str, Any]] = []

            # Extract potential search patterns from query
            # Look for common file types and code patterns
            search_patterns = self._extract_file_patterns(query)

            # Step 1: Glob for relevant files
            for pattern in search_patterns["glob_patterns"]:

                def _glob(p: str = pattern) -> str:
                    return glob_files(pattern=p)

                glob_result = await anyio.to_thread.run_sync(_glob)
                try:
                    glob_data = json.loads(glob_result)
                    if glob_data.get("files"):
                        findings.append(
                            {
                                "type": "glob",
                                "pattern": pattern,
                                "files": glob_data["files"][:10],  # Limit files
                                "total": glob_data.get("total", 0),
                            }
                        )
                except json.JSONDecodeError:
                    pass

            # Step 2: Grep for relevant patterns in code
            for pattern in search_patterns["grep_patterns"]:

                def _grep(p: str = pattern) -> str:
                    return grep_files(
                        pattern=p,
                        glob_pattern="**/*.py",  # Focus on Python files
                        max_matches=20,
                    )

                grep_result = await anyio.to_thread.run_sync(_grep)
                try:
                    grep_data = json.loads(grep_result)
                    if grep_data.get("matches"):
                        findings.append(
                            {
                                "type": "grep",
                                "pattern": pattern,
                                "matches": grep_data["matches"][:10],
                                "total": grep_data.get("total", 0),
                            }
                        )
                except json.JSONDecodeError:
                    pass

            # Step 3: Read a few key files if we found matches
            files_to_read = set()
            for finding in findings:
                if finding["type"] == "glob":
                    files_to_read.update(finding["files"][:3])
                elif finding["type"] == "grep":
                    for match in finding["matches"][:3]:
                        files_to_read.add(match.get("file", ""))

            file_contents = []
            for file_path in list(files_to_read)[:5]:  # Limit to 5 files
                if file_path:

                    def _read(fp: str = file_path) -> str:
                        return read_file(path=fp, max_lines=50)

                    read_result = await anyio.to_thread.run_sync(_read)
                    try:
                        read_data = json.loads(read_result)
                        if read_data.get("content"):
                            file_contents.append(
                                {
                                    "path": file_path,
                                    "content": read_data["content"][:2000],  # Limit content
                                    "total_lines": read_data.get("total_lines", 0),
                                }
                            )
                    except json.JSONDecodeError:
                        pass

            if file_contents:
                findings.append(
                    {
                        "type": "file_contents",
                        "files": file_contents,
                    }
                )

            return SubagentResult(
                source_type="file",
                query=query,
                findings=json.dumps({"results": findings, "total": len(findings)}),
            )

        except Exception as e:
            return SubagentResult(
                source_type="file",
                query=query,
                findings=json.dumps({"error": str(e), "results": []}),
                error=str(e),
            )

    def _extract_file_patterns(self, query: str) -> dict[str, list[str]]:
        """Extract file search patterns from query.

        Args:
            query: Research query

        Returns:
            Dict with glob_patterns and grep_patterns lists
        """
        query_lower = query.lower()
        glob_patterns: list[str] = []
        grep_patterns: list[str] = []

        # Default patterns based on common file types
        if any(kw in query_lower for kw in ["python", "py", "code", "function", "class"]):
            glob_patterns.append("**/*.py")
        if any(kw in query_lower for kw in ["config", "configuration", "settings"]):
            glob_patterns.extend(["**/*.json", "**/*.yaml", "**/*.toml"])
        if any(kw in query_lower for kw in ["test", "testing"]):
            glob_patterns.append("**/test*.py")
        if any(kw in query_lower for kw in ["markdown", "docs", "documentation"]):
            glob_patterns.append("**/*.md")

        # If no specific patterns, use general ones
        if not glob_patterns:
            glob_patterns = ["**/*.py", "**/*.md"]

        # Extract keywords for grep
        # Remove common stop words and extract meaningful terms
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "which",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "and",
            "or",
            "but",
            "if",
            "then",
            "else",
            "for",
            "to",
            "from",
            "in",
            "on",
            "at",
            "by",
            "with",
            "about",
            "into",
            "through",
        }
        words = query_lower.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Use top keywords as grep patterns
        grep_patterns = keywords[:3] if keywords else ["def ", "class "]

        return {
            "glob_patterns": glob_patterns,
            "grep_patterns": grep_patterns,
        }

    def _build_sources(self, results: list[SubagentResult]) -> list[Source]:
        """Build Source objects from subagent results.

        Args:
            results: List of SubagentResult objects

        Returns:
            List of Source objects for tracking
        """
        sources: list[Source] = []

        for result in results:
            try:
                data = json.loads(result.findings)
            except json.JSONDecodeError:
                data = {}

            # Count results based on response format
            result_count = 0
            if isinstance(data, list):
                result_count = len(data)
            elif "results" in data:
                result_count = len(data["results"])
            elif "citations" in data:
                result_count = len(data["citations"])

            sources.append(
                Source(
                    source_type=result.source_type,
                    query=result.query,
                    result_count=result_count,
                    store_name=result.raw_data.get("store"),
                    raw_data=data,
                )
            )

        return sources

    async def _synthesize(
        self,
        query: str,
        results: list[SubagentResult],
        emit_progress: Callable[[str], None],
    ) -> dict[str, Any]:
        """Synthesize subagent findings into research document.

        Args:
            query: Original research query
            results: List of SubagentResult objects
            emit_progress: Progress callback

        Returns:
            Dict with document, usage, and model_id
        """
        from anthropic import AsyncAnthropicBedrock

        # Get model configuration
        model_id = self._get_model_id()

        # Build context from all subagent results
        context_parts: list[str] = []

        for result in results:
            source_label = result.source_type.upper()
            if result.raw_data.get("store"):
                source_label += f" ({result.raw_data['store']})"

            context_parts.append(f"### {source_label} FINDINGS\n\n{result.findings}")

        context = "\n\n---\n\n".join(context_parts)

        # Call Claude for synthesis
        client = AsyncAnthropicBedrock(
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
            aws_profile=os.environ.get("AWS_PROFILE"),
        )

        emit_progress("Calling Claude for synthesis...")

        # Build system prompt with optional extensions
        system_prompt = RESEARCH_SYSTEM_PROMPT

        if self.obsidian_mode:
            system_prompt += OBSIDIAN_KNOWLEDGE_PROMPT

        if self.custom_prompt:
            system_prompt += f"\n\n## Custom Instructions\n\n{self.custom_prompt}"

        response = await client.messages.create(
            model=model_id,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"""Research Query: {query}

Below are the findings from parallel research agents. Synthesize these into a
comprehensive research document following the specified format.

{context}""",
                }
            ],
        )

        # Extract response text
        document = ""
        for block in response.content:
            if hasattr(block, "text"):
                document = block.text
                break

        # Track token usage
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return {
            "document": document,
            "usage": usage,
            "model_id": model_id,
        }

    def _get_model_id(self) -> str:
        """Get Bedrock model ID for selected model choice.

        Returns:
            Model ID or inference profile ARN
        """
        env_vars = {
            SDKModelChoice.HAIKU: "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            SDKModelChoice.SONNET: "ANTHROPIC_DEFAULT_SONNET_MODEL",
            SDKModelChoice.OPUS: "ANTHROPIC_DEFAULT_OPUS_MODEL",
        }
        fallbacks = {
            SDKModelChoice.HAIKU: "anthropic.claude-3-5-haiku-20241022-v1:0",
            SDKModelChoice.SONNET: "anthropic.claude-sonnet-4-20250514-v1:0",
            SDKModelChoice.OPUS: "anthropic.claude-opus-4-20250514-v1:0",
        }
        return os.environ.get(env_vars[self.model_choice], fallbacks[self.model_choice])


def run_parallel_research(
    query: str,
    model_choice: str = "sonnet",
    use_local: bool = True,
    use_aws: bool = False,
    use_web: bool = False,
    local_stores: list[str] | None = None,
    on_progress: Callable[[str], None] | None = None,
    custom_prompt: str = "",
    obsidian_mode: bool = False,
) -> ResearchResult:
    """Synchronous wrapper for parallel research.

    Core tools (always enabled):
    - glob_files, grep_files, read_file (file search)
    - todo_read, todo_write (task tracking)

    Optional tools:
    - use_local: Local RAG vector store (default: True)
    - use_aws: AWS documentation (default: False)
    - use_web: Web tools - web_search, web_fetch, extended web (default: False)

    Args:
        query: Research question or topic
        model_choice: Model to use ("haiku", "sonnet", "opus")
        use_local: Enable local vector store search (default True)
        use_aws: Enable AWS documentation search (default False)
        use_web: Enable web tools (web_search, web_fetch, web) (default False)
        local_stores: List of local vector store names to query
        on_progress: Optional callback for progress updates
        custom_prompt: Optional custom instructions to append to system prompt
        obsidian_mode: Enable Obsidian-aware behavior with vault knowledge

    Returns:
        ResearchResult with synthesized document and metadata
    """
    model_map = {
        "haiku": SDKModelChoice.HAIKU,
        "sonnet": SDKModelChoice.SONNET,
        "opus": SDKModelChoice.OPUS,
    }
    model = model_map.get(model_choice.lower(), SDKModelChoice.SONNET)

    agent = SDKResearchAgent(
        model_choice=model,
        custom_prompt=custom_prompt,
        obsidian_mode=obsidian_mode,
    )

    async def _run() -> ResearchResult:
        return await agent.research(
            query=query,
            use_local=use_local,
            use_aws=use_aws,
            use_web=use_web,
            local_stores=local_stores,
            on_progress=on_progress,
        )

    return anyio.run(_run)
