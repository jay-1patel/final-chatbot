import sqlite3
conn = sqlite3.connect('faq.db')
for r in conn.execute('SELECT id, slug, display_name FROM tenants'):
    s = str(r[0])+str(r[1])+str(r[2])
    if 'leeway' in s.lower():
        print(r)
conn.close()
