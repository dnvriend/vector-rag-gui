"""AWS Knowledge tool wrapper for Claude Agent SDK.

Provides search functionality for AWS documentation using aws-knowledge-tool.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import subprocess  # nosec B404

from anthropic import beta_tool


@beta_tool
def search_aws_docs(query: str) -> str:
    """Search AWS documentation for official guidance and best practices.

    Args:
        query: Search query for AWS documentation

    Returns:
        JSON string with AWS documentation search results
    """
    try:
        result = subprocess.run(  # nosec B603, B607
            ["aws-knowledge-tool", "search", query, "--json"],
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
                "error": "Search timed out",
                "error_type": "TimeoutError",
                "results": [],
            }
        )
    except FileNotFoundError:
        return json.dumps(
            {
                "error": "aws-knowledge-tool not found. Please ensure it is installed.",
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
