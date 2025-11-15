from flask import render_template, url_for, flash, redirect, request
# Add login_required to this import line
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import or_
from app import db, bcrypt
from app.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from app.models import User, PatientProfile, DoctorProfile, Department, Notification
from . import main_bp

# Import the Blueprint instance from the routes package's __init__.py
from . import main_bp

@main_bp.route('/')
@main_bp.route('/home')
def home():
    """
    Handles the homepage.
    If user is logged in, redirect them to their correct dashboard.
    """
    if current_user.is_authenticated:
        # --- THIS IS THE "SMART REDIRECT" FIX ---
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        else:
            return redirect(url_for('patient.dashboard'))
    
    # Guests will see the homepage
    return render_template('home.html', title='Home')



@main_bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, password_hash=hashed_password, role='patient')
        db.session.add(user)
        db.session.commit()

        profile = PatientProfile(user_id=user.id, full_name=user.email)
        db.session.add(profile)
        db.session.commit()
        
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)


@main_bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        # First, check if user exists and password is correct
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            
            # --- NEW BLACKLIST CHECK ---
            # Second, check if the user's account is active
            if not user.is_active:
                flash('Your account has been suspended. Please contact an administrator.', 'danger')
                return redirect(url_for('main.login'))
            # --- END OF CHECK ---

            # If both checks pass, log the user in
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            
            # Redirect to the correct dashboard based on role
            if user.role == 'admin':
                return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
            elif user.role == 'doctor':
                return redirect(next_page) if next_page else redirect(url_for('doctor.dashboard'))
            else:
                return redirect(next_page) if next_page else redirect(url_for('patient.dashboard'))
        else:
            # If user doesn't exist or password is wrong
            flash('Login Unsuccessful. Please check email and password.', 'danger')
            
    return render_template('login.html', title='Login', form=form)


@main_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@main_bp.route("/search")
@login_required
def search():
    query = request.args.get('query', '', type=str)
    
    if not query:
        flash('Please enter a search term.', 'warning')
        return redirect(request.referrer or url_for('main.home'))

    if current_user.role == 'admin':
        patients = PatientProfile.query.join(User).filter(
            or_(PatientProfile.full_name.ilike(f'%{query}%'), User.email.ilike(f'%{query}%'))
        ).all()
        doctors = DoctorProfile.query.join(Department).filter(
            or_(DoctorProfile.full_name.ilike(f'%{query}%'), Department.name.ilike(f'%{query}%'))
        ).all()
        return render_template('admin/search_results.html', query=query, patients=patients, doctors=doctors)

    elif current_user.role == 'patient':
        doctors = DoctorProfile.query.join(Department).filter(
            or_(DoctorProfile.full_name.ilike(f'%{query}%'), Department.name.ilike(f'%{query}%'))
        ).all()
        return render_template('patient/search_results.html', query=query, doctors=doctors)
        
    flash("Search is not yet configured for your role.", "info")
    return redirect(request.referrer or url_for('main.home'))

@main_bp.route('/notifications')
@login_required
def notifications():
    # Fetch all notifications for the current user, newest first
    all_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Mark all unread notifications as read
    for notification in current_user.notifications:
        notification.is_read = True
    db.session.commit()
    
    return render_template('notifications.html', title='My Notifications', notifications=all_notifications)


@main_bp.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        token = user.get_reset_token()
        
        # --- SIMULATE SENDING EMAIL ---
        # In a real app, you would email this link to the user.
        # For this project, we will just print it to the console.
        reset_link = url_for('main.reset_token', token=token, _external=True)
        print("--- PASSWORD RESET LINK (COPY AND PASTE THIS INTO YOUR BROWSER) ---")
        print(reset_link)
        print("-----------------------------------------------------------------")
        
        flash('A (simulated) email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('main.login'))
    return render_template('request_reset.html', title='Reset Password', form=form)


@main_bp.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token.', 'warning')
        return redirect(url_for('main.reset_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password_hash = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('reset_token.html', title='Reset Password', form=form)