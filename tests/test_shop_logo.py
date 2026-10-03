from io import BytesIO
from pathlib import Path

from PIL import Image

from app.extensions import db
from app.models.shop_profile import ShopProfile
from app.models.user import User


def _image_upload(color):
    image = Image.new("RGB", (24, 24), color)
    stream = BytesIO()
    image.save(stream, "PNG")
    stream.seek(0)
    return stream


def _register_and_log_in(client):
    client.post(
        "/auth/register",
        data={
            "username": "logo-owner",
            "email": "logo-owner@example.com",
            "password": "secure-password",
            "confirm_password": "secure-password",
        },
    )
    client.post(
        "/auth/login",
        data={"email": "logo-owner@example.com", "password": "secure-password"},
    )


def test_shop_logo_upload_displayed_in_settings(client, app):
    _register_and_log_in(client)
    with app.app_context():
        user = User.query.filter_by(email="logo-owner@example.com").one()
        db.session.add(ShopProfile(user_id=user.id, shop_name="Logo Shop"))
        db.session.commit()

    saved_file = None
    try:
        response = client.post(
            "/settings/logo",
            data={"logo": (_image_upload("green"), "logo.png")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            profile = ShopProfile.query.join(User).filter(User.email == "logo-owner@example.com").one()
            logo_path = profile.logo
        assert logo_path and logo_path.startswith("uploads/logos/")
        saved_file = Path(app.static_folder) / logo_path
        assert saved_file.is_file()

        settings = client.get("/settings")
        assert f'src="/static/{logo_path}"'.encode() in settings.data
        assert b"No logo uploaded" not in settings.data

        image_response = client.get(f"/static/{logo_path}")
        assert image_response.status_code == 200
        image_response.close()
    finally:
        if saved_file:
            saved_file.unlink(missing_ok=True)
