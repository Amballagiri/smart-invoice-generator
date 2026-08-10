from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, FieldList, Form, FormField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, InputRequired, Length, NumberRange, Optional

from app.models.customer import Customer
from app.models.product import Product


class InvoiceItemForm(Form):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    quantity = DecimalField(
        "Quantity", places=3, validators=[DataRequired(), NumberRange(min=Decimal("0.001"))]
    )
    unit_price = DecimalField("Unit price", places=2, validators=[Optional(), NumberRange(min=Decimal("0.001"))])
    tax_percentage = DecimalField("Tax %", places=2, validators=[Optional(), NumberRange(min=Decimal("0"), max=Decimal("100"))])
    discount_percentage = DecimalField("Discount %", places=2, validators=[Optional(), NumberRange(min=Decimal("0"), max=Decimal("100"))])
    description = StringField("Description", validators=[Optional()])


class InvoiceForm(FlaskForm):
    customer_id = SelectField("Customer", coerce=int, validators=[DataRequired()])
    invoice_date = DateField("Invoice date", validators=[DataRequired()])
    due_date = DateField("Due date", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("Draft", "Draft"), ("Unpaid", "Pending"), ("Paid", "Paid"), ("Cancelled", "Cancelled")],
        validators=[DataRequired()],
    )
    discount = DecimalField(
        "Discount", places=2, default=Decimal("0.00"), validators=[Optional(), NumberRange(min=Decimal("0"))]
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    terms = TextAreaField("Terms & conditions", validators=[Optional()])
    currency = SelectField("Currency", choices=[("INR", "INR (₹)"), ("USD", "USD ($)"), ("EUR", "EUR (€)")], default="INR")
    payment_method = SelectField("Payment method", choices=[("", "Select payment method"), ("Bank transfer", "Bank transfer"), ("UPI", "UPI"), ("Cash", "Cash"), ("Card", "Card")], validators=[Optional()])
    template_name = SelectField("Invoice template", choices=[("Modern Blue", "Modern Blue"), ("Corporate", "Corporate"), ("Minimal", "Minimal"), ("Classic", "Classic"), ("Premium", "Premium")], default="Modern Blue")
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


class QuickInvoiceItemForm(Form):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    quantity = DecimalField(
        "Quantity", places=3, validators=[DataRequired(), NumberRange(min=Decimal("0.001"))]
    )
    unit_price = DecimalField("Unit price", places=2, validators=[Optional(), NumberRange(min=Decimal("0.001"))])
    tax_percentage = DecimalField("Tax %", places=2, validators=[Optional(), NumberRange(min=Decimal("0"), max=Decimal("100"))])


class QuickInvoiceForm(FlaskForm):
    customer_name = StringField("Customer name", validators=[DataRequired(), Length(max=120)])
    customer_phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    customer_email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    invoice_date = DateField("Invoice date", validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[("Draft", "Draft"), ("Unpaid", "Pending"), ("Paid", "Paid")],
        validators=[DataRequired()],
    )
    discount = DecimalField(
        "Discount", places=2, default=Decimal("0.00"), validators=[Optional(), NumberRange(min=Decimal("0"))]
    )
    items = FieldList(FormField(QuickInvoiceItemForm), min_entries=1, validators=[DataRequired()])
    submit = SubmitField("Generate invoice")

    def __init__(self, user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        products = Product.query.filter_by(user_id=user_id, is_active=True).order_by(Product.name).all()
        self.product_choices = [(0, "Select a product")] + [
            (product.id, f"{product.name} ({product.sku})") for product in products
        ]
        for item in self.items:
            item.form.product_id.choices = self.product_choices

    def add_item_entry(self, data=None):
        entry = self.items.append_entry(data)
        entry.form.product_id.choices = self.product_choices
        return entry
