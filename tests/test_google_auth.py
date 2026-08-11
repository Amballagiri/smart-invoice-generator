import pytest

from app.extensions import db, oauth
from app.models.user import User


@pytest.fixture()
def google_configured_app(app):
    app.config["GOOGLE_CLIENT_ID"] = "test-client-id"
    app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
    app.config["GOOGLE_REDIRECT_URI"] = "https://smart-invoice-generator-9k3v.onrender.com/auth/google/callback"
    return app


def _stub_google(monkeypatch, userinfo):
    google = oauth.google

    def fake_authorize_access_token():
        return {"access_token": "fake-token", "id_token": "fake-id-token"}

    def fake_userinfo():
        return userinfo

    monkeypatch.setattr(google, "authorize_access_token", fake_authorize_access_token)
    monkeypatch.setattr(google, "userinfo", fake_userinfo)


def test_google_login_redirects_when_configured(client, google_configured_app, monkeypatch):
    google = oauth.google
    monkeypatch.setattr(google, "authorize_redirect", lambda redirect_uri: redirect_uri)
    response = client.get("/auth/google")
    assert response.status_code == 200
    assert "onrender.com" in response.get_data(as_text=True)


def test_google_login_missing_config(client, app):
    app.config["GOOGLE_CLIENT_ID"] = None
    app.config["GOOGLE_CLIENT_SECRET"] = None
    response = client.get("/auth/google", follow_redirects=True)
    assert b"not configured" in response.data


def test_google_new_user_created(client, google_configured_app, monkeypatch):
    _stub_google(monkeypatch, {
        "email": "newgoogle@example.com",
        "email_verified": True,
        "sub": "google-sub-111",
    })
    response = client.get("/auth/google/callback", follow_redirects=True)
    with google_configured_app.app_context():
        user = User.query.filter_by(email="newgoogle@example.com").first()
        assert user is not None
        assert user.google_sub == "google-sub-111"
        assert user.check_password("anything") is False
    assert response.status_code == 200


def test_google_returning_user_no_duplicate(client, google_configured_app, monkeypatch, app):
    _stub_google(monkeypatch, {
        "email": "returning@example.com",
        "email_verified": True,
        "sub": "google-sub-222",
    })
    with app.app_context():
        user = User(username="returning", email="returning@example.com", google_sub="google-sub-222")
        user.set_password("secret-pass")
        db.session.add(user)
        db.session.commit()

    client.get("/auth/google/callback", follow_redirects=True)

    with app.app_context():
        count = User.query.filter_by(email="returning@example.com").count()
        user = User.query.filter_by(email="returning@example.com").first()
        assert count == 1
        assert user.google_sub == "google-sub-222"


def test_google_matches_existing_email_account(client, google_configured_app, monkeypatch, app):
    _stub_google(monkeypatch, {
        "email": "existing@example.com",
        "email_verified": True,
        "sub": "google-sub-333",
    })
    with app.app_context():
        user = User(username="existing", email="existing@example.com")
        user.set_password("keep-my-password")
        db.session.add(user)
        db.session.commit()

    client.get("/auth/google/callback", follow_redirects=True)

    with app.app_context():
        count = User.query.filter_by(email="existing@example.com").count()
        user = User.query.filter_by(email="existing@example.com").first()
        assert count == 1
        assert user.google_sub == "google-sub-333"
        assert user.check_password("keep-my-password") is True


def test_google_unverified_email_rejected(client, google_configured_app, monkeypatch, app):
    _stub_google(monkeypatch, {
        "email": "unverified@example.com",
        "email_verified": False,
        "sub": "google-sub-444",
    })
    response = client.get("/auth/google/callback", follow_redirects=True)
    assert b"not verified" in response.data
    with app.app_context():
        assert User.query.filter_by(email="unverified@example.com").count() == 0
