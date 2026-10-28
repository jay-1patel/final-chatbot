import sqlite3
conn = sqlite3.connect('faq.db')
cur = conn.cursor()
for r in cur.execute("SELECT id, tenant_id, title, source FROM knowledge_base LIMIT 50"):
    s = str(r)
    if 'leeway' in s.lower():
        print('KB:', r)
for r in cur.execute("SELECT id, tenant_id, source_file, content_type, content FROM faq_dataset LIMIT 50"):
    s = str(r)
    if 'leeway' in s.lower():
        print('FAQ:', r)
conn.close()
