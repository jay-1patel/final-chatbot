"""Admin API for recent external-API / runtime error logs."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from routes.auth import require_permission
from services.error_reporter import list_recent_errors

router = APIRouter(prefix="/api/admin/api-errors", tags=["api-errors"])


@router.get("")
def get_api_errors(
    limit: int = Query(50, ge=1, le=500),
    provider: Optional[str] = Query(None, description="Filter e.g. send2, groq, fastapi"),
    current_admin: dict = Depends(require_permission("manage_operations")),
):
    """Return recent API/runtime errors so ops can see failures without grepping logs."""
    rows = list_recent_errors(limit=limit, provider=(provider or None))
    return {"count": len(rows), "errors": rows}
