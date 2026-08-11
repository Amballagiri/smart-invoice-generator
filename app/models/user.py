from flask_login import UserMixin
from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)
    google_sub = db.Column(db.String(255), unique=True, nullable=True, index=True)
    customers = db.relationship("Customer", back_populates="user", cascade="all, delete-orphan")
    products = db.relationship("Product", back_populates="user", cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", back_populates="created_by", cascade="all, delete-orphan")
    inventory_history = db.relationship("InventoryHistory", back_populates="user", cascade="all, delete-orphan")
    ai_conversations = db.relationship(
        "AIConversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    shop_profile = db.relationship(
        "ShopProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps({"user_id": self.id}, salt="password-reset")

    @staticmethod
    def verify_reset_password_token(token, max_age=3600):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = serializer.loads(token, salt="password-reset", max_age=max_age)
            user_id = int(data["user_id"])
        except (BadData, KeyError, TypeError, ValueError):
            return None
        return db.session.get(User, user_id)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
