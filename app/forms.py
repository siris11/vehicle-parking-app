from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, FloatField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange, Length, Regexp
from flask_login import current_user
from .models import User, ParkingLot

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Username is not available. Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email is already registered. Please use a different email address.')

class ParkingLotForm(FlaskForm):
    name = StringField('Lot Name (e.g., City Center Parking)', validators=[DataRequired(), Length(max=128)],
                       render_kw={"placeholder": "e.g., Centre ville Parking"})
    address = StringField('Address', validators=[DataRequired(), Length(max=255)],
                          render_kw={"placeholder": "e.g., Near capetown"})

    pin_code = StringField('Pin Code', validators=[DataRequired(), Length(min=6, max=10), Regexp(r'^\d{6,10}$', message='Pin Code must be 6-10 digits.')],
                           render_kw={"placeholder": "e.g., 123456"})
    price_per_hour = FloatField('Price Per Hour (₹)', validators=[DataRequired()])
    maximum_capacity = IntegerField('Maximum Capacity (Number of Spots)', validators=[DataRequired()])
    submit = SubmitField('Save Parking Lot')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_name = kwargs.get('obj').name if kwargs.get('obj') else None

    def validate_name(self, name):
        if hasattr(self, '_original_name') and self._original_name == name.data:
            return 
        lot = ParkingLot.query.filter_by(name=name.data).first()
        if lot:
            raise ValidationError('A parking lot with this name already exists.')

class BookSpotForm(FlaskForm):
    vehicle_number = StringField('Vehicle Number', validators=[DataRequired(), Length(min=3, max=20)])
    submit = SubmitField('Confirm Booking')

# For the user to confirm they've arrived and parked
class CheckInForm(FlaskForm):
    submit = SubmitField('Check In Now')

# ParkOutForm
class ParkOutForm(FlaskForm):
    submit = SubmitField('Park Out & End Session') 

class EditProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)]) 
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Update Profile')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('This username is already taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('This email address is already registered. Please choose a different one.')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField(
        'Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

    def validate_current_password(self, current_password):
        if not current_user.check_password(current_password.data):
            raise ValidationError('Incorrect current password.')