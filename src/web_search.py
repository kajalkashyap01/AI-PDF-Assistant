
from __future__ import annotations

import os
import json
import urllib.request
import urllib.error
from typing import Any


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def search_web(
    query: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Search the internet using Tavily.

    Returns a list of results containing:
    title, url, content and score.
    """

    api_key = os.getenv("TAVILY_API_KEY", "").strip()

    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY is missing. Add your Tavily API key "
            "to the project's .env file."
        )

    if not query or not query.strip():
        return []

    payload = {
        "query": query.strip(),
        "search_depth": "basic",
        "topic": "general",
        "max_results": max(1, min(max_results, 10)),
        "include_answer": False,
        "include_raw_content": False,
    }

    request = urllib.request.Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        error_details = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Tavily search failed (HTTP {error.code}): "
            f"{error_details}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not connect to the web search service: {error}"
        ) from error

    results = []

    for item in data.get("results", []):

        results.append({
            "title": item.get("title", "Untitled source"),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
            "score": item.get("score", 0),
            "source": "web",
        })

    return results
