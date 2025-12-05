"""Settings management for vector-rag-gui.

Handles loading and saving application settings to ~/.config/vector-rag-gui/settings.json.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vector_rag_gui.logging_config import get_logger

logger = get_logger(__name__)

SETTINGS_DIR = Path.home() / ".config" / "vector-rag-gui"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# Default settings values
DEFAULT_PORT = 8000
DEFAULT_WINDOW_X = 100
DEFAULT_WINDOW_Y = 100
DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 700
DEFAULT_SPLITTER_SIZES = [500, 120]


@dataclass
class WindowSettings:
    """Window position and size settings."""

    x: int = DEFAULT_WINDOW_X
    y: int = DEFAULT_WINDOW_Y
    width: int = DEFAULT_WINDOW_WIDTH
    height: int = DEFAULT_WINDOW_HEIGHT
    splitter_sizes: list[int] = field(default_factory=lambda: list(DEFAULT_SPLITTER_SIZES))


@dataclass
class AgentSettings:
    """Agent prompt and behavior settings."""

    custom_prompt: str = ""  # User-defined custom instructions appended to system prompt
    obsidian_mode: bool = False  # Enable Obsidian-aware behavior


@dataclass
class ResearchSettings:
    """Research mode settings."""

    research_mode: bool = True
    use_local: bool = True
    use_aws: bool = False
    use_web: bool = False
    model: str = "sonnet"
    dark_mode: bool = True
    full_content: bool = False
    parallel_mode: bool = True  # Enable parallel subagent execution by default


@dataclass
class Settings:
    """Application settings."""

    port: int = DEFAULT_PORT
    selected_stores: list[str] = field(default_factory=list)
    window: WindowSettings = field(default_factory=WindowSettings)
    research: ResearchSettings = field(default_factory=ResearchSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary for JSON serialization."""
        return {
            "port": self.port,
            "selected_stores": self.selected_stores,
            "window": {
                "x": self.window.x,
                "y": self.window.y,
                "width": self.window.width,
                "height": self.window.height,
                "splitter_sizes": self.window.splitter_sizes,
            },
            "research": {
                "research_mode": self.research.research_mode,
                "use_local": self.research.use_local,
                "use_aws": self.research.use_aws,
                "use_web": self.research.use_web,
                "model": self.research.model,
                "dark_mode": self.research.dark_mode,
                "full_content": self.research.full_content,
                "parallel_mode": self.research.parallel_mode,
            },
            "agent": {
                "custom_prompt": self.agent.custom_prompt,
                "obsidian_mode": self.agent.obsidian_mode,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        """Create settings from dictionary."""
        window_data = data.get("window", {})
        research_data = data.get("research", {})
        agent_data = data.get("agent", {})

        window = WindowSettings(
            x=window_data.get("x", DEFAULT_WINDOW_X),
            y=window_data.get("y", DEFAULT_WINDOW_Y),
            width=window_data.get("width", DEFAULT_WINDOW_WIDTH),
            height=window_data.get("height", DEFAULT_WINDOW_HEIGHT),
            splitter_sizes=window_data.get("splitter_sizes", list(DEFAULT_SPLITTER_SIZES)),
        )

        research = ResearchSettings(
            research_mode=research_data.get("research_mode", True),
            use_local=research_data.get("use_local", True),
            use_aws=research_data.get("use_aws", False),
            use_web=research_data.get("use_web", False),
            model=research_data.get("model", "sonnet"),
            dark_mode=research_data.get("dark_mode", True),
            full_content=research_data.get("full_content", False),
            parallel_mode=research_data.get("parallel_mode", True),
        )

        agent = AgentSettings(
            custom_prompt=agent_data.get("custom_prompt", ""),
            obsidian_mode=agent_data.get("obsidian_mode", False),
        )

        return cls(
            port=data.get("port", DEFAULT_PORT),
            selected_stores=data.get("selected_stores", []),
            window=window,
            research=research,
            agent=agent,
        )


def load_settings() -> Settings:
    """Load settings from file.

    Returns:
        Settings object with loaded values or defaults if file doesn't exist.
    """
    if not SETTINGS_FILE.exists():
        logger.debug("Settings file not found, using defaults")
        return Settings()

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        settings = Settings.from_dict(data)
        logger.debug("Loaded settings from %s", SETTINGS_FILE)
        return settings
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to load settings: %s, using defaults", e)
        return Settings()


def save_settings(settings: Settings) -> None:
    """Save settings to file.

    Args:
        settings: Settings object to save.
    """
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            json.dumps(settings.to_dict(), indent=2),
            encoding="utf-8",
        )
        logger.debug("Saved settings to %s", SETTINGS_FILE)
    except OSError as e:
        logger.error("Failed to save settings: %s", e)
