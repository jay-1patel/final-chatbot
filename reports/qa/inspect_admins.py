import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[2] / "faq.db"
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row
print("admins cols:", [r[1] for r in c.execute("PRAGMA table_info(admins)").fetchall()])
rows = c.execute("SELECT * FROM admins LIMIT 20").fetchall()
print("admins count", len(rows))
for r in rows:
    d = dict(r)
    d.pop("password_hash", None)
    d.pop("password", None)
    d.pop("hashed_password", None)
    print(d)
print("tenants cols:", [r[1] for r in c.execute("PRAGMA table_info(tenants)").fetchall()])
for r in c.execute("SELECT * FROM tenants LIMIT 20").fetchall():
    d = {k: dict(r)[k] for k in dict(r) if k in ("id", "slug", "display_name", "company_name", "status", "vertical", "phone", "wa_number")}
    print("tenant", d)
