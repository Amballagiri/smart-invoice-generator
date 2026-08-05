from app.extensions import db
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.user import User


def _login(client, app, email="owner@example.com"):
    with app.app_context():
        user = User(username=email.split("@")[0], email=email)
        user.set_password("secure-password")
        db.session.add(user)
        db.session.commit()
    client.post("/auth/login", data={"email": email, "password": "secure-password"})


def _setup_invoice_data(app):
    with app.app_context():
        user = User.query.filter_by(email="owner@example.com").one()
        customer = Customer(name="Acme Ltd", user=user)
        product = Product(name="Desk lamp", sku="LAMP-001", user=user, cost_price=100, selling_price=150, tax_percentage=18, current_stock=10, unit="Piece", low_stock_alert_level=2)
        db.session.add_all([customer, product])
        db.session.commit()
        return customer.id, product.id


def _invoice_data(customer_id, product_id, **overrides):
    data = {"customer_id": str(customer_id), "invoice_date": "2026-08-05", "due_date": "2026-08-20", "status": "Draft", "discount": "10.00", "notes": "Thank you", "items-0-product_id": str(product_id), "items-0-quantity": "2"}
    data.update(overrides)
    return data


def test_invoice_routes_require_login(client):
    response = client.get("/invoices/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_create_list_detail_edit_and_delete_draft_invoice(client, app):
    _login(client, app)
    customer_id, product_id = _setup_invoice_data(app)
    response = client.post("/invoices/create", data=_invoice_data(customer_id, product_id), follow_redirects=True)
    assert b"Invoice created successfully" in response.data
    assert b"Acme Ltd" in response.data

    with app.app_context():
        invoice = Invoice.query.one()
        invoice_id = invoice.id
        invoice_number = invoice.invoice_number
        assert str(invoice.grand_total) == "344.00"
    assert invoice_number.encode() in client.get(f"/invoices/?q={invoice_number}").data

    response = client.post(f"/invoices/{invoice_id}/edit", data=_invoice_data(customer_id, product_id, notes="Updated note", discount="0"), follow_redirects=True)
    assert b"Draft invoice updated successfully" in response.data
    assert b"Updated note" in response.data
    response = client.post(f"/invoices/{invoice_id}/delete", follow_redirects=True)
    assert b"Draft invoice deleted successfully" in response.data
    with app.app_context():
        assert db.session.get(Invoice, invoice_id) is None


def test_paid_invoice_cannot_be_edited_or_deleted(client, app):
    _login(client, app)
    customer_id, product_id = _setup_invoice_data(app)
    client.post("/invoices/create", data=_invoice_data(customer_id, product_id, status="Paid"))
    with app.app_context():
        invoice_id = Invoice.query.one().id
    assert b"Only draft invoices can be edited" in client.get(f"/invoices/{invoice_id}/edit", follow_redirects=True).data
    assert b"Only draft invoices can be deleted" in client.post(f"/invoices/{invoice_id}/delete", follow_redirects=True).data
    with app.app_context():
        assert db.session.get(Invoice, invoice_id) is not None


def test_invoice_is_not_accessible_by_another_user(client, app):
    _login(client, app)
    customer_id, product_id = _setup_invoice_data(app)
    client.post("/invoices/create", data=_invoice_data(customer_id, product_id))
    with app.app_context():
        invoice_id = Invoice.query.one().id
    client.post("/auth/logout")
    _login(client, app, "other@example.com")
    assert client.get(f"/invoices/{invoice_id}").status_code == 404
