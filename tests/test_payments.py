import re
from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.user import User
from app.services.payment_service import PaymentService


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _make_user(app, email="owner@example.com", password="secure-password"):
    with app.app_context():
        user = User(username=email.split("@")[0], email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="owner@example.com", password="secure-password"):
    return client.post("/auth/login", data={"email": email, "password": password})


def _make_invoice(app, email="owner@example.com", status="Draft", grand_total="177.00"):
    with app.app_context():
        user = User.query.filter_by(email=email).one()
        customer = Customer(name="Acme Ltd", email="acme@example.com", user=user)
        db.session.add(customer)
        db.session.commit()
        invoice = Invoice(
            customer_id=customer.id,
            created_by_id=user.id,
            status=status,
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
        return PaymentService.create_payment_token(invoice)


def _snapshot(app, invoice_id):
    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        return {
            "status": invoice.status,
            "payment_status": invoice.payment_status,
            "transaction_id": invoice.payment_transaction_id,
            "grand_total": str(invoice.grand_total),
        }


# --------------------------------------------------------------------------- #
# Public (token) pages: read-only, non-enumerable
# --------------------------------------------------------------------------- #
def test_public_payment_page_is_read_only_and_uses_token(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)
    token = _token(app, invoice_id)

    response = client.get(f"/payments/pay/{token}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "TEST MODE" in body
    assert "Mark as Paid (TEST)" not in body  # public page never mutates


def test_invalid_or_tampered_token_returns_404(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)

    assert client.get("/payments/pay/not-a-real-token").status_code == 404
    # Legacy numeric id must not resolve as a token.
    assert client.get(f"/payments/success/{invoice_id}").status_code == 404


def test_get_success_never_marks_invoice_paid(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)
    token = _token(app, invoice_id)
    before = _snapshot(app, invoice_id)

    response = client.get(f"/payments/success/{token}")

    assert response.status_code == 302  # redirected to the pay page
    assert _snapshot(app, invoice_id) == before


def test_status_endpoint_uses_token(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)
    token = _token(app, invoice_id)

    response = client.get(f"/payments/status/{token}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["payment_status"] == "Pending"
    assert payload["status"] == "Draft"


# --------------------------------------------------------------------------- #
# Authentication / authorization
# --------------------------------------------------------------------------- #
def test_anonymous_cannot_mark_invoice_paid(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)
    before = _snapshot(app, invoice_id)

    response = client.post(
        f"/payments/invoice/{invoice_id}/mark-paid",
        data={"amount": "177.00"},
    )

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
    assert _snapshot(app, invoice_id) == before


def test_other_user_cannot_mark_paid_or_view_qr(client, app):
    _make_user(app, "owner@example.com")
    invoice_id = _make_invoice(app, "owner@example.com")

    _make_user(app, "intruder@example.com")
    _login(client, "intruder@example.com")

    before = _snapshot(app, invoice_id)
    assert client.post(
        f"/payments/invoice/{invoice_id}/mark-paid", data={"amount": "177.00"}
    ).status_code == 403
    assert client.get(f"/payments/invoice/{invoice_id}/qr").status_code == 403
    assert _snapshot(app, invoice_id) == before


def test_qr_requires_login(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)

    response = client.get(f"/payments/invoice/{invoice_id}/qr")

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


# --------------------------------------------------------------------------- #
# Amount validation & status transitions
# --------------------------------------------------------------------------- #
def test_owner_mark_paid_validates_amount(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)
    _login(client)

    # Wrong amount -> rejected, no state change.
    client.post(
        f"/payments/invoice/{invoice_id}/mark-paid", data={"amount": "1.00"}
    )
    assert _snapshot(app, invoice_id)["payment_status"] == "Pending"

    # Non-numeric amount -> rejected.
    client.post(
        f"/payments/invoice/{invoice_id}/mark-paid", data={"amount": "abc"}
    )
    assert _snapshot(app, invoice_id)["payment_status"] == "Pending"

    # Correct amount -> paid.
    client.post(
        f"/payments/invoice/{invoice_id}/mark-paid", data={"amount": "177.00"}
    )
    after = _snapshot(app, invoice_id)
    assert after["status"] == "Paid"
    assert after["payment_status"] == "Paid"
    assert after["transaction_id"]
    assert after["grand_total"] == "177.00"


def test_mock_payment_is_idempotent(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)
    _login(client)

    client.post(
        f"/payments/invoice/{invoice_id}/mark-paid", data={"amount": "177.00"}
    )
    first = _snapshot(app, invoice_id)

    # Second confirmation must not change anything (same transaction id).
    client.post(
        f"/payments/invoice/{invoice_id}/mark-paid", data={"amount": "177.00"}
    )
    second = _snapshot(app, invoice_id)

    assert first == second
    assert second["payment_status"] == "Paid"


def test_paid_invoice_pay_page_redirects_to_receipt(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app, status="Paid")
    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        invoice.payment_status = "Paid"
        db.session.commit()
    token = _token(app, invoice_id)

    response = client.get(f"/payments/pay/{token}")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/payments/success/{token}")

    receipt = client.get(f"/payments/success/{token}")
    assert receipt.status_code == 200
    assert "TEST payment" in receipt.get_data(as_text=True)


# --------------------------------------------------------------------------- #
# Legacy / dead routes removed
# --------------------------------------------------------------------------- #
def test_legacy_insecure_routes_are_gone(client, app):
    _make_user(app)
    invoice_id = _make_invoice(app)

    assert client.get(f"/payments/pay/invoice/{invoice_id}").status_code == 404
    assert client.get(f"/payments/invoice/{invoice_id}/payment-links").status_code == 404
    assert client.post(
        f"/payments/invoice/{invoice_id}/verify-payment", json={}
    ).status_code == 404
    assert client.get("/payments/test").status_code == 404


# --------------------------------------------------------------------------- #
# CSRF protection (needs its own app with CSRF enabled)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def csrf_client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": True,
            "AUTO_CREATE_DB": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.db'}",
            "SECRET_KEY": "csrf-test-secret",
        }
    )
    client = app.test_client()
    yield client, app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_csrf_is_required_to_mark_paid(csrf_client):
    client, app = csrf_client
    user_id = _make_user(app)
    invoice_id = _make_invoice(app)

    # Log in without going through the CSRF-protected login form.
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    # POST without a CSRF token -> rejected, no state change.
    response = client.post(
        f"/payments/invoice/{invoice_id}/mark-paid", data={"amount": "177.00"}
    )
    assert response.status_code == 400
    assert _snapshot(app, invoice_id)["payment_status"] == "Pending"

    # Pull the real CSRF token from the invoice detail page and retry.
    detail = client.get(f"/invoices/{invoice_id}")
    match = re.search(r'name="csrf_token" value="([^"]+)"', detail.get_data(as_text=True))
    assert match, "invoice detail page should expose a CSRF token"
    token = match.group(1)

    response = client.post(
        f"/payments/invoice/{invoice_id}/mark-paid",
        data={"amount": "177.00", "csrf_token": token},
    )
    assert response.status_code == 302
    assert _snapshot(app, invoice_id)["payment_status"] == "Paid"
