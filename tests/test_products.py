from app.extensions import db
from app.models.product import Product
from app.models.user import User


def _login(client, app, email="owner@example.com"):
    with app.app_context():
        user = User(username=email.split("@")[0], email=email)
        user.set_password("secure-password")
        db.session.add(user)
        db.session.commit()
    client.post("/auth/login", data={"email": email, "password": "secure-password"})


def _product_data(**overrides):
    data = {"name": "Desk lamp", "sku": "LAMP-001", "category": "Lighting", "description": "LED desk lamp", "cost_price": "120.00", "selling_price": "199.00", "tax_percentage": "18", "current_stock": "8", "unit": "Piece", "low_stock_alert_level": "3", "is_active": "y"}
    data.update(overrides)
    return data


def test_products_require_login(client):
    response = client.get("/products/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_add_filter_edit_and_delete_product(client, app):
    _login(client, app)
    response = client.post("/products/add", data=_product_data(), follow_redirects=True)
    assert b"Product added successfully" in response.data
    assert b"Desk lamp" in client.get("/products/?q=LAMP-001&category=Lighting").data

    with app.app_context():
        product = Product.query.filter_by(sku="LAMP-001").one()
        product_id = product.id
    response = client.post(f"/products/{product_id}/edit", data=_product_data(name="Reading lamp", current_stock="2"), follow_redirects=True)
    assert b"Product updated successfully" in response.data
    assert b"Reading lamp" in response.data
    response = client.post(f"/products/{product_id}/delete", follow_redirects=True)
    assert b"Product deleted successfully" in response.data
    with app.app_context():
        assert db.session.get(Product, product_id) is None


def test_sku_must_be_unique_per_user(client, app):
    _login(client, app)
    client.post("/products/add", data=_product_data())
    response = client.post("/products/add", data=_product_data(name="Other lamp"), follow_redirects=True)
    assert b"already have a product with this SKU" in response.data


def test_product_cannot_be_accessed_by_another_user(client, app):
    _login(client, app)
    with app.app_context():
        owner = User.query.filter_by(email="owner@example.com").one()
        product = Product(name="Private product", sku="PRIVATE-01", user_id=owner.id, cost_price=1, selling_price=2, tax_percentage=0, current_stock=1, unit="Piece", low_stock_alert_level=0)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    client.post("/auth/logout")
    _login(client, app, "other@example.com")
    assert client.get(f"/products/{product_id}/edit").status_code == 404
