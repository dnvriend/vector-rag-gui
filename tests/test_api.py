"""Tests for REST API endpoints.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vector_rag_gui.api.models import ModelChoice, ResearchRequest, ToolChoice
from vector_rag_gui.api.server import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/v1/health endpoint."""

    def test_health_check_success(self, client: TestClient) -> None:
        """Test successful health check."""
        with patch("vector_rag_gui.api.routes.list_stores") as mock_list:
            mock_list.return_value = [
                {"name": "store1", "display_name": "Store 1"},
                {"name": "store2", "display_name": "Store 2"},
            ]
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["stores_available"] is True
        assert data["store_count"] == 2

    def test_health_check_backend_failure(self, client: TestClient) -> None:
        """Test health check when backend fails."""
        with patch("vector_rag_gui.api.routes.list_stores") as mock_list:
            mock_list.side_effect = Exception("Backend unavailable")
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["stores_available"] is False
        assert data["store_count"] == 0


class TestModelsEndpoint:
    """Tests for /api/v1/models endpoint."""

    def test_list_models_success(self, client: TestClient) -> None:
        """Test successful models listing."""
        response = client.get("/api/v1/models")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["models"]) == 3

        # Check model names
        model_names = [m["name"] for m in data["models"]]
        assert "haiku" in model_names
        assert "sonnet" in model_names
        assert "opus" in model_names

        # Check model structure
        for model in data["models"]:
            assert "name" in model
            assert "description" in model
            assert "input_price" in model
            assert "output_price" in model
            assert isinstance(model["input_price"], float)
            assert isinstance(model["output_price"], float)


class TestToolsEndpoint:
    """Tests for /api/v1/tools endpoint."""

    def test_list_tools_success(self, client: TestClient) -> None:
        """Test successful tools listing."""
        response = client.get("/api/v1/tools")

        assert response.status_code == 200
        data = response.json()
        # 5 core tools + 3 optional tools = 8 total
        assert data["count"] == 8
        assert len(data["tools"]) == 8

        # Check tool structure - core tools (always enabled)
        tool_names = [t["name"] for t in data["tools"]]
        assert "glob" in tool_names
        assert "grep" in tool_names
        assert "read" in tool_names
        assert "todo_read" in tool_names
        assert "todo_write" in tool_names
        # Optional tools (toggleable)
        assert "local" in tool_names
        assert "aws" in tool_names
        assert "web" in tool_names  # enables web_search, web_fetch, extended web

        # Check categories
        categories = {t["name"]: t["category"] for t in data["tools"]}
        assert categories["local"] == "search"
        assert categories["aws"] == "search"
        assert categories["web"] == "web"
        assert categories["glob"] == "file"
        assert categories["grep"] == "file"
        assert categories["read"] == "file"
        assert categories["todo_read"] == "task"
        assert categories["todo_write"] == "task"


class TestStoresEndpoint:
    """Tests for /api/v1/stores endpoint."""

    def test_list_stores_success(self, client: TestClient) -> None:
        """Test successful store listing."""
        with patch("vector_rag_gui.api.routes.list_stores") as mock_list:
            mock_list.return_value = [
                {"name": "obsidian", "display_name": "Obsidian Knowledge Base"},
                {"name": "code", "display_name": "Code Repository"},
            ]
            response = client.get("/api/v1/stores")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["stores"]) == 2
        assert data["stores"][0]["name"] == "obsidian"
        assert data["stores"][0]["display_name"] == "Obsidian Knowledge Base"

    def test_list_stores_empty(self, client: TestClient) -> None:
        """Test store listing when no stores exist."""
        with patch("vector_rag_gui.api.routes.list_stores") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/v1/stores")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["stores"] == []

    def test_list_stores_error(self, client: TestClient) -> None:
        """Test store listing when backend fails."""
        with patch("vector_rag_gui.api.routes.list_stores") as mock_list:
            mock_list.side_effect = Exception("Database error")
            response = client.get("/api/v1/stores")

        assert response.status_code == 500


class TestResearchEndpoint:
    """Tests for /api/v1/research endpoint."""

    def test_research_request_model_defaults(self) -> None:
        """Test ResearchRequest model defaults."""
        # With defaults: stores defaults to obsidian-knowledge-base, tools defaults to [LOCAL]
        request = ResearchRequest(question="What is AWS Lambda?")
        assert request.question == "What is AWS Lambda?"
        assert request.stores == ["obsidian-knowledge-base"]  # Default store
        assert request.model == ModelChoice.SONNET
        # Default tools: only LOCAL (core tools are always enabled separately)
        assert ToolChoice.LOCAL in request.tools
        assert ToolChoice.AWS not in request.tools
        assert ToolChoice.WEB not in request.tools
        assert request.top_k == 5

    def test_research_request_custom_config(self) -> None:
        """Test ResearchRequest with custom configuration."""
        request = ResearchRequest(
            question="How do I deploy to ECS?",
            stores=["aws-docs", "internal-wiki"],
            tools=[ToolChoice.LOCAL, ToolChoice.AWS],
            model=ModelChoice.HAIKU,
            top_k=10,
        )
        assert request.question == "How do I deploy to ECS?"
        assert request.stores == ["aws-docs", "internal-wiki"]
        assert request.model == ModelChoice.HAIKU
        assert request.top_k == 10
        assert ToolChoice.WEB not in request.tools

    def test_research_endpoint_success(self, client: TestClient) -> None:
        """Test successful research request."""
        # Mock the ResearchAgent
        mock_result = MagicMock()
        mock_result.document = "# Research: Test\n\nTest content"
        mock_result.sources = []
        mock_result.usage.input_tokens = 100
        mock_result.usage.output_tokens = 50
        mock_result.usage.total_tokens = 150
        mock_result.usage.calculate_cost.return_value = 0.001
        mock_result.model.value = "sonnet"
        mock_result.model_id = "anthropic.claude-sonnet-4"
        mock_result.query = "Test question"

        with patch("vector_rag_gui.api.routes.ResearchAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.research.return_value = mock_result
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/api/v1/research",
                json={
                    "question": "What is AWS Lambda?",
                    "stores": ["test-store"],
                    "tools": ["local", "aws"],
                    "model": "sonnet",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "document" in data
        assert "sources" in data
        assert "usage" in data
        assert data["model"] == "sonnet"

    def test_research_endpoint_validation_error_empty_question(self, client: TestClient) -> None:
        """Test research request with empty question."""
        response = client.post(
            "/api/v1/research",
            json={
                "question": "",  # Empty question should fail validation
                "stores": ["test-store"],
            },
        )
        assert response.status_code == 422  # Validation error

    def test_research_endpoint_with_defaults(self, client: TestClient) -> None:
        """Test research request using default stores (stores field is now optional)."""
        # Since stores has a default value, requests without stores should use the default
        # This test ensures the default store is used
        mock_result = MagicMock()
        mock_result.document = "# Research\n\nContent"
        mock_result.sources = []
        mock_result.usage.input_tokens = 50
        mock_result.usage.output_tokens = 100
        mock_result.usage.total_tokens = 150
        mock_result.usage.calculate_cost.return_value = 0.001
        mock_result.model.value = "sonnet"
        mock_result.model_id = "anthropic.claude-sonnet"
        mock_result.query = "Test question"

        with patch("vector_rag_gui.api.routes.ResearchAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.research.return_value = mock_result
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/api/v1/research",
                json={"question": "Test question"},  # No stores - uses default
            )

        assert response.status_code == 200

    def test_research_endpoint_agent_error(self, client: TestClient) -> None:
        """Test research request when agent fails."""
        with patch("vector_rag_gui.api.routes.ResearchAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.research.side_effect = Exception("Model unavailable")
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/api/v1/research",
                json={"question": "Test question", "stores": ["test-store"]},
            )

        assert response.status_code == 500


class TestOpenAPISchema:
    """Tests for OpenAPI documentation."""

    def test_openapi_schema_available(self, client: TestClient) -> None:
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/api/v1/health" in schema["paths"]
        assert "/api/v1/models" in schema["paths"]
        assert "/api/v1/tools" in schema["paths"]
        assert "/api/v1/stores" in schema["paths"]
        assert "/api/v1/research" in schema["paths"]

    def test_swagger_docs_available(self, client: TestClient) -> None:
        """Test that Swagger UI is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client: TestClient) -> None:
        """Test that ReDoc is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
