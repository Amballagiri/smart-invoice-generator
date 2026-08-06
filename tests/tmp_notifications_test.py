import os
import sys

# Ensure the project root is on sys.path so 'app' package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.services.notification_service import create_notification

app = create_app({
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'AUTO_CREATE_DB': True,
})

with app.app_context():
    # create tables
    db.create_all()
    # create a user
    u = User(username='testuser', email='test@example.com')
    u.set_password('password')
    db.session.add(u)
    db.session.commit()
    # create a notification
    n = create_notification(u.id, 'Test notice', 'This is a test', icon='bi-bell', tone='info')
    print('Created notification id=', n.id)
    # use test client
    client = app.test_client()
    # login the user via login route (bypass by setting session)
    with client.session_transaction() as sess:
        sess['user_id'] = u.get_id()
    # Try API
    resp = client.get('/notifications/api')
    print('API status:', resp.status_code)
    print('API json:', resp.get_json())
