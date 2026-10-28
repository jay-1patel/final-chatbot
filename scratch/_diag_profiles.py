import json
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
db = root / "faq.db"
c = sqlite3.connect(str(db))
c.row_factory = sqlite3.Row

print("tenants:", c.execute("SELECT COUNT(*) FROM tenants").fetchone()[0])
print("profile versions:", c.execute("SELECT COUNT(*) FROM tenant_profile_versions").fetchone()[0])

cols = [r[1] for r in c.execute("PRAGMA table_info(tenant_profile_versions)")]
print("cols:", cols)

q = "SELECT * FROM tenant_profile_versions ORDER BY tenant_id, version DESC"
for r in c.execute(q):
    d = dict(r)
    payload = d.get("payload") or d.get("profile_json") or "{}"
    try:
        p = json.loads(payload) if isinstance(payload, str) else (payload or {})
    except Exception as e:
        print("bad json", d.get("tenant_id"), e)
        continue
    brand = p.get("brand") or {}
    bn = brand.get("name") if isinstance(brand, dict) else brand
    menu = p.get("menu") or {}
    body = menu.get("body") if isinstance(menu, dict) else None
    print(
        f"tenant={d.get('tenant_id')} v={d.get('version')} current={d.get('is_current')} "
        f"brand={bn!r:.80} body={body!r:.80}"
    )

# clients dirs
clients = root / "clients"
if clients.exists():
    for d in sorted(clients.iterdir()):
        cfg = d / "config.json"
        if not cfg.exists():
            continue
        try:
            p = json.loads(cfg.read_text(encoding="utf-8"))
            if "tenant_profile" in p:
                p = p["tenant_profile"]
            brand = (p.get("brand") or {})
            bn = brand.get("name") if isinstance(brand, dict) else brand
            menu = p.get("menu") or {}
            body = menu.get("body") if isinstance(menu, dict) else None
            print(f"FILE {d.name}: brand={bn!r:.80} body={body!r:.80}")
        except Exception as e:
            print(f"FILE {d.name}: err {e}")
