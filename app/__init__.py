from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'a_super_secret_key_change_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- INITIALIZE EXTENSIONS ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'main.login' 
login_manager.login_message_category = 'info' 

# --- IMPORT BLUEPRINTS AND ROUTES ---
# First, import the blueprint objects
from app.routes import main_bp, admin_bp, patient_bp, doctor_bp

# Second, import the route files. This runs the code inside them,
# connecting the @...route() decorators to the blueprint objects.
from app.routes import main_routes, admin_routes, doctor_routes, patient_routes

# --- BLUEPRINT REGISTRATION ---
# Third, now that the blueprints are fully configured with their routes,
# register them with the Flask app.
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(doctor_bp)

# --- IMPORT MODELS ---
# Import models to ensure they are known to SQLAlchemy
from app import models

# This function makes variables globally available to all templates.
@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        # Fetch the 5 most recent unread notifications for the current user
        unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
        # Get a total count of unread notifications
        notification_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return dict(unread_notifications=unread_notifications, notification_count=notification_count)
    return dict(unread_notifications=[], notification_count=0)

# --- IMPORT MODELS AND ROUTES ---
# Ensure these are at the very end of the file
from app import models
from app.routes import main_routes, admin_routes, doctor_routes, patient_routes