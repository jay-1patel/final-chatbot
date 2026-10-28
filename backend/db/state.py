"""User conversation state and human-handover flags data access — extracted from backend/database.py."""
import os
import json
import re
import sqlite3
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from .core import (
    DB_PATH, BASE_DIR, PROJECT_ROOT, logger, get_db, get_db_context,
    _ensure_columns, _loads_json, _current_tenant, set_request_tenant,
    get_request_tenant
)


def get_user_state(wa_id: str) -> dict:
    with get_db_context() as conn:
        row = conn.execute(
            "SELECT * FROM user_states WHERE wa_id = ?",
            (wa_id,),
        ).fetchone()
    if row:
        result = dict(row)
        try:
            result["context_json"] = json.loads(result.get("context_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            result["context_json"] = {}
        return result
    return {"wa_id": wa_id, "state": "MAIN_MENU", "context_json": {}, "lang": "en"}


def set_user_state(wa_id: str, state: str, context: dict = None, lang: str = None) -> bool:
    with get_db_context() as conn:
        context_json = json.dumps(context or {})
        if lang:
            conn.execute(
                """INSERT INTO user_states (wa_id, state, context_json, lang)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                     state = ?,
                     context_json = ?,
                     lang = ?,
                     updated_at = CURRENT_TIMESTAMP""",
                (wa_id, state, context_json, lang, state, context_json, lang),
            )
        else:
            conn.execute(
                """INSERT INTO user_states (wa_id, state, context_json)
                   VALUES (?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                     state = ?,
                     context_json = ?,
                     updated_at = CURRENT_TIMESTAMP""",
                (wa_id, state, context_json, state, context_json),
            )
    return True


def update_user_context(wa_id: str, context: dict) -> bool:
    current = get_user_state(wa_id)
    merged = {**current.get("context_json", {}), **context}
    return set_user_state(wa_id, current.get("state", "MAIN_MENU"), merged)


def clear_user_context(wa_id: str) -> bool:
    return set_user_state(wa_id, "MAIN_MENU", {})


def set_human_handover(wa_id: str, active: bool) -> bool:
    """Set or clear the human-handover state for a conversation.

    When ``active`` is True the conversation enters the live human inbox and any
    previous "resolved" marker is cleared. When False the human session is
    terminated, control returns to the bot, and ``handover_resolved_at`` is
    stamped so the live inbox stops showing the conversation.
    """
    try:
        with get_db_context() as conn:
            if active:
                conn.execute(
                    """
                    INSERT INTO user_states (wa_id, human_handover, updated_at, handover_resolved_at)
                    VALUES (?, 1, CURRENT_TIMESTAMP, NULL)
                    ON CONFLICT(wa_id) DO UPDATE SET
                        human_handover = 1,
                        updated_at = CURRENT_TIMESTAMP,
                        handover_resolved_at = NULL
                    """,
                    (wa_id,),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO user_states (wa_id, human_handover, updated_at, handover_resolved_at)
                    VALUES (?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(wa_id) DO UPDATE SET
                        human_handover = 0,
                        updated_at = CURRENT_TIMESTAMP,
                        handover_resolved_at = CURRENT_TIMESTAMP
                    """,
                    (wa_id,),
                )
        return True
    except Exception as e:
        logger.error(f"set_human_handover failed for {wa_id}: {e}")
        return False


def reopen_conversation_on_inbound(wa_id: str) -> bool:
    """Clear a stale ``handover_resolved_at`` so a new inbound message puts the
    conversation back in the live inbox.

    ``resolve_handoff``/``set_human_handover(False)`` stamp ``handover_resolved_at``
    so the inbox stops showing a conversation. Without this, that stamp was
    permanent: the customer could write again and the thread stayed hidden
    (the default inbox query filters on ``handover_resolved_at IS NULL``). A new
    inbound message from the customer reopens it.
    """
    try:
        with get_db_context() as conn:
            conn.execute(
                "UPDATE user_states SET handover_resolved_at = NULL, updated_at = CURRENT_TIMESTAMP "
                "WHERE wa_id = ? AND handover_resolved_at IS NOT NULL",
                (wa_id,),
            )
        return True
    except Exception as e:
        logger.error(f"reopen_conversation_on_inbound failed for {wa_id}: {e}")
        return False
