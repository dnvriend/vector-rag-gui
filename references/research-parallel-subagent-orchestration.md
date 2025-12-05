# Research: Parallel Subagent Orchestration with Map-Reduce Pattern

## Abstract

This document analyzes the changes required to transform the current sequential research agent in `vector-rag-gui` into a parallel execution model using map-reduce. The current implementation executes tool calls sequentially within an agentic loop. Two approaches are evaluated: (1) native `asyncio.gather()` for tool-level parallelism, and (2) the official Claude Agent SDK (`claude-agent-sdk`) which supports subagent orchestration with automatic parallel execution.

## Current Architecture Analysis

### Execution Flow (Sequential)

```
agent.py:266-411 - ResearchAgent.research()
├── Agentic loop (while True)
│   ├── Call Claude API with tools
│   ├── If tool_use: execute tools SEQUENTIALLY
│   │   └── for tool_use in tool_uses: execute one-by-one
│   └── If end_turn: return synthesized document
```

**Key limitation**: Tools execute in sequence within a single API call iteration. Even when Claude requests multiple tool calls, they run sequentially in `agent.py:360-378`.

### Current Tool Structure

| File | Tool | Description |
|------|------|-------------|
| `tools/vector_rag.py:14-54` | `search_local_knowledge` | Local FAISS vector search |
| `tools/aws_knowledge.py:15-61` | `search_aws_docs` | AWS documentation search |
| `tools/web_search.py:15-62` | `search_web` | Web search via Gemini |
| `tools/file_tools.py` | `glob_files`, `grep_files`, `read_file` | File operations |

All tools currently use `@beta_tool` decorator from `anthropic` SDK.

## Claude Agent SDK (Official)

**The Claude Agent SDK exists** as an official Anthropic package:

- **Package**: `claude-agent-sdk`
- **PyPI**: https://pypi.org/project/claude-agent-sdk/
- **GitHub**: https://github.com/anthropics/claude-agent-sdk-python
- **Version**: 0.1.12 (Dec 4, 2025)
- **Python**: 3.10+
- **License**: MIT

### Installation

```bash
pip install claude-agent-sdk
```

### Core API

| Component | Description |
|-----------|-------------|
| `query()` | Async function for single queries, returns `AsyncIterator` |
| `ClaudeSDKClient` | Stateful client for bidirectional conversations |
| `@tool` decorator | Define custom tools with MCP server integration |
| `create_sdk_mcp_server()` | Create in-process MCP server |
| `ClaudeAgentOptions` | Configuration (system_prompt, allowed_tools, mcp_servers, hooks) |
| `AgentDefinition` | Define subagents with description, prompt, tools, model |

### Subagent Support

The SDK **supports subagents by default** with two definition methods:

1. **Programmatic** (recommended): Use `agents` parameter in `query()` options
2. **Filesystem-based**: Markdown files in `.claude/agents/` directories

### Parallel Execution

From the documentation:
> "Multiple subagents can run concurrently, dramatically speeding up complex workflows."

Example scenario: "During a code review, you can run `style-checker`, `security-scanner`, and `test-coverage` subagents simultaneously, reducing review time from minutes to seconds."

### Code Example (TypeScript, Python API similar)

```typescript
const result = query({
  prompt: "Review authentication and optimize queries",
  options: {
    agents: {
      'code-reviewer': {
        description: 'Expert code review specialist',
        prompt: 'You are a security-focused code reviewer...',
        tools: ['Read', 'Grep', 'Glob']
      },
      'performance-optimizer': {
        description: 'Use PROACTIVELY for optimization tasks',
        prompt: 'You are a performance specialist...',
        tools: ['Read', 'Edit', 'Bash', 'Grep'],
        model: 'sonnet'
      }
    }
  }
});
```

### Custom Tool Definition

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient

@tool("greet", "Greet a user", {"name": str})
async def greet_user(args):
    return {
        "content": [
            {"type": "text", "text": f"Hello, {args['name']}!"}
        ]
    }

server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[greet_user]
)

options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__greet"]
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Greet Alice")
    async for msg in client.receive_response():
        print(msg)
```

## Architecture Options

### Option A: Native asyncio (No SDK)

Use `asyncio.gather()` with existing tools:

```
┌─────────────────────────────────────────────────────────────────┐
│                     ParallelResearchAgent                       │
│                                                                 │
│  ┌──────────────┐                                               │
│  │ Coordinator  │                                               │
│  │   (Claude)   │                                               │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼  MAP PHASE (asyncio.gather)                           │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │       │
│  │  │ RAG     │  │ AWS     │  │ Web     │  │ File    │  │       │
│  │  │ Worker  │  │ Worker  │  │ Worker  │  │ Worker  │  │       │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │       │
│  │       │            │            │            │        │       │
│  │       ▼            ▼            ▼            ▼        │       │
│  │   vector_rag   aws_docs    web_search    file_ops    │       │
│  └──────────────────────────────────────────────────────┘       │
│         │                                                       │
│         ▼  REDUCE PHASE                                         │
│  ┌──────────────┐                                               │
│  │  Synthesizer │  (Claude call to merge results)               │
│  │    (Claude)  │                                               │
│  └──────────────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │ ResearchDoc  │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Pros**: No new dependencies, full control, simpler architecture
**Cons**: Manual orchestration, no automatic subagent selection

### Option B: Claude Agent SDK

Use `claude-agent-sdk` with `AgentDefinition` for subagents:

```
┌─────────────────────────────────────────────────────────────────┐
│                     ClaudeSDKClient                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                    Orchestrator                       │       │
│  │  (Claude Code CLI via SDK - auto parallel dispatch)   │       │
│  └──────────────────────────────────────────────────────┘       │
│         │                                                       │
│         ▼  AUTOMATIC PARALLEL DISPATCH                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │       │
│  │  │ rag-agent   │  │ aws-agent   │  │ web-agent   │   │       │
│  │  │ (subagent)  │  │ (subagent)  │  │ (subagent)  │   │       │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │       │
│  └──────────────────────────────────────────────────────┘       │
│         │                                                       │
│         ▼  AUTOMATIC SYNTHESIS                                  │
│  ┌──────────────┐                                               │
│  │ ResearchDoc  │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Pros**: Official SDK, automatic parallel dispatch, context isolation, built-in synthesis
**Cons**: New dependency, bundled CLI, learning curve, less control over execution

## Implementation Comparison

### Option A: Native asyncio Implementation

```python
"""Parallel research agent with map-reduce execution pattern."""

import asyncio
from dataclasses import dataclass
from typing import Callable

from anthropic import AsyncAnthropicBedrock

from vector_rag_gui.tools.vector_rag import search_local_knowledge
from vector_rag_gui.tools.aws_knowledge import search_aws_docs
from vector_rag_gui.tools.web_search import search_web


@dataclass
class SubagentResult:
    """Result from a subagent worker."""
    source_type: str
    query: str
    data: str
    error: str | None = None


async def run_subagent(
    source_type: str,
    query: str,
    tool_fn: Callable[..., str],
    **kwargs
) -> SubagentResult:
    """Execute a single tool as a subagent."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: tool_fn(query=query, **kwargs)
        )
        return SubagentResult(source_type=source_type, query=query, data=result)
    except Exception as e:
        return SubagentResult(source_type=source_type, query=query, data="{}", error=str(e))


class ParallelResearchAgent:
    """Research agent with parallel subagent execution."""

    async def research(self, query: str, local_stores: list[str]) -> ResearchResult:
        # MAP PHASE
        tasks = [
            run_subagent("local", query, search_local_knowledge, store=store, top_k=3)
            for store in local_stores
        ]
        tasks.append(run_subagent("aws", query, search_aws_docs))
        tasks.append(run_subagent("web", query, search_web))

        results = await asyncio.gather(*tasks)

        # REDUCE PHASE
        return await self._synthesize(query, results)
```

### Option B: Claude Agent SDK Implementation

```python
"""Parallel research agent using Claude Agent SDK."""

import anyio
from claude_agent_sdk import (
    query,
    tool,
    create_sdk_mcp_server,
    ClaudeAgentOptions,
)


@tool("search_rag", "Search local vector stores", {"query": str, "store": str})
async def search_rag_tool(args):
    from vector_rag_gui.tools.vector_rag import search_local_knowledge
    result = search_local_knowledge(query=args["query"], store=args["store"])
    return {"content": [{"type": "text", "text": result}]}


@tool("search_aws", "Search AWS documentation", {"query": str})
async def search_aws_tool(args):
    from vector_rag_gui.tools.aws_knowledge import search_aws_docs
    result = search_aws_docs(query=args["query"])
    return {"content": [{"type": "text", "text": result}]}


@tool("search_web", "Search the web", {"query": str})
async def search_web_tool(args):
    from vector_rag_gui.tools.web_search import search_web
    result = search_web(query=args["query"])
    return {"content": [{"type": "text", "text": result}]}


async def research_with_sdk(user_query: str, stores: list[str]) -> str:
    """Execute research using Claude Agent SDK with parallel subagents."""

    # Create MCP server with tools
    tool_server = create_sdk_mcp_server(
        name="research-tools",
        version="1.0.0",
        tools=[search_rag_tool, search_aws_tool, search_web_tool]
    )

    # Define subagents
    agents = {
        "rag-researcher": {
            "description": "Search local knowledge bases for internal documentation",
            "prompt": f"Search these stores: {', '.join(stores)}. Return relevant findings.",
            "tools": ["mcp__research-tools__search_rag"],
            "model": "haiku"  # Cheaper for extraction
        },
        "aws-researcher": {
            "description": "Search AWS documentation for official guidance",
            "prompt": "Search AWS docs and extract relevant best practices.",
            "tools": ["mcp__research-tools__search_aws"],
            "model": "haiku"
        },
        "web-researcher": {
            "description": "Search the web for current information",
            "prompt": "Search the web for recent and relevant information.",
            "tools": ["mcp__research-tools__search_web"],
            "model": "haiku"
        }
    }

    options = ClaudeAgentOptions(
        system_prompt=RESEARCH_SYSTEM_PROMPT,
        mcp_servers={"research-tools": tool_server},
        agents=agents
    )

    # SDK handles parallel dispatch and synthesis automatically
    result_text = ""
    async for message in query(prompt=user_query, options=options):
        if hasattr(message, "text"):
            result_text += message.text

    return result_text
```

## Changes to Existing Files

### Option A (asyncio)

| File | Change | Impact |
|------|--------|--------|
| `core/agent.py` | Keep for backwards compatibility | None |
| `core/parallel_agent.py` | New file | ~150 lines |
| `gui/worker.py` | Add `ParallelResearchWorker` | ~50 lines |
| `gui/main_window.py` | Add parallel mode toggle | UI change |
| `pyproject.toml` | No new deps | None |

### Option B (Claude Agent SDK)

| File | Change | Impact |
|------|--------|--------|
| `core/agent.py` | Deprecate or keep as fallback | None |
| `core/sdk_agent.py` | New file using SDK | ~100 lines |
| `tools/*.py` | Migrate to `@tool` decorator | Refactor |
| `gui/worker.py` | Add `SDKResearchWorker` | ~50 lines |
| `pyproject.toml` | Add `claude-agent-sdk>=0.1.12` | New dep |

## Performance Comparison

| Metric | Sequential | Option A (asyncio) | Option B (SDK) |
|--------|------------|-------------------|----------------|
| 3 tools × 1s each | ~3s | ~1s | ~1s |
| 6 tools × 1s each | ~6s | ~1s | ~1s |
| API calls | 1 + N iterations | 1 map + 1 reduce | SDK managed |
| Token usage | Higher | ~30-50% less | SDK optimized |
| Code complexity | Low | Medium | Medium |
| New dependencies | None | None | claude-agent-sdk |

## Risk Assessment

| Risk | Option A Mitigation | Option B Mitigation |
|------|---------------------|---------------------|
| Race conditions | Isolated tasks | SDK handles |
| API rate limits | `asyncio.Semaphore` | SDK rate limiting |
| Thread safety (Qt) | Signals are thread-safe | Same |
| Error propagation | `gather(return_exceptions=True)` | SDK error handling |
| Vendor lock-in | None | Anthropic SDK |
| Breaking changes | Full control | SDK versioning |

## Recommendation

**Start with Option A (asyncio)** for these reasons:

1. **No new dependencies** - Uses existing `anthropic` SDK async support
2. **Full control** - Explicit map-reduce phases, predictable behavior
3. **Simpler migration** - Minimal changes to existing tool code
4. **Lower risk** - No external CLI bundled, no new SDK to learn

**Consider Option B (SDK)** when:
- Anthropic SDK stabilizes (currently 0.1.x)
- You need automatic subagent orchestration at scale
- You want built-in context isolation per subagent
- You're building a larger multi-agent system

## Migration Path

1. **Phase 1**: Implement Option A (`parallel_agent.py`)
2. **Phase 2**: Add UI toggle "Parallel mode (faster)"
3. **Phase 3**: Validate performance gains in production
4. **Phase 4**: Evaluate SDK migration when stable (1.0+)

## Conclusion

The Claude Agent SDK (`claude-agent-sdk`) is real and supports parallel subagent execution. However, for `vector-rag-gui`, the simpler `asyncio.gather()` approach is recommended initially:

1. **Tool-level parallelism** is sufficient for the current use case
2. **No new dependencies** simplifies deployment
3. **Explicit control** over map-reduce phases
4. **SDK migration** can happen later when the API stabilizes

Estimated code changes: ~200-300 lines new code for Option A, minimal changes to existing files.
