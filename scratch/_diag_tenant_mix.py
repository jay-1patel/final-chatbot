"""Diagnose multi-tenant greeting mix — no secrets printed."""
import os
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
db_candidates = [
    root / "faq.db",
    root / "backend" / "faq.db",
    root / "routing" / "faq.db",
    root / "data" / "faq.db",
]

print("CWD root:", root)
print("SEND2_POLLER_ENABLED env:", repr(os.getenv("SEND2_POLLER_ENABLED")))
print("DEFAULT_TENANT_ID env:", repr(os.getenv("DEFAULT_TENANT_ID")))

# Parse routing/.env for non-secret keys only
env_path = root / "routing" / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        key = s.split("=", 1)[0].strip()
        if key in ("SEND2_POLLER_ENABLED", "DEFAULT_TENANT_ID", "ROUTER_PORT"):
            print(f"routing/.env {key}=", s.split("=", 1)[1].strip()[:40] if "=" in s else "")

for db in db_candidates:
    if not db.exists():
        continue
    print("\nDB:", db)
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"
    )]
    print(" tables sample:", [t for t in tables if "tenant" in t.lower() or "dedup" in t.lower() or "active" in t.lower() or "processed" in t.lower()])

    if "tenants" in tables:
        cols = [r[1] for r in c.execute("PRAGMA table_info(tenants)")]
        print(" tenants cols:", cols)
        # pick safe columns
        want = [x for x in ("id", "slug", "display_name", "company_name", "waba_phone_id", "status", "vertical") if x in cols]
        q = "SELECT " + ", ".join(want) + " FROM tenants LIMIT 30"
        rows = c.execute(q).fetchall()
        print(f" tenants count={len(list(c.execute('SELECT 1 FROM tenants')))} rows:")
        for r in rows:
            print("  ", dict(r))

    for t in ("active_test_tenant", "app_settings", "system_settings", "bot_settings"):
        if t in tables:
            try:
                rows = c.execute(f"SELECT * FROM {t} LIMIT 10").fetchall()
                print(f" {t}:", [dict(r) for r in rows])
            except Exception as e:
                print(f" {t} err:", e)

    if "webhook_dedup" in tables:
        n = c.execute("SELECT COUNT(*) FROM webhook_dedup").fetchone()[0]
        recent = c.execute(
            "SELECT message_id, wa_id, processed_at FROM webhook_dedup ORDER BY processed_at DESC LIMIT 8"
        ).fetchall()
        print(f" webhook_dedup count={n} recent:")
        for r in recent:
            mid = str(r["message_id"])
            print("  ", mid[:48], r["wa_id"], r["processed_at"])

    if "processed_inbound_messages" in tables:
        n = c.execute("SELECT COUNT(*) FROM processed_inbound_messages").fetchone()[0]
        print(f" processed_inbound_messages count={n}")

    # published profiles brand names if present
    for t in ("tenant_profiles", "published_profiles", "tenant_profile"):
        if t in tables:
            cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})")]
            print(f" {t} cols:", cols[:20])
            try:
                rows = c.execute(f"SELECT * FROM {t} LIMIT 5").fetchall()
                for r in rows:
                    d = dict(r)
                    # redact large blobs
                    for k, v in list(d.items()):
                        if isinstance(v, str) and len(v) > 120:
                            d[k] = v[:120] + "..."
                    print("  row:", d)
            except Exception as e:
                print("  err", e)
    c.close()
