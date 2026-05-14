"""WebSocket handler for streaming chat."""

import asyncio
import json
import uuid
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

    # ── Queues for concurrent reader pattern ──
    raw_queue: asyncio.Queue = asyncio.Queue()
    user_msg_queue: asyncio.Queue = asyncio.Queue()

    # ── Confirmation events: confirm_id -> (asyncio.Event, [bool_result]) ──
    confirm_events: dict[str, tuple[asyncio.Event, list[bool]]] = {}

    # ── Background reader: reads ALL ws messages into raw_queue ──
    async def reader():
        try:
            while True:
                raw = await ws.receive_text()
                await raw_queue.put(json.loads(raw))
        except WebSocketDisconnect:
            await raw_queue.put(None)  # sentinel to stop dispatcher

    # ── Background dispatcher: routes messages ──
    async def dispatcher():
        while True:
            data = await raw_queue.get()
            if data is None:  # disconnect sentinel
                await user_msg_queue.put(None)
                break
            msg_type = data.get("type", "")
            if msg_type == "confirm_response":
                cid = data.get("confirm_id", "")
                allowed = data.get("allowed", False)
                entry = confirm_events.get(cid)
                if entry is not None:
                    event, result = entry
                    result[0] = allowed
                    event.set()
            elif msg_type == "message":
                await user_msg_queue.put(data)
            # Ignore other types

    reader_task = asyncio.create_task(reader())
    dispatcher_task = asyncio.create_task(dispatcher())

    # ── Confirmation handler: sends confirm_tool, waits for response ──
    async def confirm_handler(command: str, reason: str) -> bool:
        cid = uuid.uuid4().hex[:8]
        event = asyncio.Event()
        result = [False]
        confirm_events[cid] = (event, result)
        await ws.send_json({
            "type": "confirm_tool",
            "confirm_id": cid,
            "command": command,
            "reason": reason,
        })
        try:
            await asyncio.wait_for(event.wait(), timeout=30)
        except asyncio.TimeoutError:
            return False
        finally:
            confirm_events.pop(cid, None)
        return result[0]

    try:
        while True:
            data = await user_msg_queue.get()
            if data is None:  # disconnect sentinel
                break

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
                # Load recent conversation history
                history = session_manager.get_session(session_id)
                history_messages = history[:-1] if len(history) > 1 else []
                MAX_HISTORY = 40
                if len(history_messages) > MAX_HISTORY:
                    history_messages = history_messages[-MAX_HISTORY:]

                # Prepend session summary if available
                summary = session_manager.get_summary(session_id)
                context_messages = history_messages
                if summary:
                    context_messages = [
                        {"role": "system", "content": f"[Conversation summary: {summary}]"}
                    ] + history_messages

                runner = AgentRunner(
                    config=config,
                    project_dir=_STARTUP_CWD,
                    confirm_handler=confirm_handler,
                )
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

    finally:
        reader_task.cancel()
        dispatcher_task.cancel()
        try:
            await asyncio.gather(reader_task, dispatcher_task)
        except (asyncio.CancelledError, WebSocketDisconnect):
            pass
