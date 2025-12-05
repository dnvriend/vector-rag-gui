"""Web fetch tool for retrieving and processing web page content.

Fetches content from URLs and returns processed text/markdown.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import subprocess  # nosec B404

from anthropic import beta_tool


@beta_tool
def web_fetch(url: str, prompt: str | None = None) -> str:
    """Fetch content from a URL and optionally process with a prompt.

    Uses curl to fetch web content and optionally processes it.

    Args:
        url: URL to fetch content from
        prompt: Optional prompt to describe what to extract (not used in basic fetch)

    Returns:
        JSON string with fetched content or error
    """
    try:
        # Use curl to fetch the URL
        result = subprocess.run(  # nosec B603, B607
            [
                "curl",
                "-sL",  # Silent, follow redirects
                "-A",
                "Mozilla/5.0 (compatible; ResearchBot/1.0)",  # User agent
                "--max-time",
                "30",  # Timeout
                url,
            ],
            capture_output=True,
            text=True,
            timeout=35,
        )

        if result.returncode != 0:
            return json.dumps(
                {
                    "error": f"Failed to fetch URL: {result.stderr}",
                    "url": url,
                    "content": None,
                }
            )

        content = result.stdout

        # Basic HTML to text conversion (strip tags)
        # For more sophisticated conversion, use a library like html2text
        import re

        # Remove script and style elements
        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        content = re.sub(r"<[^>]+>", " ", content)
        # Clean up whitespace
        content = re.sub(r"\s+", " ", content).strip()

        # Truncate if too long
        max_length = 10000
        truncated = len(content) > max_length
        if truncated:
            content = content[:max_length]

        return json.dumps(
            {
                "url": url,
                "content": content,
                "length": len(content),
                "truncated": truncated,
                "prompt": prompt,
            }
        )

    except subprocess.TimeoutExpired:
        return json.dumps(
            {
                "error": "Request timed out",
                "error_type": "TimeoutError",
                "url": url,
                "content": None,
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "url": url,
                "content": None,
            }
        )
