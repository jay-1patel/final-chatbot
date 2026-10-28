"""24h session-open helpers data access — extracted from backend/database.py."""
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


def update_session_inbound(wa_id: str):
    with get_db_context() as conn:
        conn.execute(
            """INSERT INTO user_sessions (wa_id, last_inbound_at, session_open)
               VALUES (?, CURRENT_TIMESTAMP, 1)
               ON CONFLICT(wa_id) DO UPDATE SET
                 last_inbound_at = CURRENT_TIMESTAMP,
                 session_open = 1""",
            (wa_id,),
        )


def update_session_outbound(wa_id: str):
    with get_db_context() as conn:
        conn.execute(
            """INSERT INTO user_sessions (wa_id, last_outbound_at)
               VALUES (?, CURRENT_TIMESTAMP)
               ON CONFLICT(wa_id) DO UPDATE SET
                 last_outbound_at = CURRENT_TIMESTAMP""",
            (wa_id,),
        )


def is_session_open(wa_id: str, window_hours: int = 24) -> bool:
    with get_db_context() as conn:
        row = conn.execute(
            "SELECT last_inbound_at FROM user_sessions WHERE wa_id = ?",
            (wa_id,),
        ).fetchone()
    if not row or not row["last_inbound_at"]:
        return False
    try:
        last = datetime.strptime(row["last_inbound_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - last).total_seconds() < window_hours * 3600
    except Exception:
        return False


def get_session_info(wa_id: str) -> dict:
    with get_db_context() as conn:
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE wa_id = ?",
            (wa_id,),
        ).fetchone()
    return dict(row) if row else {}
