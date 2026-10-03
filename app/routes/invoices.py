from datetime import date
from decimal import Decimal

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.invoice_forms import InvoiceForm, QuickInvoiceForm
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.customer import Customer
from app.models.product import Product
from app.models.invoice import generate_invoice_number
from app.services.inventory_service import reduce_stock
from app.services.invoice_service import get_company_config
from app.services.payment_service import PaymentService
from app.services.pdf_service import generate_invoice_pdf
from app.services.email_service import send_invoice_email
from urllib.parse import quote

invoices_bp = Blueprint(
    "invoices",
    __name__,
    url_prefix="/invoices",
)


def _owned_invoice_or_404(invoice_id):
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        created_by_id=current_user.id,
    ).first()

    if invoice is None:
        abort(404)

    return invoice


def _invoice_defaults():
    """Return the signed-in user's saved invoice preferences."""
    profile = current_user.shop_profile
    if profile is None:
        return {
            "invoice_prefix": "INV",
            "default_gst": Decimal("18.00"),
            "currency": "INR",
            "payment_terms": "Due on Receipt",
            "footer_note": "Thank you for your business.",
        }

    return {
        "invoice_prefix": profile.invoice_prefix,
        "default_gst": profile.default_gst,
        "currency": profile.currency,
        "payment_terms": profile.payment_terms,
        "footer_note": profile.footer_note or "",
    }


@invoices_bp.get("/")
@login_required
def list_invoices():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "", type=str).strip()
    status = request.args.get("status", "", type=str).strip()

    query = Invoice.query.filter_by(
        created_by_id=current_user.id
    )

    if search:
        query = query.filter(
            Invoice.invoice_number.ilike(f"%{search}%")
        )

    if status:
        query = query.filter_by(status=status)

    invoices = (
        query.order_by(
            Invoice.invoice_date.desc(),
            Invoice.id.desc(),
        )
        .paginate(
            page=page,
            per_page=10,
            error_out=False,
        )
    )

    return render_template(
        "invoices/list.html",
        invoices=invoices,
        search=search,
        selected_status=status,
    )


@invoices_bp.route("/create", methods=["GET", "POST"])
@invoices_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_invoice():
    defaults = _invoice_defaults()
    form = InvoiceForm(
         user_id=current_user.id,
         invoice_date=date.today(),
         status="Draft",
    )
    if request.method == "GET":
        form.currency.data = defaults["currency"]
        form.terms.data = defaults["payment_terms"]
        form.notes.data = defaults["footer_note"]
        for item in form.items:
            item.form.tax_percentage.data = defaults["default_gst"]

    if form.validate_on_submit():

        invoice = Invoice(
            created_by_id=current_user.id
        )
        invoice.invoice_number = generate_invoice_number(defaults["invoice_prefix"])

        _populate_invoice(invoice, form)
        _replace_items(invoice, form)

        invoice.recalculate_totals()

        db.session.add(invoice)

        try:

            if invoice.status != "Draft":
                reduce_stock(invoice)

            db.session.commit()

            flash(
                "Invoice created successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "invoices.invoice_detail",
                    invoice_id=invoice.id,
                )
            )

        except ValueError as e:

            db.session.rollback()

            flash(str(e), "danger")

    return render_template(
        "invoices/builder.html",
        form=form,
        heading="Create invoice",
        products=_product_price_data(),
        customers=_customer_preview_data(),
    )


@invoices_bp.route("/quick", methods=["GET", "POST"])
@login_required
def quick_invoice():
    defaults = _invoice_defaults()
    form = QuickInvoiceForm(user_id=current_user.id, invoice_date=date.today(), status="Unpaid")
    if request.method == "GET":
        for item in form.items:
            item.form.tax_percentage.data = defaults["default_gst"]

    if form.validate_on_submit():
        customer = _find_or_create_customer(
            form.customer_name.data,
            form.customer_phone.data,
            form.customer_email.data,
        )

        invoice = Invoice(created_by_id=current_user.id)
        invoice.invoice_number = generate_invoice_number(defaults["invoice_prefix"])
        invoice.invoice_date = form.invoice_date.data
        invoice.status = form.status.data
        invoice.discount = form.discount.data or Decimal("0.00")
        invoice.currency = defaults["currency"]
        invoice.terms = defaults["payment_terms"]
        invoice.notes = defaults["footer_note"]

        _replace_quick_items(invoice, form)

        invoice.recalculate_totals()

        db.session.add(invoice)
        invoice.customer = customer

        try:
            if invoice.status != "Draft":
                reduce_stock(invoice)
            db.session.commit()
            flash("Invoice generated successfully.", "success")
            return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")

    return render_template(
        "invoices/quick_invoice.html",
        form=form,
        products=_product_price_data(),
        customers=_customer_preview_data(),
    )


def _find_or_create_customer(name, phone, email):
    name = (name or "").strip()
    phone = (phone or "").strip()
    email = (email or "").strip().lower()

    customer = None
    if phone:
        customer = Customer.query.filter_by(user_id=current_user.id, phone=phone).first()
    if customer is None and name:
        customer = Customer.query.filter_by(user_id=current_user.id, name=name).first()

    if customer is not None:
        if phone and not customer.phone:
            customer.phone = phone
        if email and not customer.email:
            customer.email = email
        return customer

    customer = Customer(user_id=current_user.id, name=name, phone=phone or None, email=email or None)
    db.session.add(customer)
    return customer


def _replace_quick_items(invoice, form):
    for entry in form.items.entries:
        product = db.session.get(Product, entry.form.product_id.data)
        invoice.items.append(
            InvoiceItem(
                product=product,
                quantity=entry.form.quantity.data,
                unit_price=entry.form.unit_price.data or product.selling_price,
                tax_percentage=entry.form.tax_percentage.data
                if entry.form.tax_percentage.data is not None
                else product.tax_percentage,
            )
        )


@invoices_bp.get("/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    invoice = _owned_invoice_or_404(invoice_id)

    return render_template(
        "invoices/detail.html",
        invoice=invoice,
        payment_token=PaymentService.create_payment_token(invoice),
    )


@invoices_bp.get("/<int:invoice_id>/pdf")
@login_required
def download_invoice_pdf(invoice_id):
    invoice = _owned_invoice_or_404(invoice_id)

    company = get_company_config(current_user)

    return send_file(
        generate_invoice_pdf(invoice, company),
        as_attachment=True,
        download_name=f"{invoice.invoice_number}.pdf",
        mimetype="application/pdf",
    )

@invoices_bp.get("/<int:invoice_id>/send-email")
@login_required
def send_invoice(invoice_id):

    invoice = _owned_invoice_or_404(invoice_id)

    company = get_company_config(current_user)

    try:
        send_invoice_email(invoice, company)

        flash(
            "Invoice emailed successfully.",
            "success",
        )

    except Exception as e:

        flash(
            f"Email failed: {e}",
            "danger",
        )


    return redirect(
        url_for(
            "invoices.invoice_detail",
            invoice_id=invoice.id,
        )
    )
@invoices_bp.get("/<int:invoice_id>/whatsapp")
@login_required
def send_whatsapp(invoice_id):

    invoice = _owned_invoice_or_404(invoice_id)

    phone = invoice.customer.phone

    if not phone:
        flash("Customer phone number not found.", "warning")
        return redirect(
            url_for(
                "invoices.invoice_detail",
                invoice_id=invoice.id,
            )
        )

    phone = (
        phone.replace(" ", "")
             .replace("+", "")
             .replace("-", "")
    )

    message = f"""
Hello {invoice.customer.name},

Thank you for your purchase.

Invoice Number: {invoice.invoice_number}

Total Amount: ₹{invoice.grand_total}

Regards,
Smart Invoice Generator
"""

    whatsapp_url = f"https://wa.me/{phone}?text={quote(message)}"

    return redirect(whatsapp_url)
@invoices_bp.route("/<int:invoice_id>/edit", methods=["GET", "POST"])
@login_required
def edit_invoice(invoice_id):

    invoice = _owned_invoice_or_404(invoice_id)

    if invoice.status != "Draft":
        flash(
            "Only draft invoices can be edited.",
            "warning",
        )
        return redirect(
            url_for(
                "invoices.invoice_detail",
                invoice_id=invoice.id,
            )
        )

    form = InvoiceForm(user_id=current_user.id)

    if request.method == "GET":
        _load_invoice_into_form(form, invoice)

    if form.validate_on_submit():

        _populate_invoice(invoice, form)
        _replace_items(invoice, form)

        invoice.recalculate_totals()

        db.session.commit()

        flash(
            "Draft invoice updated successfully.",
            "success",
        )

        return redirect(
            url_for(
                "invoices.invoice_detail",
                invoice_id=invoice.id,
            )
        )

    return render_template(
        "invoices/form.html",
        form=form,
        heading="Edit draft invoice",
        invoice=invoice,
        products=_product_price_data(),
    )
@invoices_bp.post("/<int:invoice_id>/delete")
@login_required
def delete_invoice(invoice_id):

    invoice = _owned_invoice_or_404(invoice_id)

    if invoice.status != "Draft":
        flash(
            "Only draft invoices can be deleted.",
            "warning",
        )

        return redirect(
            url_for(
                "invoices.invoice_detail",
                invoice_id=invoice.id,
            )
        )

    db.session.delete(invoice)
    db.session.commit()

    flash(
        "Draft invoice deleted successfully.",
        "info",
    )

    return redirect(
        url_for("invoices.list_invoices")
    )


def _populate_invoice(invoice, form):
    invoice.customer_id = form.customer_id.data
    invoice.invoice_date = form.invoice_date.data
    invoice.due_date = form.due_date.data
    invoice.status = form.status.data
    invoice.discount = form.discount.data or 0
    invoice.currency = form.currency.data
    invoice.payment_method = form.payment_method.data or None
    invoice.template_name = form.template_name.data
    invoice.terms = form.terms.data.strip() if form.terms.data else None

    if form.notes.data:
        invoice.notes = form.notes.data.strip()
    else:
        invoice.notes = None


def _replace_items(invoice, form):

    invoice.items.clear()

    for entry in form.items.entries:

        product = db.session.get(
            Product,
            entry.form.product_id.data,
        )

        invoice.items.append(
            InvoiceItem(
                product=product,
                quantity=entry.form.quantity.data,
                unit_price=entry.form.unit_price.data or product.selling_price,
                tax_percentage=entry.form.tax_percentage.data if entry.form.tax_percentage.data is not None else product.tax_percentage,
                discount_percentage=entry.form.discount_percentage.data or 0,
                description=entry.form.description.data.strip() if entry.form.description.data else None,
            )
        )


def _load_invoice_into_form(form, invoice):

    form.customer_id.data = invoice.customer_id
    form.invoice_date.data = invoice.invoice_date
    form.due_date.data = invoice.due_date
    form.status.data = invoice.status
    form.discount.data = invoice.discount
    form.notes.data = invoice.notes
    form.terms.data = invoice.terms
    form.currency.data = invoice.currency
    form.payment_method.data = invoice.payment_method
    form.template_name.data = invoice.template_name

    while form.items.entries:
        form.items.pop_entry()

    for item in invoice.items:
        form.add_item_entry(
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_percentage": item.tax_percentage,
                "discount_percentage": item.discount_percentage,
                "description": item.description,
            }
        )


def _product_price_data():

    products = Product.query.filter_by(
        user_id=current_user.id,
        is_active=True,
    ).all()

    return {
        product.id: {
            "price": float(product.selling_price),
            "tax": float(product.tax_percentage),
            "name": product.name,
            "description": product.description or "",
        }
        for product in products
    }


def _customer_preview_data():
    customers = Customer.query.filter_by(
        user_id=current_user.id,
    ).order_by(Customer.name).all()

    return {
        customer.id: {
            "email": customer.email or "",
            "phone": customer.phone or "",
            "address": customer.address or "",
        }
        for customer in customers
    }
