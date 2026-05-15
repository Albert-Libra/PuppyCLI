"""HTTP REST API routes for PuppyCLI."""

from pathlib import Path

from fastapi import APIRouter, Body, HTTPException

from puppycli.config import Config
from puppycli.session.manager import SessionManager

router = APIRouter(prefix="/api")

# The working directory when the server started — treated as the user's project root.
_STARTUP_CWD = Path.cwd()


def get_config() -> Config:
    return Config()


def get_session_manager() -> SessionManager:
    config = get_config()
    return SessionManager(sessions_dir=config.base_dir / "sessions")


@router.get("/config")
async def api_get_config():
    """Get current configuration (api_key masked)."""
    config = get_config()
    data = config.as_dict()
    # Show if key is set, but never send the actual value
    data["api_key"] = "••••••••" if data.get("api_key") else ""
    return data


@router.put("/config")
async def api_update_config(updates: dict):
    """Update configuration values."""
    config = get_config()
    allowed_keys = {"api_key", "model", "base_url", "theme", "python_env", "data_dir"}
    for key, value in updates.items():
        if key in allowed_keys:
            # Skip api_key if value is the masked placeholder
            if key == "api_key" and value and value.startswith("••"):
                continue
            config.set(key, value)
    return {"status": "ok"}


@router.get("/sessions")
async def api_list_sessions():
    """List all conversation sessions."""
    manager = get_session_manager()
    sessions = manager.list_sessions()
    # Sort by created_at descending
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return sessions


@router.get("/sessions/{session_id}")
async def api_get_session(session_id: str):
    """Get messages for a specific session."""
    manager = get_session_manager()
    messages = manager.get_session(session_id)
    return {"id": session_id, "messages": messages}


@router.delete("/sessions/{session_id}")
async def api_delete_session(session_id: str):
    """Delete a session."""
    manager = get_session_manager()
    if manager.delete_session(session_id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.put("/sessions/{session_id}")
async def api_rename_session(session_id: str, body: dict = Body(...)):
    """Rename a session."""
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Missing 'title' field")
    manager = get_session_manager()
    if manager.rename_session(session_id, title):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/sessions")
async def api_create_session():
    """Create a new session and return its ID."""
    manager = get_session_manager()
    session_id = manager.create_session()
    return {"session_id": session_id}


@router.post("/sessions/{session_id}/messages")
async def api_save_message(session_id: str, body: dict = Body(...)):
    """Save a message to a session."""
    role = body.get("role", "").strip()
    content = body.get("content", "")
    if not role or not content:
        raise HTTPException(status_code=400, detail="Missing 'role' or 'content'")
    if role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'assistant'")
    manager = get_session_manager()
    try:
        manager.save_message(session_id, role, content)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ok"}


# ---- Skills API ----

@router.get("/skills")
async def api_list_skills():
    """List all installed skills."""
    from puppycli.skill.manager import SkillManager
    manager = SkillManager(project_dir=_STARTUP_CWD)
    return manager.list_skills()


@router.get("/skills/search")
async def api_search_skills(q: str = "", limit: int = 10):
    """Search for skills on the registry."""
    from puppycli.skill.registry import search_registry
    return search_registry(q, limit)


@router.post("/skills/install")
async def api_install_skill(request: dict):
    """Install a skill from a path, GitHub repo, or URL.

    Body:
        source: str — path, GitHub repo (owner/repo), or URL
        project: bool — install to project-level skills (default: False)
        adapt: bool — auto-adapt for PuppyCLI frontend (default: True)
    """
    from puppycli.skill.manager import SkillManager

    source = request.get("source", "")
    project = request.get("project", False)
    adapt = request.get("adapt", True)

    manager = SkillManager(project_dir=_STARTUP_CWD)

    if not source:
        raise HTTPException(status_code=400, detail="Missing 'source' field")

    try:
        # Determine source type
        if source.startswith("http://") or source.startswith("https://"):
            if "github.com" in source:
                info = manager.install_from_github(source, project=project, adapt=adapt)
            else:
                info = manager.install_from_url(source, project=project, adapt=adapt)
        elif "/" in source and not source.startswith(".") and not source.startswith("~"):
            # GitHub shorthand: owner/repo
            info = manager.install_from_github(source, project=project, adapt=adapt)
        else:
            # Local path
            from pathlib import Path
            info = manager.install_from_path(Path(source).expanduser().resolve(), project=project, adapt=adapt)
        return {"status": "ok", "skill": info}
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/skills/{name}")
async def api_remove_skill(name: str):
    """Remove an installed skill."""
    from puppycli.skill.manager import SkillManager
    manager = SkillManager(project_dir=_STARTUP_CWD)
    if manager.remove_skill(name):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")


@router.post("/skills/{name}/adapt")
async def api_adapt_skill(name: str):
    """Adapt an installed skill for PuppyCLI's browser frontend.

    Use this after installing a skill with adapt=False, or to re-adapt
    after restoring the original version.
    """
    from puppycli.skill.manager import SkillManager
    manager = SkillManager(project_dir=_STARTUP_CWD)
    try:
        result = manager.adapt_skill(name)
        return {"status": "ok", "adaptation": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skills/{name}/restore")
async def api_restore_skill(name: str):
    """Restore a skill to its original CLI content (revert adaptation)."""
    from puppycli.skill.manager import SkillManager
    manager = SkillManager(project_dir=_STARTUP_CWD)
    try:
        restored = manager.restore_skill(name)
        if restored:
            return {"status": "ok", "message": f"Skill '{name}' restored to original"}
        raise HTTPException(status_code=404, detail=f"No original backup found for '{name}'")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/skills/{name}/analysis")
async def api_analyze_skill(name: str):
    """Analyze a skill for CLI indicators and adaptation needs."""
    from puppycli.skill.manager import SkillManager
    from puppycli.skill.adapter import get_adaptation_info
    manager = SkillManager(project_dir=_STARTUP_CWD)
    skill_path = manager.get_skill_path(name)
    if not skill_path:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return get_adaptation_info(skill_path)


# ---- Local File Serving (for images, etc.) ----

@router.get("/file")
async def api_serve_file(path: str = ""):
    """Serve a local file (images, etc.) by absolute path."""
    from pathlib import Path
    from starlette.responses import FileResponse

    if not path:
        raise HTTPException(status_code=400, detail="Missing 'path' parameter")

    file_path = Path(path).expanduser().resolve()
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Allowed extensions
    allowed = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"}
    if file_path.suffix.lower() not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_path.suffix}")

    mime_map = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
        ".bmp": "image/bmp", ".ico": "image/x-icon",
    }
    return FileResponse(file_path, media_type=mime_map.get(file_path.suffix.lower(), "application/octet-stream"))


# ---- PowerShell Execution ----

@router.post("/powershell")
async def api_run_powershell(request: dict):
    """Execute a PowerShell command and return the output."""
    import subprocess
    import os

    command = request.get("command", "")
    if not command or not command.strip():
        raise HTTPException(status_code=400, detail="Missing 'command' field")

    timeout = min(request.get("timeout", 60), 120)

    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Command timed out after {timeout}s")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="PowerShell not found on this system")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Knowledge Base API ----

@router.get("/kb")
async def api_list_knowledge():
    """List all knowledge base entries."""
    from puppycli.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    return store.list_all()


@router.get("/kb/search")
async def api_search_knowledge(q: str = "", top_k: int = 5):
    """Search the knowledge base."""
    from puppycli.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    return store.search(q, top_k)


@router.post("/kb")
async def api_add_knowledge(request: dict):
    """Add an entry to the knowledge base."""
    title = request.get("title", "").strip()
    content = request.get("content", "").strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="Both 'title' and 'content' are required")
    tags = request.get("tags", [])
    source = request.get("source", "manual")

    from puppycli.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    entry = store.add(title=title, content=content, tags=tags, source=source)
    return {"status": "ok", "entry": entry}


@router.put("/kb/{entry_id}")
async def api_update_knowledge(entry_id: str, request: dict):
    """Update a knowledge base entry."""
    from puppycli.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    entry = store.update(
        entry_id,
        title=request.get("title"),
        content=request.get("content"),
        tags=request.get("tags"),
    )
    if entry:
        return {"status": "ok", "entry": entry}
    raise HTTPException(status_code=404, detail="Entry not found")


@router.delete("/kb/{entry_id}")
async def api_delete_knowledge(entry_id: str):
    """Delete a knowledge base entry."""
    from puppycli.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    if store.delete(entry_id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Entry not found")


@router.get("/kb/count")
async def api_knowledge_count():
    """Get total knowledge base entry count."""
    from puppycli.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    return {"count": store.count()}


# ---- PDF Processing ----

@router.post("/pdf/process")
async def api_process_pdf(request: dict):
    """Process a PDF file and save to knowledge base.

    Body: {"file_path": "/path/to/file.pdf", "tags": ["optional", "tags"]}
    """
    from pathlib import Path

    file_path = request.get("file_path", "").strip()
    if not file_path:
        raise HTTPException(status_code=400, detail="Missing 'file_path' field")

    file_path_input = file_path  # keep original for error messages
    file_path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path_input}")

    if file_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    tags = request.get("tags", ["pdf"])

    from puppycli.config import Config
    from puppycli.processing.pdf import process_pdf, save_to_knowledge

    config = Config()
    token = config.get("mineru_token", "") or None

    try:
        result = process_pdf(str(file_path), token=token)
        kb_id = save_to_knowledge(result, tags=tags)
        return {
            "status": "ok",
            "mode": result["mode"],
            "filename": result["filename"],
            "kb_entry_id": kb_id,
            "preview": result["markdown"][:500],
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
