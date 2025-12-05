"""Background worker threads for query execution and research synthesis.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import anyio
from PyQt6.QtCore import QThread, pyqtSignal

from vector_rag_gui.core.query import query_store


class QueryWorker(QThread):
    """Background worker for executing vector store queries.

    Executes queries in a separate thread to keep the UI responsive.

    Signals:
        finished: Emitted with QueryResult when query completes
        error: Emitted with error message string on failure
    """

    finished = pyqtSignal(object)  # QueryResult
    error = pyqtSignal(str)

    def __init__(
        self,
        store_name: str,
        query: str,
        top_k: int = 5,
        full_content: bool = False,
        snippet_length: int = 300,
    ) -> None:
        """Initialize query worker.

        Args:
            store_name: Name of the store to query
            query: Search query text
            top_k: Number of results to return
            full_content: If True, return full content instead of snippets
            snippet_length: Max snippet length
        """
        super().__init__()
        self.store_name = store_name
        self.query = query
        self.top_k = top_k
        self.full_content = full_content
        self.snippet_length = snippet_length

    def run(self) -> None:
        """Execute the query in background thread."""
        try:
            result = query_store(
                store_name=self.store_name,
                query_text=self.query,
                top_k=self.top_k,
                full_content=self.full_content,
                snippet_length=self.snippet_length,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ResearchWorker(QThread):
    """Background worker for executing research queries with agent synthesis.

    Uses AWS Bedrock as the backend for Claude model access.

    Signals:
        finished: Emitted with ResearchResult object when complete
        progress: Emitted with status updates during execution
        error: Emitted with error message string on failure
    """

    finished = pyqtSignal(object)  # ResearchResult
    progress = pyqtSignal(str)  # Status updates
    error = pyqtSignal(str)

    def __init__(
        self,
        query: str,
        model_choice: str = "sonnet",
        use_local: bool = True,
        use_aws: bool = True,
        use_web: bool = True,
        local_stores: list[str] | None = None,
    ) -> None:
        """Initialize research worker.

        Args:
            query: Research question or topic
            model_choice: Model to use for synthesis ("haiku", "sonnet", "opus")
            use_local: Enable local vector store search
            use_aws: Enable AWS documentation search
            use_web: Enable web search
            local_stores: List of local vector store names to query
        """
        super().__init__()
        self.query = query
        self.model_choice = model_choice
        self.use_local = use_local
        self.use_aws = use_aws
        self.use_web = use_web
        self.local_stores = local_stores or ["obsidian-knowledge-base"]

    def run(self) -> None:
        """Execute research query in background thread."""
        try:
            self.progress.emit(f"Initializing {self.model_choice.capitalize()} agent...")

            from vector_rag_gui.core.agent import ModelChoice, ResearchAgent

            # Map string to enum
            model_map = {
                "haiku": ModelChoice.HAIKU,
                "sonnet": ModelChoice.SONNET,
                "opus": ModelChoice.OPUS,
            }
            model = model_map.get(self.model_choice.lower(), ModelChoice.SONNET)

            agent = ResearchAgent(model_choice=model)

            # Pass progress callback to agent
            result = agent.research(
                query=self.query,
                use_local=self.use_local,
                use_aws=self.use_aws,
                use_web=self.use_web,
                local_stores=self.local_stores,
                on_progress=self._emit_progress,
            )

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

    def _emit_progress(self, message: str) -> None:
        """Emit progress signal from agent callback.

        Args:
            message: Progress message to emit
        """
        self.progress.emit(message)


class ParallelResearchWorker(QThread):
    """Background worker for parallel research using SDK subagents.

    Uses Claude Agent SDK with parallel subagent execution for faster research.
    Implements map-reduce pattern: parallel data gathering, then synthesis.

    Signals:
        finished: Emitted with ResearchResult object when complete
        progress: Emitted with status updates during execution
        error: Emitted with error message string on failure
    """

    finished = pyqtSignal(object)  # ResearchResult
    progress = pyqtSignal(str)  # Status updates
    error = pyqtSignal(str)

    def __init__(
        self,
        query: str,
        model_choice: str = "sonnet",
        use_local: bool = True,
        use_aws: bool = True,
        use_web: bool = True,
        local_stores: list[str] | None = None,
        custom_prompt: str = "",
        obsidian_mode: bool = False,
    ) -> None:
        """Initialize parallel research worker.

        Args:
            query: Research question or topic
            model_choice: Model to use for synthesis ("haiku", "sonnet", "opus")
            use_local: Enable local vector store search
            use_aws: Enable AWS documentation search
            use_web: Enable web search
            local_stores: List of local vector store names to query
            custom_prompt: Optional custom instructions to append to system prompt
            obsidian_mode: Enable Obsidian-aware behavior with vault knowledge
        """
        super().__init__()
        self.query = query
        self.model_choice = model_choice
        self.use_local = use_local
        self.use_aws = use_aws
        self.use_web = use_web
        self.local_stores = local_stores or ["obsidian-knowledge-base"]
        self.custom_prompt = custom_prompt
        self.obsidian_mode = obsidian_mode

    def run(self) -> None:
        """Execute parallel research in background thread."""
        try:
            self.progress.emit("Starting parallel research agents...")

            from vector_rag_gui.core.sdk_agent import SDKModelChoice, SDKResearchAgent

            # Map string to enum
            model_map = {
                "haiku": SDKModelChoice.HAIKU,
                "sonnet": SDKModelChoice.SONNET,
                "opus": SDKModelChoice.OPUS,
            }
            model = model_map.get(self.model_choice.lower(), SDKModelChoice.SONNET)

            agent = SDKResearchAgent(
                model_choice=model,
                custom_prompt=self.custom_prompt,
                obsidian_mode=self.obsidian_mode,
            )

            # Create async wrapper and run with anyio
            async def run_research() -> object:
                return await agent.research(
                    query=self.query,
                    use_local=self.use_local,
                    use_aws=self.use_aws,
                    use_web=self.use_web,
                    local_stores=self.local_stores,
                    on_progress=self._emit_progress,
                )

            result = anyio.run(run_research)

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

    def _emit_progress(self, message: str) -> None:
        """Emit progress signal from agent callback.

        Args:
            message: Progress message to emit
        """
        self.progress.emit(message)
