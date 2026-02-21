import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_migrate import Migrate

# =========================
# Load Environment Variables
# =========================
load_dotenv()

# =========================
# Create App
# =========================
app = Flask(__name__)

# =========================
# Configuration
# =========================
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///hospital.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# =========================
# Extensions
# =========================
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "main.login"
login_manager.login_message_category = "info"

# =========================
# Import Models (after db init)
# =========================
from app import models
from app.models import Notification

# =========================
# Register Blueprints
# =========================
from app.routes import main_bp, admin_bp, patient_bp, doctor_bp

app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(doctor_bp)

# =========================
# Force Doctor Password Change
# =========================
@app.before_request
def force_password_change():
    if (
        current_user.is_authenticated
        and current_user.role == "doctor"
        and current_user.must_change_password
        and request.endpoint
        and request.endpoint != "doctor.change_password"
        and not request.endpoint.startswith("static")
    ):
        return redirect(url_for("doctor.change_password"))


# =========================
# Global Notification Context (Navbar)
# =========================
@app.context_processor
def navbar_context():
    if current_user.is_authenticated:
        unread = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).order_by(Notification.created_at.desc()).limit(5).all()

        return {
            "notification_count": len(unread),
            "unread_notifications": unread
        }

    return {
        "notification_count": 0,
        "unread_notifications": []
    }


# =========================
# Global Year for Footer
# =========================
@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}
