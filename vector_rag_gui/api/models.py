"""Pydantic models for the REST API.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ModelChoice(str, Enum):
    """Available model choices for synthesis."""

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


class ToolChoice(str, Enum):
    """Available optional tool choices for research.

    Core tools (glob, grep, read, todo_read, todo_write) are always enabled.
    """

    # Optional tools that can be enabled/disabled
    LOCAL = "local"  # Local RAG vector stores (default: enabled)
    AWS = "aws"  # AWS documentation (default: disabled)
    WEB = "web"  # Web tools: web_search, web_fetch, extended web (default: disabled)


class ResearchRequest(BaseModel):
    """Request model for research synthesis endpoint.

    Core tools are always enabled:
    - glob, grep, read (file operations)
    - todo_read, todo_write (task tracking)

    Optional tools can be toggled:
    - local: RAG vector stores (default: enabled)
    - aws: AWS documentation (default: disabled)
    - web: Web tools (web_search, web_fetch, extended web) (default: disabled)
    """

    question: str = Field(..., description="Research question or topic", min_length=1)
    stores: list[str] = Field(
        default_factory=lambda: ["obsidian-knowledge-base"],
        description="List of local vector store names to query",
    )
    tools: list[ToolChoice] = Field(
        default_factory=lambda: [ToolChoice.LOCAL],
        description="Optional tools to enable (default: local). Core tools always enabled.",
    )
    model: ModelChoice = Field(
        default=ModelChoice.SONNET,
        description="Claude model to use for synthesis (default: sonnet)",
    )
    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of results to retrieve per source"
    )


class SourceInfo(BaseModel):
    """Information about a source used during research."""

    source_type: str = Field(..., description="Type of source (local, aws, web, file)")
    query: str = Field(..., description="Query used to search this source")
    result_count: int = Field(..., description="Number of results returned")
    store_name: str | None = Field(None, description="Store name for local sources")


class TokenUsageInfo(BaseModel):
    """Token usage statistics."""

    input_tokens: int = Field(..., description="Number of input tokens used")
    output_tokens: int = Field(..., description="Number of output tokens used")
    total_tokens: int = Field(..., description="Total tokens used")
    cost_usd: float = Field(..., description="Estimated cost in USD")


class ResearchResponse(BaseModel):
    """Response model for research synthesis endpoint."""

    document: str = Field(..., description="Synthesized markdown research document")
    sources: list[SourceInfo] = Field(..., description="Sources consulted during research")
    usage: TokenUsageInfo = Field(..., description="Token usage statistics")
    model: str = Field(..., description="Model used for synthesis")
    model_id: str = Field(..., description="Full model ID/ARN")
    query: str = Field(..., description="Original research query")


class StoreInfo(BaseModel):
    """Information about a vector store."""

    name: str = Field(..., description="Store name (identifier)")
    display_name: str = Field(..., description="Human-readable store name")


class StoresResponse(BaseModel):
    """Response model for list stores endpoint."""

    stores: list[StoreInfo] = Field(..., description="List of available stores")
    count: int = Field(..., description="Number of stores")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Health status (healthy/unhealthy)")
    version: str = Field(..., description="API version")
    stores_available: bool = Field(..., description="Whether stores backend is accessible")
    store_count: int = Field(0, description="Number of available stores")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Detailed error information")


class ToolInfo(BaseModel):
    """Information about an available tool."""

    name: str = Field(..., description="Tool identifier")
    description: str = Field(..., description="What this tool does")
    category: str = Field(..., description="Tool category (search, file)")


class ToolsResponse(BaseModel):
    """Response model for list tools endpoint."""

    tools: list[ToolInfo] = Field(..., description="List of available tools")
    count: int = Field(..., description="Number of tools")


class ModelInfo(BaseModel):
    """Information about an available model."""

    name: str = Field(..., description="Model identifier (haiku, sonnet, opus)")
    description: str = Field(..., description="What this model is best for")
    input_price: float = Field(..., description="Price per 1M input tokens (USD)")
    output_price: float = Field(..., description="Price per 1M output tokens (USD)")


class ModelsResponse(BaseModel):
    """Response model for list models endpoint."""

    models: list[ModelInfo] = Field(..., description="List of available models")
    count: int = Field(..., description="Number of models")
