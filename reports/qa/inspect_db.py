import sqlite3
import json
from pathlib import Path

db = Path(__file__).resolve().parents[2] / "faq.db"
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1").fetchall()]
print("tables_count", len(tables))
print("tables_sample", tables[:50])
for q in [
    "SELECT id, username, role, tenant_id FROM admins LIMIT 20",
    "SELECT id, username, role FROM admin_users LIMIT 20",
    "SELECT id, slug, name, status FROM tenants LIMIT 30",
]:
    try:
        rows = [dict(r) for r in c.execute(q).fetchall()]
        print(q.split()[3], rows)
    except Exception as e:
        print("ERR", q.split()[3], type(e).__name__, str(e)[:120])
# serviceable_pincodes?
print("has_serviceable_pincodes", "serviceable_pincodes" in tables)
out = Path(__file__).with_name("db_inspect.json")
out.write_text(json.dumps({"tables": tables}, indent=2), encoding="utf-8")
