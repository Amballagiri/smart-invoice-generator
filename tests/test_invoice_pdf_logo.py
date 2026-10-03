import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from pypdf import PdfReader

from app.extensions import db
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.shop_profile import ShopProfile
from app.models.user import User


def _register_and_log_in(client):
    client.post(
        "/auth/register",
        data={
            "username": "pdf-logo",
            "email": "pdf-logo@example.com",
            "password": "secure-password",
            "confirm_password": "secure-password",
        },
    )
    client.post(
        "/auth/login",
        data={"email": "pdf-logo@example.com", "password": "secure-password"},
    )


def _write_webp_logo(app, rel_path, size=(300, 120)):
    """Write a real WEBP file under the static folder and return its path."""
    path = Path(app.static_folder) / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.new("RGBA", size, (16, 76, 129, 255)).save(path, "WEBP")
    return path


def _create_invoice(client, app):
    with app.app_context():
        user = User.query.filter_by(email="pdf-logo@example.com").one()
        customer = Customer(name="Acme Ltd", user=user)
        product = Product(
            name="Desk lamp",
            sku="LAMP-001",
            user=user,
            cost_price=100,
            selling_price=150,
            tax_percentage=18,
            current_stock=10,
            unit="Piece",
            low_stock_alert_level=2,
        )
        db.session.add_all([customer, product])
        db.session.commit()
        customer_id, product_id = customer.id, product.id

    client.post(
        "/invoices/create",
        data={
            "customer_id": str(customer_id),
            "invoice_date": "2026-08-05",
            "due_date": "2026-08-20",
            "status": "Draft",
            "discount": "10.00",
            "notes": "Thank you",
            "items-0-product_id": str(product_id),
            "items-0-quantity": "2",
        },
    )
    with app.app_context():
        return Invoice.query.one().id


def _pdf_image_count(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    return sum(len(page.images) for page in reader.pages)


def test_invoice_pdf_embeds_company_logo(client, app):
    _register_and_log_in(client)
    rel_path = f"uploads/logos/test-{uuid.uuid4().hex}.webp"
    logo_file = _write_webp_logo(app, rel_path)
    try:
        with app.app_context():
            user = User.query.filter_by(email="pdf-logo@example.com").one()
            db.session.add(ShopProfile(user_id=user.id, shop_name="Logo Shop", logo=rel_path))
            db.session.commit()

        invoice_id = _create_invoice(client, app)
        response = client.get(f"/invoices/{invoice_id}/pdf")

        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert _pdf_image_count(response.data) >= 1

        text = "".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.data)).pages)
        assert "Logo Shop" in text
    finally:
        logo_file.unlink(missing_ok=True)


def test_invoice_pdf_without_logo_still_generates(client, app):
    _register_and_log_in(client)
    with app.app_context():
        user = User.query.filter_by(email="pdf-logo@example.com").one()
        db.session.add(ShopProfile(user_id=user.id, shop_name="No Logo Shop"))
        db.session.commit()

    invoice_id = _create_invoice(client, app)
    response = client.get(f"/invoices/{invoice_id}/pdf")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert _pdf_image_count(response.data) == 0

    text = "".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.data)).pages)
    assert "No Logo Shop" in text
