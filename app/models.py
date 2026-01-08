from datetime import datetime, time
from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from app import db, login_manager


# -----------------------------
# Flask-Login user loader
# -----------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -----------------------------
# User Model
# -----------------------------
class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(db.String(128), nullable=False)

    role = db.Column(
        db.String(10),
        nullable=False
    )

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.CheckConstraint(
            "role IN ('admin', 'doctor', 'patient')",
            name="check_valid_role"
        ),
    )

    doctor_profile = db.relationship(
        "DoctorProfile",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    patient_profile = db.relationship(
        "PatientProfile",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    notifications = db.relationship(
        "Notification",
        backref="user",
        cascade="all, delete-orphan"
    )

    # -------- Password handling --------
    @property
    def password(self):
        raise AttributeError("Password is write-only.")

    @password.setter
    def password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def verify_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # -------- Reset token --------
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config["SECRET_KEY"])
        return s.dumps({"user_id": self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            user_id = s.loads(token, max_age=expires_sec)["user_id"]
        except Exception:
            return None
        return User.query.get(user_id)


# -----------------------------
# Department
# -----------------------------
class Department(db.Model):
    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)

    doctors = db.relationship("DoctorProfile", backref="department")


# -----------------------------
# Doctor Profile
# -----------------------------
class DoctorProfile(db.Model):
    __tablename__ = "doctor_profile"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        unique=True,
        nullable=False
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("department.id"),
        nullable=False
    )

    full_name = db.Column(db.String(100), nullable=False)
    qualifications = db.Column(db.String(200))
    experience_years = db.Column(db.Integer, default=0)
    contact_number = db.Column(db.String(20))
    bio = db.Column(db.Text)

    # Billing-ready
    consultation_fee = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    currency = db.Column(db.String(5), default="INR")

    availabilities = db.relationship(
        "Availability",
        backref="doctor_profile",
        cascade="all, delete-orphan"
    )


# -----------------------------
# Patient Profile
# -----------------------------
class PatientProfile(db.Model):
    __tablename__ = "patient_profile"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        unique=True,
        nullable=False
    )

    full_name = db.Column(db.String(100), nullable=False)

    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    contact_number = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    allergies = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# -----------------------------
# Availability (Time-based)
# -----------------------------
class Availability(db.Model):
    __tablename__ = "availability"

    id = db.Column(db.Integer, primary_key=True)

    doctor_profile_id = db.Column(
        db.Integer,
        db.ForeignKey("doctor_profile.id"),
        nullable=False
    )

    available_date = db.Column(db.Date, nullable=False)

    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            "start_time < end_time",
            name="check_valid_time_range"
        ),
    )


# -----------------------------
# Appointment
# -----------------------------
class Appointment(db.Model):
    __tablename__ = "appointment"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    appointment_datetime = db.Column(db.DateTime, nullable=False, index=True)

    status = db.Column(
    db.String(20),
    nullable=False,
    default="Booked"
    )


    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    status_history = db.relationship(
        "AppointmentStatusHistory",
        backref="appointment",
        cascade="all, delete-orphan",
        order_by="AppointmentStatusHistory.changed_at"
    )

    patient = relationship(
        'User',
        foreign_keys=[patient_id],
        backref='patient_appointments'
    )

    doctor = relationship(
        'User',
        foreign_keys=[doctor_id],
        backref='doctor_appointments'
    )

# -----------------------------
# Appointment Status History
# -----------------------------
class AppointmentStatusHistory(db.Model):
    __tablename__ = "appointment_status_history"

    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointment.id"),
        nullable=False
    )

    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)

    changed_at = db.Column(db.DateTime, default=datetime.utcnow)


# -----------------------------
# Notification
# -----------------------------
class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    type = db.Column(
        db.String(50),
        nullable=False
    )

    message = db.Column(db.Text, nullable=False)

    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
