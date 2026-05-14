"""Knowledge store — JSON-based local knowledge base.

Each entry: {"id", "title", "content", "tags", "source", "created_at", "updated_at"}
Stored as a JSONL file at <data_dir>/knowledge/entries.jsonl
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class KnowledgeStore:
    """Manages a local knowledge base stored as JSONL."""

    def __init__(self, knowledge_dir: Path | None = None):
        if knowledge_dir is None:
            from puppycli.config import Config

            knowledge_dir = Config().base_dir / "knowledge"
        self._dir = Path(knowledge_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / "entries.jsonl"

    def _read_all(self) -> list[dict[str, Any]]:
        """Read all entries from the JSONL file."""
        if not self._file.exists():
            return []
        entries = []
        with open(self._file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    def _write_all(self, entries: list[dict[str, Any]]) -> None:
        """Write all entries to the JSONL file."""
        with open(self._file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def add(self, title: str, content: str, tags: list[str] | None = None,
            source: str = "manual") -> dict[str, Any]:
        """Add a knowledge entry."""
        entries = self._read_all()
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "tags": tags or [],
            "source": source,
            "created_at": now,
            "updated_at": now,
        }
        entries.append(entry)
        self._write_all(entries)
        return entry

    def update(self, entry_id: str, title: str | None = None,
               content: str | None = None, tags: list[str] | None = None) -> dict | None:
        """Update an existing entry."""
        entries = self._read_all()
        for e in entries:
            if e["id"] == entry_id:
                if title is not None:
                    e["title"] = title
                if content is not None:
                    e["content"] = content
                if tags is not None:
                    e["tags"] = tags
                e["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write_all(entries)
                return e
        return None

    def delete(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        entries = self._read_all()
        new_entries = [e for e in entries if e["id"] != entry_id]
        if len(new_entries) < len(entries):
            self._write_all(new_entries)
            return True
        return False

    def get(self, entry_id: str) -> dict | None:
        """Get a single entry by ID."""
        entries = self._read_all()
        for e in entries:
            if e["id"] == entry_id:
                return e
        return None

    def list_all(self) -> list[dict[str, Any]]:
        """List all entries (metadata only, content truncated)."""
        entries = self._read_all()
        results = []
        for e in entries:
            results.append({
                "id": e["id"],
                "title": e["title"],
                "tags": e["tags"],
                "source": e["source"],
                "created_at": e["created_at"],
                "preview": e["content"][:150] + "..." if len(e["content"]) > 150 else e["content"],
            })
        return results

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search entries by keyword matching.

        Scores entries by:
        1. Exact phrase match in title (highest weight)
        2. Word overlap in title
        3. Word overlap in content
        4. Tag match
        """
        entries = self._read_all()
        if not entries or not query.strip():
            return []

        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))

        scored = []
        for e in entries:
            title_lower = e["title"].lower()
            content_lower = e["content"].lower()
            tag_lower = [t.lower() for t in e.get("tags", [])]

            score = 0.0

            # Exact phrase match (title)
            if query_lower in title_lower:
                score += 10.0
            # Exact phrase match (content)
            if query_lower in content_lower:
                score += 3.0

            # Word overlap (title)
            title_words = set(re.findall(r'\w+', title_lower))
            score += len(query_words & title_words) * 2.0

            # Word overlap (content)
            content_words = set(re.findall(r'\w+', content_lower))
            score += len(query_words & content_words) * 0.5

            # Tag match
            for t in tag_lower:
                if any(qw in t for qw in query_words):
                    score += 1.5

            if score > 0:
                scored.append((score, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    def search_and_format(self, query: str, top_k: int = 5) -> str:
        """Search and format results for injection into LLM context."""
        results = self.search(query, top_k)
        if not results:
            return ""

        lines = [
            "",
            "## Relevant Knowledge Base Entries",
            "",
            "The following entries from your knowledge base may be relevant:",
            "",
        ]
        for i, r in enumerate(results, 1):
            lines.append(f"### [{i}] {r['title']}")
            lines.append(f"Tags: {', '.join(r.get('tags', []))}")
            lines.append(f"```\n{r['content']}\n```")
            lines.append("")

        return "\n".join(lines)

    def count(self) -> int:
        """Return total number of entries."""
        return len(self._read_all())
