"""SDK-compatible tools for Claude Agent SDK.

Provides tools wrapped with the @tool decorator for use with
create_sdk_mcp_server() and Claude Agent SDK subagents.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from typing import Any

# Import from claude_agent_sdk (installed as dependency)
from claude_agent_sdk import create_sdk_mcp_server, tool

# Import existing tool implementations
from vector_rag_gui.tools.aws_knowledge import search_aws_docs as _search_aws_docs
from vector_rag_gui.tools.file_tools import (
    glob_files as _glob_files,
)
from vector_rag_gui.tools.file_tools import (
    grep_files as _grep_files,
)
from vector_rag_gui.tools.file_tools import (
    read_file as _read_file,
)
from vector_rag_gui.tools.vector_rag import (
    search_local_knowledge as _search_local_knowledge,
)
from vector_rag_gui.tools.web_search import search_web as _search_web


@tool(
    "search_rag",
    "Search local vector RAG stores for internal documentation",
    {
        "query": str,
        "store": str,
        "top_k": int,
    },
)
async def search_rag_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Search local vector store for documents.

    Args:
        args: Dict with query, store, and top_k parameters

    Returns:
        MCP-compatible response with text content
    """
    query = args.get("query", "")
    store = args.get("store", "obsidian-knowledge-base")
    top_k = args.get("top_k", 5)

    result = _search_local_knowledge(query=query, store=store, top_k=top_k)

    return {"content": [{"type": "text", "text": result}]}


@tool(
    "search_aws",
    "Search AWS documentation for official guidance",
    {
        "query": str,
    },
)
async def search_aws_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Search AWS documentation.

    Args:
        args: Dict with query parameter

    Returns:
        MCP-compatible response with text content
    """
    query = args.get("query", "")

    result = _search_aws_docs(query=query)

    return {"content": [{"type": "text", "text": result}]}


@tool(
    "search_web",
    "Search the web for current information",
    {
        "query": str,
    },
)
async def search_web_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Search the web.

    Args:
        args: Dict with query parameter

    Returns:
        MCP-compatible response with text content
    """
    query = args.get("query", "")

    result = _search_web(query=query)

    return {"content": [{"type": "text", "text": result}]}


@tool(
    "glob_files",
    "Find files matching a glob pattern",
    {
        "pattern": str,
        "directory": str,
    },
)
async def glob_files_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Find files matching glob pattern.

    Args:
        args: Dict with pattern and optional directory parameters

    Returns:
        MCP-compatible response with text content
    """
    pattern = args.get("pattern", "*")
    directory = args.get("directory")

    result = _glob_files(pattern=pattern, directory=directory)

    return {"content": [{"type": "text", "text": result}]}


@tool(
    "grep_files",
    "Search for regex patterns in files",
    {
        "pattern": str,
        "glob_pattern": str,
        "directory": str,
        "case_insensitive": bool,
    },
)
async def grep_files_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Search for regex patterns in files.

    Args:
        args: Dict with pattern, glob_pattern, directory, case_insensitive parameters

    Returns:
        MCP-compatible response with text content
    """
    pattern = args.get("pattern", "")
    glob_pattern = args.get("glob_pattern", "**/*")
    directory = args.get("directory")
    case_insensitive = args.get("case_insensitive", False)

    result = _grep_files(
        pattern=pattern,
        glob_pattern=glob_pattern,
        directory=directory,
        case_insensitive=case_insensitive,
    )

    return {"content": [{"type": "text", "text": result}]}


@tool(
    "read_file",
    "Read contents of a specific file",
    {
        "path": str,
        "start_line": int,
        "end_line": int,
    },
)
async def read_file_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Read file contents.

    Args:
        args: Dict with path, start_line, end_line parameters

    Returns:
        MCP-compatible response with text content
    """
    path = args.get("path", "")
    start_line = args.get("start_line")
    end_line = args.get("end_line")

    result = _read_file(path=path, start_line=start_line, end_line=end_line)

    return {"content": [{"type": "text", "text": result}]}


# All SDK-compatible tools
SDK_TOOLS = [
    search_rag_tool,
    search_aws_tool,
    search_web_tool,
    glob_files_tool,
    grep_files_tool,
    read_file_tool,
]


def create_research_tools_server() -> Any:
    """Create MCP server with all research tools.

    Returns:
        MCP server instance or None if SDK not available
    """
    return create_sdk_mcp_server(
        name="research-tools",
        version="1.0.0",
        tools=SDK_TOOLS,
    )
