# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SubmitField
from wtforms.validators import DataRequired, Length, Email

class CheckoutForm(FlaskForm):
    fullname = StringField("Họ và tên", validators=[DataRequired(), Length(min=2, max=200)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=200)])
    address = StringField("Địa chỉ", validators=[DataRequired(), Length(min=5, max=400)])
    submit = SubmitField("Thanh toán với PayPal")
