import sqlite3
conn = sqlite3.connect('faq.db')
# knowledge_base schema
print('KB SCHEMA:')
for r in conn.execute('PRAGMA table_info(knowledge_base)'):
    print(r)
print('\nFAQ SCHEMA:')
for r in conn.execute('PRAGMA table_info(faq_dataset)'):
    print(r)
conn.close()
