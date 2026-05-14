"""WebSocket handler for streaming chat."""

import json
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from puppycli.agent.runner import AgentRunner
from puppycli.config import Config
from puppycli.session.manager import SessionManager

router = APIRouter()

_STARTUP_CWD = Path.cwd()


def _get_manager() -> SessionManager:
    config = Config()
    return SessionManager(sessions_dir=config.base_dir / "sessions")


@router.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """WebSocket endpoint for streaming AI chat."""
    await ws.accept()
    config = Config()
    session_manager = _get_manager()

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type", "")
            if msg_type != "message":
                continue

            content = data.get("content", "")
            session_id = data.get("session_id", "")

            if not content.strip():
                continue

            # Create session if needed
            if not session_id:
                session_id = session_manager.create_session()

            # Save user message
            session_manager.save_message(session_id, "user", content)

            # Send session_id back so client knows it
            await ws.send_json({"type": "session_id", "session_id": session_id})

            # Stream AI response
            full_response = ""
            try:
                # Load recent conversation history (sliding window: last 40 messages)
                history = session_manager.get_session(session_id)
                history_messages = history[:-1] if len(history) > 1 else []
                MAX_HISTORY = 40  # 20 user-assistant turns
                if len(history_messages) > MAX_HISTORY:
                    history_messages = history_messages[-MAX_HISTORY:]

                # Prepend session summary if available
                summary = session_manager.get_summary(session_id)
                context_messages = history_messages
                if summary:
                    context_messages = [
                        {"role": "system", "content": f"[Conversation summary: {summary}]"}
                    ] + history_messages

                runner = AgentRunner(config=config, project_dir=_STARTUP_CWD)
                async for token in runner.run_stream(
                    user_message=content,
                    history=context_messages,
                ):
                    full_response += token
                    await ws.send_json({"type": "token", "content": token})

            except ValueError as e:
                await ws.send_json({"type": "error", "message": str(e)})
                continue
            except Exception as e:
                err_msg = str(e)
                if "401" in err_msg or "AuthenticationError" in type(e).__name__:
                    err_msg = "API key is invalid. Please set a valid key in Settings (⚙️)."
                await ws.send_json({"type": "error", "message": err_msg})
                continue

            # Save assistant message
            session_manager.save_message(session_id, "assistant", full_response)

            # Signal completion
            await ws.send_json({"type": "done", "session_id": session_id})

    except WebSocketDisconnect:
        pass
