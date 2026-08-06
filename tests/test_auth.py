from app.models.user import User


def test_dashboard_requires_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_user_can_register_log_in_and_log_out(client, app):
    response = client.post("/auth/register", data={"username": "ada", "email": "ada@example.com", "password": "secure-password", "confirm_password": "secure-password"}, follow_redirects=True)
    assert b"account has been created" in response.data
    with app.app_context():
        user = User.query.filter_by(email="ada@example.com").first()
        assert user and user.check_password("secure-password")
    assert b"Welcome back! You are now logged in." in client.post("/auth/login", data={"email": "ada@example.com", "password": "secure-password"}, follow_redirects=True).data
    assert b"logged out" in client.post("/auth/logout", follow_redirects=True).data
