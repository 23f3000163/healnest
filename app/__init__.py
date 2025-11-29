from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
app = Flask(__name__)


app.config['SECRET_KEY'] = 'a_super_secret_key_change_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'main.login' 
login_manager.login_message_category = 'info' 

from app.models import Notification

@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
        notification_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return dict(unread_notifications=unread_notifications, notification_count=notification_count)
    return dict(unread_notifications=[], notification_count=0)



from app.routes import main_bp, admin_bp, patient_bp, doctor_bp


from app.routes import main_routes, admin_routes, doctor_routes, patient_routes


app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(doctor_bp)


from app import models


@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
       
        unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
      
        notification_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return dict(unread_notifications=unread_notifications, notification_count=notification_count)
    return dict(unread_notifications=[], notification_count=0)


from app import models
from app.routes import main_routes, admin_routes, doctor_routes, patient_routes