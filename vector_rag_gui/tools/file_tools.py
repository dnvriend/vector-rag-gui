"""File tools for Claude Agent SDK.

Provides read-only filesystem access tools: glob, grep, and read.
Allows reading any file accessible to the user.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import re
from pathlib import Path

from anthropic import beta_tool


def _resolve_path(path: str | None, default_dir: Path | None = None) -> Path:
    """Resolve path to absolute path.

    Args:
        path: Path string to resolve (can be absolute or relative)
        default_dir: Default directory if path is None (defaults to cwd)

    Returns:
        Resolved absolute Path object
    """
    if default_dir is None:
        default_dir = Path.cwd()

    if path is None:
        return default_dir

    path_obj = Path(path).expanduser()

    if path_obj.is_absolute():
        return path_obj.resolve()

    return (default_dir / path_obj).resolve()


@beta_tool
def glob_files(pattern: str, directory: str | None = None) -> str:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g., '**/*.py', 'src/*.ts', '*.md')
        directory: Directory to search in (default: current working directory)

    Returns:
        JSON string with list of matching file paths
    """
    try:
        search_dir = _resolve_path(directory)

        matches = list(search_dir.glob(pattern))

        # Limit results to avoid token explosion
        max_results = 100
        files = []
        for match in matches[:max_results]:
            if match.is_file():
                files.append(str(match))

        return json.dumps(
            {
                "files": sorted(files),
                "total": len(files),
                "truncated": len(matches) > max_results,
            }
        )

    except Exception as e:
        return json.dumps({"error": str(e), "error_type": type(e).__name__, "files": []})


@beta_tool
def grep_files(
    pattern: str,
    glob_pattern: str = "**/*",
    directory: str | None = None,
    case_insensitive: bool = False,
    max_matches: int = 50,
) -> str:
    """Search for a regex pattern in files.

    Args:
        pattern: Regular expression pattern to search for
        glob_pattern: Glob pattern to filter files (default: all files)
        directory: Directory to search in (default: current working directory)
        case_insensitive: Whether to ignore case (default: False)
        max_matches: Maximum number of matches to return (default: 50)

    Returns:
        JSON string with matching lines and file locations
    """
    try:
        search_dir = _resolve_path(directory)

        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)

        matches = []
        files_searched = 0

        for file_path in search_dir.glob(glob_pattern):
            if not file_path.is_file():
                continue

            # Skip binary files
            if file_path.suffix in {
                ".pyc",
                ".so",
                ".dylib",
                ".exe",
                ".bin",
                ".png",
                ".jpg",
                ".gif",
            }:
                continue

            files_searched += 1

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        matches.append(
                            {
                                "file": str(file_path),
                                "line": line_num,
                                "content": line[:200],  # Truncate long lines
                            }
                        )

                        if len(matches) >= max_matches:
                            return json.dumps(
                                {
                                    "matches": matches,
                                    "total": len(matches),
                                    "truncated": True,
                                    "files_searched": files_searched,
                                }
                            )
            except (OSError, UnicodeDecodeError):
                continue

        return json.dumps(
            {
                "matches": matches,
                "total": len(matches),
                "truncated": False,
                "files_searched": files_searched,
            }
        )

    except re.error as e:
        return json.dumps({"error": f"Invalid regex: {e}", "matches": []})
    except Exception as e:
        return json.dumps({"error": str(e), "error_type": type(e).__name__, "matches": []})


@beta_tool
def read_file(
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    max_lines: int = 200,
) -> str:
    """Read contents of a file.

    Args:
        path: Path to the file (absolute or relative to current working directory)
        start_line: Starting line number (1-indexed, default: 1)
        end_line: Ending line number (inclusive, default: start_line + max_lines)
        max_lines: Maximum lines to read if end_line not specified (default: 200)

    Returns:
        JSON string with file contents and metadata
    """
    try:
        file_path = _resolve_path(path)

        if not file_path.exists():
            return json.dumps({"error": f"File not found: {path}", "content": None})

        if not file_path.is_file():
            return json.dumps({"error": f"Not a file: {path}", "content": None})

        # Check file size to avoid reading huge files
        file_size = file_path.stat().st_size
        if file_size > 1_000_000:  # 1MB limit
            return json.dumps(
                {
                    "error": f"File too large: {file_size} bytes (max 1MB)",
                    "content": None,
                }
            )

        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        # Apply line range
        start = (start_line or 1) - 1  # Convert to 0-indexed
        if start < 0:
            start = 0

        if end_line is not None:
            end = end_line
        else:
            end = start + max_lines

        selected_lines = lines[start:end]

        # Format with line numbers
        numbered_lines = []
        for i, line in enumerate(selected_lines, start + 1):
            numbered_lines.append(f"{i:4d} | {line}")

        return json.dumps(
            {
                "path": path,
                "content": "\n".join(numbered_lines),
                "start_line": start + 1,
                "end_line": min(end, total_lines),
                "total_lines": total_lines,
                "truncated": end < total_lines,
            }
        )

    except ValueError as e:
        return json.dumps({"error": str(e), "content": None})
    except Exception as e:
        return json.dumps({"error": str(e), "error_type": type(e).__name__, "content": None})
