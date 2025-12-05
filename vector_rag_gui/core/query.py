"""Query execution for vector-rag-gui.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from dataclasses import dataclass
from typing import Any

from vector_rag_tool.core.backend_factory import get_backend
from vector_rag_tool.services.querier import Querier


@dataclass
class QueryResult:
    """Result from a vector store query."""

    query: str
    store_name: str
    results: list[dict[str, Any]]
    total_results: int
    query_time: float


def query_store(
    store_name: str,
    query_text: str,
    top_k: int = 5,
    full_content: bool = False,
    snippet_length: int = 300,
) -> QueryResult:
    """Execute a query against a vector store.

    Args:
        store_name: Name of the store to query
        query_text: The search query
        top_k: Number of results to return
        full_content: If True, return full chunk content instead of snippets
        snippet_length: Max length of snippets (if full_content=False)

    Returns:
        QueryResult with matching chunks and metadata
    """
    backend = get_backend()
    querier = Querier(backend=backend)

    result = querier.query(
        store_name=store_name,
        query_text=query_text,
        top_k=top_k,
        snippet_length=snippet_length if not full_content else 10000,
    )

    # Convert to our result format
    results = []
    for chunk, score in result.get_sorted_chunks():
        results.append(
            {
                "score": score,
                "similarity_level": _get_similarity_level(score),
                "file_path": chunk.metadata.source_file if chunk.metadata else "Unknown",
                "line_start": chunk.metadata.line_start if chunk.metadata else None,
                "line_end": chunk.metadata.line_end if chunk.metadata else None,
                "content": chunk.content,
                "tags": chunk.metadata.tags if chunk.metadata else [],
                "links": chunk.metadata.links if chunk.metadata else [],
                "word_count": chunk.metadata.word_count if chunk.metadata else 0,
                "char_count": chunk.metadata.char_count if chunk.metadata else 0,
            }
        )

    return QueryResult(
        query=query_text,
        store_name=store_name,
        results=results,
        total_results=len(results),
        query_time=result.query_time,
    )


def _get_similarity_level(score: float) -> str:
    """Get human-readable similarity level from score."""
    if score >= 0.85:
        return "duplicate"
    elif score >= 0.60:
        return "very_similar"
    elif score >= 0.30:
        return "related"
    elif score >= 0.0:
        return "unrelated"
    else:
        return "contradiction"
