import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'instance' / 'smart_invoice.db'

if not DB_PATH.exists():
    print('Database file not found at', DB_PATH)
    raise SystemExit(1)

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Ensure notifications table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications';")
if not cur.fetchone():
    print('notifications table not found. Run scripts/sql_create_notifications_table.py first.')
    conn.close()
    raise SystemExit(1)

# Ensure a user exists; if not, create one using available non-null columns
cur.execute("PRAGMA table_info(users);")
cols = cur.fetchall()
if not cols:
    print('users table not found; cannot create notification without a user.')
    conn.close()
    raise SystemExit(1)

col_names = [c['name'] for c in cols]
notnull = {c['name']: c['notnull'] for c in cols}

# Try to find existing user
cur.execute("SELECT id FROM users LIMIT 1;")
row = cur.fetchone()
if row:
    user_id = row['id']
    print('Found existing user id=', user_id)
else:
    # Build insert for a minimal user
    fields = []
    values = []
    placeholders = []
    # Common columns to set
    if 'username' in col_names:
        fields.append('username')
        values.append('notif_test')
        placeholders.append('?')
    if 'email' in col_names:
        fields.append('email')
        values.append('test+notifications@example.com')
        placeholders.append('?')
    if 'password_hash' in col_names:
        fields.append('password_hash')
        values.append('x')
        placeholders.append('?')
    if 'created_at' in col_names:
        fields.append('created_at')
        values.append(datetime.utcnow().isoformat())
        placeholders.append('?')
    # For any other NOT NULL columns without default, insert blank/zero
    for name in col_names:
        if name in fields:
            continue
        if notnull.get(name) and name != 'id':
            fields.append(name)
            values.append('')
            placeholders.append('?')

    sql = f"INSERT INTO users ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
    cur.execute(sql, values)
    user_id = cur.lastrowid
    conn.commit()
    print('Inserted test user id=', user_id)

# Insert test notification (build values based on actual notifications columns)
now = datetime.utcnow().isoformat()
# Rebuild values with correct columns present in notifications table
cur.execute("PRAGMA table_info(notifications);")
notif_cols = [c['name'] for c in cur.fetchall()]
fields = []
placeholders = []
values = []
for name in ['user_id', 'title', 'body', 'icon', 'tone', 'link', 'invoice_id', 'is_read', 'created_at']:
    if name in notif_cols:
        fields.append(name)
        placeholders.append('?')
        if name == 'user_id':
            values.append(user_id)
        elif name == 'title':
            values.append('Test notification')
        elif name == 'body':
            values.append('Created by assistant script')
        elif name == 'icon':
            values.append('bi-bell')
        elif name == 'tone':
            values.append('info')
        elif name == 'link':
            values.append(None)
        elif name == 'invoice_id':
            values.append(None)
        elif name == 'is_read':
            values.append(0)
        elif name == 'created_at':
            values.append(now)

sql = f"INSERT INTO notifications ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
cur.execute(sql, values)
notif_id = cur.lastrowid
conn.commit()
print('Inserted notification id=', notif_id)

# Query the notification back
cur.execute('SELECT * FROM notifications WHERE id=?', (notif_id,))
notif = cur.fetchone()
print('Notification row:')
for k in notif.keys():
    print(k, '=>', notif[k])

conn.close()
print('Done')
