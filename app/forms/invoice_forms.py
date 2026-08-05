from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, FieldList, Form, FormField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, NumberRange, Optional

from app.models.customer import Customer
from app.models.product import Product


class InvoiceItemForm(Form):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    quantity = DecimalField(
        "Quantity", places=3, validators=[DataRequired(), NumberRange(min=Decimal("0.001"))]
    )


class InvoiceForm(FlaskForm):
    customer_id = SelectField("Customer", coerce=int, validators=[DataRequired()])
    invoice_date = DateField("Invoice date", validators=[DataRequired()])
    due_date = DateField("Due date", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("Draft", "Draft"), ("Unpaid", "Unpaid"), ("Paid", "Paid"), ("Cancelled", "Cancelled")],
        validators=[DataRequired()],
    )
    discount = DecimalField(
        "Discount", places=2, default=Decimal("0.00"), validators=[InputRequired(), NumberRange(min=Decimal("0"))]
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    items = FieldList(FormField(InvoiceItemForm), min_entries=1, validators=[DataRequired()])
    submit = SubmitField("Save invoice")

    def __init__(self, user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        customers = Customer.query.filter_by(user_id=user_id).order_by(Customer.name).all()
        products = Product.query.filter_by(user_id=user_id, is_active=True).order_by(Product.name).all()
        self.customer_id.choices = [(0, "Select a customer")] + [(customer.id, customer.name) for customer in customers]
        self.product_choices = [(0, "Select a product")] + [
            (product.id, f"{product.name} ({product.sku})") for product in products
        ]
        for item in self.items:
            item.form.product_id.choices = self.product_choices

    def add_item_entry(self, data=None):
        entry = self.items.append_entry(data)
        entry.form.product_id.choices = self.product_choices
        return entry
