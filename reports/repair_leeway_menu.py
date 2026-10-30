"""One-off repair: leewaysoftech draft + published menu.

The old (pre-dedupe) pipeline published 7 id-less LLM buttons into the tenant's
DB layers, which both duplicated the vertical defaults and broke profile
validation (bot fell back to the generic skeleton). This replaces the menu
buttons in the draft and a freshly published version with the canonical kit
menu from clients/leewaysoftech/config.json. Previous versions stay in
tenant_profile_versions for rollback.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)

from shared.tenancy import loader, store  # noqa: E402

TID = "leewaysoftech"


def main() -> None:
    file_layer = loader._strip_wrapper(loader.load_file_layer(TID))
    kit_buttons = (file_layer.get("menu") or {}).get("buttons") or []
    assert len(kit_buttons) == 6, f"expected 6 kit buttons, got {len(kit_buttons)}"

    draft = store.get_draft(TID) or {}
    published = store.get_current_payload(TID) or {}
    for layer in (draft, published):
        menu = dict(layer.get("menu") or {})
        menu["buttons"] = [dict(b) for b in kit_buttons]
        layer["menu"] = menu

    store.save_draft(TID, draft, updated_by="menu-dedupe-repair")
    version = store.publish_version(TID, published, published_by="menu-dedupe-repair")
    loader.reload_profile(TID)
    print("published version", version)

    profile = loader.get_tenant_profile(TID)
    titles = [b.title for b in profile.menu.buttons]
    print("buttons:", len(profile.menu.buttons))
    for b in profile.menu.buttons:
        print(" ", b.id, "|", b.title, "|", b.icon)
    dupes = sorted({t for t in titles if titles.count(t) > 1})
    print("duplicate titles:", dupes or "none")


if __name__ == "__main__":
    main()
