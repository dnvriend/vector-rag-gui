# vector-rag-gui - Project Specification

## Goal

A Qt6 GUI application for searching local vector RAG stores with markdown rendering.

## What is vector-rag-gui?

`vector-rag-gui` is a desktop application that provides a graphical interface for querying local FAISS-based vector stores managed by `vector-rag-tool`. It enables semantic document search with rich markdown result rendering, similar to `gemini-file-search-gui` but using local vector stores instead of Gemini's cloud-based File Search API.

## Technical Requirements

### Runtime

- Python 3.14+
- Installable globally with mise
- Cross-platform (macOS, Linux, Windows)

### Dependencies

- `click` - CLI framework
- `PyQt6` - Qt6 GUI framework
- `PyQt6-WebEngine` - Web rendering for markdown display
- `markdown` - Markdown to HTML conversion
- `pygments` - Syntax highlighting for code blocks
- `vector-rag-tool` - Local vector RAG backend (library dependency)

### Development Dependencies

- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pytest` - Testing framework
- `bandit` - Security linting
- `pip-audit` - Dependency vulnerability scanning
- `gitleaks` - Secret detection (requires separate installation)

## CLI Commands

```bash
vector-rag-gui [OPTIONS] COMMAND [ARGS]
```

### Global Options

- `-v, --verbose` - Enable verbose output (count flag: -v, -vv, -vvv)
- `--help` / `-h` - Show help message
- `--version` - Show version

### Commands

#### `start` - Launch GUI (default)
```bash
vector-rag-gui start [--store STORE_NAME]
```
- `--store/-s` - Default store to select on startup

#### `stores` - List available stores
```bash
vector-rag-gui stores [--json]
```
- `--json` - Output as JSON

#### `config` - Show current configuration
```bash
vector-rag-gui config
```

## Project Structure

```
vector-rag-gui/
├── vector_rag_gui/
│   ├── __init__.py
│   ├── cli.py            # Click CLI entry point (group with subcommands)
│   ├── completion.py     # Shell completion command
│   ├── logging_config.py # Multi-level verbosity logging
│   ├── icons/
│   │   └── icon.png      # Application icon (256x256)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py      # Research agent with Claude via AWS Bedrock
│   │   ├── stores.py     # Store management (list, get info)
│   │   └── query.py      # Query execution wrapper
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── aws_knowledge.py  # AWS documentation search tool
│   │   ├── file_tools.py     # Glob, grep, read file tools
│   │   ├── vector_rag.py     # Local vector store search tool
│   │   └── web_search.py     # Web search tool
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py # Qt6 main application window
│       └── worker.py      # Background query thread
├── tests/
│   ├── __init__.py
│   ├── test_core.py
│   └── test_utils.py
├── pyproject.toml        # Project configuration
├── README.md             # User documentation
├── CLAUDE.md             # This file
├── Makefile              # Development commands
├── LICENSE               # MIT License
├── .mise.toml            # mise configuration
├── .gitleaks.toml        # Gitleaks configuration
└── .gitignore
```

## GUI Features

### Main Window
- Store selector dropdown with refresh button
- Search input field with Enter key support
- QWebEngineView for GitHub-flavored markdown rendering
- Splitter layout with results view and sources panel
- Status bar showing query time and result count
- System tray integration

### Result Display
- Configurable: snippets (default) or full content (toggle)
- Syntax highlighting for code blocks (Pygments)
- Dark/Light mode toggle (Ctrl+D, default dark)

### Metadata Panel (Sources)
- File path with line numbers
- Similarity score with human-readable level
- Tags and links from chunk metadata

### Keyboard Shortcuts
- Ctrl+L: Focus search input
- Ctrl+R: Refresh stores
- Ctrl+D: Toggle dark/light mode
- Ctrl+I: Show store info
- Ctrl+M: Minimize to tray
- Ctrl+Q: Quit

## Research Agent Tools

The research agent has access to 6 tools for gathering information:

| Tool | Description |
|------|-------------|
| `search_local_knowledge` | Search local FAISS vector stores |
| `search_aws_docs` | Search AWS documentation via aws-knowledge-tool |
| `search_web` | Search the web via gemini-google-search-tool |
| `glob_files` | Find files matching glob patterns (e.g., `**/*.py`) |
| `grep_files` | Search for regex patterns in files |
| `read_file` | Read contents of a specific file |

File tools are read-only and restricted to the current working directory for security.

## Backend Integration

The GUI integrates with `vector-rag-tool` as a library dependency:

```python
# List stores
from vector_rag_tool.core.backend_factory import get_backend
backend = get_backend()
stores = backend.list_stores()

# Query a store
from vector_rag_tool.services.querier import Querier
querier = Querier(backend=backend)
result = querier.query(
    store_name="my-store",
    query_text="search query",
    top_k=5,
    snippet_length=300
)
```

### Query Result Format
```python
# QueryResult contains:
result.query            # Original query text
result.chunks           # List of Chunk objects with metadata
result.scores           # Similarity scores
result.query_time       # Query duration in seconds

# Each Chunk contains:
chunk.content           # Text content (snippet or full)
chunk.metadata.source_file     # File path
chunk.metadata.line_start      # Start line number
chunk.metadata.line_end        # End line number
chunk.metadata.tags            # List of tags
chunk.metadata.links           # List of links
chunk.metadata.word_count      # Word count
chunk.metadata.char_count      # Character count
```

## Code Style

- Type hints for all functions
- Docstrings for all public functions
- Follow PEP 8 via ruff
- 100 character line length
- Strict mypy checking

## Development Workflow

```bash
# Install dependencies
make install

# Run linting
make lint

# Format code
make format

# Type check
make typecheck

# Run tests
make test

# Security scanning
make security-bandit       # Python security linting
make security-pip-audit    # Dependency CVE scanning
make security-gitleaks     # Secret detection
make security              # Run all security checks

# Run all checks (includes security)
make check

# Full pipeline (includes security)
make pipeline
```

## Security

The template includes three lightweight security tools:

1. **bandit** - Python code security linting
   - Detects: SQL injection, hardcoded secrets, unsafe functions
   - Speed: ~2-3 seconds

2. **pip-audit** - Dependency vulnerability scanning
   - Detects: Known CVEs in dependencies
   - Speed: ~2-3 seconds

3. **gitleaks** - Secret and API key detection
   - Detects: AWS keys, GitHub tokens, API keys, private keys
   - Speed: ~1 second
   - Requires: `brew install gitleaks` (macOS)

All security checks run automatically in `make check` and `make pipeline`.

## Multi-Level Verbosity Logging

The template includes a centralized logging system with progressive verbosity levels.

### Implementation Pattern

1. **logging_config.py** - Centralized logging configuration
   - `setup_logging(verbose_count)` - Configure logging based on -v count
   - `get_logger(name)` - Get logger instance for module
   - Maps verbosity to Python logging levels (WARNING/INFO/DEBUG)

2. **CLI Integration** - Add to every CLI command
   ```python
   from vector_rag_gui.logging_config import get_logger, setup_logging

   logger = get_logger(__name__)

   @click.command()
   @click.option("-v", "--verbose", count=True, help="...")
   def command(verbose: int):
       setup_logging(verbose)  # First thing in command
       logger.info("Operation started")
       logger.debug("Detailed info")
   ```

3. **Logging Levels**
   - **0 (no -v)**: WARNING only - production/quiet mode
   - **1 (-v)**: INFO - high-level operations
   - **2 (-vv)**: DEBUG - detailed debugging
   - **3+ (-vvv)**: TRACE - enable library internals

4. **Best Practices**
   - Always log to stderr (keeps stdout clean for piping)
   - Use structured messages with placeholders: `logger.info("Found %d items", count)`
   - Call `setup_logging()` first in every command
   - Use `get_logger(__name__)` at module level
   - For TRACE level, enable third-party library loggers in `logging_config.py`

5. **Customizing Library Logging**
   Edit `logging_config.py` to add project-specific libraries:
   ```python
   if verbose_count >= 3:
       logging.getLogger("requests").setLevel(logging.DEBUG)
       logging.getLogger("urllib3").setLevel(logging.DEBUG)
   ```

## Shell Completion

The template includes shell completion for bash, zsh, and fish following the Click Shell Completion Pattern.

### Implementation

1. **completion.py** - Separate module for completion command
   - Uses Click's `BashComplete`, `ZshComplete`, `FishComplete` classes
   - Generates shell-specific completion scripts
   - Includes installation instructions in help text

2. **CLI Integration** - Added as subcommand
   ```python
   from vector_rag_gui.completion import completion_command

   @click.group(invoke_without_command=True)
   def main(ctx: click.Context):
       # Default behavior when no subcommand
       if ctx.invoked_subcommand is None:
           # Main command logic here
           pass

   # Add completion subcommand
   main.add_command(completion_command)
   ```

3. **Usage Pattern** - User-friendly command
   ```bash
   # Generate completion script
   vector-rag-gui completion bash
   vector-rag-gui completion zsh
   vector-rag-gui completion fish

   # Install (eval or save to file)
   eval "$(vector-rag-gui completion bash)"
   ```

4. **Supported Shells**
   - **Bash** (≥ 4.4) - Uses bash-completion
   - **Zsh** (any recent) - Uses zsh completion system
   - **Fish** (≥ 3.0) - Uses fish completion system
   - **PowerShell** - Not supported by Click

5. **Installation Methods**
   - **Temporary**: `eval "$(vector-rag-gui completion bash)"`
   - **Permanent**: Add eval to ~/.bashrc or ~/.zshrc
   - **File-based** (recommended): Save to dedicated completion file

### Adding More Commands

The CLI uses `@click.group()` for extensibility. To add new commands:

1. Create new command module in `vector_rag_gui/`
2. Import and add to CLI group:
   ```python
   from vector_rag_gui.new_command import new_command
   main.add_command(new_command)
   ```

3. Completion will automatically work for new commands and their options

## Installation Methods

### Global installation with mise

```bash
cd /path/to/vector-rag-gui
mise use -g python@3.14
uv sync
uv tool install .
```

After installation, `vector-rag-gui` command is available globally.

### Local development

```bash
uv sync
uv run vector-rag-gui [args]
```

## Publishing to PyPI

The template includes GitHub Actions workflow for automated PyPI publishing with trusted publishing (no API tokens required).

### Setup PyPI Trusted Publishing

1. **Create PyPI Account** at https://pypi.org/account/register/
   - Enable 2FA (required)
   - Verify email

2. **Configure Trusted Publisher** at https://pypi.org/manage/account/publishing/
   - Click "Add a new pending publisher"
   - **PyPI Project Name**: `vector-rag-gui`
   - **Owner**: `dnvriend`
   - **Repository name**: `vector-rag-gui`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`

3. **(Optional) Configure TestPyPI** at https://test.pypi.org/manage/account/publishing/
   - Same settings but use environment: `testpypi`

### Publishing Workflow

The `.github/workflows/publish.yml` workflow:
- Builds on every push
- Publishes to TestPyPI and PyPI on git tags (v*)
- Uses trusted publishing (no secrets needed)

### Create a Release

```bash
# Commit your changes
git add .
git commit -m "Release v0.1.0"
git push

# Create and push tag
git tag v0.1.0
git push origin v0.1.0
```

The workflow automatically builds and publishes to PyPI.

### Install from PyPI

After publishing, users can install with:

```bash
pip install vector-rag-gui
```

### Build Locally

```bash
# Build package with force rebuild (avoids cache issues)
make build

# Output in dist/
ls dist/
```
