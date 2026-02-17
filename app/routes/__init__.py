from flask import Blueprint

# This file now ONLY creates the blueprints.

main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')
patient_bp = Blueprint('patient', __name__, url_prefix='/patient')


from . import main_routes
from . import admin_routes
from . import doctor_routes
from . import patient_routes