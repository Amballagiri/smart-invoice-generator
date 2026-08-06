import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    conn = db.engine.connect()
    res = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications';")
    rows = list(res)
    if rows:
        print('notifications table exists')
    else:
        print('notifications table missing')
    conn.close()
