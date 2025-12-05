"""Research agent for synthesizing knowledge from multiple sources.

The ResearchAgent uses the Claude Agent SDK to orchestrate multiple knowledge sources
and synthesize findings into a structured markdown research document.

Supports both direct Anthropic API and AWS Bedrock backends.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from anthropic import AnthropicBedrock

from vector_rag_gui.tools.aws_knowledge import search_aws_docs
from vector_rag_gui.tools.file_tools import glob_files, grep_files, read_file
from vector_rag_gui.tools.vector_rag import search_local_knowledge
from vector_rag_gui.tools.web_search import search_web


class ModelChoice(Enum):
    """Available model choices for synthesis."""

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


# Pricing per 1M tokens (USD) - AWS Bedrock pricing
# https://aws.amazon.com/bedrock/pricing/
MODEL_PRICING = {
    ModelChoice.HAIKU: {"input": 0.80, "output": 4.00},
    ModelChoice.SONNET: {"input": 3.00, "output": 15.00},
    ModelChoice.OPUS: {"input": 15.00, "output": 75.00},
}


@dataclass
class Source:
    """A source used during research."""

    source_type: str  # "local", "aws", "web"
    query: str
    result_count: int
    store_name: str | None = None  # For local sources, the store name
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsage:
    """Token usage statistics for a research session."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    def calculate_cost(self, model: ModelChoice) -> float:
        """Calculate cost in USD based on model pricing."""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING[ModelChoice.SONNET])
        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


def _slugify(text: str, max_length: int = 50) -> str:
    """Convert text to kebab-case slug.

    Args:
        text: Text to convert
        max_length: Maximum length of slug

    Returns:
        Kebab-case slug
    """
    # Convert to lowercase and replace spaces/underscores with hyphens
    slug = text.lower().strip()
    slug = re.sub(r"[_\s]+", "-", slug)
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Truncate to max length at word boundary
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0]
    return slug


def _get_queries_dir() -> Path:
    """Get the queries directory path.

    Returns:
        Path to ~/.config/vector-rag-gui/queries/
    """
    queries_dir = Path.home() / ".config" / "vector-rag-gui" / "queries"
    queries_dir.mkdir(parents=True, exist_ok=True)
    return queries_dir


@dataclass
class ResearchResult:
    """Result from a research query including document, sources, and usage."""

    document: str
    sources: list[Source]
    usage: TokenUsage
    model: ModelChoice
    model_id: str
    query: str = ""  # Original query text

    def save(self, query: str | None = None) -> Path:
        """Save research result to queries directory.

        Saves to ~/.config/vector-rag-gui/queries/<timestamp>-<slug>.md

        Args:
            query: Optional query text (uses self.query if not provided)

        Returns:
            Path to saved file
        """
        query_text = query or self.query or "research"
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        slug = _slugify(query_text)
        filename = f"{timestamp}-{slug}.md"

        queries_dir = _get_queries_dir()
        file_path = queries_dir / filename

        file_path.write_text(self.document, encoding="utf-8")
        return file_path


# Model ID mapping for AWS Bedrock
# Uses global inference profiles from environment variables when available
# Falls back to direct model IDs if env vars not set
def get_bedrock_model(choice: ModelChoice) -> str:
    """Get model ID/ARN for the given choice.

    Prefers inference profile ARNs from environment variables:
    - ANTHROPIC_DEFAULT_HAIKU_MODEL
    - ANTHROPIC_DEFAULT_SONNET_MODEL
    - ANTHROPIC_DEFAULT_OPUS_MODEL

    Falls back to direct model IDs if not set.
    """
    env_vars = {
        ModelChoice.HAIKU: "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        ModelChoice.SONNET: "ANTHROPIC_DEFAULT_SONNET_MODEL",
        ModelChoice.OPUS: "ANTHROPIC_DEFAULT_OPUS_MODEL",
    }
    fallbacks = {
        ModelChoice.HAIKU: "anthropic.claude-3-5-haiku-20241022-v1:0",
        ModelChoice.SONNET: "anthropic.claude-sonnet-4-20250514-v1:0",
        ModelChoice.OPUS: "anthropic.claude-opus-4-20250514-v1:0",
    }
    return os.environ.get(env_vars[choice], fallbacks[choice])


RESEARCH_SYSTEM_PROMPT = """You are a research assistant that synthesizes information from \
multiple knowledge sources into a structured research document.

Available tools:
1. search_local_knowledge: Search local vector stores (notes, code, internal docs)
2. search_aws_docs: Search official AWS documentation
3. search_web: Search the web for current information
4. glob_files: Find files matching a glob pattern (e.g., '**/*.py', 'src/*.ts')
5. grep_files: Search for regex patterns in files
6. read_file: Read contents of a specific file

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
"""


OBSIDIAN_KNOWLEDGE_PROMPT = """
## Obsidian Vault Knowledge

You are researching an Obsidian vault. Follow these MANDATORY steps:

### Step 1: Find Relevant Notes
Use LOCAL RAG results to identify relevant files. RAG gives you file paths - use them.

### Step 2: Read Full Files (REQUIRED)
For EVERY relevant file path from RAG:
```
read_file(path="/path/to/note.md")
```
RAG only shows snippets. You MUST read the full file to get complete context.

### Step 3: Follow Wiki Links (REQUIRED)
When you see `[[Note Title]]` or `[[folder/Note Title]]` in a note:
1. Search for the linked file:
   ```
   glob_files(pattern="**/Note Title.md")
   ```
2. Read the linked file:
   ```
   read_file(path="/found/path/Note Title.md")
   ```
3. Repeat for important links (2-3 levels deep)

### Step 4: Date Questions - Check Daily Notes
For questions about dates/events, ALWAYS glob daily notes:
```
glob_files(pattern="daily/2025/2025-01/*.md")  # January 2025
```
Then read relevant daily notes.

### Step 5: Search for Keywords
If RAG misses something, use grep:
```
grep_files(pattern="keyword", glob_pattern="**/*.md")
```

### Transcripts
- Transcripts are long - summarize key points, decisions, action items
- Look for existing `## Summary` sections first

### CRITICAL RULES
1. NEVER skip reading files - RAG snippets are NOT enough
2. ALWAYS follow wiki links with glob_files + read_file
3. For dates, glob the daily/ folder for that time period
4. Read at least 3-5 connected notes for proper context
"""


class ResearchAgent:
    """Agent that synthesizes research from multiple knowledge sources.

    Uses AWS Bedrock as the backend for Claude model access.
    Configurable via AWS_PROFILE and AWS_REGION environment variables.
    """

    def __init__(
        self,
        model_choice: ModelChoice = ModelChoice.SONNET,
        aws_profile: str | None = None,
        aws_region: str | None = None,
    ) -> None:
        """Initialize research agent with AWS Bedrock backend.

        Args:
            model_choice: Which Claude model to use (HAIKU, SONNET, OPUS)
            aws_profile: AWS profile name (defaults to AWS_PROFILE env var)
            aws_region: AWS region (defaults to AWS_REGION env var or us-east-1)
        """
        # Get AWS configuration from environment or parameters
        self.aws_profile = aws_profile or os.environ.get("AWS_PROFILE")
        self.aws_region = aws_region or os.environ.get("AWS_REGION", "us-east-1")

        # Initialize Bedrock client
        self.client = AnthropicBedrock(
            aws_region=self.aws_region,
            aws_profile=self.aws_profile,
        )

        self.model_choice = model_choice
        self.model = get_bedrock_model(model_choice)

        # Store tools as Any to avoid complex generic type issues
        self.tools: list[Any] = [
            search_local_knowledge,
            search_aws_docs,
            search_web,
            glob_files,
            grep_files,
            read_file,
        ]

    def research(
        self,
        query: str,
        use_local: bool = True,
        use_aws: bool = True,
        use_web: bool = True,
        local_stores: list[str] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> ResearchResult:
        """Execute research query and return synthesized markdown document.

        Args:
            query: Research question or topic
            use_local: Enable local vector store search
            use_aws: Enable AWS documentation search
            use_web: Enable web search
            local_stores: List of local vector store names to query
            on_progress: Optional callback for progress updates

        Returns:
            ResearchResult with document, sources, and usage statistics
        """
        # Default stores if none provided
        if local_stores is None:
            local_stores = ["obsidian-knowledge-base"]

        self._local_stores = local_stores

        def emit_progress(message: str) -> None:
            """Emit progress update if callback is set."""
            if on_progress:
                on_progress(message)

        # Filter tools based on settings
        active_tools: list[Any] = []
        if use_local:
            active_tools.append(search_local_knowledge)
        if use_aws:
            active_tools.append(search_aws_docs)
        if use_web:
            active_tools.append(search_web)

        # File tools are always available (read-only)
        active_tools.extend([glob_files, grep_files, read_file])

        if not active_tools:
            return ResearchResult(
                document="# Error\n\nNo knowledge sources enabled.",
                sources=[],
                usage=TokenUsage(),
                model=self.model_choice,
                model_id=self.model,
                query=query,
            )

        # Track sources and usage
        sources: list[Source] = []
        usage = TokenUsage()

        # Build system prompt with available stores
        system_prompt = self._build_system_prompt(local_stores if use_local else [])

        # Use Any type for messages to avoid MessageParam type complexity
        messages: list[Any] = [{"role": "user", "content": query}]

        emit_progress("Analyzing query...")

        # Agentic loop
        iteration = 0
        while True:
            iteration += 1
            if iteration == 1:
                emit_progress("Planning research strategy...")
            else:
                emit_progress("Continuing analysis...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=[t.to_dict() for t in active_tools],
                messages=messages,
            )

            # Track token usage from response
            if hasattr(response, "usage"):
                usage.input_tokens += response.usage.input_tokens
                usage.output_tokens += response.usage.output_tokens

            if response.stop_reason == "tool_use":
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tool_use in tool_uses:
                    # Emit progress for each tool (include store name for local searches)
                    progress_msg = self._get_tool_progress_message(tool_use.name, tool_use.input)
                    emit_progress(progress_msg)

                    result = self._execute_tool(tool_use.name, tool_use.input)

                    # Track source
                    source = self._parse_source(tool_use.name, tool_use.input, result)
                    if source:
                        sources.append(source)

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result,
                        }
                    )

                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                emit_progress("Synthesizing findings...")
                for block in response.content:
                    if hasattr(block, "text"):
                        return ResearchResult(
                            document=block.text,
                            sources=sources,
                            usage=usage,
                            model=self.model_choice,
                            model_id=self.model,
                            query=query,
                        )
                return ResearchResult(
                    document="# Error\n\nNo response generated.",
                    sources=sources,
                    usage=usage,
                    model=self.model_choice,
                    model_id=self.model,
                    query=query,
                )

            else:
                return ResearchResult(
                    document=f"# Error\n\nUnexpected stop: {response.stop_reason}",
                    sources=sources,
                    usage=usage,
                    model=self.model_choice,
                    model_id=self.model,
                    query=query,
                )

    def _build_system_prompt(self, local_stores: list[str]) -> str:
        """Build system prompt with available store information.

        Args:
            local_stores: List of available local store names

        Returns:
            Complete system prompt string
        """
        stores_section = ""
        if local_stores:
            stores_list = "\n".join(f"   - {store}" for store in local_stores)
            stores_section = f"""

IMPORTANT: You have access to the following local knowledge stores.
Search ALL of them for comprehensive results:
{stores_list}

When using search_local_knowledge, call it ONCE for EACH store."""

        return RESEARCH_SYSTEM_PROMPT + stores_section

    def _get_tool_progress_message(self, tool_name: str, inputs: dict[str, Any]) -> str:
        """Get human-readable progress message for a tool.

        Args:
            tool_name: Name of the tool being executed
            inputs: Tool input parameters

        Returns:
            Human-readable progress message
        """
        query = inputs.get("query", "")
        # Truncate long queries for display
        if len(query) > 50:
            query = query[:47] + "..."

        if tool_name == "search_local_knowledge":
            store = inputs.get("store", "unknown")
            return f'Searching {store} for "{query}"...'
        elif tool_name == "search_aws_docs":
            return f'Searching AWS docs for "{query}"...'
        elif tool_name == "search_web":
            return f'Searching the web for "{query}"...'
        elif tool_name == "glob_files":
            pattern = inputs.get("pattern", "*")
            return f'Finding files matching "{pattern}"...'
        elif tool_name == "grep_files":
            pattern = inputs.get("pattern", "")
            return f'Searching files for "{pattern}"...'
        elif tool_name == "read_file":
            path = inputs.get("path", "unknown")
            return f'Reading file "{path}"...'
        return f"Executing {tool_name}..."

    def _execute_tool(self, name: str, inputs: dict[str, Any]) -> str:
        """Execute a tool by name.

        Args:
            name: Tool name
            inputs: Tool input parameters

        Returns:
            Tool execution result as JSON string
        """
        if name == "search_local_knowledge":
            # Use the store from inputs (agent specifies which store)
            return search_local_knowledge(**inputs)
        elif name == "search_aws_docs":
            return search_aws_docs(**inputs)
        elif name == "search_web":
            return search_web(**inputs)
        elif name == "glob_files":
            return glob_files(**inputs)
        elif name == "grep_files":
            return grep_files(**inputs)
        elif name == "read_file":
            return read_file(**inputs)
        return json.dumps({"error": f"Unknown tool: {name}"})

    def _parse_source(self, tool_name: str, inputs: dict[str, Any], result: str) -> Source | None:
        """Parse tool result into a Source object.

        Args:
            tool_name: Name of the tool that was called
            inputs: Tool input parameters
            result: JSON string result from tool

        Returns:
            Source object or None if parsing fails
        """
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            return None

        # Map tool names to source types
        type_map = {
            "search_local_knowledge": "local",
            "search_aws_docs": "aws",
            "search_web": "web",
            "glob_files": "file",
            "grep_files": "file",
            "read_file": "file",
        }
        source_type = type_map.get(tool_name, "unknown")

        # Get query from inputs (varies by tool)
        query = inputs.get("query", "") or inputs.get("pattern", "") or inputs.get("path", "")

        # Count results based on tool type/response format
        result_count = 0
        if isinstance(data, list):
            # AWS knowledge tool returns array directly
            result_count = len(data)
        elif "results" in data:
            result_count = len(data["results"])
        elif "chunks" in data:
            result_count = len(data["chunks"])
        elif "citations" in data:
            # Web search returns citations
            result_count = len(data["citations"])
        elif "files" in data:
            # glob_files returns files
            result_count = len(data["files"])
        elif "matches" in data:
            # grep_files returns matches
            result_count = len(data["matches"])
        elif "content" in data and data["content"]:
            # read_file returns content
            result_count = 1

        # Get store name for local sources
        store_name = inputs.get("store") if tool_name == "search_local_knowledge" else None

        return Source(
            source_type=source_type,
            query=query,
            result_count=result_count,
            store_name=store_name,
            raw_data=data,
        )
