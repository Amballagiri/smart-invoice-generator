from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    icon = Column(String(80), nullable=True)
    tone = Column(String(30), nullable=True)
    link = Column(String(255), nullable=True)
    invoice_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "icon": self.icon,
            "tone": self.tone,
            "link": self.link,
            "invoice_id": self.invoice_id,
            "is_read": bool(self.is_read),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
