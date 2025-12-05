"""REST API routes for vector-rag-gui.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from fastapi import APIRouter, HTTPException

from vector_rag_gui.api.models import (
    ErrorResponse,
    HealthResponse,
    ModelInfo,
    ModelsResponse,
    ResearchRequest,
    ResearchResponse,
    SourceInfo,
    StoreInfo,
    StoresResponse,
    TokenUsageInfo,
    ToolChoice,
    ToolInfo,
    ToolsResponse,
)
from vector_rag_gui.core.agent import ModelChoice as AgentModelChoice
from vector_rag_gui.core.agent import ResearchAgent
from vector_rag_gui.core.stores import list_stores
from vector_rag_gui.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check API health and backend availability",
)
async def health_check() -> HealthResponse:
    """Check API health and stores backend availability."""
    try:
        stores = list_stores()
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            stores_available=True,
            store_count=len(stores),
        )
    except Exception as e:
        logger.warning("Health check failed: %s", e)
        return HealthResponse(
            status="unhealthy",
            version="0.1.0",
            stores_available=False,
            store_count=0,
        )


# Core tools - always enabled, cannot be disabled
CORE_TOOLS = [
    ToolInfo(
        name="glob",
        description="Find files matching glob patterns (e.g., '**/*.py')",
        category="file",
    ),
    ToolInfo(
        name="grep",
        description="Search for regex patterns in files",
        category="file",
    ),
    ToolInfo(
        name="read",
        description="Read contents of a specific file",
        category="file",
    ),
    ToolInfo(
        name="todo_read",
        description="Read current task list",
        category="task",
    ),
    ToolInfo(
        name="todo_write",
        description="Update task list",
        category="task",
    ),
]

# Optional tools - can be enabled/disabled
OPTIONAL_TOOLS = [
    ToolInfo(
        name="local",
        description="Search local FAISS vector stores (notes, code, internal docs)",
        category="search",
    ),
    ToolInfo(
        name="aws",
        description="Search official AWS documentation via aws-knowledge-tool",
        category="search",
    ),
    ToolInfo(
        name="web",
        description="Web tools: web_search, web_fetch, extended web research (default: off)",
        category="web",
    ),
]

# Combined list for API
AVAILABLE_TOOLS = CORE_TOOLS + OPTIONAL_TOOLS


@router.get(
    "/tools",
    response_model=ToolsResponse,
    summary="List tools",
    description="List all available research tools",
)
async def get_tools() -> ToolsResponse:
    """List all available research tools."""
    return ToolsResponse(tools=AVAILABLE_TOOLS, count=len(AVAILABLE_TOOLS))


AVAILABLE_MODELS = [
    ModelInfo(
        name="haiku",
        description="Fast and cost-effective for simple queries",
        input_price=0.80,
        output_price=4.00,
    ),
    ModelInfo(
        name="sonnet",
        description="Balanced performance and cost (recommended)",
        input_price=3.00,
        output_price=15.00,
    ),
    ModelInfo(
        name="opus",
        description="Highest capability for complex research",
        input_price=15.00,
        output_price=75.00,
    ),
]


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List models",
    description="List all available Claude models for synthesis",
)
async def get_models() -> ModelsResponse:
    """List all available Claude models."""
    return ModelsResponse(models=AVAILABLE_MODELS, count=len(AVAILABLE_MODELS))


@router.get(
    "/stores",
    response_model=StoresResponse,
    summary="List stores",
    description="List all available local vector stores",
)
async def get_stores() -> StoresResponse:
    """List all available local vector stores."""
    try:
        stores = list_stores()
        return StoresResponse(
            stores=[StoreInfo(name=s["name"], display_name=s["display_name"]) for s in stores],
            count=len(stores),
        )
    except Exception as e:
        logger.error("Failed to list stores: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/research",
    response_model=ResearchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Research failed"},
    },
    summary="Execute research synthesis",
    description="Execute a research query using Claude and return synthesized markdown",
)
async def research(request: ResearchRequest) -> ResearchResponse:
    """Execute research synthesis using the research agent.

    Args:
        request: Research request with question, tools, stores, and model selection

    Returns:
        ResearchResponse with synthesized document and metadata
    """
    logger.info("Research request: question=%r, model=%s", request.question, request.model.value)

    # Map API model choice to agent model choice
    model_map = {
        "haiku": AgentModelChoice.HAIKU,
        "sonnet": AgentModelChoice.SONNET,
        "opus": AgentModelChoice.OPUS,
    }
    agent_model = model_map.get(request.model.value, AgentModelChoice.SONNET)

    # Determine which tools to enable
    use_local = ToolChoice.LOCAL in request.tools
    use_aws = ToolChoice.AWS in request.tools
    use_web = ToolChoice.WEB in request.tools

    try:
        agent = ResearchAgent(model_choice=agent_model)
        result = agent.research(
            query=request.question,
            use_local=use_local,
            use_aws=use_aws,
            use_web=use_web,
            local_stores=request.stores if use_local else None,
        )

        # Convert sources to API format
        sources = [
            SourceInfo(
                source_type=s.source_type,
                query=s.query,
                result_count=s.result_count,
                store_name=s.store_name,
            )
            for s in result.sources
        ]

        # Calculate cost
        cost = result.usage.calculate_cost(result.model)

        return ResearchResponse(
            document=result.document,
            sources=sources,
            usage=TokenUsageInfo(
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                total_tokens=result.usage.total_tokens,
                cost_usd=round(cost, 6),
            ),
            model=result.model.value,
            model_id=result.model_id,
            query=result.query,
        )
    except Exception as e:
        logger.error("Research failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
