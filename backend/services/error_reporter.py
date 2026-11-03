"""Central API / runtime error reporter.

Every external-API failure (Send2, LLM, payments, logistics, …) and every
unhandled server exception should call :func:`report_error`. That:

1. Emits a greppable console line: ``API_ERROR | provider=… | …``
2. Persists a row in ``api_error_logs`` (readable via admin API)
3. Optionally pushes to ``ALERT_WEBHOOK_URL`` and/or admin WhatsApp
   (rate-limited so a stuck poller cannot spam you)

Env:
  ALERT_WEBHOOK_URL          Slack/Discord/etc webhook (optional)
  ADMIN_NOTIFICATION_MODE    log (default) | send
  ADMIN_WHATSAPP_ID          recipient when mode=send
  ERROR_ALERT_COOLDOWN_SECONDS  default 60 — min gap between identical alerts
"""

from __future__ import annotations

import logging
import os
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("error_reporter")

_lock = threading.Lock()
_last_alert_at: Dict[str, float] = {}


def _cooldown_seconds() -> float:
    try:
        return float(os.getenv("ERROR_ALERT_COOLDOWN_SECONDS", "60"))
    except ValueError:
        return 60.0


def _should_notify(key: str) -> bool:
    now = time.monotonic()
    cool = _cooldown_seconds()
    with _lock:
        last = _last_alert_at.get(key, 0.0)
        if now - last < cool:
            return False
        _last_alert_at[key] = now
        return True


def _persist(
    *,
    provider: str,
    operation: str,
    severity: str,
    message: str,
    detail: str,
    http_status: Optional[int],
    tenant_id: Optional[str],
    wa_id: Optional[str],
) -> None:
    try:
        from database import get_db_context
    except Exception:
        try:
            from backend.database import get_db_context  # type: ignore
        except Exception:
            return
    try:
        with get_db_context() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS api_error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'error',
                    message TEXT NOT NULL DEFAULT '',
                    detail TEXT NOT NULL DEFAULT '',
                    http_status INTEGER,
                    tenant_id TEXT,
                    wa_id TEXT
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_api_error_logs_created "
                "ON api_error_logs(created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_api_error_logs_provider "
                "ON api_error_logs(provider, created_at DESC)"
            )
            conn.execute(
                """INSERT INTO api_error_logs
                   (created_at, provider, operation, severity, message, detail,
                    http_status, tenant_id, wa_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    (provider or "unknown")[:80],
                    (operation or "unknown")[:120],
                    (severity or "error")[:20],
                    (message or "")[:500],
                    (detail or "")[:4000],
                    http_status,
                    (tenant_id or None),
                    (wa_id or None),
                ),
            )
    except Exception as exc:
        logger.debug("api_error_logs persist failed: %s", exc)


def _push_webhook(text: str, severity: str) -> None:
    try:
        from services.alerts import send_alert
    except Exception:
        try:
            from backend.services.alerts import send_alert  # type: ignore
        except Exception:
            return
    try:
        send_alert(text, severity=severity)
    except Exception as exc:
        logger.debug("webhook alert failed: %s", exc)


def _push_admin_whatsapp(text: str) -> None:
    try:
        from services.whatsapp_outbox import notify_admin
    except Exception:
        try:
            from backend.services.whatsapp_outbox import notify_admin  # type: ignore
        except Exception:
            return
    try:
        notify_admin(text[:1500])
    except Exception as exc:
        logger.debug("admin whatsapp alert failed: %s", exc)


def report_error(
    provider: str,
    operation: str,
    message: str,
    *,
    detail: str = "",
    severity: str = "error",
    http_status: Optional[int] = None,
    tenant_id: Optional[str] = None,
    wa_id: Optional[str] = None,
    notify: bool = True,
    exc: Optional[BaseException] = None,
) -> None:
    """Log + store + (optionally) notify about an API/runtime failure."""
    if exc is not None and not detail:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-3500:]

    line = (
        f"API_ERROR | provider={provider} | op={operation} | severity={severity} "
        f"| http={http_status if http_status is not None else '-'} "
        f"| tenant={tenant_id or '-'} | wa_id={wa_id or '-'} "
        f"| message={str(message)[:300]}"
    )
    if detail:
        line = f"{line} | detail={str(detail)[:500]}"

    if severity == "warning":
        logger.warning(line)
    else:
        logger.error(line)

    _persist(
        provider=provider,
        operation=operation,
        severity=severity,
        message=message,
        detail=detail,
        http_status=http_status,
        tenant_id=tenant_id,
        wa_id=wa_id,
    )

    if not notify:
        return

    key = f"{provider}|{operation}|{severity}|{wa_id or ''}|{str(message)[:80]}"
    if not _should_notify(key):
        return

    alert_text = (
        f"[{severity.upper()}] {provider}/{operation}: {message}"
        + (f" (http {http_status})" if http_status is not None else "")
        + (f" wa={wa_id}" if wa_id else "")
        + (f" tenant={tenant_id}" if tenant_id else "")
    )
    _push_webhook(alert_text, severity)
    _push_admin_whatsapp(alert_text)


def report_exception(
    provider: str,
    operation: str,
    exc: BaseException,
    *,
    tenant_id: Optional[str] = None,
    wa_id: Optional[str] = None,
    notify: bool = True,
) -> None:
    report_error(
        provider,
        operation,
        str(exc) or exc.__class__.__name__,
        severity="error",
        tenant_id=tenant_id,
        wa_id=wa_id,
        notify=notify,
        exc=exc,
    )


def list_recent_errors(limit: int = 50, provider: Optional[str] = None) -> list:
    try:
        from database import get_db_context
    except Exception:
        from backend.database import get_db_context  # type: ignore

    limit = max(1, min(int(limit or 50), 500))
    with get_db_context() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS api_error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                provider TEXT NOT NULL,
                operation TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'error',
                message TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT '',
                http_status INTEGER,
                tenant_id TEXT,
                wa_id TEXT
            )"""
        )
        if provider:
            rows = conn.execute(
                """SELECT * FROM api_error_logs
                   WHERE provider = ?
                   ORDER BY id DESC LIMIT ?""",
                (provider, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM api_error_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
