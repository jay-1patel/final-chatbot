"""Onboarding Kits & Document Bifurcation API Routes.

Provides endpoints to:
  1. List and download pre-defined Onboarding Kits (DOCX & PDF) for all 8 verticals.
  2. Parse & Stage uploaded onboarding documents via Section-by-Section Targeted Ollama Bifurcation.
  3. Publish reviewed and confirmed bifurcated tenant configurations.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials

from routes.auth import get_current_admin, require_tenant_access, security

logger = logging.getLogger("onboarding_kits")
router = APIRouter(prefix="/api/admin", tags=["onboarding-kits"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "static" / "templates" / "onboarding"

VERTICAL_INFO = [
    {"slug": "real_estate", "title": "Real Estate & Property Development", "icon": "🏢"},
    {"slug": "ecommerce", "title": "E-Commerce & Retail Brands", "icon": "🛍️"},
    {"slug": "it_software", "title": "Software & IT Services", "icon": "💻"},
    {"slug": "tours_travel", "title": "Tours & Travel Agency", "icon": "✈️"},
    {"slug": "healthcare", "title": "Healthcare & Specialist Clinics", "icon": "🩺"},
    {"slug": "banking", "title": "Banking & Insurance Services", "icon": "💳"},
    {"slug": "finance", "title": "Finance, Accounting & Tax Advisory", "icon": "📊"},
    {"slug": "generic", "title": "General Business & Enterprise Services", "icon": "📦"},
]


# ──────────────────────────────────────────────────────────────────────────────
# 1. Template Kits Listing & Download Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/onboarding-kits/list")
def list_onboarding_kits():
    """List all available industry onboarding templates with download links."""
    kits = []
    for v in VERTICAL_INFO:
        slug = v["slug"]
        docx_name = f"{slug}_onboarding_kit.docx"
        pdf_name = f"{slug}_onboarding_kit.pdf"
        docx_exists = (TEMPLATES_DIR / docx_name).exists()
        pdf_exists = (TEMPLATES_DIR / pdf_name).exists()

        kits.append({
            "vertical": slug,
            "title": v["title"],
            "icon": v["icon"],
            "docx_url": f"/api/admin/onboarding-kits/{slug}/docx" if docx_exists else None,
            "pdf_url": f"/api/admin/onboarding-kits/{slug}/pdf" if pdf_exists else None,
            "has_docx": docx_exists,
            "has_pdf": pdf_exists,
        })
    return {"templates": kits}


@router.get("/onboarding-kits/{vertical}/{fmt}")
def download_onboarding_kit(vertical: str, fmt: str):
    """Download a specific vertical onboarding kit in docx or pdf format."""
    fmt = fmt.lower().strip(".")
    if fmt not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="Supported formats are 'docx' or 'pdf'")

    valid_slugs = {v["slug"] for v in VERTICAL_INFO}
    if vertical not in valid_slugs:
        raise HTTPException(status_code=404, detail=f"Vertical '{vertical}' not found")

    filename = f"{vertical}_onboarding_kit.{fmt}"
    file_path = TEMPLATES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Template file '{filename}' not found on server")

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if fmt == "docx"
        else "application/pdf"
    )
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2. Document Staging Endpoints (Parse & Preview before Publish)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/onboarding/stage")
async def stage_onboarding_document_global(
    request: Request,
    file: Optional[UploadFile] = File(None),
):
    """Parse an onboarding document globally (e.g. inside new registration wizard)."""
    files_payload = []
    content_type = request.headers.get("content-type", "")

    if file:
        raw = await file.read()
        files_payload.append({
            "filename": file.filename or "onboarding_doc.docx",
            "content": raw,
        })
    elif "multipart/form-data" in content_type:
        form = await request.form()
        for field_name in ("file", "files", "document"):
            uploaded = form.getlist(field_name)
            for uf in uploaded:
                if uf and hasattr(uf, "read"):
                    raw = await uf.read()
                    files_payload.append({
                        "filename": uf.filename or "onboarding_doc.docx",
                        "content": raw,
                    })
    elif "application/json" in content_type:
        body = await request.json()
        raw_files = body.get("files") or []
        for rf in raw_files:
            files_payload.append({
                "filename": rf.get("filename", "document.docx"),
                "content": rf.get("content", ""),
            })

    if not files_payload:
        raise HTTPException(status_code=400, detail="No document provided to stage")

    from services.auto_bifurcator import AutoBifurcator
    bifurcator = AutoBifurcator(tenant_id="draft_tenant")
    try:
        staged = bifurcator.stage_files(files_payload)
        return staged
    except Exception as exc:
        logger.error("Global onboarding document staging failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document parsing failed: {exc}")


@router.post("/tenants/{tenant_id}/onboarding/stage")
async def stage_onboarding_document_tenant(
    tenant_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    principal: dict = Depends(require_tenant_access()),
):
    """Parse an onboarding document for a specific tenant in staging mode."""
    files_payload = []
    content_type = request.headers.get("content-type", "")

    if file:
        raw = await file.read()
        files_payload.append({
            "filename": file.filename or "onboarding_doc.docx",
            "content": raw,
        })
    elif "multipart/form-data" in content_type:
        form = await request.form()
        for field_name in ("file", "files", "document"):
            uploaded = form.getlist(field_name)
            for uf in uploaded:
                if uf and hasattr(uf, "read"):
                    raw = await uf.read()
                    files_payload.append({
                        "filename": uf.filename or "onboarding_doc.docx",
                        "content": raw,
                    })
    elif "application/json" in content_type:
        body = await request.json()
        raw_files = body.get("files") or []
        for rf in raw_files:
            files_payload.append({
                "filename": rf.get("filename", "document.docx"),
                "content": rf.get("content", ""),
            })

    if not files_payload:
        raise HTTPException(status_code=400, detail="No document provided to stage")

    from services.auto_bifurcator import AutoBifurcator
    actor = principal.get("actor") or {"username": "admin", "role": "super_admin", "tenant_id": tenant_id}
    bifurcator = AutoBifurcator(tenant_id=tenant_id, actor=actor)
    try:
        staged = bifurcator.stage_files(files_payload)
        return staged
    except Exception as exc:
        logger.error("Tenant onboarding document staging failed for %s: %s", tenant_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document parsing failed: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# 3. Confirmation & Publishing Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/onboarding/publish")
async def publish_onboarding_bifurcation(
    tenant_id: str,
    request: Request,
    principal: dict = Depends(require_tenant_access()),
):
    """Commit and publish reviewed bifurcated configuration to live tenant system."""
    body = await request.json()
    bifurcation_draft = body.get("draft") or body
    if not bifurcation_draft:
        raise HTTPException(status_code=400, detail="No bifurcation draft provided to publish")

    from services.auto_bifurcator import AutoBifurcator
    actor = principal.get("actor") or {"username": "admin", "role": "super_admin", "tenant_id": tenant_id}
    bifurcator = AutoBifurcator(tenant_id=tenant_id, actor=actor)

    try:
        summary = bifurcator.apply_bifurcation(
            bifurcation=bifurcation_draft,
            raw_files=[],
            auto_publish=True,
        )
        return {
            "status": "published",
            "summary": summary,
        }
    except Exception as exc:
        logger.error("Publishing bifurcated draft failed for %s: %s", tenant_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Publishing failed: {exc}")



