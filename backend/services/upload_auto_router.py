"""Post-upload auto-bifurcation router.

Called from the background document ingestion path after a tenant (or admin)
file is saved. Extracts products, FAQs, and KB content via AutoBifurcator and
publishes them live. Brand/menu merges are careful so placeholder LLM defaults
do not wipe an existing tenant profile.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("upload_auto_router")


def _full_bifurcate_enabled() -> bool:
    return os.environ.get("AUTO_BIFURCATE_FULL", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def route_uploaded_document(
    tenant_id: Optional[str],
    filename: str,
    content: bytes,
    actor: Optional[dict] = None,
) -> Dict[str, Any]:
    """Run full LLM bifurcation for one uploaded document.

    Returns a compact stats dict suitable for storing on ``admin_files``.
    Empty/disabled results still return a structured dict (never None).
    """
    empty = {
        "offerings_created": 0,
        "offerings_sample": [],
        "faqs_saved": 0,
        "kb_chunks_indexed": 0,
        "menu_buttons_count": 0,
        "intents_count": 0,
        "brand_updated": False,
        "brand": {},
        "vertical": None,
        "status": "skipped",
        "files_processed": [filename],
    }

    if not _full_bifurcate_enabled():
        empty["status"] = "disabled"
        return empty

    if not tenant_id:
        empty["status"] = "no_tenant"
        logger.info("UPLOAD_AUTO_ROUTER_SKIP | reason=no_tenant | file=%s", filename)
        return empty

    if not content:
        empty["status"] = "empty_file"
        return empty

    try:
        try:
            from services.auto_bifurcator import AutoBifurcator
        except ImportError:
            from backend.services.auto_bifurcator import AutoBifurcator

        bifurcator = AutoBifurcator(tenant_id=str(tenant_id), actor=actor)
        result = bifurcator.process_document_bytes(
            filename=filename,
            content=content,
            auto_publish=True,
            careful_brand_merge=True,
        )
        result["status"] = "configured"
        logger.info(
            "UPLOAD_AUTO_ROUTER_OK | tenant=%s | file=%s | offerings=%s | faqs=%s | kb=%s",
            tenant_id,
            filename,
            result.get("offerings_created"),
            result.get("faqs_saved"),
            result.get("kb_chunks_indexed"),
        )
        return result
    except Exception as exc:
        logger.warning(
            "UPLOAD_AUTO_ROUTER_FAILED | tenant=%s | file=%s | err=%s",
            tenant_id,
            filename,
            exc,
            exc_info=True,
        )
        empty["status"] = "error"
        empty["error"] = str(exc)
        return empty
