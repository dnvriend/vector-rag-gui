"""Main window for Vector RAG GUI.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import markdown
from pygments.formatters import HtmlFormatter
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QCloseEvent,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vector_rag_gui.core.agent import ResearchResult
from vector_rag_gui.core.query import QueryResult
from vector_rag_gui.core.settings import Settings, load_settings, save_settings
from vector_rag_gui.gui.worker import ParallelResearchWorker, QueryWorker, ResearchWorker
from vector_rag_gui.logging_config import get_logger

logger = get_logger(__name__)

# Default store to select if available
DEFAULT_STORE = "obsidian-knowledge-base"


class MainWindow(QMainWindow):
    """Main application window with search UI and markdown rendering."""

    def __init__(self, default_store: str | None = None, settings: Settings | None = None) -> None:
        """Initialize main window.

        Args:
            default_store: Optional store name to select on startup
            settings: Optional settings object (loads from file if not provided)
        """
        super().__init__()
        self.settings = settings or load_settings()
        self.default_store = default_store or DEFAULT_STORE
        self.worker: QueryWorker | ResearchWorker | ParallelResearchWorker | None = None
        self.stores: list[dict[str, str]] = []
        self.stores_menu: QMenu  # Initialized in _init_menu
        self.splitter: QSplitter  # Initialized in _init_ui

        # Load settings
        self.dark_mode: bool = self.settings.research.dark_mode
        self.full_content: bool = self.settings.research.full_content
        self.research_mode: bool = self.settings.research.research_mode
        self.use_local: bool = self.settings.research.use_local
        self.use_aws: bool = self.settings.research.use_aws
        self.use_web: bool = self.settings.research.use_web
        self._selected_stores: list[str] = list(self.settings.selected_stores)

        self._last_result: ResearchResult | None = None  # Last research result for export
        # Status message queue for minimum display time
        self._status_queue: list[str] = []
        self._status_timer: QTimer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._process_status_queue)
        self._status_busy: bool = False
        self._init_ui()
        self._init_menu()
        self._init_tray()
        self._load_stores()
        self._restore_window_geometry()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Vector RAG GUI")
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumSize(600, 400)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Selected stores loaded from settings in __init__

        # Research mode controls
        research_layout = QHBoxLayout()
        research_layout.setSpacing(15)

        # Research mode toggle
        self.research_mode_checkbox = QCheckBox("Research Mode")
        self.research_mode_checkbox.setToolTip(
            "Enable AI agent to synthesize research from multiple sources"
        )
        self.research_mode_checkbox.setChecked(self.research_mode)
        self.research_mode_checkbox.stateChanged.connect(self._toggle_research_mode)
        research_layout.addWidget(self.research_mode_checkbox)

        # Tool selection checkboxes (only visible in research mode)
        research_layout.addWidget(QLabel("Sources:"))

        self.use_local_checkbox = QCheckBox("Local Knowledge")
        self.use_local_checkbox.setToolTip("Search local vector stores")
        self.use_local_checkbox.setChecked(self.use_local)
        self.use_local_checkbox.stateChanged.connect(self._toggle_use_local)
        research_layout.addWidget(self.use_local_checkbox)

        self.use_aws_checkbox = QCheckBox("AWS Docs")
        self.use_aws_checkbox.setToolTip("Search AWS documentation")
        self.use_aws_checkbox.setChecked(self.use_aws)
        self.use_aws_checkbox.stateChanged.connect(self._toggle_use_aws)
        research_layout.addWidget(self.use_aws_checkbox)

        self.use_web_checkbox = QCheckBox("Web Search")
        self.use_web_checkbox.setToolTip("Search the web with Google")
        self.use_web_checkbox.setChecked(self.use_web)
        self.use_web_checkbox.stateChanged.connect(self._toggle_use_web)
        research_layout.addWidget(self.use_web_checkbox)

        # Model selector
        research_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItem("Haiku (Fast)", "haiku")
        self.model_combo.addItem("Sonnet (Balanced)", "sonnet")
        self.model_combo.addItem("Opus (Best)", "opus")
        # Set model from settings
        model_index = {"haiku": 0, "sonnet": 1, "opus": 2}.get(self.settings.research.model, 1)
        self.model_combo.setCurrentIndex(model_index)
        self.model_combo.setToolTip("Select Claude model for synthesis")
        self.model_combo.setFixedWidth(140)
        research_layout.addWidget(self.model_combo)

        # Parallel mode toggle
        self.parallel_mode_checkbox = QCheckBox("Parallel")
        self.parallel_mode_checkbox.setToolTip(
            "Enable parallel subagent execution (faster, map-reduce pattern)"
        )
        self.parallel_mode_checkbox.setChecked(
            getattr(self.settings.research, "parallel_mode", True)
        )
        research_layout.addWidget(self.parallel_mode_checkbox)

        # Full content toggle (only for direct search mode)
        self.full_content_checkbox = QCheckBox("Full Content")
        self.full_content_checkbox.setToolTip("Show full content instead of snippets")
        self.full_content_checkbox.setChecked(self.full_content)
        self.full_content_checkbox.stateChanged.connect(self._toggle_full_content)
        research_layout.addWidget(self.full_content_checkbox)

        research_layout.addStretch()
        layout.addLayout(research_layout)

        # Update visibility based on initial research mode
        self._update_research_controls_visibility()

        # Search row
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter your question...")
        self.search_input.returnPressed.connect(self._perform_search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("Ask")
        self.search_btn.setFixedWidth(80)
        self.search_btn.clicked.connect(self._perform_search)
        search_layout.addWidget(self.search_btn)

        layout.addLayout(search_layout)

        # Splitter for results and sources
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # Results view (markdown)
        self.results_view = QWebEngineView()
        self.results_view.setHtml(self._get_welcome_html())
        self.splitter.addWidget(self.results_view)

        # Sources panel
        sources_widget = QWidget()
        sources_layout = QVBoxLayout(sources_widget)
        sources_layout.setContentsMargins(0, 0, 0, 0)

        sources_label = QLabel("📚 Sources:")
        sources_label.setStyleSheet("font-weight: bold;")
        sources_layout.addWidget(sources_label)

        self.sources_text = QTextEdit()
        self.sources_text.setReadOnly(True)
        self.sources_text.setPlaceholderText("Sources will appear here after a query...")
        sources_layout.addWidget(self.sources_text)

        self.splitter.addWidget(sources_widget)

        # Configure splitter behavior
        self.splitter.setChildrenCollapsible(False)  # Prevent panels from collapsing completely
        self.splitter.setHandleWidth(6)  # Make handle easier to grab
        # Splitter sizes restored in _restore_window_geometry

        layout.addWidget(self.splitter)

        # Status bar with progress indicator
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)

        # Progress bar (indeterminate mode)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.hide()  # Hidden by default
        status_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Keyboard shortcuts
        search_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        search_shortcut.activated.connect(lambda: self.search_input.setFocus())

        # Focus search input
        self.search_input.setFocus()

    def _init_menu(self) -> None:
        """Initialize menu bar."""
        menubar = self.menuBar()
        assert menubar is not None

        # File menu
        file_menu = menubar.addMenu("&File")
        assert file_menu is not None

        refresh_action = QAction("&Refresh Stores", self)
        refresh_action.setShortcut("Ctrl+R")
        refresh_action.triggered.connect(self._load_stores)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        self.export_action = QAction("&Export...", self)
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.triggered.connect(self._export_result)
        self.export_action.setEnabled(False)  # Disabled until we have a result
        file_menu.addAction(self.export_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        assert view_menu is not None

        self.dark_mode_action = QAction("&Dark Mode", self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setChecked(self.dark_mode)
        self.dark_mode_action.setShortcut("Ctrl+D")
        self.dark_mode_action.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(self.dark_mode_action)

        view_menu.addSeparator()

        minimize_action = QAction("&Minimize to Tray", self)
        minimize_action.setShortcut("Ctrl+M")
        minimize_action.triggered.connect(self.hide)
        view_menu.addAction(minimize_action)

        # Stores menu
        stores_menu = menubar.addMenu("&Stores")
        assert stores_menu is not None
        self.stores_menu = stores_menu
        self._update_stores_menu()

        # Agent menu
        agent_menu = menubar.addMenu("&Agent")
        assert agent_menu is not None

        prompt_action = QAction("&Custom Prompt...", self)
        prompt_action.setShortcut("Ctrl+P")
        prompt_action.setToolTip("Set custom instructions for the research agent")
        prompt_action.triggered.connect(self._show_prompt_dialog)
        agent_menu.addAction(prompt_action)

        agent_menu.addSeparator()

        self.obsidian_mode_action = QAction("&Obsidian Mode", self)
        self.obsidian_mode_action.setCheckable(True)
        self.obsidian_mode_action.setChecked(self.settings.agent.obsidian_mode)
        self.obsidian_mode_action.setToolTip(
            "Enable Obsidian vault knowledge (daily notes, wiki links, transcripts)"
        )
        self.obsidian_mode_action.triggered.connect(self._toggle_obsidian_mode)
        agent_menu.addAction(self.obsidian_mode_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        assert help_menu is not None

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_tray(self) -> None:
        """Initialize system tray icon."""
        # Create tray icon with a search magnifying glass
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._create_tray_icon())
        self.tray_icon.setToolTip("Vector RAG GUI")

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_window)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _create_tray_icon(self) -> QIcon:
        """Create a simple search icon for the tray."""
        # Create a 32x32 pixmap with a magnifying glass
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw magnifying glass circle
        pen = QPen(Qt.GlobalColor.white)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        painter.drawEllipse(4, 4, 18, 18)

        # Draw handle
        painter.drawLine(20, 20, 28, 28)

        painter.end()
        return QIcon(pixmap)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def _toggle_visibility(self) -> None:
        """Toggle window visibility."""
        if self.isVisible():
            self.hide()
        else:
            self._show_window()

    def _show_window(self) -> None:
        """Show and activate the window."""
        self.show()
        self.activateWindow()
        self.raise_()
        self.search_input.setFocus()

    def _quit_app(self) -> None:
        """Quit the application."""
        self._save_settings()
        self.tray_icon.hide()
        from PyQt6.QtWidgets import QApplication

        QApplication.quit()

    def closeEvent(self, event: QCloseEvent | None) -> None:  # noqa: N802
        """Handle window close event."""
        self._save_settings()
        super().closeEvent(event)

    def _restore_window_geometry(self) -> None:
        """Restore window position and size from settings."""
        self.setGeometry(
            self.settings.window.x,
            self.settings.window.y,
            self.settings.window.width,
            self.settings.window.height,
        )
        if self.settings.window.splitter_sizes:
            self.splitter.setSizes(self.settings.window.splitter_sizes)
        else:
            self.splitter.setSizes([500, 120])

    def _save_settings(self) -> None:
        """Save current settings to file."""
        # Window geometry
        geo = self.geometry()
        self.settings.window.x = geo.x()
        self.settings.window.y = geo.y()
        self.settings.window.width = geo.width()
        self.settings.window.height = geo.height()
        self.settings.window.splitter_sizes = self.splitter.sizes()

        # Selected stores
        self.settings.selected_stores = self._selected_stores.copy()

        # Research settings
        self.settings.research.research_mode = self.research_mode
        self.settings.research.use_local = self.use_local
        self.settings.research.use_aws = self.use_aws
        self.settings.research.use_web = self.use_web
        self.settings.research.model = self.model_combo.currentData() or "sonnet"
        self.settings.research.dark_mode = self.dark_mode
        self.settings.research.full_content = self.full_content
        self.settings.research.parallel_mode = self.parallel_mode_checkbox.isChecked()

        # Agent settings already saved via their respective handlers

        save_settings(self.settings)

    def _toggle_full_content(self) -> None:
        """Toggle between full content and snippets."""
        self.full_content = self.full_content_checkbox.isChecked()

    def _toggle_research_mode(self) -> None:
        """Toggle between direct search and research mode."""
        self.research_mode = self.research_mode_checkbox.isChecked()
        self._update_research_controls_visibility()

    def _toggle_use_local(self) -> None:
        """Toggle local knowledge source."""
        self.use_local = self.use_local_checkbox.isChecked()

    def _toggle_use_aws(self) -> None:
        """Toggle AWS documentation source."""
        self.use_aws = self.use_aws_checkbox.isChecked()

    def _toggle_use_web(self) -> None:
        """Toggle web search source."""
        self.use_web = self.use_web_checkbox.isChecked()

    def _toggle_obsidian_mode(self) -> None:
        """Toggle Obsidian mode for vault-aware research."""
        self.settings.agent.obsidian_mode = self.obsidian_mode_action.isChecked()

    def _show_prompt_dialog(self) -> None:
        """Show dialog for editing custom agent prompt."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Custom Agent Prompt")
        dialog.setMinimumSize(500, 300)

        layout = QVBoxLayout(dialog)

        # Instructions label
        label = QLabel(
            "Enter custom instructions to append to the research agent's system prompt.\n"
            "These instructions guide how the agent synthesizes information."
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        # Text editor for prompt
        prompt_edit = QPlainTextEdit()
        prompt_edit.setPlaceholderText(
            "Example:\n"
            "- Focus on Python best practices\n"
            "- Include cost comparisons where relevant\n"
            "- Write for a technical audience"
        )
        prompt_edit.setPlainText(self.settings.agent.custom_prompt)
        layout.addWidget(prompt_edit)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings.agent.custom_prompt = prompt_edit.toPlainText()

    def _update_research_controls_visibility(self) -> None:
        """Update visibility of research-specific controls."""
        # Tool selection checkboxes and model selector are only relevant in research mode
        visible = self.research_mode
        self.use_local_checkbox.setVisible(visible)
        self.use_aws_checkbox.setVisible(visible)
        self.use_web_checkbox.setVisible(visible)
        self.model_combo.setVisible(visible)
        self.parallel_mode_checkbox.setVisible(visible)

        # Find and update the "Sources:" and "Model:" labels visibility
        parent = self.use_local_checkbox.parent()
        if parent is not None and isinstance(parent, QWidget):
            research_layout = parent.layout()
            if research_layout is not None:
                for i in range(research_layout.count()):
                    item = research_layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if isinstance(widget, QLabel) and widget.text() in ("Sources:", "Model:"):
                            widget.setVisible(visible)

        # Update full content checkbox visibility (only for direct search)
        self.full_content_checkbox.setVisible(not self.research_mode)

    def _update_stores_menu(self) -> None:
        """Update the stores menu with available stores."""
        self.stores_menu.clear()

        if not self.stores:
            no_stores = QAction("No stores loaded", self)
            no_stores.setEnabled(False)
            self.stores_menu.addAction(no_stores)
            return

        selected_stores = self._get_selected_stores()

        for store in self.stores:
            display_name = store.get("display_name", "Unknown")
            store_name = store.get("name", "")
            action = QAction(display_name, self)
            action.setCheckable(True)

            # Check if this store is selected
            if store_name in selected_stores:
                action.setChecked(True)

            # Connect to toggle this store selection
            action.triggered.connect(
                lambda checked, s=store_name: self._toggle_store_from_menu(s, checked)
            )
            self.stores_menu.addAction(action)

        self.stores_menu.addSeparator()

        # Store info action
        info_action = QAction("Store &Info...", self)
        info_action.setShortcut("Ctrl+I")
        info_action.triggered.connect(self._show_store_info)
        self.stores_menu.addAction(info_action)

    def _toggle_store_from_menu(self, store_name: str, checked: bool) -> None:
        """Toggle a store selection from the menu."""
        if checked and store_name not in self._selected_stores:
            self._selected_stores.append(store_name)
        elif not checked and store_name in self._selected_stores:
            self._selected_stores.remove(store_name)
        self._update_stores_menu()

    def _show_store_info(self) -> None:
        """Show information about the selected stores."""
        selected_stores = self._get_selected_stores()

        if not selected_stores:
            QMessageBox.information(self, "Store Info", "No stores selected.")
            return

        try:
            from vector_rag_gui.core.stores import get_store_info

            info_parts = []
            for store_name in selected_stores:
                info = get_store_info(store_name)
                info_parts.append(f"""Store: {store_name}
Backend: {info.get("backend", "Unknown")}
Location: {info.get("location", "Unknown")}
Dimension: {info.get("dimension", "Unknown")}
Vector Count: {info.get("vector_count", 0)}
Index Size: {info.get("index_size_mb", 0):.2f} MB""")

            info_text = "\n\n---\n\n".join(info_parts)
            QMessageBox.information(self, "Store Info", info_text)
        except Exception as e:
            QMessageBox.warning(self, "Store Info", f"Could not retrieve store info: {e}")

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Vector RAG GUI",
            """<h3>Vector RAG GUI</h3>
            <p>Version 0.1.0</p>
            <p>A Qt6 GUI for searching local vector stores with markdown rendering.</p>
            <p>Uses vector-rag-tool for local FAISS-based document search and retrieval.</p>
            """,
        )

    def _toggle_dark_mode(self) -> None:
        """Toggle between dark and light mode."""
        self.dark_mode = self.dark_mode_action.isChecked()
        # Refresh the current view
        self.results_view.setHtml(self._get_welcome_html())

    def _export_result(self) -> None:
        """Export last research result to a markdown file."""
        if self._last_result is None:
            QMessageBox.warning(
                self,
                "No Result",
                "No research result to export. Run a query first.",
            )
            return

        # Generate default filename from query
        from vector_rag_gui.core.agent import _slugify

        query = self._last_result.query or "research"
        default_name = f"{_slugify(query)}.md"

        # Show file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Research Result",
            default_name,
            "Markdown Files (*.md);;All Files (*)",
        )

        if file_path:
            try:
                from pathlib import Path

                Path(file_path).write_text(self._last_result.document, encoding="utf-8")
                self.status_label.setText(f"Exported to {file_path}")
                logger.info("Exported research to %s", file_path)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export: {e}",
                )
                logger.error("Failed to export research: %s", e)

    def _load_stores(self) -> None:
        """Load available stores from backend."""
        try:
            from vector_rag_gui.core.stores import list_stores

            self.stores = list_stores()

            # Select default store if specified and not already selected
            if self.default_store and not self._selected_stores:
                for store in self.stores:
                    store_name = store.get("name", "")
                    display_name = store.get("display_name", "")
                    if store_name == self.default_store or display_name.startswith(
                        self.default_store
                    ):
                        self._selected_stores.append(store_name)
                        break

            self.status_label.setText(f"Loaded {len(self.stores)} stores")
            self._update_stores_menu()

        except Exception as e:
            self.status_label.setText(f"Failed to load stores: {e}")
            QMessageBox.warning(
                self,
                "Store Loading Failed",
                f"Could not load stores: {e}\n\nMake sure vector stores exist.",
            )

    def _get_selected_stores(self) -> list[str]:
        """Get list of selected store names.

        Returns:
            List of store names that are selected
        """
        return self._selected_stores.copy()

    def _perform_search(self) -> None:
        """Execute search query."""
        query = self.search_input.text().strip()
        if not query:
            return

        # Get selected stores
        selected_stores = self._get_selected_stores()

        # Disable UI during search
        self.search_btn.setEnabled(False)
        self.search_input.setEnabled(False)
        self.results_view.setHtml(self._get_loading_html())

        if self.research_mode:
            # Research mode: Use ResearchWorker with multiple stores
            if not selected_stores and self.use_local:
                selected_stores = ["obsidian-knowledge-base"]

            self.sources_text.clear()

            # Get selected model
            model_choice = self.model_combo.currentData() or "sonnet"

            # Check if parallel mode is enabled
            parallel_mode = self.parallel_mode_checkbox.isChecked()

            # Show progress bar during research
            self.progress_bar.show()

            if parallel_mode:
                self.status_label.setText("Researching (parallel)...")
                self.worker = ParallelResearchWorker(
                    query=query,
                    model_choice=model_choice,
                    use_local=self.use_local,
                    use_aws=self.use_aws,
                    use_web=self.use_web,
                    local_stores=selected_stores,
                    custom_prompt=self.settings.agent.custom_prompt,
                    obsidian_mode=self.settings.agent.obsidian_mode,
                )
            else:
                self.status_label.setText("Researching (sequential)...")
                self.worker = ResearchWorker(
                    query=query,
                    model_choice=model_choice,
                    use_local=self.use_local,
                    use_aws=self.use_aws,
                    use_web=self.use_web,
                    local_stores=selected_stores,
                )

            self.worker.finished.connect(self._on_research_finished)
            self.worker.progress.connect(self._on_research_progress)
            self.worker.error.connect(self._on_query_error)
            self.worker.start()

        else:
            # Direct search mode: Use QueryWorker (first selected store only)
            if not selected_stores:
                QMessageBox.warning(self, "No Store Selected", "Please select a store first.")
                self.search_btn.setEnabled(True)
                self.search_input.setEnabled(True)
                return

            self.status_label.setText("Searching...")

            # Use first selected store for direct search
            self.worker = QueryWorker(
                store_name=selected_stores[0],
                query=query,
                top_k=5,
                full_content=self.full_content,
                snippet_length=300,
            )
            self.worker.finished.connect(self._on_query_finished)
            self.worker.error.connect(self._on_query_error)
            self.worker.start()

    def _on_query_finished(self, result: QueryResult) -> None:
        """Handle successful query result."""
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.progress_bar.hide()

        # Render results as markdown
        if not result.results:
            html_content = "<p>No results found.</p>"
        else:
            # Build markdown from results
            markdown_content = self._build_results_markdown(result)
            html_content = self._render_markdown(markdown_content)

        query = self.search_input.text()
        styled_html = self._get_result_html(query, html_content)
        self.results_view.setHtml(styled_html)

        # Display sources
        self._display_sources(result)

        # Update status
        query_time = result.query_time or 0
        self.status_label.setText(f"Found {result.total_results} results in {query_time:.3f}s")

    def _on_query_error(self, error_msg: str) -> None:
        """Handle query error."""
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"Error: {error_msg}")
        self.results_view.setHtml(self._get_error_html(error_msg))
        self.sources_text.clear()

    def _on_research_finished(self, result: ResearchResult) -> None:
        """Handle successful research completion."""
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.progress_bar.hide()

        # Store result for export
        self._last_result = result
        self.export_action.setEnabled(True)

        # Render the markdown document
        html_content = self._render_markdown(result.document)
        query = self.search_input.text()
        styled_html = self._get_result_html(query, html_content)
        self.results_view.setHtml(styled_html)

        # Auto-save research result
        try:
            saved_path = result.save(query)
            logger.info("Saved research to %s", saved_path)
        except Exception as e:
            logger.warning("Failed to save research: %s", e)

        # Calculate cost
        cost = result.usage.calculate_cost(result.model)

        # Update status with model, tokens, and cost (immediate, clears queue)
        model_name = result.model.value.capitalize()
        status = (
            f"Research completed | {model_name} | "
            f"{result.usage.input_tokens:,} in + {result.usage.output_tokens:,} out = "
            f"{result.usage.total_tokens:,} tokens | ${cost:.4f}"
        )
        self._set_status_immediate(status)

        # Display sources in panel
        self._display_research_sources(result)

    def _on_research_progress(self, status: str) -> None:
        """Handle research progress updates with minimum display time."""
        self._queue_status(status)

    def _queue_status(self, message: str) -> None:
        """Queue a status message with minimum 1 second display time.

        Messages are queued and displayed sequentially, each staying visible
        for at least 1 second before the next message appears.

        Args:
            message: Status message to display
        """
        self._status_queue.append(message)
        if not self._status_busy:
            self._process_status_queue()

    def _process_status_queue(self) -> None:
        """Process the next message in the status queue."""
        if self._status_queue:
            message = self._status_queue.pop(0)
            self.status_label.setText(message)
            self._status_busy = True
            self._status_timer.start(1000)  # 1 second minimum display
        else:
            self._status_busy = False

    def _set_status_immediate(self, message: str) -> None:
        """Set status immediately, clearing the queue.

        Use for final/important messages that should display right away.

        Args:
            message: Status message to display
        """
        self._status_queue.clear()
        self._status_timer.stop()
        self._status_busy = False
        self.status_label.setText(message)

    def _build_results_markdown(self, result: QueryResult) -> str:
        """Build markdown content from query results."""
        lines = []

        for i, item in enumerate(result.results, 1):
            score = item.get("score", 0.0)
            similarity_level = item.get("similarity_level", "unknown")
            file_path = item.get("file_path", "Unknown")
            line_start = item.get("line_start")
            line_end = item.get("line_end")
            content = item.get("content", "")
            tags = item.get("tags", [])
            links = item.get("links", [])

            # Result header
            lines.append(f"## Result {i}: {similarity_level.replace('_', ' ').title()}")
            lines.append(f"**Score:** {score:.3f}")

            # File location
            if line_start and line_end:
                lines.append(f"**Location:** `{file_path}:{line_start}-{line_end}`")
            else:
                lines.append(f"**Location:** `{file_path}`")

            # Metadata
            if tags:
                lines.append(f"**Tags:** {', '.join(tags)}")
            if links:
                lines.append(f"**Links:** {', '.join(links)}")

            # Content
            lines.append("")
            lines.append("### Content")
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _display_sources(self, result: QueryResult) -> None:
        """Display sources in the sources panel."""
        self.sources_text.clear()

        if not result.results:
            self.sources_text.setPlainText("No sources available")
            return

        sources_text = []
        for i, item in enumerate(result.results, 1):
            file_path = item.get("file_path", "Unknown")
            score = item.get("score", 0.0)
            similarity_level = item.get("similarity_level", "unknown")
            line_start = item.get("line_start")
            line_end = item.get("line_end")

            if line_start and line_end:
                location = f"{file_path}:{line_start}-{line_end}"
            else:
                location = str(file_path)

            sources_text.append(f"{i}. {location} (score: {score:.3f}, {similarity_level})")

        self.sources_text.setPlainText("\n".join(sources_text))

    def _display_research_sources(self, result: ResearchResult) -> None:
        """Display research sources in the sources panel."""
        self.sources_text.clear()

        if not result.sources:
            self.sources_text.setPlainText("No tool calls were made during research.")
            return

        # Group sources by type
        source_lines = []
        type_icons = {"local": "📁", "aws": "☁️", "web": "🌐"}

        for i, source in enumerate(result.sources, 1):
            icon = type_icons.get(source.source_type, "❓")
            # Include store name for local sources
            if source.source_type == "local" and source.store_name:
                source_lines.append(
                    f"{i}. {icon} [{source.store_name}] "
                    f'"{source.query}" ({source.result_count} results)'
                )
            else:
                source_lines.append(
                    f"{i}. {icon} [{source.source_type.upper()}] "
                    f'"{source.query}" ({source.result_count} results)'
                )

        self.sources_text.setPlainText("\n".join(source_lines))

    def _render_markdown(self, text: str) -> str:
        """Convert markdown to HTML with syntax highlighting."""
        return markdown.markdown(
            text,
            extensions=[
                "fenced_code",
                "tables",
                "codehilite",
                "nl2br",
                "sane_lists",
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "guess_lang": True,
                }
            },
        )

    def _get_css(self) -> str:
        """Get CSS styles for markdown rendering based on current theme."""
        # Get Pygments CSS for syntax highlighting
        pygments_style = "monokai" if self.dark_mode else "github-dark"
        formatter = HtmlFormatter(style=pygments_style)
        pygments_css: str = formatter.get_style_defs(".highlight")  # type: ignore[no-untyped-call]

        if self.dark_mode:
            # Dark mode colors (GitHub dark theme)
            bg_color = "#0d1117"
            text_color = "#e6edf3"
            heading_color = "#e6edf3"
            border_color = "#30363d"
            code_bg = "#161b22"
            table_header_bg = "#161b22"
            link_color = "#58a6ff"
            blockquote_color = "#8b949e"
            query_header_bg = "#161b22"
            muted_color = "#8b949e"
        else:
            # Light mode colors (GitHub light theme)
            bg_color = "#ffffff"
            text_color = "#24292e"
            heading_color = "#1f2328"
            border_color = "#d0d7de"
            code_bg = "#f6f8fa"
            table_header_bg = "#f6f8fa"
            link_color = "#0969da"
            blockquote_color = "#656d76"
            query_header_bg = "#f6f8fa"
            muted_color = "#656d76"

        return f"""
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            color: {text_color};
            background-color: {bg_color};
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            color: {heading_color};
        }}
        h1 {{ font-size: 2em; border-bottom: 1px solid {border_color}; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid {border_color}; padding-bottom: 0.3em; }}
        h3 {{ font-size: 1.25em; }}
        p {{ margin-bottom: 16px; }}
        code {{
            background-color: {code_bg};
            padding: 0.2em 0.4em;
            border-radius: 6px;
            font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 85%;
        }}
        pre {{
            background-color: {code_bg};
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
            line-height: 1.45;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
            font-size: 100%;
        }}
        blockquote {{
            border-left: 4px solid {border_color};
            padding: 0 16px;
            margin: 0 0 16px 0;
            color: {blockquote_color};
        }}
        ul, ol {{
            padding-left: 2em;
            margin-bottom: 16px;
        }}
        li {{ margin-bottom: 4px; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 16px;
        }}
        th, td {{
            border: 1px solid {border_color};
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: {table_header_bg};
            font-weight: 600;
        }}
        a {{
            color: {link_color};
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: 0;
            border-top: 1px solid {border_color};
            margin: 24px 0;
        }}
        .query-header {{
            background-color: {query_header_bg};
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            border-left: 4px solid {link_color};
        }}
        .query-header strong {{
            color: {link_color};
        }}
        .muted {{
            color: {muted_color};
        }}
        kbd {{
            background-color: {code_bg};
            border: 1px solid {border_color};
            border-radius: 3px;
            padding: 2px 6px;
            font-family: SFMono-Regular, Consolas, monospace;
            font-size: 85%;
        }}
        {pygments_css}
        """

    def _get_welcome_html(self) -> str:
        """Get welcome screen HTML."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>{self._get_css()}</style>
        </head>
        <body>
            <div style="text-align: center; margin-top: 100px;" class="muted">
                <h2>🔍 Vector RAG Search</h2>
                <p>Select a store and enter your question above.</p>
                <p style="font-size: 0.9em;">Press <kbd>Ctrl+L</kbd> to focus search</p>
            </div>
        </body>
        </html>
        """

    def _get_loading_html(self) -> str:
        """Get loading screen HTML."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>{self._get_css()}</style>
        </head>
        <body>
            <div style="text-align: center; margin-top: 100px;" class="muted">
                <h3>🔄 Searching...</h3>
                <p>Querying your documents...</p>
            </div>
        </body>
        </html>
        """

    def _get_error_html(self, error_msg: str) -> str:
        """Get error screen HTML."""
        # Use theme-aware error colors
        if self.dark_mode:
            error_bg = "#3d1a1a"
            error_border = "#f85149"
            error_text = "#f85149"
        else:
            error_bg = "#ffebe9"
            error_border = "#ff8182"
            error_text = "#cf222e"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>{self._get_css()}</style>
        </head>
        <body>
            <div style="margin-top: 50px; padding: 20px; background-color: {error_bg};
                        border: 1px solid {error_border}; border-radius: 6px;">
                <h3 style="color: {error_text}; margin-top: 0;">❌ Error</h3>
                <p>{error_msg}</p>
            </div>
        </body>
        </html>
        """

    def _get_result_html(self, query: str, content: str) -> str:
        """Get result HTML with query header and content."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>{self._get_css()}</style>
        </head>
        <body>
            <div class="query-header">
                <strong>Query:</strong> {query}
            </div>
            {content}
        </body>
        </html>
        """
