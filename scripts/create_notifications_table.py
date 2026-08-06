"""Fallback script to create the notifications table via SQLAlchemy if migrations can't be run.

Run: python scripts/create_notifications_table.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db

app = create_app({'AUTO_CREATE_DB': True})

with app.app_context():
    # Create only missing tables (safer than drop/create)
    db.create_all()
    print('db.create_all() executed; check your database for the notifications table.')
