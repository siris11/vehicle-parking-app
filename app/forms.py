from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, FloatField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange, Length
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
    name = StringField('Parking Lot Name', validators=[DataRequired(), Length(max=128)])
    address = TextAreaField('Address', validators=[Length(max=255)])
    pin_code = StringField('Pin Code', validators=[Length(max=10)])
    price_per_hour = FloatField('Price Per Hour (₹)', validators=[DataRequired(), NumberRange(min=0)])
    maximum_capacity = IntegerField('Maximum Capacity (Number of Spots)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Save Parking Lot')

    def validate_name(self, name):
        # Checking if the name is being changed during an edit
        # The logic for _original_name should be set in the route when editing
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

# NEW FORM: For changing user's password
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField(
        'Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

    def validate_current_password(self, current_password):
        # This validation checks if the current password matches the user's stored password.
        # It needs the User model's check_password method.
        # current_user must be imported from flask_login
        if not current_user.check_password(current_password.data):
            raise ValidationError('Incorrect current password.')