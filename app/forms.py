from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, FloatField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange, Length
from .models import User, ParkingLot

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ParkingLotForm(FlaskForm):
    name = StringField('Parking Lot Name', validators=[DataRequired(), Length(max=128)])
    address = TextAreaField('Address', validators=[Length(max=255)])
    pin_code = StringField('Pin Code', validators=[Length(max=10)])
    price_per_hour = FloatField('Price Per Hour (₹)', validators=[DataRequired(), NumberRange(min=0)])
    maximum_capacity = IntegerField('Maximum Capacity (Number of Spots)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Save Parking Lot')

    def validate_name(self, name):
        # Check if the name is being changed during an edit
        if hasattr(self, '_original_name') and self._original_name == name.data:
            return # Name hasn't changed, so no validation needed against existing names
        lot = ParkingLot.query.filter_by(name=name.data).first()
        if lot:
            raise ValidationError('A parking lot with this name already exists.')

class BookSpotForm(FlaskForm):
    vehicle_number = StringField('Vehicle Number', validators=[DataRequired(), Length(min=3, max=20)])
    # spot_id will be passed via URL, user_id from current_user
    submit = SubmitField('Confirm Booking')

class ReleaseSpotForm(FlaskForm):
    reservation_id = IntegerField('Reservation ID', validators=[DataRequired()]) # Hidden field, perhaps
    submit = SubmitField('Release Parking Spot')

class EditProfileForm(FlaskForm):
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

# More forms can be added here as needed, e.g., for editing user profiles, etc. 