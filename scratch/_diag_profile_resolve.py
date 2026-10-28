"""Reproduce greeting headers for the live DB tenant ids."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "routing"))

# Force the same DB the app uses
from dotenv import load_dotenv
load_dotenv(ROOT / "routing" / ".env")

os.chdir(ROOT / "backend")

from shared.tenancy.loader import get_tenant_profile, build_profile, ProfileValidationError
from shared.tenancy import store
from shared.tenancy.resolver import resolve_tenant_for_user, resolve_default_tenant, _active_test_override

print("active_test_override:", _active_test_override())
print("default:", resolve_default_tenant())
print("for user 919512777899:", resolve_tenant_for_user("919512777899"))

for tid in ["l", "leewaysoftech", "leeway-softech", "default", "99destinations", "wanderly", "1"]:
    rec = store.get_tenant(tid)
    print(f"\nget_tenant({tid!r}) =>", (rec or {}).get("id"), (rec or {}).get("slug"), (rec or {}).get("display_name"))
    try:
        p = build_profile(tid)
        print(f"  build_profile OK brand={p.brand.name!r} body={p.menu.body!r:.60}")
    except ProfileValidationError as e:
        print(f"  build_profile INVALID: {e}")
        p2 = get_tenant_profile(tid)
        print(f"  get_tenant_profile fallback brand={p2.brand.name!r} body={p2.menu.body!r:.60}")

# Also simulate get_main_menu headers
from bots.customer_b2c.menus import get_main_menu
for tid in [None, "leeway-softech", "leewaysoftech", "l", "99destinations"]:
    m = get_main_menu("919512777899", tenant_id=tid)
    print(f"menu tenant_id={tid!r} => header={m.get('header')!r} type={m.get('type')} body={str(m.get('body') or m.get('text'))[:50]!r} resolved={m.get('tenant_id')}")
