from flask import Blueprint

# This file now ONLY creates the blueprints.
# The actual routes that use them will be imported in the main __init__.py

main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')
patient_bp = Blueprint('patient', __name__, url_prefix='/patient')