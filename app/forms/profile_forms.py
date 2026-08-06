from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.models.user import User


class ProfileForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=120)])
    profile_image = FileField("Profile picture", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Choose a JPG, PNG, or WebP image.")])
    submit = SubmitField("Save profile")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def validate_username(self, username):
        existing = User.query.filter_by(username=username.data.strip()).first()
        if existing and existing.id != self.user.id:
            raise ValidationError("That username is already in use.")

    def validate_email(self, email):
        existing = User.query.filter_by(email=email.data.strip().lower()).first()
        if existing and existing.id != self.user.id:
            raise ValidationError("That email address is already registered.")

    def validate_profile_image(self, profile_image):
        upload = profile_image.data
        if not isinstance(upload, FileStorage):
            return

        upload.stream.seek(0, 2)
        size = upload.stream.tell()
        upload.stream.seek(0)
        if size > 2 * 1024 * 1024:
            raise ValidationError("Profile pictures must be 2 MB or smaller.")

        try:
            image = Image.open(upload.stream)
            image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValidationError("Choose a valid JPG, PNG, or WebP image.")
        finally:
            upload.stream.seek(0)


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")])
    submit = SubmitField("Update password")
