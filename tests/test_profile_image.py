from io import BytesIO
from pathlib import Path

from PIL import Image

from app.extensions import db
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
            "username": "image-owner",
            "email": "image-owner@example.com",
            "password": "secure-password",
            "confirm_password": "secure-password",
        },
    )
    client.post(
        "/auth/login",
        data={"email": "image-owner@example.com", "password": "secure-password"},
    )


def _saved_path(app):
    with app.app_context():
        user = User.query.filter_by(email="image-owner@example.com").one()
        return user.profile_image


def test_profile_image_upload_display_login_and_replacement(client, app):
    _register_and_log_in(client)
    upload_directory = Path(app.static_folder) / "uploads" / "profiles"
    second_file = None

    try:
        response = client.post(
            "/profile/edit",
            data={
                "username": "image-owner",
                "email": "image-owner@example.com",
                "profile_image": (_image_upload("red"), "first.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        first_path = _saved_path(app)
        assert response.status_code == 200
        assert first_path and first_path.startswith("uploads/profiles/")
        assert (Path(app.static_folder) / first_path).is_file()
        assert f'src="/static/{first_path}"'.encode() in response.data

        image_response = client.get(f"/static/{first_path}")
        assert image_response.status_code == 200
        assert image_response.mimetype == "image/webp"
        image_response.close()

        client.post("/auth/logout")
        client.post(
            "/auth/login",
            data={"email": "image-owner@example.com", "password": "secure-password"},
        )
        assert f'src="/static/{first_path}"'.encode() in client.get("/profile").data

        response = client.post(
            "/profile/edit",
            data={
                "username": "image-owner",
                "email": "image-owner@example.com",
                "profile_image": (_image_upload("blue"), "second.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        second_path = _saved_path(app)
        second_file = Path(app.static_folder) / second_path
        assert response.status_code == 200
        assert second_path != first_path
        assert second_file.is_file()
        assert not (Path(app.static_folder) / first_path).exists()
        assert f'src="/static/{second_path}"'.encode() in response.data
    finally:
        if second_file:
            second_file.unlink(missing_ok=True)
