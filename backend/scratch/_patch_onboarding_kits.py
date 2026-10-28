import subprocess
from pathlib import Path

data = subprocess.check_output(["git", "show", "6d70aa8:backend/routes/onboarding_kits.py"])
path = Path("backend/routes/onboarding_kits.py")
path.write_bytes(data)
t = path.read_text(encoding="utf-8")

old = """    from services.auto_bifurcator import AutoBifurcator
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
"""

new = """    try:
        from services.auto_bifurcator import AutoBifurcator, _sanitize_business_hours
    except ImportError:
        from backend.services.auto_bifurcator import AutoBifurcator, _sanitize_business_hours

    actor = principal.get("actor") or {
        "username": principal.get("username") or principal.get("label") or "admin",
        "role": principal.get("role") or "super_admin",
        "tenant_id": tenant_id,
    }
    bifurcator = AutoBifurcator(tenant_id=tenant_id, actor=actor)

    draft = dict(bifurcation_draft)
    if isinstance(draft.get("business_hours"), dict):
        draft["business_hours"] = _sanitize_business_hours(draft["business_hours"])

    try:
        summary = bifurcator.apply_bifurcation(
            bifurcation=draft,
            raw_files=[],
            auto_publish=True,
            careful_brand_merge=False,
        )
        return {
            "status": "published",
            "summary": summary,
        }
    except Exception as exc:
        logger.error("Publishing bifurcated draft failed for %s: %s", tenant_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Publishing failed: {exc}")
"""

if old not in t:
    raise SystemExit("old publish block not found")
path.write_text(t.replace(old, new), encoding="utf-8")
print("patched ok", path.stat().st_size)
