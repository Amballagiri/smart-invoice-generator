from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DecimalField, SelectField, StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, Regexp



class CompanyForm(FlaskForm):
    name = StringField("Company name", validators=[DataRequired(), Length(max=200)])
    address = TextAreaField("Business address", validators=[Optional(), Length(max=1000)])
    gst_number = StringField("GST / Tax number", validators=[Optional(), Length(max=64)])
    email = StringField("Contact email", validators=[Optional(), Email(), Length(max=120)])
    phone = StringField("Contact phone", validators=[Optional(), Length(max=60)])
    submit = SubmitField("Save company")


class ShopSetupForm(FlaskForm):
    shop_name = StringField("Shop name", validators=[DataRequired(), Length(max=200)])
    address = TextAreaField("Shop address", validators=[Optional(), Length(max=1000)])
    phone = StringField("Shop phone", validators=[Optional(), Length(max=60)])
    email = StringField("Shop email", validators=[Optional(), Email(), Length(max=120)])
    gst_number = StringField("GSTIN (optional)", validators=[Optional(), Length(max=64)])
    logo = FileField(
        "Shop logo (optional)",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "Choose a PNG, JPG, or WebP image.")],
    )
    submit = SubmitField("Save & continue")


class ShopLogoForm(FlaskForm):
    logo = FileField(
        "Shop logo",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "Choose a PNG, JPG, or WebP image.")],
    )
    submit = SubmitField("Upload logo")


class InvoiceSettingsForm(FlaskForm):
    """Persistent invoice settings stored in ShopProfile."""

    invoice_prefix = StringField(
        "Invoice prefix",
        validators=[
            DataRequired(message="Invoice prefix is required."),
            Length(max=20, message="Prefix must be 20 characters or fewer."),
            Regexp(
                r"^[A-Za-z0-9\-]+$",
                message="Prefix may only contain letters, digits, and hyphens.",
            ),
        ],
    )
    default_gst = DecimalField(
        "Default GST (%)",
        places=2,
        validators=[
            DataRequired(message="Default GST is required."),
            NumberRange(min=0, max=100, message="GST must be between 0 and 100."),
        ],
    )
    currency = SelectField(
        "Currency",
        choices=[
            ("INR", "INR (₹) – Indian Rupee"),
            ("USD", "USD ($) – US Dollar"),
            ("EUR", "EUR (€) – Euro"),
        ],
        validators=[DataRequired()],
    )
    payment_terms = SelectField(
        "Payment terms",
        choices=[
            ("Due on Receipt", "Due on Receipt"),
            ("Net 7", "Net 7"),
            ("Net 15", "Net 15"),
            ("Net 30", "Net 30"),
            ("Net 60", "Net 60"),
        ],
        validators=[DataRequired()],
    )
    footer_note = TextAreaField(
        "Footer note",
        validators=[Optional(), Length(max=500, message="Footer note must be 500 characters or fewer.")],
    )
    submit = SubmitField("Save changes")


