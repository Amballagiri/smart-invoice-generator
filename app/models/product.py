from datetime import datetime, timezone

from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (db.UniqueConstraint("user_id", "sku", name="uq_products_user_sku"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    sku = db.Column(db.String(80), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    cost_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    selling_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    tax_percentage = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(30), nullable=False, default="Piece")
    low_stock_alert_level = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="products")
    invoice_items = db.relationship("InvoiceItem", back_populates="product")

    def __repr__(self):
        return f"<Product {self.sku}>"
