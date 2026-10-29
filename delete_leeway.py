import sqlite3
conn = sqlite3.connect('faq.db')
cur = conn.cursor()
cur.execute("DELETE FROM knowledge_base WHERE tenant_id = 'leewaysoftech'")
print('kb deleted:', cur.rowcount)
cur.execute("DELETE FROM faq_dataset WHERE tenant_id = 'leewaysoftech'")
print('faq deleted:', cur.rowcount)
conn.commit()
conn.close()
