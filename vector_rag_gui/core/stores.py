"""Store management for vector-rag-gui.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from typing import Any

from vector_rag_tool.core.backend_factory import get_backend


def list_stores() -> list[dict[str, Any]]:
    """List all available local vector stores.

    Returns:
        List of store dictionaries with 'name' and 'display_name' keys.
    """
    backend = get_backend()
    stores = backend.list_stores()
    return [{"name": name, "display_name": name} for name in stores]


def get_store_info(store_name: str) -> dict[str, Any]:
    """Get detailed information about a store.

    Args:
        store_name: Name of the store

    Returns:
        Dictionary with store information (vector_count, dimension, etc.)
    """
    backend = get_backend()
    result: dict[str, Any] = backend.get_store_info(store_name)
    return result
