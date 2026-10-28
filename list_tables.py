import sqlite3
conn = sqlite3.connect('faq.db')
for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(r[0])
conn.close()
