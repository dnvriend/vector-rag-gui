"""Tools for Claude Agent SDK integration.

This module contains tool wrappers for various knowledge sources:
- vector_rag: Local vector store search
- aws_knowledge: AWS documentation search
- web_search: Web search via Google

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from vector_rag_gui.tools.aws_knowledge import search_aws_docs
from vector_rag_gui.tools.vector_rag import search_local_knowledge
from vector_rag_gui.tools.web_search import search_web

__all__ = ["search_local_knowledge", "search_aws_docs", "search_web"]
