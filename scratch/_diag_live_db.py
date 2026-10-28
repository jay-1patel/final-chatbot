"""Inspect the live ROUTING_DB_PATH tenants (no secrets)."""
import json
import sqlite3
from pathlib import Path

env = {}
for line in Path("routing/.env").read_text(encoding="utf-8").splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, v = s.split("=", 1)
    env[k.strip()] = v.strip()

db = env.get("ROUTING_DB_PATH") or "faq.db"
print("DB:", db)
print("exists:", Path(db).exists())
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row

print("tenants:")
for r in c.execute(
    "SELECT id, slug, display_name, waba_phone_id, vertical, status FROM tenants ORDER BY id"
):
    d = dict(r)
    # mask phone id partially
    pid = d.get("waba_phone_id")
    if pid:
        d["waba_phone_id"] = str(pid)[:4] + "…" + str(pid)[-4:]
    print(" ", d)

print("active test tenant / settings:")
for t in ("active_test_tenant", "app_settings"):
    try:
        rows = c.execute(f"SELECT * FROM {t} LIMIT 20").fetchall()
        print(t, [dict(x) for x in rows])
    except Exception as e:
        print(t, "n/a", e)

print("\ncurrent profiles brand:")
for r in c.execute(
    "SELECT tenant_id, version, payload FROM tenant_profile_versions WHERE is_current=1"
):
    try:
        p = json.loads(r["payload"] or "{}")
        brand = (p.get("brand") or {})
        bn = brand.get("name") if isinstance(brand, dict) else brand
        body = (p.get("menu") or {}).get("body") if isinstance(p.get("menu"), dict) else None
        print(f"  {r['tenant_id']} v{r['version']} brand={bn!r:.90} body={body!r:.90}")
    except Exception as e:
        print("  parse", r["tenant_id"], e)

# recent dedup
try:
    n = c.execute("SELECT COUNT(*) FROM webhook_dedup").fetchone()[0]
    print("\nwebhook_dedup count", n)
    for r in c.execute(
        "SELECT message_id, wa_id, processed_at FROM webhook_dedup ORDER BY rowid DESC LIMIT 10"
    ):
        print(" ", str(r["message_id"])[:50], r["wa_id"], r["processed_at"])
except Exception as e:
    print("dedup", e)

# user_states tenant stamps
try:
    rows = c.execute(
        "SELECT wa_id, tenant_id, COUNT(*) c FROM user_states GROUP BY wa_id, tenant_id ORDER BY c DESC LIMIT 15"
    ).fetchall()
    print("\nuser_states sample:")
    for r in rows:
        print(" ", dict(r))
except Exception as e:
    print("user_states", e)
