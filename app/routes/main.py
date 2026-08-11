from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, url_for, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from PIL import Image, ImageOps
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import RequestEntityTooLarge

from app.extensions import db
from app.forms.profile_forms import ChangePasswordForm, ProfileForm
from app.forms.company_forms import CompanyForm, ShopSetupForm
import json
from flask import jsonify
from app.models.notification import Notification
from app.models.shop_profile import ShopProfile
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.services.notification_service import mark_read, mark_all_read, clear_all, create_notification
from datetime import date

main_bp = Blueprint("main", __name__)


PROFILE_IMAGE_SIZE = (300, 300)
PROFILE_IMAGE_QUALITY = 82
LOGO_IMAGE_SIZE = (512, 512)
LOGO_IMAGE_QUALITY = 85


def shop_is_configured():
    """True when the current user has saved shop details."""
    return getattr(current_user, "shop_profile", None) is not None


def home_redirect():
    """Landing after login: onboard new users, then the dashboard overview."""
    if not shop_is_configured():
        return redirect(url_for("main.setup_shop"))
    return redirect(url_for("main.dashboard"))


@main_bp.route("/")
@login_required
def dashboard():

    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    total_customers = len(current_user.customers)

    total_products = len(current_user.products)

    total_invoices = len(current_user.invoices)

    total_revenue = sum(
        float(invoice.grand_total or 0)
        for invoice in current_user.invoices
        if invoice.status == "Paid"
    )

    low_stock = sum(
        1
        for product in current_user.products
        if product.current_stock <= product.low_stock_alert_level
    )

    recent_invoices = sorted(
        current_user.invoices,
        key=lambda invoice: invoice.created_at,
        reverse=True,
    )[:5]

    # Monthly sales data (Jan-Dec)
    monthly_sales = [0] * 12

    for invoice in current_user.invoices:
        if invoice.status == "Paid":
            month = invoice.invoice_date.month - 1
            monthly_sales[month] += float(invoice.grand_total)

    return render_template(
        "main/dashboard.html",
        greeting=greeting,
        total_customers=total_customers,
        total_products=total_products,
        total_invoices=total_invoices,
        total_revenue=f"{total_revenue:.2f}",
        low_stock=low_stock,
        recent_invoices=recent_invoices,
        monthly_sales=monthly_sales,
    )


@main_bp.get("/profile")
@login_required
def profile():
    return render_template("main/profile.html")


@main_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = ProfileForm(current_user, obj=current_user)
    if form.validate_on_submit():
        current_user.username = form.username.data.strip()
        current_user.email = form.email.data.strip().lower()

        previous_image = current_user.profile_image
        if isinstance(form.profile_image.data, FileStorage):
            current_user.profile_image = _save_profile_image(
                form.profile_image.data,
                current_user.id,
            )

        db.session.commit()
        if current_user.profile_image != previous_image:
            _delete_custom_profile_image(previous_image)
        flash("Your profile has been updated.", "success")
        return redirect(url_for("main.profile"))
    return render_template("main/edit_profile.html", form=form)


@main_bp.post("/profile/photo/remove")
@login_required
def profile_photo_remove():
    previous_image = current_user.profile_image
    current_user.profile_image = None
    db.session.commit()
    _delete_custom_profile_image(previous_image)
    flash("Your profile photo has been removed.", "success")
    return redirect(url_for("main.profile"))


@main_bp.route("/profile/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Your current password is incorrect.")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Your password has been updated.", "success")
            return redirect(url_for("main.profile"))
    return render_template("main/change_password.html", form=form)


@main_bp.route("/settings")
@login_required
def settings():
    company = {
        "name": current_app.config["COMPANY_NAME"],
        "gst_number": current_app.config["COMPANY_GST_NUMBER"],
        "email": current_user.email,
    }

    return render_template(
        "main/settings.html",
         company=company,
    )


@main_bp.get("/about")
@login_required
def about():
    return render_template("main/about.html")


@main_bp.route("/company", methods=["GET", "POST"])
@login_required
def company():
    form = CompanyForm()

    # Base values from config
    company = {
        "name": current_app.config.get("COMPANY_NAME"),
        "address": current_app.config.get("COMPANY_ADDRESS"),
        "gst_number": current_app.config.get("COMPANY_GST_NUMBER"),
        "email": current_app.config.get("COMPANY_EMAIL"),
        "phone": current_app.config.get("COMPANY_PHONE"),
    }

    # If query param ?edit=1 is present, render the edit form (prefilled).
    if request.method == "GET" and request.args.get("edit"):
        form.name.data = company["name"]
        form.address.data = company["address"]
        form.gst_number.data = company["gst_number"]
        form.email.data = company["email"]
        form.phone.data = company["phone"]
        return render_template("main/company.html", company=company, form=form)

    # Handle save
    if request.method == "POST":
        if form.validate_on_submit():
            # Merge submitted values and persist to instance/company.json
            overrides = {
                "COMPANY_NAME": form.name.data.strip(),
                "COMPANY_ADDRESS": form.address.data.strip() if form.address.data else "",
                "COMPANY_GST_NUMBER": form.gst_number.data.strip() if form.gst_number.data else "",
                "COMPANY_EMAIL": form.email.data.strip() if form.email.data else "",
                "COMPANY_PHONE": form.phone.data.strip() if form.phone.data else "",
            }
            instance_dir = Path(current_app.instance_path)
            instance_dir.mkdir(parents=True, exist_ok=True)
            company_file = instance_dir / "company.json"
            try:
                with company_file.open("w", encoding="utf-8") as fh:
                    json.dump(overrides, fh, indent=2, ensure_ascii=False)
                # Update runtime config for immediate effect
                for k, v in overrides.items():
                    current_app.config[k] = v
                flash("Company details updated.", "success")
                return redirect(url_for("main.company"))
            except Exception:
                current_app.logger.exception("Failed to save company overrides")
                flash("Failed to save company details.", "danger")
        # Validation failed - re-render form with errors
        return render_template("main/company.html", company=company, form=form)

    # Default: view-only
    return render_template("main/company.html", company=company)


@main_bp.route("/setup", methods=["GET", "POST"])
@login_required
def setup_shop():
    form = ShopSetupForm()

    if form.validate_on_submit():
        profile = current_user.shop_profile
        if profile is None:
            profile = ShopProfile(user_id=current_user.id)
            db.session.add(profile)

        profile.shop_name = form.shop_name.data.strip()
        profile.address = form.address.data.strip() if form.address.data else None
        profile.phone = form.phone.data.strip() if form.phone.data else None
        profile.email = form.email.data.strip().lower() if form.email.data else None
        profile.gst_number = form.gst_number.data.strip() if form.gst_number.data else None

        if isinstance(form.logo.data, FileStorage):
            previous = profile.logo
            profile.logo = _save_shop_logo(form.logo.data, current_user.id)
            if previous and previous != profile.logo:
                _delete_shop_logo(previous)

        db.session.commit()
        flash("Your shop has been set up. Create your first invoice.", "success")
        return redirect(url_for("invoices.quick_invoice"))

    if request.method == "GET" and current_user.shop_profile is not None:
        form.shop_name.data = current_user.shop_profile.shop_name
        form.address.data = current_user.shop_profile.address
        form.phone.data = current_user.shop_profile.phone
        form.email.data = current_user.shop_profile.email
        form.gst_number.data = current_user.shop_profile.gst_number

    return render_template("main/setup_shop.html", form=form)



@main_bp.get("/notifications")
@login_required
def notifications():
    # Ensure overdue invoices produce notifications (one per invoice)
    today = date.today()
    for invoice in current_user.invoices:
        try:
            if invoice.due_date and invoice.status != "Paid" and invoice.due_date < today:
                exists = Notification.query.filter_by(user_id=current_user.id, invoice_id=invoice.id).first()
                if not exists:
                    create_notification(
                        current_user.id,
                        title=f"Invoice overdue: {invoice.invoice_number}",
                        body=f"{invoice.customer.name} — due {invoice.due_date:%b %d, %Y}",
                        icon="bi-exclamation-triangle",
                        tone="warning",
                        link=url_for("invoices.invoice_detail", invoice_id=invoice.id),
                        invoice_id=invoice.id,
                    )
        except Exception:
            current_app.logger.exception("Failed to auto-create overdue notification")

    notifications_list = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return render_template("main/notifications.html", notifications=notifications_list, today=datetime.now())


@main_bp.get("/notifications/api")
@login_required
def notifications_api():
    items = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    data = [n.to_dict() for n in items]
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"ok": True, "notifications": data, "unread": unread})


@main_bp.post("/notifications/mark-read")
@login_required
def notifications_mark_read():
    nid = request.form.get("id") or request.json.get("id") if request.is_json else None
    if not nid:
        return jsonify({"ok": False}), 400
    mark_read(int(nid), current_user.id)
    return jsonify({"ok": True})


@main_bp.post("/notifications/mark-all-read")
@login_required
def notifications_mark_all_read():
    mark_all_read(current_user.id)
    return jsonify({"ok": True})


@main_bp.post("/notifications/clear")
@login_required
def notifications_clear():
    clear_all(current_user.id)
    return jsonify({"ok": True})


@main_bp.get("/search")
@login_required
def global_search():
    query = request.args.get("q", "", type=str).strip()
    results = []

    if query:
        pattern = f"%{query}%"
        customers = (
            Customer.query.filter_by(user_id=current_user.id)
            .filter(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.email.ilike(pattern),
                    Customer.phone.ilike(pattern),
                )
            )
            .order_by(Customer.name.asc())
            .limit(5)
            .all()
        )
        for customer in customers:
            results.append({
                "type": "customer",
                "label": customer.name,
                "url": url_for("customers.edit_customer", customer_id=customer.id),
            })

        invoices = (
            Invoice.query.filter_by(created_by_id=current_user.id)
            .filter(Invoice.invoice_number.ilike(pattern))
            .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
            .limit(5)
            .all()
        )
        for invoice in invoices:
            results.append({
                "type": "invoice",
                "label": invoice.invoice_number,
                "url": url_for("invoices.invoice_detail", invoice_id=invoice.id),
            })

    return jsonify({"ok": True, "results": results})


@main_bp.get("/reports")
@login_required
def reports():
    paid_invoices = [invoice for invoice in current_user.invoices if invoice.status == "Paid"]
    revenue = sum(float(invoice.grand_total or 0) for invoice in paid_invoices)
    top_products = sorted(current_user.products, key=lambda product: product.current_stock, reverse=True)[:5]
    return render_template("main/reports.html", paid_invoices=paid_invoices, revenue=revenue, top_products=top_products)


def _save_profile_image(upload, user_id):
    upload_directory = Path(current_app.static_folder) / "uploads" / "profiles"
    upload_directory.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}-{uuid4().hex}.webp"
    destination = upload_directory / filename

    with Image.open(upload.stream) as image:
        normalized = ImageOps.fit(
            image.convert("RGB"),
            PROFILE_IMAGE_SIZE,
            method=Image.Resampling.LANCZOS,
        )
        normalized.save(destination, "WEBP", quality=PROFILE_IMAGE_QUALITY, method=6)
    upload.stream.seek(0)
    return f"uploads/profiles/{filename}"


def _delete_custom_profile_image(image_path):
    if not image_path or not image_path.startswith("uploads/profiles/"):
        return

    upload_directory = (Path(current_app.static_folder) / "uploads" / "profiles").resolve()
    candidate = (Path(current_app.static_folder) / image_path).resolve()
    if candidate.is_relative_to(upload_directory) and candidate.is_file():
        candidate.unlink()


def _save_shop_logo(upload, user_id):
    upload_directory = Path(current_app.static_folder) / "uploads" / "logos"
    upload_directory.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}-{uuid4().hex}.webp"
    destination = upload_directory / filename

    with Image.open(upload.stream) as image:
        normalized = ImageOps.fit(
            image.convert("RGB"),
            LOGO_IMAGE_SIZE,
            method=Image.Resampling.LANCZOS,
        )
        normalized.save(destination, "WEBP", quality=LOGO_IMAGE_QUALITY, method=6)
    upload.stream.seek(0)
    return f"uploads/logos/{filename}"


def _delete_shop_logo(image_path):
    if not image_path or not image_path.startswith("uploads/logos/"):
        return

    upload_directory = (Path(current_app.static_folder) / "uploads" / "logos").resolve()
    candidate = (Path(current_app.static_folder) / image_path).resolve()
    if candidate.is_relative_to(upload_directory) and candidate.is_file():
        candidate.unlink()


@main_bp.app_errorhandler(RequestEntityTooLarge)
def profile_image_too_large(_error):
    flash("Profile pictures must be 2 MB or smaller.", "danger")
    return redirect(url_for("main.edit_profile"))
