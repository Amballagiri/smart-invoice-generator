from urllib.parse import urljoin, urlparse

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.extensions import csrf, db, oauth
from app.forms.auth_forms import ForgotPasswordForm, LoginForm, RegistrationForm, ResetPasswordForm
from app.models.user import User
from app.routes.main import home_redirect
from app.services.email_service import send_password_reset_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _is_safe_next_url(target):
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {"http", "https"} and host_url.netloc == redirect_url.netloc


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip(), email=form.email.data.strip().lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Your account has been created. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Welcome back! You are now logged in.", "success")
            next_page = request.args.get("next")
            if next_page and _is_safe_next_url(next_page):
                return redirect(next_page)
            return home_redirect()
        flash("Invalid email address or password.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            try:
                send_password_reset_email(user, user.get_reset_password_token())
            except Exception:
                current_app.logger.exception("Password reset email could not be sent")
        flash("If an account matches that email address, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    user = User.verify_reset_password_token(token)
    if user is None:
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)


@auth_bp.route("/logout", methods=["GET", "POST"])
@csrf.exempt
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


def _unique_username(base):
    """Return a unique username derived from base, appending numbers as needed."""
    candidate = base.strip() or "user"
    if not User.query.filter_by(username=candidate).first():
        return candidate
    i = 1
    while True:
        candidate = f"{base.strip()[:50]}{i}"
        if not User.query.filter_by(username=candidate).first():
            return candidate
        i += 1


@auth_bp.route("/google")
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if not current_app.config.get("GOOGLE_CLIENT_ID") or not current_app.config.get(
        "GOOGLE_CLIENT_SECRET"
    ):
        flash("Google sign-in is not configured.", "danger")
        return redirect(url_for("auth.login"))
    redirect_uri = current_app.config.get("GOOGLE_REDIRECT_URI") or url_for(
        "auth.google_callback", _external=True
    )
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        current_app.logger.exception("Google OAuth authorization failed")
        flash("Google sign-in could not be completed.", "danger")
        return redirect(url_for("auth.login"))

    userinfo = oauth.google.userinfo()
    if not userinfo.get("email_verified"):
        flash("Your Google email is not verified.", "danger")
        return redirect(url_for("auth.login"))

    email = (userinfo.get("email") or "").strip().lower()
    sub = userinfo.get("sub")
    if not email or not sub:
        flash("Google sign-in returned incomplete profile information.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(google_sub=sub).first()
    if user is None:
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(username=_unique_username(email.split("@")[0]), email=email)
            db.session.add(user)
        user.google_sub = sub

    db.session.commit()
    login_user(user)
    flash("You are now logged in.", "success")
    next_page = request.args.get("next")
    if next_page and _is_safe_next_url(next_page):
        return redirect(next_page)
    return home_redirect()
