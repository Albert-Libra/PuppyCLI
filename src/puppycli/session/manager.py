"""Session manager for PuppyCLI conversations.

Stores conversations as JSONL files in <data_dir>/sessions/.
Metadata indexed in sessions-index.json.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SessionManager:
    """Manages conversation sessions stored as JSONL files."""

    def __init__(self, sessions_dir: Path | None = None):
        if sessions_dir is None:
            from puppycli.config import Config

            config = Config()
            sessions_dir = config.base_dir / "sessions"
        self._dir = Path(sessions_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._dir / "sessions-index.json"

    def _load_index(self) -> list[dict[str, Any]]:
        """Load session index."""
        if self._index_file.exists():
            with open(self._index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_index(self, index: list[dict[str, Any]]) -> None:
        """Save session index."""
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _session_file(self, session_id: str) -> Path:
        """Get the JSONL file path for a session."""
        return self._dir / f"{session_id}.jsonl"

    def create_session(self, title: str = "") -> str:
        """Create a new session and return its UUID."""
        session_id = str(uuid.uuid4())
        index = self._load_index()
        index.append({
            "id": session_id,
            "title": title or "New Conversation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message_count": 0,
            "summary": "",
        })
        self._save_index(index)
        # Create empty session file
        self._session_file(session_id).touch()
        return session_id

    def get_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all messages in a session."""
        fpath = self._session_file(session_id)
        if not fpath.exists():
            return []
        messages = []
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
        return messages

    def save_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to a session's JSONL file."""
        fpath = self._session_file(session_id)
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")
        # Update index
        index = self._load_index()
        for entry in index:
            if entry["id"] == session_id:
                entry["message_count"] = len(self.get_session(session_id))
                break
        self._save_index(index)

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions with metadata."""
        return self._load_index()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        fpath = self._session_file(session_id)
        if fpath.exists():
            fpath.unlink()
            index = self._load_index()
            index = [e for e in index if e["id"] != session_id]
            self._save_index(index)
            return True
        return False

    def rename_session(self, session_id: str, title: str) -> bool:
        """Rename a session. Returns True if renamed, False if not found."""
        index = self._load_index()
        for entry in index:
            if entry["id"] == session_id:
                entry["title"] = title
                self._save_index(index)
                return True
        return False

    def get_summary(self, session_id: str) -> str:
        """Get the conversation summary for a session."""
        index = self._load_index()
        for entry in index:
            if entry["id"] == session_id:
                return entry.get("summary", "")
        return ""

    def set_summary(self, session_id: str, summary: str) -> bool:
        """Set the conversation summary for a session."""
        index = self._load_index()
        for entry in index:
            if entry["id"] == session_id:
                entry["summary"] = summary
                self._save_index(index)
                return True
        return False
