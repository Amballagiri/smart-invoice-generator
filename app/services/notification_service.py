from datetime import datetime
from typing import Optional

from app.extensions import db
from app.models.notification import Notification


def create_notification(user_id: int, title: str, body: str = "", icon: Optional[str] = None, tone: Optional[str] = None, link: Optional[str] = None, invoice_id: Optional[int] = None):
    n = Notification(
        user_id=user_id,
        title=title,
        body=body,
        icon=icon,
        tone=tone,
        link=link,
        invoice_id=invoice_id,
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.session.add(n)
    db.session.commit()
    return n


def mark_read(notification_id: int, user_id: int):
    n = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not n:
        return None
    n.is_read = True
    db.session.commit()
    return n


def mark_all_read(user_id: int):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()


def clear_all(user_id: int):
    Notification.query.filter_by(user_id=user_id).delete()
    db.session.commit()
