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


def test_login_with_remember_creates_remember_cookie(client, app):
    client.post("/auth/register", data={"username": "reme", "email": "reme@example.com", "password": "secure-password", "confirm_password": "secure-password"}, follow_redirects=True)
    resp = client.post("/auth/login", data={"email": "reme@example.com", "password": "secure-password", "remember": "1"}, follow_redirects=False)
    cookies = resp.headers.getlist("Set-Cookie")
    assert any(c.split(";")[0].startswith("remember_token=") for c in cookies)


def test_login_without_remember_has_no_remember_cookie(client, app):
    client.post("/auth/register", data={"username": "nor", "email": "nor@example.com", "password": "secure-password", "confirm_password": "secure-password"}, follow_redirects=True)
    resp = client.post("/auth/login", data={"email": "nor@example.com", "password": "secure-password"}, follow_redirects=False)
    cookies = resp.headers.getlist("Set-Cookie")
    assert not any(c.split(";")[0].startswith("remember_token=") for c in cookies)
