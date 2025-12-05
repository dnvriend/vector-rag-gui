"""Web search tool wrapper for Claude Agent SDK.

Provides web search functionality using gemini-google-search-tool.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import subprocess  # nosec B404

from anthropic import beta_tool


@beta_tool
def search_web(query: str) -> str:
    """Search the web for current information using Google Search.

    Args:
        query: Web search query

    Returns:
        JSON string with web search results
    """
    try:
        # Default output is JSON, no --json flag needed
        result = subprocess.run(  # nosec B603, B607
            ["gemini-google-search-tool", "query", query],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return json.dumps({"error": result.stderr, "results": []})

        return result.stdout

    except subprocess.TimeoutExpired:
        return json.dumps(
            {
                "error": "Web search timed out",
                "error_type": "TimeoutError",
                "results": [],
            }
        )
    except FileNotFoundError:
        return json.dumps(
            {
                "error": "gemini-google-search-tool not found. Please ensure it is installed.",
                "error_type": "FileNotFoundError",
                "results": [],
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "results": [],
            }
        )
