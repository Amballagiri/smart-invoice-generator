from datetime import date

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms.invoice_forms import InvoiceForm
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.product import Product
from app.services.pdf_service import generate_invoice_pdf

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")


def _owned_invoice_or_404(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, created_by_id=current_user.id).first()
    if invoice is None:
        abort(404)
    return invoice


@invoices_bp.get("/")
@login_required
def list_invoices():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "", type=str).strip()
    status = request.args.get("status", "", type=str).strip()
    query = Invoice.query.filter_by(created_by_id=current_user.id)
    if search:
        query = query.filter(Invoice.invoice_number.ilike(f"%{search}%"))
    if status:
        query = query.filter_by(status=status)
    invoices = query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("invoices/list.html", invoices=invoices, search=search, selected_status=status)


@invoices_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_invoice():
    form = InvoiceForm(user_id=current_user.id, invoice_date=date.today(), status="Draft")
    if form.validate_on_submit():
        invoice = Invoice(created_by_id=current_user.id)
        _populate_invoice(invoice, form)
        _replace_items(invoice, form)
        invoice.recalculate_totals()
        db.session.add(invoice)
        db.session.commit()
        flash("Invoice created successfully.", "success")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))
    return render_template("invoices/form.html", form=form, heading="Create invoice", products=_product_price_data())


@invoices_bp.get("/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    return render_template("invoices/detail.html", invoice=_owned_invoice_or_404(invoice_id))


@invoices_bp.get("/<int:invoice_id>/pdf")
@login_required
def download_invoice_pdf(invoice_id):
    invoice = _owned_invoice_or_404(invoice_id)
    company = {
        "name": current_app.config["COMPANY_NAME"],
        "address": current_app.config["COMPANY_ADDRESS"],
        "gst_number": current_app.config["COMPANY_GST_NUMBER"],
    }
    return send_file(
        generate_invoice_pdf(invoice, company),
        as_attachment=True,
        download_name=f"{invoice.invoice_number}.pdf",
        mimetype="application/pdf",
    )


@invoices_bp.route("/<int:invoice_id>/edit", methods=["GET", "POST"])
@login_required
def edit_invoice(invoice_id):
    invoice = _owned_invoice_or_404(invoice_id)
    if invoice.status != "Draft":
        flash("Only draft invoices can be edited.", "warning")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))

    form = InvoiceForm(user_id=current_user.id)
    if request.method == "GET":
        _load_invoice_into_form(form, invoice)
    if form.validate_on_submit():
        _populate_invoice(invoice, form)
        _replace_items(invoice, form)
        invoice.recalculate_totals()
        db.session.commit()
        flash("Draft invoice updated successfully.", "success")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))
    return render_template("invoices/form.html", form=form, heading="Edit draft invoice", invoice=invoice, products=_product_price_data())


@invoices_bp.post("/<int:invoice_id>/delete")
@login_required
def delete_invoice(invoice_id):
    invoice = _owned_invoice_or_404(invoice_id)
    if invoice.status != "Draft":
        flash("Only draft invoices can be deleted.", "warning")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))
    db.session.delete(invoice)
    db.session.commit()
    flash("Draft invoice deleted successfully.", "info")
    return redirect(url_for("invoices.list_invoices"))


def _populate_invoice(invoice, form):
    invoice.customer_id = form.customer_id.data
    invoice.invoice_date = form.invoice_date.data
    invoice.due_date = form.due_date.data
    invoice.status = form.status.data
    invoice.discount = form.discount.data
    invoice.notes = form.notes.data.strip() if form.notes.data else None


def _replace_items(invoice, form):
    invoice.items.clear()
    for entry in form.items.entries:
        product = db.session.get(Product, entry.form.product_id.data)
        invoice.items.append(
            InvoiceItem(
                product=product,
                quantity=entry.form.quantity.data,
                unit_price=product.selling_price,
                tax_percentage=product.tax_percentage,
            )
        )


def _load_invoice_into_form(form, invoice):
    form.customer_id.data = invoice.customer_id
    form.invoice_date.data = invoice.invoice_date
    form.due_date.data = invoice.due_date
    form.status.data = invoice.status
    form.discount.data = invoice.discount
    form.notes.data = invoice.notes
    while form.items.entries:
        form.items.pop_entry()
    for item in invoice.items:
        form.add_item_entry({"product_id": item.product_id, "quantity": item.quantity})


def _product_price_data():
    products = Product.query.filter_by(user_id=current_user.id, is_active=True).all()
    return {
        product.id: {"price": float(product.selling_price), "tax": float(product.tax_percentage)}
        for product in products
    }
