from decimal import Decimal

from app.extensions import db


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    tax_percentage = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    line_total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    invoice = db.relationship("Invoice", back_populates="items")
    product = db.relationship("Product", back_populates="invoice_items")

    def recalculate_line_total(self):
        base_total = self.quantity * self.unit_price
        self.line_total = (base_total * (Decimal("1.00") + self.tax_percentage / Decimal("100"))).quantize(Decimal("0.01"))

    def __repr__(self):
        return f"<InvoiceItem invoice={self.invoice_id} product={self.product_id}>"
