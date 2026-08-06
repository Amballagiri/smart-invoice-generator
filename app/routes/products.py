from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms.product_forms import ProductForm
from app.forms.product_forms import RestockForm
from app.models.inventory_history import InventoryHistory
from app.models.product import Product
from app.services.notification_service import create_notification

products_bp = Blueprint("products", __name__, url_prefix="/products")


def _owned_product_or_404(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
    if product is None:
        abort(404)
    return product


@products_bp.get("/")
@login_required
def list_products():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "", type=str).strip()
    category = request.args.get("category", "", type=str).strip()
    query = Product.query.filter_by(user_id=current_user.id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern), Product.category.ilike(pattern)))
    if category:
        query = query.filter(Product.category == category)
    products = query.order_by(Product.name.asc()).paginate(page=page, per_page=10, error_out=False)
    categories = [value for (value,) in db.session.query(Product.category).filter_by(user_id=current_user.id).filter(Product.category.is_not(None), Product.category != "").distinct().order_by(Product.category).all()]
    return render_template("products/list.html", products=products, search=search, category=category, categories=categories)


@products_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_product():
    form = ProductForm(user_id=current_user.id)
    if form.validate_on_submit():
        product = Product(user_id=current_user.id)
        _populate_product(product, form)
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully.", "success")
        try:
            create_notification(
                current_user.id,
                title=f"Product added: {product.name}",
                body=product.category or "",
                icon="bi-box-seam",
                tone="primary",
                link=url_for("products.list_products"),
            )
        except Exception:
            current_app.logger.exception("Failed to create notification for product added")
        return redirect(url_for("products.list_products"))
    return render_template("products/form.html", form=form, heading="Add product")


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = _owned_product_or_404(product_id)
    form = ProductForm(user_id=current_user.id, product=product, obj=product)
    if form.validate_on_submit():
        _populate_product(product, form)
        db.session.commit()
        flash("Product updated successfully.", "success")
        return redirect(url_for("products.list_products"))
    return render_template("products/form.html", form=form, heading="Edit product", product=product)


@products_bp.post("/<int:product_id>/delete")
@login_required
def delete_product(product_id):
    product = _owned_product_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully.", "info")
    return redirect(url_for("products.list_products"))


@products_bp.route("/<int:product_id>/restock", methods=["GET", "POST"])
@login_required
def restock_product(product_id):
    product = _owned_product_or_404(product_id)
    form = RestockForm()
    if form.validate_on_submit():
        product.current_stock += int(form.quantity.data) if form.quantity.data == int(form.quantity.data) else float(form.quantity.data)
        db.session.add(InventoryHistory(product=product, user_id=current_user.id, quantity_change=form.quantity.data, stock_after=product.current_stock, reason=form.reason.data.strip()))
        db.session.commit()
        flash("Product restocked successfully.", "success")
        return redirect(url_for("products.list_products"))
    return render_template("products/restock.html", form=form, product=product)


def _populate_product(product, form):
    for field in ("name", "sku", "category", "description", "cost_price", "selling_price", "tax_percentage", "current_stock", "unit", "low_stock_alert_level", "is_active"):
        value = getattr(form, field).data
        setattr(product, field, value.strip() if isinstance(value, str) else value)
