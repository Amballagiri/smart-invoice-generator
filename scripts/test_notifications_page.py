"""Test helper: create a test user and notification and load the notifications page.

Run after applying migrations and installing requirements:

python scripts/test_notifications_page.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.services.notification_service import create_notification

app = create_app()

with app.app_context():
    # If migrations weren't applied, ensure tables exist
    db.create_all()

    # Create or get a test user
    user = User.query.filter_by(email='test+notifications@example.com').first()
    if not user:
        user = User(username='notif_test', email='test+notifications@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

    # Create a notification
    n = create_notification(user.id, 'Test notification', 'Created by test script', icon='bi-bell', tone='info')
    print('Created notification id=', n.id)

    # Use test client to fetch the notifications page
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.get_id()

    resp = client.get('/notifications')
    print('Notifications page status:', resp.status_code)
    if resp.status_code == 200:
        print('Notifications page loaded OK')
    else:
        print(resp.get_data(as_text=True))
