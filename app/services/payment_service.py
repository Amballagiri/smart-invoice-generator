"""Payment service for Smart Invoice Generator.

Two payment paths exist, selected by ``PAYMENT_PROVIDER``:

* ``mock`` (default) - the original, deliberately-secure local mock flow. It
  makes no network calls and is unchanged.
* ``razorpay`` - real provider integration using the official Razorpay Python
  SDK for API calls. Signatures are verified server-side with the documented
  HMAC-SHA256 algorithm.

Security invariants:
* Public pages are addressed by signed, expiring tokens, never database ids.
* An invoice is only marked paid after a server-side signature check, a
  provider-side fetch/verification (or a signature-verified webhook), a check
  that the payment/order belongs to the invoice, and an exact amount match.
* Provider status updates are a single conditional UPDATE guarded on the
  invoice not already being paid, so they are atomic and idempotent.
* Provider webhooks are deduplicated on ``PaymentEvent.event_id``.
* Secrets are only read from configuration and never returned to clients.
"""

import base64
import hashlib
import hmac
import io
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import quote

import qrcode
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentEvent


PAYMENT_TOKEN_SALT = "invoice-payment-link"
PAYMENT_TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

RAZORPAY_PROVIDER = "razorpay"
PAISE = Decimal("100")


class PaymentResult:
    """Outcome of a payment action."""

    OK = "ok"
    ALREADY_PAID = "already_paid"
    AMOUNT_MISMATCH = "amount_mismatch"
    NOT_FOUND = "not_found"
    SIGNATURE_INVALID = "signature_invalid"
    ORDER_MISMATCH = "order_mismatch"
    PROVIDER_ERROR = "provider_error"
    PAYMENT_FAILED = "payment_failed"
    DUPLICATE = "duplicate"


class PaymentError(Exception):
    """Raised when the provider cannot fulfil a request."""


def _to_paise(amount):
    """Convert a rupee amount to integer paise (Razorpay's subunit)."""
    return int(
        (Decimal(str(amount)) * PAISE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def _paise_to_amount(paise):
    return (Decimal(str(paise)) / PAISE).quantize(Decimal("0.01"))


def _hmac_sha256_hex(secret, message):
    return hmac.new(
        (secret or "").encode("utf-8"),
        (message or "").encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _utcnow():
    return datetime.now(timezone.utc)


class RazorpayProvider:
    """Thin wrapper around the official Razorpay Python SDK.

    The SDK is imported lazily so the application (and its test suite) can run
    in ``mock`` mode - or with an injected fake client - without the package or
    real credentials being present.
    """

    def __init__(self, key_id=None, key_secret=None, webhook_secret=None, client=None):
        self.key_id = key_id if key_id is not None else current_app.config.get("RAZORPAY_KEY_ID")
        self.key_secret = (
            key_secret if key_secret is not None else current_app.config.get("RAZORPAY_KEY_SECRET")
        )
        self.webhook_secret = (
            webhook_secret
            if webhook_secret is not None
            else current_app.config.get("RAZORPAY_WEBHOOK_SECRET")
        )
        self._client = client

    @property
    def client(self):
        if self._client is None:
            import razorpay  # imported lazily; only needed for real API calls

            self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
        return self._client

    # -- API calls ---------------------------------------------------------
    def create_order(self, invoice):
        data = {
            "amount": _to_paise(invoice.grand_total),
            "currency": invoice.currency or "INR",
            "receipt": invoice.invoice_number,
            # Notes let a later webhook find the correct invoice.
            "notes": {
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
            },
        }
        try:
            return self.client.order.create(data=data)
        except Exception as exc:  # noqa: BLE001 - surface as a clean provider error
            current_app.logger.exception("Razorpay order creation failed")
            raise PaymentError("Could not create payment order") from exc

    def fetch_payment(self, payment_id):
        return self.client.payment.fetch(payment_id)

    # -- Signature verification (documented HMAC-SHA256) -------------------
    def verify_payment_signature(self, order_id, payment_id, signature):
        """Verify ``order_id|payment_id`` signed with the API key secret."""
        if not signature or not order_id or not payment_id:
            return False
        expected = _hmac_sha256_hex(self.key_secret, f"{order_id}|{payment_id}")
        return hmac.compare_digest(expected, signature)

    def verify_webhook_signature(self, body, signature):
        """Verify the raw webhook body signed with the webhook secret."""
        if not signature:
            return False
        expected = _hmac_sha256_hex(self.webhook_secret, body)
        return hmac.compare_digest(expected, signature)


def get_payment_provider():
    """Return a RazorpayProvider when configured, otherwise ``None``."""
    if (current_app.config.get("PAYMENT_PROVIDER") or "mock").lower() != RAZORPAY_PROVIDER:
        return None
    return RazorpayProvider()


class PaymentService:
    """QR helpers, signed payment links and the atomic payment confirmation."""

    # ------------------------------------------------------------------ #
    # Signed payment tokens
    # ------------------------------------------------------------------ #
    @staticmethod
    def _serializer():
        return URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"],
            salt=PAYMENT_TOKEN_SALT,
        )

    @staticmethod
    def create_payment_token(invoice):
        """Return a signed, expiring token that identifies this invoice."""
        return PaymentService._serializer().dumps({"invoice_id": invoice.id})

    @staticmethod
    def resolve_payment_token(token, max_age=PAYMENT_TOKEN_MAX_AGE):
        """Return the invoice id encoded in a valid token, or ``None``."""
        try:
            payload = PaymentService._serializer().loads(token, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        if not isinstance(payload, dict):
            return None
        return payload.get("invoice_id")

    @staticmethod
    def provider_is_mock():
        return (current_app.config.get("PAYMENT_PROVIDER") or "mock").lower() != RAZORPAY_PROVIDER

    # ------------------------------------------------------------------ #
    # UPI (mock) helpers - used only by the mock flow
    # ------------------------------------------------------------------ #
    @staticmethod
    def _upi_id():
        # Falls back to a clearly non-routable placeholder so the mock never
        # accidentally points at a real account.
        return current_app.config.get("UPI_ID") or "mock@upi"

    @staticmethod
    def _company_name():
        return current_app.config.get("COMPANY_NAME", "Smart Invoice Generator")

    @staticmethod
    def _payment_url(invoice):
        amount = invoice.grand_total
        return (
            f"upi://pay?pa={quote(PaymentService._upi_id())}"
            f"&pn={quote(PaymentService._company_name())}"
            f"&am={amount}&cu=INR"
            f"&tn={quote('Payment for ' + invoice.invoice_number)}"
        )

    @staticmethod
    def generate_upi_qr_code(invoice):
        """Return a dict with a base64 PNG QR code for the invoice."""
        try:
            upi_url = PaymentService._payment_url(invoice)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(upi_url)
            qr.make(fit=True)
            image = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            encoded = base64.b64encode(buffer.getvalue()).decode()

            return {
                "qr_code_data": f"data:image/png;base64,{encoded}",
                "upi_url": upi_url,
                "amount": str(invoice.grand_total),
            }
        except Exception:
            current_app.logger.exception("Error generating QR code")
            return None

    @staticmethod
    def generate_upi_deep_links(invoice):
        """Return UPI app deep links for the invoice (mock)."""
        params = (
            f"pa={quote(PaymentService._upi_id())}"
            f"&pn={quote(PaymentService._company_name())}"
            f"&am={invoice.grand_total}&cu=INR"
            f"&tn={quote('Payment for ' + invoice.invoice_number)}"
        )
        return {
            "gpay": f"tez://upi/pay?{params}",
            "phonepe": f"phonepe://upi/pay?{params}",
            "paytm": f"paytmmp://upi/pay?{params}",
            "bhim": f"bhim://upi/pay?{params}",
            "generic": f"upi://pay?{params}",
        }

    # ------------------------------------------------------------------ #
    # Atomic mock confirmation (unchanged mock behaviour)
    # ------------------------------------------------------------------ #
    @staticmethod
    def confirm_mock_payment(invoice_id, amount):
        """Atomically mark an invoice paid exactly once (mock flow).

        Returns a ``(PaymentResult, invoice_or_None)`` tuple. The write is a
        single conditional UPDATE guarded on the invoice not already being
        paid, which prevents duplicate/concurrent payments. The amount must
        match the invoice grand total.
        """
        try:
            expected = Decimal(str(amount)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            return PaymentResult.AMOUNT_MISMATCH, None

        invoice = db.session.get(Invoice, invoice_id)
        if invoice is None:
            return PaymentResult.NOT_FOUND, None
        if invoice.payment_status == "Paid" or invoice.status == "Paid":
            return PaymentResult.ALREADY_PAID, invoice
        if expected != Decimal(invoice.grand_total).quantize(Decimal("0.01")):
            return PaymentResult.AMOUNT_MISMATCH, invoice

        transaction_id = f"MOCK-{uuid.uuid4().hex[:20].upper()}"
        statement = (
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.payment_status != "Paid",
                Invoice.status != "Paid",
            )
            .values(
                status="Paid",
                payment_status="Paid",
                payment_method="Mock UPI",
                payment_gateway="mock",
                payment_transaction_id=transaction_id,
                payment_date=_utcnow(),
            )
        )

        try:
            result = db.session.execute(statement)
            if result.rowcount != 1:
                db.session.rollback()
                return PaymentResult.ALREADY_PAID, db.session.get(Invoice, invoice_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Error confirming mock payment")
            raise

        db.session.expire_all()
        return PaymentResult.OK, db.session.get(Invoice, invoice_id)

    # ================================================================== #
    # Razorpay provider flow
    # ================================================================== #
    @staticmethod
    def create_provider_order(invoice, provider):
        """Create (or reuse) a Razorpay order for an invoice.

        Returns only non-secret checkout parameters; the key secret is never
        included.
        """
        amount = _to_paise(invoice.grand_total)
        existing = (
            Payment.query.filter_by(invoice_id=invoice.id, provider=RAZORPAY_PROVIDER)
            .filter(Payment.status.notin_(["captured", "failed", "refunded"]))
            .order_by(Payment.created_at.desc())
            .first()
        )

        if (
            existing is not None
            and existing.provider_order_id
            and Decimal(existing.amount or 0) == Decimal(invoice.grand_total)
        ):
            order = {
                "id": existing.provider_order_id,
                "amount": _to_paise(existing.amount),
                "currency": existing.currency,
            }
        else:
            order = provider.create_order(invoice)
            existing = Payment(
                invoice_id=invoice.id,
                provider=RAZORPAY_PROVIDER,
                provider_order_id=order.get("id"),
                amount=invoice.grand_total,
                currency=order.get("currency") or (invoice.currency or "INR"),
                status="created",
            )
            db.session.add(existing)
            db.session.commit()

        return {
            "order_id": order.get("id"),
            "amount": int(order.get("amount") or amount),
            "currency": order.get("currency") or (invoice.currency or "INR"),
            "key_id": provider.key_id,
            "name": PaymentService._company_name(),
            "invoice_number": invoice.invoice_number,
        }

    @staticmethod
    def verify_provider_payment(invoice, order_id, payment_id, signature):
        """Server-side verification of a Checkout callback.

        Never trusts the browser: verifies the signature, then fetches the
        payment from the provider and checks order ownership, status and
        amount before marking the invoice paid.
        """
        provider = get_payment_provider()
        if provider is None:
            return PaymentResult.PROVIDER_ERROR, invoice
        if not order_id or not payment_id or not signature:
            return PaymentResult.SIGNATURE_INVALID, invoice

        payment = Payment.query.filter_by(
            invoice_id=invoice.id,
            provider=RAZORPAY_PROVIDER,
            provider_order_id=order_id,
        ).first()
        if payment is None:
            return PaymentResult.ORDER_MISMATCH, invoice

        if not provider.verify_payment_signature(order_id, payment_id, signature):
            return PaymentResult.SIGNATURE_INVALID, invoice

        try:
            entity = provider.fetch_payment(payment_id)
        except Exception:
            current_app.logger.exception("Razorpay payment fetch failed")
            return PaymentResult.PROVIDER_ERROR, invoice

        if not isinstance(entity, dict):
            return PaymentResult.PROVIDER_ERROR, invoice
        if entity.get("order_id") != order_id:
            return PaymentResult.ORDER_MISMATCH, invoice

        return PaymentService._capture_from_entity(
            invoice, payment, entity, signature_verified=True
        )

    @staticmethod
    def process_webhook_event(event, event_id=None, raw_body=None, signature_valid=True):
        """Idempotently process a (already signature-verified) webhook event."""
        event_type = event.get("event") or "unknown"
        payload = event.get("payload") or {}

        entity = None
        for kind in ("payment", "order", "refund", "payment_link", "qr_code"):
            node = payload.get(kind)
            if isinstance(node, dict) and isinstance(node.get("entity"), dict):
                entity = node["entity"]
                break

        if event_id is None:
            entity_id = (entity or {}).get("id") or ""
            event_id = f"{event_type}:{entity_id}"

        # Idempotency: claim the event id atomically via the unique constraint.
        if PaymentEvent.query.filter_by(event_id=event_id).first() is not None:
            return PaymentResult.DUPLICATE

        record = PaymentEvent(
            provider=RAZORPAY_PROVIDER,
            event_id=event_id,
            event_type=event_type,
            payload=raw_body,
            signature_valid=bool(signature_valid),
        )
        db.session.add(record)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return PaymentResult.DUPLICATE

        success_events = {"payment.captured", "order.paid"}
        if event_type not in success_events:
            if event_type == "payment.failed" and entity is not None:
                PaymentService._record_failed_payment(entity)
            record.processed_at = _utcnow()
            db.session.commit()
            return PaymentResult.OK

        if entity is None:
            record.processed_at = _utcnow()
            db.session.commit()
            return PaymentResult.PROVIDER_ERROR

        invoice, payment = PaymentService._associate_entity(entity)
        if invoice is None:
            record.processed_at = _utcnow()
            db.session.commit()
            return PaymentResult.NOT_FOUND

        record.invoice_id = invoice.id
        if payment is not None:
            record.payment_id = payment.id

        result, _ = PaymentService._capture_from_entity(
            invoice, payment, entity, signature_verified=True
        )
        if result in (PaymentResult.OK, PaymentResult.ALREADY_PAID):
            record.processed_at = _utcnow()
        db.session.commit()
        return result

    # ------------------------------------------------------------------ #
    # Internal helpers for the provider flow
    # ------------------------------------------------------------------ #
    @staticmethod
    def _associate_entity(entity):
        """Find the invoice/payment a provider entity belongs to."""
        entity_id = entity.get("id")
        payment_id = (
            entity_id
            if isinstance(entity_id, str) and entity_id.startswith("pay_")
            else entity.get("payment_id")
        )
        order_id = entity.get("order_id") or (
            entity_id
            if isinstance(entity_id, str) and entity_id.startswith("order_")
            else None
        )

        payment = None
        if payment_id:
            payment = Payment.query.filter_by(provider_payment_id=payment_id).first()
        if payment is None and order_id:
            payment = Payment.query.filter_by(provider_order_id=order_id).first()

        invoice = None
        if payment is not None:
            invoice = db.session.get(Invoice, payment.invoice_id)

        notes = entity.get("notes") or {}
        if invoice is None and notes.get("invoice_id"):
            try:
                invoice = db.session.get(Invoice, int(notes["invoice_id"]))
            except (TypeError, ValueError):
                invoice = None

        return invoice, payment

    @staticmethod
    def _record_failed_payment(entity):
        _, payment = PaymentService._associate_entity(entity)
        if payment is not None:
            payment.status = (entity.get("status") or "failed").lower()
            payment.raw_payload = json.dumps(entity)
            db.session.commit()

    @staticmethod
    def _capture_from_entity(invoice, payment, entity, signature_verified=False):
        """Validate a provider entity and (if valid) mark the invoice paid."""
        if not isinstance(entity, dict):
            return PaymentResult.PROVIDER_ERROR, invoice

        entity_id = entity.get("id")
        payment_id = (
            entity_id
            if isinstance(entity_id, str) and entity_id.startswith("pay_")
            else entity.get("payment_id")
        )
        order_id = entity.get("order_id") or (
            entity_id
            if isinstance(entity_id, str) and entity_id.startswith("order_")
            else None
        )

        if (
            payment is not None
            and payment.provider_order_id
            and order_id
            and order_id != payment.provider_order_id
        ):
            return PaymentResult.ORDER_MISMATCH, invoice

        entity_amount = entity.get("amount")
        if entity_amount is None or int(entity_amount) != _to_paise(invoice.grand_total):
            return PaymentResult.AMOUNT_MISMATCH, invoice
        if (entity.get("currency") or invoice.currency) != invoice.currency:
            return PaymentResult.AMOUNT_MISMATCH, invoice

        status = (entity.get("status") or "").lower()
        if status not in ("captured", "authorized", "paid"):
            if payment is not None:
                payment.status = status or "failed"
                if payment_id:
                    payment.provider_payment_id = payment_id
                payment.raw_payload = json.dumps(entity)
                db.session.commit()
            return PaymentResult.PAYMENT_FAILED, invoice

        return PaymentService._mark_invoice_paid(
            invoice, payment, entity, signature_verified=signature_verified
        )

    @staticmethod
    def _mark_invoice_paid(invoice, payment, entity, signature_verified=False):
        entity_id = entity.get("id")
        payment_id = (
            entity_id
            if isinstance(entity_id, str) and entity_id.startswith("pay_")
            else entity.get("payment_id")
        )
        order_id = entity.get("order_id") or (
            entity_id
            if isinstance(entity_id, str) and entity_id.startswith("order_")
            else None
        )

        # Never create a second record for a provider payment owned elsewhere.
        if payment_id:
            clash = Payment.query.filter(
                Payment.provider_payment_id == payment_id,
                Payment.invoice_id != invoice.id,
            ).first()
            if clash is not None:
                return PaymentResult.DUPLICATE, invoice

        amount = _paise_to_amount(entity.get("amount"))
        paid_at = _utcnow()
        created = entity.get("created_at")
        if created:
            try:
                paid_at = datetime.fromtimestamp(int(created), tz=timezone.utc)
            except (TypeError, ValueError, OSError, OverflowError):
                paid_at = _utcnow()

        if payment is None:
            payment = Payment(
                invoice_id=invoice.id,
                provider=RAZORPAY_PROVIDER,
                provider_order_id=order_id,
            )
            db.session.add(payment)

        payment.provider_payment_id = payment_id or payment.provider_payment_id
        payment.provider_order_id = order_id or payment.provider_order_id
        payment.amount = amount
        payment.currency = entity.get("currency") or payment.currency or invoice.currency
        payment.status = "captured"
        payment.method = entity.get("method") or payment.method
        payment.vpa = entity.get("vpa") or payment.vpa
        payment.signature_verified = bool(signature_verified)
        payment.raw_payload = json.dumps(entity)
        payment.paid_at = paid_at

        statement = (
            update(Invoice)
            .where(
                Invoice.id == invoice.id,
                Invoice.payment_status != "Paid",
                Invoice.status != "Paid",
            )
            .values(
                status="Paid",
                payment_status="Paid",
                payment_gateway=RAZORPAY_PROVIDER,
                payment_method=payment.method or "razorpay",
                payment_transaction_id=payment_id or invoice.payment_transaction_id,
                payment_order_id=order_id or invoice.payment_order_id,
                payment_provider_status="captured",
                amount_paid=amount,
                upi_id=payment.vpa or invoice.upi_id,
                payment_date=paid_at,
            )
        )

        try:
            result = db.session.execute(
                statement.execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                db.session.rollback()
                return PaymentResult.ALREADY_PAID, db.session.get(Invoice, invoice.id)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return PaymentResult.DUPLICATE, db.session.get(Invoice, invoice.id)
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Error confirming provider payment")
            raise

        db.session.expire_all()
        return PaymentResult.OK, db.session.get(Invoice, invoice.id)
