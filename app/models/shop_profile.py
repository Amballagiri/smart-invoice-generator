from datetime import datetime, timezone

from app.extensions import db


class ShopProfile(db.Model):
    """Per-user shop/business details used on invoices and correspondence."""

    __tablename__ = "shop_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    shop_name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(60), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    gst_number = db.Column(db.String(64), nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", back_populates="shop_profile")

    def __repr__(self):
        return f"<ShopProfile {self.shop_name}>"
