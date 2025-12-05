"""FastAPI server configuration for vector-rag-gui.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vector_rag_gui.api.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Vector RAG API",
        description="REST API for research synthesis using local vector stores and Claude",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router, prefix="/api/v1", tags=["research"])

    return app


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Run the API server using uvicorn.

    Args:
        host: Host address to bind to
        port: Port number to listen on
        reload: Enable auto-reload for development
    """
    import uvicorn

    uvicorn.run(
        "vector_rag_gui.api.server:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )
