"""Tests for core module functionality.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from vector_rag_gui.core.query import QueryResult, _get_similarity_level


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_query_result_creation(self) -> None:
        """Test creating a QueryResult."""
        result = QueryResult(
            query="test query",
            store_name="test-store",
            results=[],
            total_results=0,
            query_time=0.1,
        )
        assert result.query == "test query"
        assert result.store_name == "test-store"
        assert result.results == []
        assert result.total_results == 0
        assert result.query_time == 0.1

    def test_query_result_with_results(self) -> None:
        """Test QueryResult with actual results."""
        results = [
            {
                "score": 0.9,
                "similarity_level": "duplicate",
                "file_path": "test.py",
                "line_start": 10,
                "line_end": 20,
                "content": "Test content",
                "tags": ["test"],
                "links": [],
                "word_count": 2,
                "char_count": 12,
            }
        ]
        result = QueryResult(
            query="test",
            store_name="store",
            results=results,
            total_results=1,
            query_time=0.05,
        )
        assert result.total_results == 1
        assert result.results[0]["score"] == 0.9


class TestSimilarityLevel:
    """Tests for _get_similarity_level function."""

    def test_duplicate_level(self) -> None:
        """Test duplicate similarity level (>= 0.85)."""
        assert _get_similarity_level(0.90) == "duplicate"
        assert _get_similarity_level(0.85) == "duplicate"
        assert _get_similarity_level(1.0) == "duplicate"

    def test_very_similar_level(self) -> None:
        """Test very_similar level (>= 0.60, < 0.85)."""
        assert _get_similarity_level(0.70) == "very_similar"
        assert _get_similarity_level(0.60) == "very_similar"
        assert _get_similarity_level(0.84) == "very_similar"

    def test_related_level(self) -> None:
        """Test related level (>= 0.30, < 0.60)."""
        assert _get_similarity_level(0.40) == "related"
        assert _get_similarity_level(0.30) == "related"
        assert _get_similarity_level(0.59) == "related"

    def test_unrelated_level(self) -> None:
        """Test unrelated level (>= 0.0, < 0.30)."""
        assert _get_similarity_level(0.10) == "unrelated"
        assert _get_similarity_level(0.0) == "unrelated"
        assert _get_similarity_level(0.29) == "unrelated"

    def test_contradiction_level(self) -> None:
        """Test contradiction level (< 0.0)."""
        assert _get_similarity_level(-0.1) == "contradiction"
        assert _get_similarity_level(-0.5) == "contradiction"
        assert _get_similarity_level(-1.0) == "contradiction"
