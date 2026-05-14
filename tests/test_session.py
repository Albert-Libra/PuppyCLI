"""Tests for session manager."""
from puppycli.session.manager import SessionManager


def test_create_session(temp_manager: SessionManager):
    """Creating a session returns a UUID string."""
    sid = temp_manager.create_session()
    assert isinstance(sid, str)
    assert len(sid) == 36  # UUID4


def test_save_and_get_session(temp_manager: SessionManager):
    """Messages should round-trip through save/get."""
    sid = temp_manager.create_session()
    temp_manager.save_message(sid, "user", "hello")
    temp_manager.save_message(sid, "assistant", "hi there")

    messages = temp_manager.get_session(sid)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "hi there"


def test_list_sessions(temp_manager: SessionManager):
    """list_sessions returns metadata for all sessions."""
    sid1 = temp_manager.create_session()
    sid2 = temp_manager.create_session()
    temp_manager.save_message(sid1, "user", "msg1")

    sessions = temp_manager.list_sessions()
    assert len(sessions) >= 2
    ids = [s["id"] for s in sessions]
    assert sid1 in ids
    assert sid2 in ids


def test_delete_session(temp_manager: SessionManager):
    """Delete should remove a session."""
    sid = temp_manager.create_session()
    temp_manager.save_message(sid, "user", "test")
    assert temp_manager.delete_session(sid) is True
    assert temp_manager.get_session(sid) == []
    assert temp_manager.delete_session(sid) is False  # already gone
