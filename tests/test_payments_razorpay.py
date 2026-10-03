"""Razorpay provider tests.

All provider API calls are mocked via an injected fake client. No network
calls are made and no real credentials are required.
"""

import hashlib
import hmac
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import create_app
from app.extensions import db
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.user import User
from app.services import payment_service
from app.services import payment_service as payment_service_module
from app.services.payment_service import (
    PaymentResult,
    RazorpayProvider,
    get_payment_provider,
)
from app.routes import payments as payment_routes


KEY_SECRET = "test_key_secret"
WEBHOOK_SECRET = "test_webhook_secret"


# --------------------------------------------------------------------------- #
# Fake Razorpay client
# --------------------------------------------------------------------------- #
class FakeClient:
    """Mimics the small slice of the Razorpay SDK the provider uses."""

    def __init__(self):
        self.order = self
        self.payment = self
        self.created_orders = []
        self.payments = {}

    def create(self, data):
        order_id = f"order_{len(self.created_orders) + 1:04d}"
        self.created_orders.append(data)
        return {
            "id": order_id,
            "amount": data["amount"],
            "currency": data["currency"],
            "receipt": data.get("receipt"),
            "status": "created",
        }

    def fetch(self, payment_id):
        return self.payments[payment_id]


def _payment_signature(secret, order_id, payment_id):
    return hmac.new(
        secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()


def _webhook_signature(secret, body):
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
@pytest.fixture()
def rzp(tmp_path, monkeypatch):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "AUTO_CREATE_DB": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'rzp.db'}",
            "SECRET_KEY": "rzp-test-secret",
            "PAYMENT_PROVIDER": "razorpay",
            "RAZORPAY_KEY_ID": "rzp_test_abc",
            "RAZORPAY_KEY_SECRET": KEY_SECRET,
            "RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET,
        }
    )
    client = app.test_client()
    fake = FakeClient()
    provider = RazorpayProvider(
        key_id="rzp_test_abc",
        key_secret=KEY_SECRET,
        webhook_secret=WEBHOOK_SECRET,
        client=fake,
    )
    monkeypatch.setattr(payment_routes, "get_payment_provider", lambda: provider)
    monkeypatch.setattr(payment_service_module, "get_payment_provider", lambda: provider)
    yield SimpleNamespace(app=app, client=client, provider=provider, fake=fake)
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _make_user(app, email="owner@example.com", password="secure-password"):
    with app.app_context():
        user = User(username=email.split("@")[0], email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def _make_invoice(app, email="owner@example.com", grand_total="177.00"):
    with app.app_context():
        user = User.query.filter_by(email=email).one()
        customer = Customer(name="Acme Ltd", email="acme@example.com", user=user)
        db.session.add(customer)
        db.session.commit()
        invoice = Invoice(
            customer_id=customer.id,
            created_by_id=user.id,
            status="Draft",
            gst_total=Decimal("27.00"),
            discount=Decimal("0.00"),
            grand_total=Decimal(grand_total),
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice.id


def _token(app, invoice_id):
    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        return payment_service.PaymentService.create_payment_token(invoice)


def _snapshot(app, invoice_id):
    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        return {
            "status": invoice.status,
            "payment_status": invoice.payment_status,
            "transaction_id": invoice.payment_transaction_id,
            "payment_order_id": invoice.payment_order_id,
            "amount_paid": str(invoice.amount_paid) if invoice.amount_paid is not None else None,
        }


def _payment_entity(order_id, amount=17700, status="captured", payment_id="pay_TEST0001"):
    return {
        "id": payment_id,
        "entity": "payment",
        "amount": amount,
        "currency": "INR",
        "status": status,
        "order_id": order_id,
        "method": "upi",
        "vpa": "success@razorpay",
        "created_at": 1700000000,
    }


def _create_order(rzp, token):
    return rzp.client.post(f"/payments/pay/{token}/order").get_json()


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def test_configuration_loaded(rzp):
    cfg = rzp.app.config
    assert cfg["PAYMENT_PROVIDER"] == "razorpay"
    assert cfg["RAZORPAY_KEY_ID"] == "rzp_test_abc"
    assert cfg["RAZORPAY_KEY_SECRET"] == KEY_SECRET
    assert cfg["RAZORPAY_WEBHOOK_SECRET"] == WEBHOOK_SECRET


# --------------------------------------------------------------------------- #
# 1. Order creation
# --------------------------------------------------------------------------- #
def test_order_creation_with_mocked_provider(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)

    response = rzp.client.post(f"/payments/pay/{token}/order")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["amount"] == 17700  # paise
    assert data["currency"] == "INR"
    assert data["key_id"] == "rzp_test_abc"
    # Secret must never be present.
    assert "key_secret" not in data
    assert "secret" not in json.dumps(data).lower()
    # Provider received a correctly-formed order with an invoice note.
    assert rzp.fake.created_orders[0]["amount"] == 17700
    assert rzp.fake.created_orders[0]["notes"]["invoice_id"] == str(invoice_id)


def test_order_reuses_open_order(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)

    first = _create_order(rzp, token)
    second = _create_order(rzp, token)

    assert first["order_id"] == second["order_id"]
    assert len(rzp.fake.created_orders) == 1  # no duplicate provider orders


# --------------------------------------------------------------------------- #
# 2 & 3. Payment signature (unit + route)
# --------------------------------------------------------------------------- #
def test_provider_signature_helpers():
    provider = RazorpayProvider(
        key_id="k", key_secret=KEY_SECRET, webhook_secret=WEBHOOK_SECRET, client=object()
    )
    assert provider.verify_payment_signature(
        "order_1", "pay_1", _payment_signature(KEY_SECRET, "order_1", "pay_1")
    )
    assert not provider.verify_payment_signature("order_1", "pay_1", "deadbeef")
    assert provider.verify_webhook_signature(
        "body", _webhook_signature(WEBHOOK_SECRET, "body")
    )
    assert not provider.verify_webhook_signature("body", "deadbeef")


def test_valid_payment_signature_marks_paid(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    order = _create_order(rzp, token)

    pay_id = "pay_VALID0001"
    rzp.fake.payments[pay_id] = _payment_entity(order["order_id"], payment_id=pay_id)
    signature = _payment_signature(KEY_SECRET, order["order_id"], pay_id)

    response = rzp.client.post(
        f"/payments/verify/{token}",
        json={
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": pay_id,
            "razorpay_signature": signature,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    snap = _snapshot(rzp.app, invoice_id)
    assert snap["status"] == "Paid"
    assert snap["payment_status"] == "Paid"
    assert snap["transaction_id"] == pay_id
    assert snap["amount_paid"] == "177.00"


def test_invalid_payment_signature_does_not_mark_paid(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    order = _create_order(rzp, token)

    pay_id = "pay_BADSIG0001"
    rzp.fake.payments[pay_id] = _payment_entity(order["order_id"], payment_id=pay_id)

    response = rzp.client.post(
        f"/payments/verify/{token}",
        json={
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": pay_id,
            "razorpay_signature": "not-a-valid-signature",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert _snapshot(rzp.app, invoice_id)["payment_status"] == "Pending"


# --------------------------------------------------------------------------- #
# 4 & 5. Webhook signature
# --------------------------------------------------------------------------- #
def _send_webhook(rzp, event, signature, event_id="evt_1"):
    body = json.dumps(event)
    return rzp.client.post(
        "/payments/webhook/razorpay",
        data=body,
        content_type="application/json",
        headers={
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": event_id,
        },
    )


def test_valid_webhook_signature_marks_paid(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    order = _create_order(rzp, token)

    event = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": _payment_entity(order["order_id"], payment_id="pay_WH0001")}},
    }
    body = json.dumps(event)
    response = _send_webhook(rzp, event, _webhook_signature(WEBHOOK_SECRET, body))

    assert response.status_code == 200
    assert response.get_json()["result"] == PaymentResult.OK
    assert _snapshot(rzp.app, invoice_id)["payment_status"] == "Paid"


def test_invalid_webhook_signature_does_not_mark_paid(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    order = _create_order(rzp, token)

    event = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": _payment_entity(order["order_id"], payment_id="pay_WHBADSIG")}},
    }
    response = _send_webhook(rzp, event, "invalid-signature")

    assert response.status_code == 400
    assert _snapshot(rzp.app, invoice_id)["payment_status"] == "Pending"


# --------------------------------------------------------------------------- #
# 6. Wrong invoice association
# --------------------------------------------------------------------------- #
def test_verify_rejects_order_from_another_invoice(rzp):
    _make_user(rzp.app)
    invoice_a = _make_invoice(rzp.app)
    invoice_b = _make_invoice(rzp.app)
    token_a = _token(rzp.app, invoice_a)
    token_b = _token(rzp.app, invoice_b)

    order_b = _create_order(rzp, token_b)
    pay_id = "pay_OTHER0001"
    rzp.fake.payments[pay_id] = _payment_entity(order_b["order_id"], payment_id=pay_id)
    signature = _payment_signature(KEY_SECRET, order_b["order_id"], pay_id)

    response = rzp.client.post(
        f"/payments/verify/{token_a}",
        json={
            "razorpay_order_id": order_b["order_id"],
            "razorpay_payment_id": pay_id,
            "razorpay_signature": signature,
        },
    )

    assert response.status_code == 400
    assert _snapshot(rzp.app, invoice_a)["payment_status"] == "Pending"
    assert _snapshot(rzp.app, invoice_b)["payment_status"] == "Pending"


# --------------------------------------------------------------------------- #
# 7. Wrong amount
# --------------------------------------------------------------------------- #
def test_verify_rejects_wrong_amount(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    order = _create_order(rzp, token)

    pay_id = "pay_WRONGAMT01"
    rzp.fake.payments[pay_id] = _payment_entity(
        order["order_id"], amount=100, payment_id=pay_id  # ₹1.00 vs ₹177.00
    )
    signature = _payment_signature(KEY_SECRET, order["order_id"], pay_id)

    response = rzp.client.post(
        f"/payments/verify/{token}",
        json={
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": pay_id,
            "razorpay_signature": signature,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["result"] == PaymentResult.AMOUNT_MISMATCH
    assert _snapshot(rzp.app, invoice_id)["payment_status"] == "Pending"


# --------------------------------------------------------------------------- #
# 8. Duplicate webhook event
# --------------------------------------------------------------------------- #
def test_duplicate_webhook_event_is_ignored(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    order = _create_order(rzp, token)

    event = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": _payment_entity(order["order_id"], payment_id="pay_DUPWH01")}},
    }
    body = json.dumps(event)
    signature = _webhook_signature(WEBHOOK_SECRET, body)

    first = _send_webhook(rzp, event, signature, event_id="evt_dup")
    after_first = _snapshot(rzp.app, invoice_id)
    second = _send_webhook(rzp, event, signature, event_id="evt_dup")
    after_second = _snapshot(rzp.app, invoice_id)

    assert first.get_json()["result"] == PaymentResult.OK
    assert second.get_json()["result"] == PaymentResult.DUPLICATE
    assert after_first == after_second
    assert after_second["payment_status"] == "Paid"


# --------------------------------------------------------------------------- #
# 9. Duplicate provider payment
# --------------------------------------------------------------------------- #
def test_duplicate_provider_payment_not_applied_to_second_invoice(rzp):
    _make_user(rzp.app)
    invoice_a = _make_invoice(rzp.app)
    invoice_b = _make_invoice(rzp.app)
    token_a = _token(rzp.app, invoice_a)
    token_b = _token(rzp.app, invoice_b)

    order_a = _create_order(rzp, token_a)
    order_b = _create_order(rzp, token_b)

    # Pay invoice A with pay_SHARED.
    event_a = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": _payment_entity(order_a["order_id"], payment_id="pay_SHARED01")}},
    }
    body_a = json.dumps(event_a)
    _send_webhook(rzp, event_a, _webhook_signature(WEBHOOK_SECRET, body_a), event_id="evt_a")

    # Attempt to reuse the same provider payment id for invoice B.
    event_b = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": _payment_entity(order_b["order_id"], payment_id="pay_SHARED01")}},
    }
    body_b = json.dumps(event_b)
    result = _send_webhook(
        rzp, event_b, _webhook_signature(WEBHOOK_SECRET, body_b), event_id="evt_b"
    ).get_json()["result"]

    assert _snapshot(rzp.app, invoice_a)["payment_status"] == "Paid"
    assert _snapshot(rzp.app, invoice_b)["payment_status"] == "Pending"
    assert result in (
        PaymentResult.DUPLICATE,
        PaymentResult.ALREADY_PAID,
        PaymentResult.ORDER_MISMATCH,
    )
    with rzp.app.app_context():
        assert Payment.query.filter_by(provider_payment_id="pay_SHARED01").count() == 1


# --------------------------------------------------------------------------- #
# 10. Browser / client cannot mark paid
# --------------------------------------------------------------------------- #
def test_client_cannot_mark_paid_directly(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    _create_order(rzp, token)

    # No signature at all.
    response = rzp.client.post(
        f"/payments/verify/{token}",
        json={"razorpay_order_id": "order_x", "razorpay_payment_id": "pay_x"},
    )
    assert response.status_code == 400
    assert _snapshot(rzp.app, invoice_id)["payment_status"] == "Pending"


def test_owner_mock_confirmation_disabled_in_razorpay_mode(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    rzp.client.post(
        "/auth/login", data={"email": "owner@example.com", "password": "secure-password"}
    )

    response = rzp.client.post(
        f"/payments/invoice/{invoice_id}/mark-paid", data={"amount": "177.00"}
    )

    assert response.status_code == 302
    assert _snapshot(rzp.app, invoice_id)["payment_status"] == "Pending"


# --------------------------------------------------------------------------- #
# 12. Failed payment does not mark paid
# --------------------------------------------------------------------------- #
def test_failed_payment_does_not_mark_paid(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    order = _create_order(rzp, token)

    pay_id = "pay_FAILED001"
    rzp.fake.payments[pay_id] = _payment_entity(
        order["order_id"], status="failed", payment_id=pay_id
    )
    signature = _payment_signature(KEY_SECRET, order["order_id"], pay_id)

    response = rzp.client.post(
        f"/payments/verify/{token}",
        json={
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": pay_id,
            "razorpay_signature": signature,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["result"] == PaymentResult.PAYMENT_FAILED
    assert _snapshot(rzp.app, invoice_id)["payment_status"] == "Pending"


def test_webhook_failed_event_does_not_mark_paid(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)
    order = _create_order(rzp, token)

    event = {
        "event": "payment.failed",
        "payload": {"payment": {"entity": _payment_entity(order["order_id"], status="failed", payment_id="pay_WHFAIL01")}},
    }
    body = json.dumps(event)
    response = _send_webhook(rzp, event, _webhook_signature(WEBHOOK_SECRET, body), event_id="evt_fail")

    assert response.status_code == 200
    assert _snapshot(rzp.app, invoice_id)["payment_status"] == "Pending"


# --------------------------------------------------------------------------- #
# 13. Mock mode remains the default and untouched
# --------------------------------------------------------------------------- #
def test_mock_provider_is_default(client, app):
    assert app.config.get("PAYMENT_PROVIDER") == "mock"
    with app.app_context():
        assert get_payment_provider() is None


def test_public_page_renders_razorpay_checkout_without_secrets(rzp):
    _make_user(rzp.app)
    invoice_id = _make_invoice(rzp.app)
    token = _token(rzp.app, invoice_id)

    response = rzp.client.get(f"/payments/pay/{token}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Razorpay" in body
    assert "checkout.razorpay.com" in body
    assert "TEST MODE" not in body
    assert KEY_SECRET not in body
    assert WEBHOOK_SECRET not in body
