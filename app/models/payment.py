"""Payment provider models.

These tables hold individual provider transactions and the raw provider events
used for idempotent webhook processing. They exist alongside the invoice-level
"current payment summary" fields (``Invoice.payment_*``) and do not replace the
secure mock flow.
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class Payment(db.Model):
    """A single payment attempt/transaction for an invoice via a provider."""

    __tablename__ = "payments"
    __table_args__ = (
        db.UniqueConstraint("provider_order_id", name="uq_payments_provider_order_id"),
        db.UniqueConstraint("provider_payment_id", name="uq_payments_provider_payment_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = db.Column(db.String(30), nullable=False, default="razorpay")
    provider_order_id = db.Column(db.String(100), nullable=True)
    provider_payment_id = db.Column(db.String(100), nullable=True)
    provider_link_id = db.Column(db.String(100), nullable=True)
    provider_qr_id = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(3), nullable=False, default="INR")
    status = db.Column(db.String(30), nullable=True)
    method = db.Column(db.String(30), nullable=True)
    vpa = db.Column(db.String(100), nullable=True)
    signature_verified = db.Column(db.Boolean, nullable=False, default=False)
    amount_refunded = db.Column(
        db.Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    raw_payload = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow
    )
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)

    invoice = db.relationship(
        "Invoice",
        backref=db.backref(
            "payments",
            cascade="all, delete-orphan",
            order_by="Payment.created_at",
        ),
    )

    def __repr__(self):
        return (
            "<Payment "
            f"{self.provider} "
            f"{self.provider_payment_id or self.provider_order_id or self.id}>"
        )


class PaymentEvent(db.Model):
    """A raw provider webhook/callback event, deduplicated by event id."""

    __tablename__ = "payment_events"
    __table_args__ = (
        db.UniqueConstraint("event_id", name="uq_payment_events_event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(30), nullable=False, default="razorpay")
    event_id = db.Column(db.String(120), nullable=False)
    event_type = db.Column(db.String(80), nullable=True)
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    payment_id = db.Column(
        db.Integer,
        db.ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    payload = db.Column(db.Text, nullable=True)
    signature_valid = db.Column(db.Boolean, nullable=False, default=False)
    received_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow
    )
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    payment = db.relationship(
        "Payment",
        backref=db.backref(
            "events",
            cascade="all, delete-orphan",
            order_by="PaymentEvent.received_at",
        ),
    )

    def __repr__(self):
        return f"<PaymentEvent {self.event_type} {self.event_id}>"
