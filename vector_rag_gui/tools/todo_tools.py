"""Todo list tools for task tracking during research.

Provides TodoRead and TodoWrite functionality for managing research tasks.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
from pathlib import Path
from typing import Any

from anthropic import beta_tool

# Store todos in memory during session, optionally persist to file
_todos: list[dict[str, Any]] = []
_todo_file = Path.home() / ".config" / "vector-rag-gui" / "todos.json"


def _load_todos() -> list[dict[str, Any]]:
    """Load todos from file if exists."""
    global _todos
    if _todo_file.exists():
        try:
            _todos = json.loads(_todo_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            _todos = []
    return _todos


def _save_todos() -> None:
    """Save todos to file."""
    try:
        _todo_file.parent.mkdir(parents=True, exist_ok=True)
        _todo_file.write_text(json.dumps(_todos, indent=2), encoding="utf-8")
    except OSError:
        pass  # Silent fail on save


@beta_tool
def todo_read() -> str:
    """Read the current todo list.

    Returns:
        JSON string with list of todos and their statuses
    """
    todos = _load_todos()

    return json.dumps(
        {
            "todos": todos,
            "total": len(todos),
            "pending": sum(1 for t in todos if t.get("status") == "pending"),
            "in_progress": sum(1 for t in todos if t.get("status") == "in_progress"),
            "completed": sum(1 for t in todos if t.get("status") == "completed"),
        }
    )


@beta_tool
def todo_write(todos: list[dict[str, Any]]) -> str:
    """Write/update the todo list.

    Args:
        todos: List of todo items, each with:
            - content: Task description
            - status: "pending", "in_progress", or "completed"
            - activeForm: Present continuous form (e.g., "Researching topic")

    Returns:
        JSON string confirming the update
    """
    global _todos

    # Validate todos
    valid_statuses = {"pending", "in_progress", "completed"}
    validated_todos = []

    for todo in todos:
        if not isinstance(todo, dict):
            continue

        content = todo.get("content", "")
        status = todo.get("status", "pending")
        active_form = todo.get("activeForm", content)

        if not content:
            continue

        if status not in valid_statuses:
            status = "pending"

        validated_todos.append(
            {
                "content": content,
                "status": status,
                "activeForm": active_form,
            }
        )

    _todos = validated_todos
    _save_todos()

    return json.dumps(
        {
            "success": True,
            "todos": _todos,
            "total": len(_todos),
        }
    )


@beta_tool
def todo_add(content: str, active_form: str | None = None) -> str:
    """Add a single todo item.

    Args:
        content: Task description
        active_form: Present continuous form (optional)

    Returns:
        JSON string confirming the addition
    """
    global _todos
    _load_todos()

    _todos.append(
        {
            "content": content,
            "status": "pending",
            "activeForm": active_form or content,
        }
    )
    _save_todos()

    return json.dumps(
        {
            "success": True,
            "added": content,
            "total": len(_todos),
        }
    )


@beta_tool
def todo_update(index: int, status: str) -> str:
    """Update the status of a todo item.

    Args:
        index: Index of the todo (0-based)
        status: New status ("pending", "in_progress", "completed")

    Returns:
        JSON string confirming the update
    """
    global _todos
    _load_todos()

    valid_statuses = {"pending", "in_progress", "completed"}

    if index < 0 or index >= len(_todos):
        return json.dumps(
            {
                "success": False,
                "error": f"Invalid index {index}. Valid range: 0-{len(_todos) - 1}",
            }
        )

    if status not in valid_statuses:
        return json.dumps(
            {
                "success": False,
                "error": f"Invalid status '{status}'. Valid: {valid_statuses}",
            }
        )

    _todos[index]["status"] = status
    _save_todos()

    return json.dumps(
        {
            "success": True,
            "updated": _todos[index],
            "index": index,
        }
    )
