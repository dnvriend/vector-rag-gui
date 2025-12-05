"""Tests for settings module.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from vector_rag_gui.core.settings import (
    DEFAULT_PORT,
    DEFAULT_SPLITTER_SIZES,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_X,
    DEFAULT_WINDOW_Y,
    AgentSettings,
    ResearchSettings,
    Settings,
    WindowSettings,
    load_settings,
    save_settings,
)


class TestWindowSettings:
    """Tests for WindowSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = WindowSettings()
        assert settings.x == DEFAULT_WINDOW_X
        assert settings.y == DEFAULT_WINDOW_Y
        assert settings.width == DEFAULT_WINDOW_WIDTH
        assert settings.height == DEFAULT_WINDOW_HEIGHT
        assert settings.splitter_sizes == DEFAULT_SPLITTER_SIZES

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = WindowSettings(x=200, y=300, width=1000, height=800, splitter_sizes=[600, 200])
        assert settings.x == 200
        assert settings.y == 300
        assert settings.width == 1000
        assert settings.height == 800
        assert settings.splitter_sizes == [600, 200]


class TestAgentSettings:
    """Tests for AgentSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = AgentSettings()
        assert settings.custom_prompt == ""
        assert settings.obsidian_mode is False

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = AgentSettings(
            custom_prompt="Focus on Python best practices",
            obsidian_mode=True,
        )
        assert settings.custom_prompt == "Focus on Python best practices"
        assert settings.obsidian_mode is True


class TestResearchSettings:
    """Tests for ResearchSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = ResearchSettings()
        assert settings.research_mode is True
        assert settings.use_local is True
        assert settings.use_aws is False
        assert settings.use_web is False
        assert settings.model == "sonnet"
        assert settings.dark_mode is True
        assert settings.full_content is False

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = ResearchSettings(
            research_mode=False,
            use_local=False,
            use_aws=True,
            use_web=True,
            model="opus",
            dark_mode=False,
            full_content=True,
        )
        assert settings.research_mode is False
        assert settings.use_aws is True
        assert settings.model == "opus"


class TestSettings:
    """Tests for Settings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = Settings()
        assert settings.port == DEFAULT_PORT
        assert settings.selected_stores == []
        assert isinstance(settings.window, WindowSettings)
        assert isinstance(settings.research, ResearchSettings)
        assert isinstance(settings.agent, AgentSettings)

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        settings = Settings(
            port=9000,
            selected_stores=["store1", "store2"],
        )
        data = settings.to_dict()

        assert data["port"] == 9000
        assert data["selected_stores"] == ["store1", "store2"]
        assert "window" in data
        assert "research" in data
        assert "agent" in data
        assert data["window"]["x"] == DEFAULT_WINDOW_X
        assert data["research"]["model"] == "sonnet"
        assert data["agent"]["custom_prompt"] == ""
        assert data["agent"]["obsidian_mode"] is False

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "port": 9000,
            "selected_stores": ["mystore"],
            "window": {
                "x": 100,
                "y": 200,
                "width": 800,
                "height": 600,
                "splitter_sizes": [400, 100],
            },
            "research": {
                "research_mode": False,
                "use_local": True,
                "use_aws": True,
                "use_web": False,
                "model": "haiku",
                "dark_mode": False,
                "full_content": True,
            },
            "agent": {
                "custom_prompt": "Be concise",
                "obsidian_mode": True,
            },
        }
        settings = Settings.from_dict(data)

        assert settings.port == 9000
        assert settings.selected_stores == ["mystore"]
        assert settings.window.x == 100
        assert settings.window.splitter_sizes == [400, 100]
        assert settings.research.research_mode is False
        assert settings.research.model == "haiku"
        assert settings.agent.custom_prompt == "Be concise"
        assert settings.agent.obsidian_mode is True

    def test_from_dict_with_defaults(self) -> None:
        """Test from_dict fills in defaults for missing keys."""
        data = {"port": 8080}
        settings = Settings.from_dict(data)

        assert settings.port == 8080
        assert settings.selected_stores == []
        assert settings.window.x == DEFAULT_WINDOW_X
        assert settings.research.model == "sonnet"
        assert settings.agent.custom_prompt == ""
        assert settings.agent.obsidian_mode is False


class TestLoadSaveSettings:
    """Tests for load_settings and save_settings functions."""

    def test_load_missing_file_returns_defaults(self) -> None:
        """Test loading from non-existent file returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_file = Path(tmpdir) / "nonexistent" / "settings.json"
            with patch("vector_rag_gui.core.settings.SETTINGS_FILE", fake_file):
                settings = load_settings()

        assert settings.port == DEFAULT_PORT
        assert settings.selected_stores == []

    def test_save_and_load_roundtrip(self) -> None:
        """Test save and load roundtrip preserves data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_dir = Path(tmpdir)

            with (
                patch("vector_rag_gui.core.settings.SETTINGS_FILE", settings_file),
                patch("vector_rag_gui.core.settings.SETTINGS_DIR", settings_dir),
            ):
                # Save custom settings
                original = Settings(
                    port=9000,
                    selected_stores=["store1", "store2"],
                )
                original.window.x = 500
                original.research.model = "opus"
                original.agent.custom_prompt = "Be concise and technical"
                original.agent.obsidian_mode = True
                save_settings(original)

                # Load them back
                loaded = load_settings()

                assert loaded.port == 9000
                assert loaded.selected_stores == ["store1", "store2"]
                assert loaded.window.x == 500
                assert loaded.research.model == "opus"
                assert loaded.agent.custom_prompt == "Be concise and technical"
                assert loaded.agent.obsidian_mode is True

    def test_load_invalid_json_returns_defaults(self) -> None:
        """Test loading invalid JSON returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text("invalid json {{{", encoding="utf-8")

            with patch("vector_rag_gui.core.settings.SETTINGS_FILE", settings_file):
                settings = load_settings()

        assert settings.port == DEFAULT_PORT
