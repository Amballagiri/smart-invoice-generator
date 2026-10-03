from app.models.user import User
from app.extensions import db

def test_about_page_requires_login(client):
    response = client.get("/about")
    # Redirects to login
    assert response.status_code in (302, 401)

def test_about_page_renders_for_authenticated_user(client, app):
    with app.app_context():
        user = User(username="aboutuser", email="aboutuser@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    # Log in
    client.post("/auth/login", data={"email": "aboutuser@example.com", "password": "password123"})

    response = client.get("/about")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check key sections and content
    assert "Smart Invoice Generator" in html
    assert "Simple invoicing. Smarter business." in html
    assert "Everything you need to manage your business" in html
    assert "Powerful features, built for simplicity" in html
    assert "From customer to invoice in a few simple steps" in html
    assert "Why Smart Invoice Generator" in html
    assert "Built with modern technology" in html
    assert "Designed &amp; Developed by Amballa Giri" in html or "Designed & Developed by Amballa Giri" in html
    assert "@giri_79189" in html
    assert "Version" in html
    assert "1.0.0" in html

    # Verify NO fake/sample invoice data or fictional customer/payment info exists
    assert "INV-2026-0842" not in html
    assert "Apex Enterprises" not in html
    assert "Bengaluru, India" not in html
    assert "14,750" not in html
    assert "8,500" not in html
    assert "4,000" not in html
    assert "12,500" not in html
    assert "2,250" not in html
    assert "UPI QR Ready" not in html
    assert "Due on Receipt" not in html

