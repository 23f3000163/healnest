from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer as Serializer
from app import app

# Flask-Login requires this to load a user from the database given their ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ## CORE MODELS ##

class User(db.Model, UserMixin):
    """ Central table for all users: Admins, Doctors, and Patients. """
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # Role differentiates between user types
    role = db.Column(db.String(10), nullable=False)  # 'admin', 'doctor', 'patient'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    doctor_profile = db.relationship('DoctorProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    patient_profile = db.relationship('PatientProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    
    doctor_appointments = db.relationship('Appointment', foreign_keys='Appointment.doctor_id', backref='doctor', lazy=True)
    patient_appointments = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient', lazy=True)
    
    availabilities = db.relationship('Availability', backref='doctor', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")
    reviews_given = db.relationship('DoctorReview', foreign_keys='DoctorReview.patient_id', backref='patient', lazy=True)
    reviews_received = db.relationship('DoctorReview', foreign_keys='DoctorReview.doctor_id', backref='doctor', lazy=True)

    def get_reset_token(self, expires_sec=1800):
        """Generates a secure, timed token for password reset."""
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        """Verifies the reset token and returns the User object if valid."""
        s = Serializer(app.config['SECRET_KEY'])
        try:
            # The 'max_age' parameter automatically checks for expiration
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except Exception:
            return None
        return User.query.get(user_id)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.email}', '{self.role}')"

class Department(db.Model):
    """ Table for medical departments/specializations. """
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    doctors = db.relationship('DoctorProfile', backref='department', lazy=True)

    def __repr__(self):
        return self.name

class DoctorProfile(db.Model):
    """ Stores doctor-specific information, linked to a User. """
    __tablename__ = 'doctor_profile'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    qualifications = db.Column(db.String(200))
    bio = db.Column(db.Text)

class Availability(db.Model):
    """
    Stores a specific date and slot (e.g., 'morning' or 'evening')
    that a doctor has marked as available.
    """
    __tablename__ = 'availability'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    available_date = db.Column(db.Date, nullable=False)
    slot = db.Column(db.String(20), nullable=False) # e.g., 'morning', 'evening'
    
    # Ensure a doctor can't have the same slot marked twice for the same day
    __table_args__ = (db.UniqueConstraint('doctor_id', 'available_date', 'slot'),)

class Appointment(db.Model):
    """ Core table linking patients and doctors for appointments. """
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_datetime = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Booked') # Booked, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    treatment = db.relationship('Treatment', backref='appointment', uselist=False, cascade="all, delete-orphan")
    review = db.relationship('DoctorReview', backref='appointment', uselist=False, cascade="all, delete-orphan")
    
class Treatment(db.Model):
    """ Stores details of a completed appointment. """
    __tablename__ = 'treatment'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False, unique=True)
    
    # NEW FIELDS
    visit_type = db.Column(db.String(100))
    tests_done = db.Column(db.String(300))
    
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text) # We can keep this for any extra doctor notes


# ## ADDITIONAL FEATURE MODELS ##

class PatientProfile(db.Model):
    """ Stores patient-specific information, linked to a User. """
    __tablename__ = 'patient_profile'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    contact_number = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    
    # Relationship to medical documents
    documents = db.relationship('MedicalDocument', backref='patient', lazy=True)

class DoctorReview(db.Model):
    """ Table for storing patient reviews of doctors. """
    __tablename__ = 'doctor_review'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False, unique=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # Rating from 1 to 5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MedicalDocument(db.Model):
    """ Stores paths to uploaded medical documents like lab reports. """
    __tablename__ = 'medical_document'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profile.id'), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True) # Optional link
    file_path = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    """ Table for in-app user notifications. """
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)