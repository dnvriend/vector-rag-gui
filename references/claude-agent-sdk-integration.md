# Claude Agent SDK Integration Guide

## Phase 2: Agentic Research Synthesis

This document describes the Phase 2 enhancement for `vector-rag-gui` - integrating the Claude Agent SDK to synthesize research documents from multiple knowledge sources.

## Vision

**Phase 1** (Current): Query local vector stores, display raw results
**Phase 2** (This Document): Agent synthesizes a structured research document from multiple sources

### Output Format

The agent produces a **Markdown Research Document** displayed in the GUI:

```markdown
# Research: [Query Topic]

## Abstract
Brief 2-3 sentence summary of findings.

## Summary
Key findings and insights (bullet points).

## Body
Detailed analysis synthesized from all sources...

## Conclusions
- Main takeaway 1
- Main takeaway 2
- Recommendations

## Sources
1. [Local] obsidian-knowledge-base: notes/aws-lambda.md:45-67
2. [AWS Docs] Lambda Best Practices - https://docs.aws.amazon.com/...
3. [Web] AWS Lambda Cold Starts in 2024 - https://example.com/...
```

## What is the Claude Agent SDK?

The Claude Agent SDK is not a separate framework but a set of patterns within the **Anthropic Python SDK** that enable building agentic systems. The core concept is **Tool Use** - allowing Claude to identify when external functions need to be called and having those results fed back for synthesis.

### Agentic Loop Flow

```
1. User sends query -> Claude with available tools
2. Claude decides if tools are needed (stop_reason: "tool_use")
3. Extract tool calls from response
4. Execute tools locally
5. Send tool results back to Claude
6. Claude synthesizes final response
7. Loop until stop_reason != "tool_use"
```

## Installation

```bash
pip install anthropic
```

For AWS Bedrock:
```bash
pip install "anthropic[bedrock]"
```

## Defining Tools

### Using @beta_tool Decorator (Recommended)

```python
from anthropic import beta_tool
import json

@beta_tool
def search_vector_store(query: str, store: str = "obsidian-knowledge-base", top_k: int = 5) -> str:
    """Search local vector store for relevant documents.

    Args:
        query: Natural language search query
        store: Name of the vector store to query
        top_k: Number of results to return

    Returns:
        JSON string with search results including file paths and content
    """
    from vector_rag_tool.core.backend_factory import get_backend
    from vector_rag_tool.services.querier import Querier

    backend = get_backend()
    querier = Querier(backend=backend)
    result = querier.query(store_name=store, query_text=query, top_k=top_k)

    formatted = [
        {
            "file": chunk.metadata.source_file if chunk.metadata else "Unknown",
            "lines": f"{chunk.metadata.line_start}-{chunk.metadata.line_end}" if chunk.metadata else None,
            "score": float(score),
            "content": chunk.content
        }
        for chunk, score in result.get_sorted_chunks()
    ]

    return json.dumps(formatted, indent=2)
```

### Manual Tool Definition

```python
tools = [
    {
        "name": "search_vector_store",
        "description": "Search local vector store for relevant documents",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "store": {"type": "string", "description": "Store name"},
                "top_k": {"type": "integer", "description": "Number of results"}
            },
            "required": ["query"]
        }
    }
]
```

## Integration Architecture

### Target Integration

```
User Query
    |
    v
+-------------------+
| Claude Agent SDK  |
+-------------------+
    |
    +---> vector-rag-tool (Local FAISS stores)
    |         |
    |         v
    |     [RAG Results]
    |
    +---> aws-knowledge-tool (AWS Documentation)
    |         |
    |         v
    |     [AWS Docs]
    |
    +---> gemini-google-search-tool (Web Search)
              |
              v
          [Web Results]
    |
    v
+-------------------+
| Claude Synthesis  |
+-------------------+
    |
    v
Final Response
```

## Implementation

### Tool Definitions

```python
from anthropic import beta_tool
import json
import subprocess

@beta_tool
def search_local_knowledge(query: str, store: str = "obsidian-knowledge-base", top_k: int = 3) -> str:
    """Search local vector RAG store for internal documentation and notes.

    Args:
        query: Natural language search query
        store: Vector store name (default: obsidian-knowledge-base)
        top_k: Number of results to return

    Returns:
        JSON with relevant document chunks and metadata
    """
    from vector_rag_tool.core.backend_factory import get_backend
    from vector_rag_tool.services.querier import Querier

    backend = get_backend()
    querier = Querier(backend=backend)
    result = querier.query(store_name=store, query_text=query, top_k=top_k)

    formatted = []
    for chunk, score in result.get_sorted_chunks():
        formatted.append({
            "source": chunk.metadata.source_file if chunk.metadata else "Unknown",
            "lines": f"{chunk.metadata.line_start}-{chunk.metadata.line_end}" if chunk.metadata else None,
            "relevance": round(float(score), 3),
            "content": chunk.content[:500]  # Truncate for token efficiency
        })

    return json.dumps({"results": formatted, "total": len(formatted)})


@beta_tool
def search_aws_docs(query: str) -> str:
    """Search AWS documentation for official guidance and best practices.

    Args:
        query: Search query for AWS documentation

    Returns:
        JSON with AWS documentation search results
    """
    result = subprocess.run(
        ["aws-knowledge-tool", "search", query, "--json"],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        return json.dumps({"error": result.stderr, "results": []})

    return result.stdout


@beta_tool
def search_web(query: str) -> str:
    """Search the web for current information using Google Search.

    Args:
        query: Web search query

    Returns:
        JSON with web search results
    """
    result = subprocess.run(
        ["gemini-google-search-tool", "query", query, "--json"],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        return json.dumps({"error": result.stderr, "results": []})

    return result.stdout
```

### Agentic Loop Implementation

```python
from anthropic import Anthropic
import json

client = Anthropic()

# Define all tools
tools = [
    search_local_knowledge.to_dict(),
    search_aws_docs.to_dict(),
    search_web.to_dict(),
]

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute tool by name with given input."""
    if tool_name == "search_local_knowledge":
        return search_local_knowledge(**tool_input)
    elif tool_name == "search_aws_docs":
        return search_aws_docs(**tool_input)
    elif tool_name == "search_web":
        return search_web(**tool_input)
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def query_with_tools(user_query: str, system_prompt: str = None) -> str:
    """Execute a query with tool access and return synthesized response."""

    messages = [{"role": "user", "content": user_query}]

    system = system_prompt or """You are a helpful assistant with access to multiple knowledge sources:

1. Local Knowledge Base (vector-rag-tool): Internal documentation, notes, and code
2. AWS Documentation (aws-knowledge-tool): Official AWS guidance and best practices
3. Web Search (gemini-google-search-tool): Current information from the web

When answering questions:
- Use the most appropriate tool(s) for the query
- Synthesize information from multiple sources when beneficial
- Cite sources in your response
- Be concise but comprehensive
"""

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5-20251101",
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            # Extract tool calls
            tool_uses = [b for b in response.content if b.type == "tool_use"]

            # Add assistant response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Execute tools and collect results
            tool_results = []
            for tool_use in tool_uses:
                print(f"[Executing {tool_use.name}...]")
                result = execute_tool(tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            # Send results back to Claude
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        else:
            # Unexpected stop reason
            return f"Unexpected stop: {response.stop_reason}"


# Example usage
if __name__ == "__main__":
    answer = query_with_tools(
        "What are the best practices for Lambda function cold starts? "
        "Compare with any internal notes we have on the topic."
    )
    print(answer)
```

### Using Tool Runner (Simpler Approach)

```python
from anthropic import Anthropic

client = Anthropic()

# Tool runner handles the loop automatically
runner = client.beta.messages.tool_runner(
    model="claude-sonnet-4-5-20251101",
    max_tokens=4096,
    tools=[search_local_knowledge, search_aws_docs, search_web],
    messages=[
        {
            "role": "user",
            "content": "Compare AWS Lambda best practices with our internal deployment guidelines"
        }
    ]
)

for event in runner:
    if event.stop_reason == "end_turn":
        print("Answer:", event.content[-1].text)
```

## Tool Choice Control

```python
# Auto (default) - Claude decides which tools to use
tool_choice = "auto"

# Force specific tool
tool_choice = {"type": "tool", "name": "search_local_knowledge"}

# Must use at least one tool
tool_choice = "any"
```

## Error Handling

```python
@beta_tool
def search_with_error_handling(query: str) -> str:
    """Search with proper error handling."""
    try:
        # Tool implementation
        result = perform_search(query)
        return json.dumps({"status": "success", "results": result})

    except TimeoutError:
        return json.dumps({
            "status": "error",
            "error_type": "timeout",
            "message": "Search timed out, try a more specific query"
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        })
```

## Streaming Responses

```python
with client.messages.stream(
    model="claude-sonnet-4-5-20251101",
    max_tokens=2048,
    tools=tools,
    messages=messages
) as stream:
    for event in stream:
        if event.type == "content_block_delta":
            if hasattr(event.delta, "text"):
                print(event.delta.text, end="", flush=True)
```

## Parallel Tool Execution

```python
from concurrent.futures import ThreadPoolExecutor

if response.stop_reason == "tool_use":
    tool_uses = [b for b in response.content if b.type == "tool_use"]

    # Execute tools in parallel
    with ThreadPoolExecutor(max_workers=len(tool_uses)) as executor:
        results = list(executor.map(
            lambda tu: execute_tool(tu.name, tu.input),
            tool_uses
        ))

    tool_results = [
        {"type": "tool_result", "tool_use_id": tu.id, "content": result}
        for tu, result in zip(tool_uses, results)
    ]
```

## Cost Optimization

- Use **Haiku** for simple tool execution and preprocessing
- Use **Sonnet** for synthesis with moderate complexity
- Use **Opus** for complex reasoning requiring multiple tool iterations
- Truncate tool results to reduce token usage
- Cache frequently accessed results

## Phase 2 Architecture

### Updated Flow

```
User Query (vector-rag-gui)
    |
    v
+------------------------+
| Research Agent         |
| (Claude + Tools)       |
+------------------------+
    |
    +---> vector-rag-tool (Local Knowledge)
    |         - obsidian-knowledge-base
    |         - code repositories
    |         - internal docs
    |
    +---> aws-knowledge-tool (AWS Docs)
    |         - Official documentation
    |         - Best practices
    |
    +---> gemini-google-search-tool (Web)
              - Current information
              - External resources
    |
    v
+------------------------+
| Claude Synthesis       |
| -> Markdown Document   |
+------------------------+
    |
    v
+------------------------+
| vector-rag-gui         |
| QWebEngineView         |
| (Markdown Rendering)   |
+------------------------+
```

### GUI Changes for Phase 2

1. **Query Mode Toggle**: Switch between "Direct Search" (Phase 1) and "Research Synthesis" (Phase 2)
2. **Tool Selection**: Checkboxes to enable/disable knowledge sources
3. **Progress Indicator**: Show which tools are being queried
4. **Research Document View**: Structured markdown with sections

### New Module Structure

```
vector_rag_gui/
├── core/
│   ├── stores.py          # Phase 1: Store management
│   ├── query.py           # Phase 1: Direct query
│   └── agent.py           # Phase 2: Research agent
├── tools/                 # Phase 2: Tool definitions
│   ├── __init__.py
│   ├── vector_rag.py      # vector-rag-tool wrapper
│   ├── aws_knowledge.py   # aws-knowledge-tool wrapper
│   └── web_search.py      # gemini-google-search-tool wrapper
└── gui/
    ├── main_window.py     # Updated with research mode
    └── worker.py          # Updated for agent execution
```

### Research Agent Implementation

```python
"""Research agent for synthesizing knowledge from multiple sources.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from anthropic import Anthropic
import json

from vector_rag_gui.tools.vector_rag import search_local_knowledge
from vector_rag_gui.tools.aws_knowledge import search_aws_docs
from vector_rag_gui.tools.web_search import search_web

RESEARCH_SYSTEM_PROMPT = '''You are a research assistant that synthesizes information from multiple knowledge sources into a structured research document.

Available tools:
1. search_local_knowledge: Search local vector stores (notes, code, internal docs)
2. search_aws_docs: Search official AWS documentation
3. search_web: Search the web for current information

Your task is to:
1. Use the appropriate tools to gather relevant information
2. Synthesize findings into a structured Markdown research document

Output format (strict):

# Research: [Topic]

## Abstract
[2-3 sentence summary of key findings]

## Summary
- [Key finding 1]
- [Key finding 2]
- [Key finding 3]

## Body
[Detailed analysis synthesized from all sources. Use subsections if needed.]

## Conclusions
- [Main conclusion 1]
- [Main conclusion 2]
- [Actionable recommendations if applicable]

## Sources
[Numbered list of all sources used, with type indicator]
1. [Local] store-name: file/path:lines
2. [AWS] Title - URL
3. [Web] Title - URL

Guidelines:
- Cite sources inline using [1], [2], etc.
- Be comprehensive but concise
- Highlight agreements and disagreements between sources
- Note when information is outdated or uncertain
'''


class ResearchAgent:
    """Agent that synthesizes research from multiple knowledge sources."""

    def __init__(self, model: str = "claude-sonnet-4-5-20251101"):
        self.client = Anthropic()
        self.model = model
        self.tools = [
            search_local_knowledge,
            search_aws_docs,
            search_web,
        ]

    def research(
        self,
        query: str,
        use_local: bool = True,
        use_aws: bool = True,
        use_web: bool = True,
        local_store: str = "obsidian-knowledge-base",
    ) -> str:
        """Execute research query and return synthesized markdown document.

        Args:
            query: Research question or topic
            use_local: Enable local vector store search
            use_aws: Enable AWS documentation search
            use_web: Enable web search
            local_store: Name of local vector store to query

        Returns:
            Markdown formatted research document
        """
        # Filter tools based on settings
        active_tools = []
        if use_local:
            active_tools.append(search_local_knowledge)
        if use_aws:
            active_tools.append(search_aws_docs)
        if use_web:
            active_tools.append(search_web)

        if not active_tools:
            return "# Error\n\nNo knowledge sources enabled."

        messages = [{"role": "user", "content": query}]

        # Agentic loop
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=RESEARCH_SYSTEM_PROMPT,
                tools=[t.to_dict() for t in active_tools],
                messages=messages
            )

            if response.stop_reason == "tool_use":
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tool_use in tool_uses:
                    result = self._execute_tool(tool_use.name, tool_use.input, local_store)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result
                    })

                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return "# Error\n\nNo response generated."

            else:
                return f"# Error\n\nUnexpected stop: {response.stop_reason}"

    def _execute_tool(self, name: str, inputs: dict, local_store: str) -> str:
        """Execute a tool by name."""
        if name == "search_local_knowledge":
            inputs["store"] = local_store
            return search_local_knowledge(**inputs)
        elif name == "search_aws_docs":
            return search_aws_docs(**inputs)
        elif name == "search_web":
            return search_web(**inputs)
        return json.dumps({"error": f"Unknown tool: {name}"})
```

### Updated Worker for Phase 2

```python
"""Background worker for research agent execution.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import QThread, pyqtSignal

from vector_rag_gui.core.agent import ResearchAgent


class ResearchWorker(QThread):
    """Background worker for executing research queries."""

    finished = pyqtSignal(str)  # Markdown document
    progress = pyqtSignal(str)  # Status updates
    error = pyqtSignal(str)

    def __init__(
        self,
        query: str,
        use_local: bool = True,
        use_aws: bool = True,
        use_web: bool = True,
        local_store: str = "obsidian-knowledge-base",
    ) -> None:
        super().__init__()
        self.query = query
        self.use_local = use_local
        self.use_aws = use_aws
        self.use_web = use_web
        self.local_store = local_store

    def run(self) -> None:
        try:
            self.progress.emit("Initializing research agent...")
            agent = ResearchAgent()

            self.progress.emit("Gathering information from sources...")
            result = agent.research(
                query=self.query,
                use_local=self.use_local,
                use_aws=self.use_aws,
                use_web=self.use_web,
                local_store=self.local_store,
            )

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))
```

## Implementation Roadmap

### Phase 2.1: Core Agent
- [ ] Create `vector_rag_gui/core/agent.py` with ResearchAgent
- [ ] Create `vector_rag_gui/tools/` module with tool wrappers
- [ ] Add `anthropic` dependency to pyproject.toml
- [ ] Unit tests for agent and tools

### Phase 2.2: GUI Updates
- [ ] Add "Research Mode" toggle to main window
- [ ] Add tool selection checkboxes (Local/AWS/Web)
- [ ] Create ResearchWorker for background execution
- [ ] Progress indicator for multi-tool queries

### Phase 2.3: Polish
- [ ] Streaming response display
- [ ] Research history/caching
- [ ] Export research document to file
- [ ] Copy to clipboard functionality

## Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    # ... existing deps ...
    "anthropic>=0.40.0",
]
```

## Environment Variables

```bash
# Required for Phase 2
export ANTHROPIC_API_KEY="sk-ant-..."

# Or for AWS Bedrock
export AWS_PROFILE="your-profile"
export AWS_REGION="us-east-1"
```

## References

- [Anthropic SDK Python](https://github.com/anthropics/anthropic-sdk-python)
- [Tool Use Documentation](https://docs.anthropic.com/en/docs/tool-use)
- [Anthropic Cookbook - Agents](https://github.com/anthropics/cookbook/tree/main/patterns/agents)
