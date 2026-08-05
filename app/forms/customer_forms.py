from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import Email, Length, Optional, ValidationError


class CustomerForm(FlaskForm):
    name = StringField("Customer name", validators=[Length(min=2, max=120)])
    email = StringField("Email address", validators=[Optional(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    state = StringField("State / Province", validators=[Optional(), Length(max=80)])
    postal_code = StringField("Postal code", validators=[Optional(), Length(max=20)])
    country = StringField("Country", validators=[Optional(), Length(max=80)])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Save customer")

    def validate_name(self, name):
        if not name.data or not name.data.strip():
            raise ValidationError("Customer name is required.")
