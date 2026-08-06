import os
import sys
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'instance' / 'smart_invoice.db'

if not DB_PATH.exists():
    print('Database file not found at', DB_PATH)
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT,
    icon VARCHAR(80),
    tone VARCHAR(30),
    link VARCHAR(255),
    invoice_id INTEGER,
    is_read BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL
);
''')

# Create index on user_id
cur.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);")

conn.commit()
conn.close()
print('Created/verified notifications table in', DB_PATH)
