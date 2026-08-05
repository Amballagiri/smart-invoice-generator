from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.product import Product
from app.models.user import User


def test_invoice_generates_number_and_calculates_totals(app):
    with app.app_context():
        user = User(username="owner", email="owner@example.com")
        user.set_password("secure-password")
        customer = Customer(name="Acme Ltd", user=user)
        product = Product(
            name="Desk lamp",
            sku="LAMP-001",
            user=user,
            cost_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
            tax_percentage=Decimal("18.00"),
            current_stock=5,
            unit="Piece",
            low_stock_alert_level=1,
        )
        invoice = Invoice(
            customer=customer,
            created_by=user,
            invoice_date=date(2026, 8, 5),
            due_date=date(2026, 8, 20),
            status="Unpaid",
            discount=Decimal("10.00"),
        )
        item = InvoiceItem(
            invoice=invoice,
            product=product,
            quantity=Decimal("2"),
            unit_price=Decimal("50.00"),
            tax_percentage=Decimal("18.00"),
        )
        invoice.recalculate_totals()
        db.session.add_all([user, customer, product, invoice, item])
        db.session.commit()

        assert invoice.invoice_number.startswith("INV-")
        assert invoice.items == [item]
        assert item.line_total == Decimal("118.00")
        assert invoice.gst_total == Decimal("18.00")
        assert invoice.grand_total == Decimal("108.00")
        assert invoice.customer is customer
        assert invoice.created_by is user


def test_invoice_status_constraint_rejects_invalid_value(app):
    with app.app_context():
        user = User(username="owner", email="owner@example.com")
        user.set_password("secure-password")
        customer = Customer(name="Acme Ltd", user=user)
        invoice = Invoice(customer=customer, created_by=user, status="Pending")
        db.session.add(invoice)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        else:
            raise AssertionError("Invalid invoice status should fail database validation")
