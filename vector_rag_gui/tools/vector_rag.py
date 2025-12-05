"""Vector RAG tool wrapper for Claude Agent SDK.

Provides search functionality for local vector stores using vector-rag-tool.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json

from anthropic import beta_tool


@beta_tool
def search_local_knowledge(
    query: str, store: str = "obsidian-knowledge-base", top_k: int = 3
) -> str:
    """Search local vector RAG store for internal documentation and notes.

    Args:
        query: Natural language search query
        store: Vector store name (default: obsidian-knowledge-base)
        top_k: Number of results to return (default: 3)

    Returns:
        JSON string with relevant document chunks and metadata
    """
    try:
        from vector_rag_tool.core.backend_factory import get_backend
        from vector_rag_tool.services.querier import Querier

        backend = get_backend()
        querier = Querier(backend=backend)
        result = querier.query(store_name=store, query_text=query, top_k=top_k)

        formatted = []
        for chunk, score in result.get_sorted_chunks():
            formatted.append(
                {
                    "source": chunk.metadata.source_file if chunk.metadata else "Unknown",
                    "lines": (
                        f"{chunk.metadata.line_start}-{chunk.metadata.line_end}"
                        if chunk.metadata
                        else None
                    ),
                    "relevance": round(float(score), 3),
                    "content": chunk.content[:500],  # Truncate for token efficiency
                }
            )

        return json.dumps({"results": formatted, "total": len(formatted)})

    except Exception as e:
        return json.dumps({"error": str(e), "error_type": type(e).__name__, "results": []})
