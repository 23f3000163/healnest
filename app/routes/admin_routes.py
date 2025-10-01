from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user

# Import the Blueprint instance from the routes package
from . import admin_bp

@admin_bp.route('/dashboard')
@login_required # This decorator ensures only logged-in users can access this route
def dashboard():
    # Check if the current logged-in user is an admin
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    # Placeholder: Render the admin dashboard template
    # We will add logic here later to fetch stats (doctor count, etc.)
    return render_template('admin/dashboard.html', title='Admin Dashboard')

# We will add more admin routes here later (e.g., for adding doctors)
