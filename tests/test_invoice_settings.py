from decimal import Decimal

from app.extensions import db
from app.models.shop_profile import ShopProfile
from app.models.user import User


def _login(client, app):
    with app.app_context():
        user = User(username="settings-owner", email="settings@example.com")
        user.set_password("secure-password")
        db.session.add(user)
        db.session.flush()
        db.session.add(ShopProfile(user_id=user.id, shop_name="Settings Shop"))
        db.session.commit()
    client.post("/auth/login", data={"email": "settings@example.com", "password": "secure-password"})


def test_invoice_settings_can_be_updated(client, app):
    _login(client, app)

    response = client.post(
        "/settings",
        data={
            "invoice_prefix": "sale-2026",
            "default_gst": "5.5",
            "currency": "USD",
            "payment_terms": "Net 15",
            "footer_note": "We appreciate your business.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invoice settings updated." in response.data
    with app.app_context():
        profile = ShopProfile.query.one()
        assert profile.invoice_prefix == "SALE-2026"
        assert profile.default_gst == Decimal("5.50")
        assert profile.currency == "USD"
        assert profile.payment_terms == "Net 15"
        assert profile.footer_note == "We appreciate your business."
