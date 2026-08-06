from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms.customer_forms import CustomerForm
from app.models.customer import Customer
from app.services.notification_service import create_notification

customers_bp = Blueprint("customers", __name__, url_prefix="/customers")


def _owned_customer_or_404(customer_id):
    customer = Customer.query.filter_by(
        id=customer_id,
        user_id=current_user.id
    ).first()

    if customer is None:
        abort(404)

    return customer


@customers_bp.get("/")
@login_required
def list_customers():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "", type=str).strip()

    query = Customer.query.filter_by(user_id=current_user.id)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Customer.name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.phone.ilike(pattern),
            )
        )

    customers = (
        query.order_by(Customer.name.asc())
        .paginate(
            page=page,
            per_page=10,
            error_out=False,
        )
    )

    return render_template(
        "customers/list.html",
        customers=customers,
        search=search,
    )


@customers_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_customer():

    form = CustomerForm()

    if form.validate_on_submit():

        customer = Customer(user_id=current_user.id)

        _populate_customer(customer, form)

        db.session.add(customer)
        db.session.commit()

        flash(
            "Customer added successfully.",
            "success",
        )
        try:
            create_notification(
                current_user.id,
                title=f"Customer added: {customer.name}",
                body=customer.email or "",
                icon="bi-people",
                tone="primary",
                link=url_for("customers.edit_customer", customer_id=customer.id),
            )
        except Exception:
            current_app.logger.exception("Failed to create notification for customer added")

        return redirect(
            url_for("customers.list_customers")
        )

    return render_template(
        "customers/form.html",
        form=form,
        heading="Add customer",
    )


@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
def edit_customer(customer_id):

    customer = _owned_customer_or_404(customer_id)

    form = CustomerForm(obj=customer)

    if form.validate_on_submit():

        _populate_customer(customer, form)

        db.session.commit()

        flash(
            "Customer updated successfully.",
            "success",
        )

        return redirect(
            url_for("customers.list_customers")
        )

    return render_template(
        "customers/form.html",
        form=form,
        heading="Edit customer",
        customer=customer,
    )


@customers_bp.post("/<int:customer_id>/delete")
@login_required
def delete_customer(customer_id):

    customer = _owned_customer_or_404(customer_id)

    db.session.delete(customer)
    db.session.commit()

    flash(
        "Customer deleted successfully.",
        "info",
    )

    return redirect(
        url_for("customers.list_customers")
    )


def _populate_customer(customer, form):

    for field in (
        "name",
        "email",
        "phone",
        "address",
        "city",
        "state",
        "postal_code",
        "country",
        "notes",
    ):

        value = getattr(form, field).data

        setattr(
            customer,
            field,
            value.strip() if isinstance(value, str) else value,
        )