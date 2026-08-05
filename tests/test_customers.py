from app.extensions import db
from app.models.customer import Customer
from app.models.user import User


def _login(client, app, email="owner@example.com"):
    with app.app_context():
        user = User(username=email.split("@")[0], email=email)
        user.set_password("secure-password")
        db.session.add(user)
        db.session.commit()
    client.post("/auth/login", data={"email": email, "password": "secure-password"})


def test_customers_require_login(client):
    response = client.get("/customers/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_add_search_edit_and_delete_customer(client, app):
    _login(client, app)
    response = client.post(
        "/customers/add",
        data={"name": "Acme Industries", "email": "billing@acme.example.com", "phone": "555-0110"},
        follow_redirects=True,
    )
    assert b"Customer added successfully" in response.data
    assert b"Acme Industries" in client.get("/customers/?q=acme").data

    with app.app_context():
        customer = Customer.query.filter_by(name="Acme Industries").one()
        customer_id = customer.id
    response = client.post(f"/customers/{customer_id}/edit", data={"name": "Acme Limited"}, follow_redirects=True)
    assert b"Customer updated successfully" in response.data
    assert b"Acme Limited" in response.data
    response = client.post(f"/customers/{customer_id}/delete", follow_redirects=True)
    assert b"Customer deleted successfully" in response.data
    with app.app_context():
        assert db.session.get(Customer, customer_id) is None


def test_customer_cannot_be_accessed_by_another_user(client, app):
    _login(client, app)
    with app.app_context():
        owner = User.query.filter_by(email="owner@example.com").one()
        customer = Customer(name="Private customer", user_id=owner.id)
        db.session.add(customer)
        db.session.commit()
        customer_id = customer.id
    client.post("/auth/logout")
    _login(client, app, "other@example.com")
    assert client.get(f"/customers/{customer_id}/edit").status_code == 404
