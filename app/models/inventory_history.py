from datetime import datetime, timezone

from app.extensions import db


class InventoryHistory(db.Model):
    __tablename__ = "inventory_history"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True, index=True)
    quantity_change = db.Column(db.Numeric(12, 3), nullable=False)
    stock_after = db.Column(db.Numeric(12, 3), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    product = db.relationship("Product", back_populates="inventory_history")
    user = db.relationship("User", back_populates="inventory_history")
    invoice = db.relationship("Invoice")
