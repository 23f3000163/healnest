from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user

# Import the Blueprint instance from the routes package
from . import doctor_bp

@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    # Check if the current user is a doctor
    if current_user.role != 'doctor':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
        
    # Placeholder: Render the doctor dashboard template
    # We will add logic here later to fetch the doctor's appointments
    return render_template('doctor/dashboard.html', title='Doctor Dashboard')

# We will add more doctor routes here later (e.g., for treating patients)
