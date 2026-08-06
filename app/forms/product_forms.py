from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from app.models.product import Product


class ProductForm(FlaskForm):
    name = StringField("Product name", validators=[DataRequired(), Length(max=150)])
    sku = StringField("SKU", validators=[DataRequired(), Length(max=80)])
    category = StringField("Category", validators=[Optional(), Length(max=80)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    cost_price = DecimalField("Cost price", validators=[DataRequired(), NumberRange(min=Decimal("0"))], places=2)
    selling_price = DecimalField("Selling price", validators=[DataRequired(), NumberRange(min=Decimal("0"))], places=2)
    tax_percentage = DecimalField("Tax percentage (GST)", validators=[DataRequired(), NumberRange(min=Decimal("0"), max=Decimal("100"))], places=2)
    current_stock = IntegerField("Current stock", validators=[DataRequired(), NumberRange(min=0)])
    unit = SelectField("Unit", choices=[("Piece", "Piece"), ("Kg", "Kg"), ("Box", "Box"), ("Litre", "Litre"), ("Pack", "Pack"), ("Other", "Other")], validators=[DataRequired()])
    low_stock_alert_level = IntegerField("Low stock alert level", validators=[DataRequired(), NumberRange(min=0)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save product")

    def __init__(self, user_id, product=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = user_id
        self.product = product

    def validate_sku(self, sku):
        query = Product.query.filter_by(user_id=self.user_id, sku=sku.data.strip())
        if self.product is not None:
            query = query.filter(Product.id != self.product.id)
        if query.first():
            raise ValidationError("You already have a product with this SKU.")


class RestockForm(FlaskForm):
    quantity = DecimalField("Quantity to add", places=3, validators=[DataRequired(), NumberRange(min=Decimal("0.001"))])
    reason = StringField("Reason", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Restock product")
