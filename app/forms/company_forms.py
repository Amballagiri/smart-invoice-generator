from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


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

