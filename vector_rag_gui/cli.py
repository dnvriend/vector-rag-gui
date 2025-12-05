"""CLI entry point for vector-rag-gui.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import sys
from pathlib import Path

import click
from PyQt6.QtGui import QIcon

from vector_rag_gui.completion import completion_command
from vector_rag_gui.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


@click.group(invoke_without_command=True)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Enable verbose output (use -v for INFO, -vv for DEBUG, -vvv for TRACE)",
)
@click.version_option(version="0.1.0")
@click.pass_context
def main(ctx: click.Context, verbose: int) -> None:
    """Vector RAG GUI - Graphical interface for searching local vector stores.

    Launches the Qt6 GUI by default when no subcommand is given.
    Provides AI-powered research synthesis using Claude via AWS Bedrock.

    Examples:

    \b
        # Launch GUI (default action)
        vector-rag-gui

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

        from PyQt6.QtWidgets import QApplication

        from vector_rag_gui.gui.main_window import MainWindow

        app = QApplication(sys.argv)

        # Set application icon
        icon_path = Path(__file__).parent / "icons" / "icon.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        window = MainWindow(default_store=None)
        window.show()
        sys.exit(app.exec())


@main.command()
@click.option("-s", "--store", help="Default store to select on startup")
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def start(store: str | None, verbose: int) -> None:
    """Launch the Vector RAG GUI.

    Opens the graphical interface for searching local vector stores.

    Examples:

    \b
        # Launch GUI
        vector-rag-gui start

    \b
        # Launch with default store selected
        vector-rag-gui start --store obsidian-knowledge-base
    """
    setup_logging(verbose)
    logger.info("Launching Vector RAG GUI")

    from PyQt6.QtWidgets import QApplication

    from vector_rag_gui.gui.main_window import MainWindow

    app = QApplication(sys.argv)

    # Set application icon
    icon_path = Path(__file__).parent / "icons" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(default_store=store)
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
