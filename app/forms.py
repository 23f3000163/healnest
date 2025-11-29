from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, DateField, TimeField, SelectField, TextAreaField, FieldList, FormField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange, Optional
from app.models import User, Department



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



class BookingForm(FlaskForm):
  
    submit = SubmitField('Confirm Appointment')



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
    visit_type = StringField('Visit Type', 
                             validators=[DataRequired()], 
                             render_kw={"placeholder": "e.g., In-person, Follow-up"})
    tests_done = StringField('Tests Done', 
                             render_kw={"placeholder": "e.g., ECG, Blood Test"})
    diagnosis = TextAreaField('Diagnosis', 
                              validators=[DataRequired()], 
                              render_kw={"rows": 4, "placeholder": "Enter patient diagnosis details..."})
    prescription = TextAreaField('Prescription', 
                                 validators=[DataRequired()], 
                                 render_kw={"rows": 4, "placeholder": "Include medications and dosages, e.g., Paracetamol 500mg (1-0-1) for 3 days."})
    submit = SubmitField('Save and Complete Appointment')
 
class AvailabilitySlotForm(FlaskForm):
    """A sub-form for a single availability slot. (Part of Step 1)"""
    day_of_week = SelectField('Day', choices=[
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')
    ])
    # VALIDATION FIX: Add validators=[Optional()] so blank fields are allowed
    start_time = TimeField('From', format='%H:%M', validators=[Optional()])
    end_time = TimeField('To', format='%H:%M', validators=[Optional()])

class UpdateAvailabilityForm(FlaskForm):
    """The main form for the doctor to manage their schedule. (Part of Step 1)"""
    # VALIDATION FIX: Change min_entries=1 to min_entries=0
    slots = FieldList(FormField(AvailabilitySlotForm), min_entries=0)
    submit = SubmitField('Update Availability')

#add doctor form 
class AddDoctorForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    # We use coerce=int to make sure the form submission is an integer
    contact_number = StringField('Contact Number', validators=[DataRequired(), Length(min=10, max=15)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Add Doctor')

    # Custom validation to check if the email is already in use
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already in use. Please choose a different one.')    
        
class EditDoctorForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    contact_number = StringField('Contact Number', validators=[DataRequired(), Length(min=10, max=15)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Update Doctor Profile')        


class DepartmentForm(FlaskForm):
    name = StringField('Department Name', validators=[DataRequired()])
    description = TextAreaField('Description', render_kw={"rows": 3})
    submit = SubmitField('Add Department')

    # Custom validation to prevent creating duplicate departments
    def validate_name(self, name):
        dept = Department.query.filter_by(name=name.data).first()
        if dept:
            raise ValidationError('A department with this name already exists.')  


class EditPatientForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    contact_number = StringField('Contact Number')
    submit = SubmitField('Update Patient Profile')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')    

class DoctorUpdateProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    qualifications = StringField('Qualifications', validators=[Optional(), Length(max=100)], render_kw={"placeholder": "e.g., MBBS, MD - Medical Oncology"})
    contact_number = StringField('Contact Number', validators=[DataRequired(), Length(min=10, max=15)])
    experience_years = StringField('Experience (Years)', validators=[Optional()], render_kw={"placeholder": "e.g., 10"})
    bio = TextAreaField('Professional Bio', validators=[Optional()], render_kw={"rows": 4, "placeholder": "Describe your experience and specialization..."})
    submit = SubmitField('Update Profile')