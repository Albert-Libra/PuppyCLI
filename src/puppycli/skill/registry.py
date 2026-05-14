"""Skill registry — search and discover skills from agentskills.io ecosystem."""

from __future__ import annotations

import requests

AGENTSKILLS_API = "https://agentskills.io/api"


def search_registry(query: str, limit: int = 10) -> list[dict]:
    """Search for skills on agentskills.io.

    Falls back to GitHub search if the registry API is unavailable.
    """
    # Try the official registry API first
    try:
        resp = requests.get(
            f"{AGENTSKILLS_API}/skills",
            params={"search": query, "limit": limit},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                return _normalize_registry_results(data, limit)
    except Exception:
        pass

    # Fallback: search GitHub for agent skills
    return _search_github(query, limit)


def _normalize_registry_results(data: list, limit: int) -> list[dict]:
    """Normalize registry API results to a standard format."""
    results = []
    for item in data[:limit]:
        results.append({
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "source": item.get("github_url") or item.get("url", ""),
            "author": item.get("author", ""),
            "stars": item.get("stars", 0),
            "downloads": item.get("downloads", 0),
        })
    return results


def _search_github(query: str, limit: int) -> list[dict]:
    """Search GitHub for agent skills repositories."""
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"{query} agent-skill SKILL.md",
                "sort": "stars",
                "order": "desc",
                "per_page": limit,
            },
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("items", [])[:limit]:
                results.append({
                    "name": item.get("name", ""),
                    "description": (item.get("description") or "")[:200],
                    "source": item.get("html_url", ""),
                    "author": item.get("owner", {}).get("login", ""),
                    "stars": item.get("stargazers_count", 0),
                    "downloads": 0,
                })
            return results
    except Exception:
        pass
    return []


def get_skill_info(skill_name: str) -> dict | None:
    """Get detailed info for a specific skill from the registry."""
    try:
        resp = requests.get(
            f"{AGENTSKILLS_API}/skills/{skill_name}",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("name", skill_name),
                "description": data.get("description", ""),
                "source": data.get("github_url") or data.get("url", ""),
                "author": data.get("author", ""),
                "version": data.get("version", ""),
                "license": data.get("license", ""),
            }
    except Exception:
        pass
    return None
