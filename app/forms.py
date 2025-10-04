from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField,
    TextAreaField, FieldList, FormField, DateField, TimeField, SelectField
)
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional

from app.models import User

from app.models import User

# --- Keep your existing forms ---

class RegistrationForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

# --- Add the new BookingForm class at the bottom ---

class BookingForm(FlaskForm):
    appointment_date = DateField('Appointment Date', validators=[DataRequired()], format='%Y-%m-%d')
    appointment_time = TimeField('Appointment Time', validators=[DataRequired()], format='%H:%M')
    submit = SubmitField('Confirm Appointment')

# --- Add the new UpdateProfileForm below ---

class UpdateProfileForm(FlaskForm):
    full_name = StringField('Full Name', 
                            validators=[DataRequired(), Length(min=2, max=100)])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d')
    gender = SelectField('Gender', choices=[('', 'Select...'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    contact_number = StringField('Contact Number', validators=[Length(max=20)])
    blood_group = StringField('Blood Group', validators=[Length(max=5)])
    allergies = StringField('Allergies')
    submit = SubmitField('Update Profile')

class TreatmentForm(FlaskForm):
    diagnosis = TextAreaField('Diagnosis', 
                              validators=[DataRequired()], 
                              render_kw={"rows": 5, "placeholder": "Enter patient diagnosis details..."})
    prescription = TextAreaField('Prescription', 
                                 validators=[DataRequired()], 
                                 render_kw={"rows": 5, "placeholder": "e.g., Paracetamol 500mg - 1 tablet twice a day for 3 days."})
    submit = SubmitField('Complete Appointment')
 
class AvailabilitySlotForm(FlaskForm):
    """A sub-form for a single availability slot."""
    day_of_week = SelectField('Day', choices=[
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')
    ])
    start_time = TimeField('From', format='%H:%M')
    end_time = TimeField('To', format='%H:%M')

class UpdateAvailabilityForm(FlaskForm):
    """The main form that contains a list of availability slots."""
    slots = FieldList(FormField(AvailabilitySlotForm), min_entries=1)
    submit = SubmitField('Update Availability') 