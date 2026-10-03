from datetime import date, datetime, timezone
from decimal import Decimal
from secrets import token_hex

from app.extensions import db


def generate_invoice_number(prefix="INV"):
    """Generate a readable, collision-resistant invoice number."""
    return f"{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{token_hex(3).upper()}"


class Invoice(db.Model):
    __tablename__ = "invoices"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('Draft', 'Paid', 'Unpaid', 'Cancelled')",
            name="ck_invoices_status",
        ),
        db.CheckConstraint(
            "payment_status IN ('Pending', 'Paid', 'Failed', 'Refunded')",
            name="ck_invoices_payment_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(
        db.String(40),
        unique=True,
        nullable=False,
        default=generate_invoice_number,
        index=True,
    )
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False,
        index=True,
    )
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Draft")
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)
    currency = db.Column(db.String(3), nullable=False, default="INR")
    payment_method = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(20), nullable=False, default="Pending")
    payment_gateway = db.Column(db.String(50), nullable=True)  # upi, razorpay, etc.
    payment_transaction_id = db.Column(db.String(100), nullable=True)
    payment_date = db.Column(db.DateTime(timezone=True), nullable=True)
    upi_id = db.Column(db.String(100), nullable=True)  # for UPI payments
    payment_link = db.Column(db.String(200), nullable=True)  # Payment gateway link
    payment_order_id = db.Column(db.String(100), nullable=True, index=True)  # provider order id
    payment_provider_status = db.Column(db.String(30), nullable=True)  # provider-side status
    amount_paid = db.Column(db.Numeric(12, 2), nullable=True)  # captured amount
    template_name = db.Column(db.String(30), nullable=False, default="Modern Blue")
    round_off = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    discount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    gst_total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    grand_total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    stock_finalized = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
)

    customer = db.relationship("Customer", back_populates="invoices")
    created_by = db.relationship("User", back_populates="invoices")
    items = db.relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    def recalculate_totals(self):
        """Update GST and grand totals from the currently attached line items."""
        subtotal = Decimal("0.00")
        gst_total = Decimal("0.00")

        for item in self.items:
            item.recalculate_line_total()
            base_total = item.quantity * item.unit_price
            item_discount = base_total * (item.discount_percentage or Decimal("0.00")) / Decimal("100")
            base_total -= item_discount
            subtotal += base_total
            gst_total += (
                base_total * item.tax_percentage / Decimal("100")
            )

        self.gst_total = gst_total.quantize(Decimal("0.01"))
        self.grand_total = (
            subtotal + self.gst_total - (self.discount or Decimal("0.00")) + (self.round_off or Decimal("0.00"))
        ).quantize(Decimal("0.01"))

    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"
