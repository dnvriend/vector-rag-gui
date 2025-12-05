"""CLI entry point for vector-rag-gui.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import sys
import threading
from pathlib import Path

import click
from PyQt6.QtGui import QIcon

from vector_rag_gui.completion import completion_command
from vector_rag_gui.core.settings import load_settings
from vector_rag_gui.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def _is_port_in_use(port: int) -> bool:
    """Check if a port is already in use.

    Args:
        port: Port number to check

    Returns:
        True if port is in use, False otherwise
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _find_available_port(start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port.

    Args:
        start_port: Port to start searching from
        max_attempts: Maximum number of ports to try

    Returns:
        Available port number
    """
    for offset in range(max_attempts):
        port = start_port + offset
        if not _is_port_in_use(port):
            return port
    # If all ports are taken, return the last tried port (will fail on bind)
    return start_port + max_attempts - 1


def _print_banner(port: int) -> None:
    """Print startup banner with API info."""
    click.echo("")
    click.echo("╭─────────────────────────────────────────╮")
    click.echo("│         Vector RAG GUI v0.1.0           │")
    click.echo("├─────────────────────────────────────────┤")
    click.echo(f"│  REST API: http://127.0.0.1:{port:<5}        │")
    click.echo(f"│  Swagger:  http://127.0.0.1:{port}/docs     │")
    click.echo("╰─────────────────────────────────────────╯")
    click.echo("")


def _start_api_server(port: int) -> None:
    """Start the API server in a background thread."""
    import uvicorn

    from vector_rag_gui.api.server import create_app

    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


@click.group(invoke_without_command=True)
@click.option(
    "-p",
    "--port",
    type=int,
    default=None,
    help="REST API port (default: from settings or 8000)",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Enable verbose output (use -v for INFO, -vv for DEBUG, -vvv for TRACE)",
)
@click.version_option(version="0.1.0")
@click.pass_context
def main(ctx: click.Context, port: int | None, verbose: int) -> None:
    """Vector RAG GUI - Graphical interface for searching local vector stores.

    Launches the Qt6 GUI by default when no subcommand is given.
    Provides AI-powered research synthesis using Claude via AWS Bedrock.

    Examples:

    \b
        # Launch GUI (default action)
        vector-rag-gui

    \b
        # Launch with custom API port
        vector-rag-gui --port 9000

    \b
        # Launch with verbose logging
        vector-rag-gui -v

    \b
        # List available vector stores
        vector-rag-gui stores

    \b
        # Show configuration
        vector-rag-gui config
    """
    # Setup logging based on verbosity count
    setup_logging(verbose)

    # If no subcommand is provided, launch the GUI
    if ctx.invoked_subcommand is None:
        logger.info("Launching Vector RAG GUI")
        logger.debug("Running with verbose level: %d", verbose)

        # Load settings
        settings = load_settings()

        # Use port from CLI, or from settings, or default
        requested_port = port or settings.port

        # Find available port (auto-increment if taken)
        api_port = _find_available_port(requested_port)
        if api_port != requested_port:
            logger.info("Port %d in use, using port %d", requested_port, api_port)

        # Print banner
        _print_banner(api_port)

        # Start API server in background thread
        api_thread = threading.Thread(target=_start_api_server, args=(api_port,), daemon=True)
        api_thread.start()
        logger.info("REST API server started on port %d", api_port)

        from PyQt6.QtWidgets import QApplication

        from vector_rag_gui.gui.main_window import MainWindow

        app = QApplication(sys.argv)

        # Set application icon
        icon_path = Path(__file__).parent / "icons" / "icon.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        window = MainWindow(default_store=None, settings=settings)
        window.show()
        sys.exit(app.exec())


@main.command()
@click.option("-s", "--store", help="Default store to select on startup")
@click.option("-p", "--port", type=int, default=None, help="REST API port")
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def start(store: str | None, port: int | None, verbose: int) -> None:
    """Launch the Vector RAG GUI.

    Opens the graphical interface for searching local vector stores.

    Examples:

    \b
        # Launch GUI
        vector-rag-gui start

    \b
        # Launch with default store selected
        vector-rag-gui start --store obsidian-knowledge-base

    \b
        # Launch with custom API port
        vector-rag-gui start --port 9000
    """
    setup_logging(verbose)
    logger.info("Launching Vector RAG GUI")

    # Load settings
    settings = load_settings()
    requested_port = port or settings.port

    # Find available port (auto-increment if taken)
    api_port = _find_available_port(requested_port)
    if api_port != requested_port:
        logger.info("Port %d in use, using port %d", requested_port, api_port)

    # Print banner
    _print_banner(api_port)

    # Start API server in background thread
    api_thread = threading.Thread(target=_start_api_server, args=(api_port,), daemon=True)
    api_thread.start()
    logger.info("REST API server started on port %d", api_port)

    from PyQt6.QtWidgets import QApplication

    from vector_rag_gui.gui.main_window import MainWindow

    app = QApplication(sys.argv)

    # Set application icon
    icon_path = Path(__file__).parent / "icons" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(default_store=store, settings=settings)
    window.show()
    sys.exit(app.exec())


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def stores(as_json: bool, verbose: int) -> None:
    """List available local vector stores.

    Displays all vector stores available for searching. Use --json for
    machine-readable output suitable for scripting and automation.

    Examples:

    \b
        # List stores in human-readable format
        vector-rag-gui stores

    \b
        # Output as JSON for scripting
        vector-rag-gui stores --json

    \b
        # Pipe to jq for filtering
        vector-rag-gui stores --json | jq '.[].display_name'

    \b
    Output Format (--json):
        [
          {"name": "store-name", "display_name": "Store Name"},
          ...
        ]
    """
    setup_logging(verbose)
    import json

    from vector_rag_gui.core.stores import list_stores

    logger.info("Listing available stores")
    store_list = list_stores()

    if as_json:
        click.echo(json.dumps(store_list, indent=2))
    else:
        if not store_list:
            click.echo("No stores found")
            return
        click.echo(f"Found {len(store_list)} stores:")
        for s in store_list:
            click.echo(f"  - {s['display_name']}")


@main.command()
@click.option("-h", "--host", default="127.0.0.1", help="Host address to bind to")
@click.option("-p", "--port", default=8000, type=int, help="Port number to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def serve(host: str, port: int, reload: bool, verbose: int) -> None:
    """Start the REST API server.

    Launches a FastAPI server for programmatic access to research synthesis.
    The API provides endpoints for health checks, listing stores, and executing
    research queries.

    Examples:

    \b
        # Start server on default port 8000
        vector-rag-gui serve

    \b
        # Start on custom host and port
        vector-rag-gui serve --host 0.0.0.0 --port 8080

    \b
        # Start with auto-reload for development
        vector-rag-gui serve --reload

    \b
    API Endpoints:
        GET  /api/v1/health   - Health check
        GET  /api/v1/stores   - List available stores
        POST /api/v1/research - Execute research synthesis

    \b
    OpenAPI docs available at:
        http://localhost:8000/docs (Swagger UI)
        http://localhost:8000/redoc (ReDoc)
    """
    setup_logging(verbose)
    logger.info("Starting API server on %s:%d", host, port)

    from vector_rag_gui.api.server import run_server

    run_server(host=host, port=port, reload=reload)


@main.command()
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def config(verbose: int) -> None:
    """Show current configuration.

    Displays the current configuration including store location and
    environment settings for AWS Bedrock integration.

    Examples:

    \b
        # Show current configuration
        vector-rag-gui config

    \b
        # Show with verbose details
        vector-rag-gui config -v

    \b
    Output:
        Vector RAG GUI Configuration
          Store location: ~/.config/vector-rag-tool/stores
          Store exists: True
    """
    setup_logging(verbose)
    from pathlib import Path

    logger.info("Displaying configuration")
    store_path = Path.home() / ".config" / "vector-rag-tool" / "stores"

    click.echo("Vector RAG GUI Configuration")
    click.echo(f"  Store location: {store_path}")
    click.echo(f"  Store exists: {store_path.exists()}")


# Add completion subcommand
main.add_command(completion_command)


if __name__ == "__main__":
    main()
