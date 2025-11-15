from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, date, timedelta

from app import db, bcrypt
from . import admin_bp

# All forms imported here
from app.forms import (
    AddDoctorForm, EditDoctorForm, DepartmentForm, EditPatientForm
)

# All models imported here, in one line
from app.models import (
    User, Appointment, Department, DoctorProfile, PatientProfile
)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Renders the main admin dashboard page, including data for
    KPI cards, charts (via API), and preview tables.
    """
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    # --- 1. Fetch data for the KPI cards ---
    doctor_count = User.query.filter_by(role='doctor').count()
    patient_count = User.query.filter_by(role='patient').count()
    appointment_count = Appointment.query.count()

    # --- 2. Fetch data for the preview tables (show top 5) ---
    doctors = User.query.filter_by(role='doctor').limit(5).all()
    patients = User.query.filter_by(role='patient').limit(5).all()
    upcoming_appointments = Appointment.query.filter(
        Appointment.status == 'Booked',
        Appointment.appointment_datetime >= datetime.now()
    ).order_by(Appointment.appointment_datetime.asc()).limit(5).all()
    
    # --- 3. Pass ALL data to the template ---
    return render_template(
        'admin/dashboard.html', 
        title='Admin Dashboard',
        doctor_count=doctor_count,
        patient_count=patient_count,
        appointment_count=appointment_count,
        doctors=doctors,
        patients=patients,
        appointments=upcoming_appointments
    )

@admin_bp.route('/api/dashboard-stats')
@login_required
def dashboard_stats():
    """
    API endpoint to provide data for the admin dashboard charts.
    """
    if current_user.role != 'admin':
        return jsonify(error="Unauthorized"), 403

    # --- Query 1: Total Counts ---
    doctor_count = User.query.filter_by(role='doctor').count()
    patient_count = User.query.filter_by(role='patient').count()

    # --- Query 2: Appointments by Department ---
    appt_by_dept = db.session.query(
        Department.name, func.count(Appointment.id)
    ).join(
        DoctorProfile, Department.id == DoctorProfile.department_id
    ).join(
        User, DoctorProfile.user_id == User.id
    ).join(
        Appointment, User.id == Appointment.doctor_id
    ).group_by(Department.name).order_by(func.count(Appointment.id).desc()).all()
    
    dept_labels = [row[0] for row in appt_by_dept]
    dept_values = [row[1] for row in appt_by_dept]

    # --- Query 3: NEW - New Patients in Last 7 Days (SQLite compatible) ---
    seven_days_ago = datetime.utcnow() - timedelta(days=6)
    
    # Use strftime to group by date in a way SQLite understands
    new_patient_data = db.session.query(
        func.strftime('%Y-%m-%d', User.created_at), func.count(User.id)
    ).filter(
        User.role == 'patient',
        User.created_at >= seven_days_ago
    ).group_by(
        func.strftime('%Y-%m-%d', User.created_at)
    ).order_by(
        func.strftime('%Y-%m-%d', User.created_at)
    ).all()
    
    # Format data for the line chart (fill in missing days with 0)
    patient_trend_labels = [(date.today() - timedelta(days=i)) for i in range(6, -1, -1)]
    patient_trend_values = [0] * 7
    
    db_data_map = {day_str: count for day_str, count in new_patient_data}
    
    for i, date_obj in enumerate(patient_trend_labels):
        date_str_key = date_obj.strftime("%Y-%m-%d")
        if date_str_key in db_data_map:
            patient_trend_values[i] = db_data_map[date_str_key]

    # Convert date objects to user-friendly strings (e.g., "Nov 13")
    patient_trend_labels_formatted = [day.strftime("%b %d") for day in patient_trend_labels]

    return jsonify(
        total_counts={
            'labels': ['Doctors', 'Patients'],
            'values': [doctor_count, patient_count]
        },
        appointments_by_department={
            'labels': dept_labels,
            'values': dept_values
        },
        new_patient_trend={
            'labels': patient_trend_labels_formatted,
            'values': patient_trend_values
        }
    )

# --- (ALL YOUR OTHER ADMIN ROUTES GO HERE) ---

@admin_bp.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    form = AddDoctorForm()
    form.department_id.choices = [(0, 'Select Department...')] + [(d.id, d.name) for d in Department.query.order_by('name').all()]
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, password_hash=hashed_password, role='doctor')
        db.session.add(user)
        db.session.commit() 
        profile = DoctorProfile(user_id=user.id, full_name=form.full_name.data, department_id=form.department_id.data, qualifications='MD')
        db.session.add(profile)
        db.session.commit()
        flash(f'Doctor account for Dr. {form.full_name.data} has been created.', 'success')
        return redirect(url_for('admin.dashboard')) 
    return render_template('admin/add_doctor.html', title='Add New Doctor', form=form)

@admin_bp.route('/doctors')
@login_required
def manage_doctors():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    doctors = User.query.filter_by(role='doctor').join(DoctorProfile).order_by(DoctorProfile.full_name).all()
    return render_template('admin/manage_doctors.html', title='Manage Doctors', doctors=doctors)

@admin_bp.route('/doctor/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(user_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.home'))
    doctor_user = User.query.get_or_404(user_id)
    profile = doctor_user.doctor_profile
    form = EditDoctorForm(obj=profile)
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by('name').all()]
    if form.validate_on_submit():
        profile.full_name = form.full_name.data
        doctor_user.email = form.email.data
        profile.department_id = form.department_id.data
        db.session.commit()
        flash('Doctor profile has been updated successfully.', 'success')
        return redirect(url_for('admin.manage_doctors'))
    elif request.method == 'GET':
        form.email.data = doctor_user.email
    return render_template('admin/edit_doctor.html', title='Edit Doctor', form=form)

@admin_bp.route('/doctor/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_doctor(user_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.home'))
    doctor_user = User.query.get_or_404(user_id)
    if doctor_user.role != 'doctor':
        flash('This user is not a doctor.', 'warning')
        return redirect(url_for('admin.manage_doctors'))
    db.session.delete(doctor_user)
    db.session.commit()
    flash(f'Doctor account for {doctor_user.email} has been deleted.', 'success')
    return redirect(url_for('admin.manage_doctors'))

@admin_bp.route('/patients')
@login_required
def manage_patients():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    patients = User.query.filter_by(role='patient').join(PatientProfile).order_by(PatientProfile.full_name).all()
    return render_template('admin/manage_patients.html', title='Manage Patients', patients=patients)

@admin_bp.route('/patient/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(user_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.home'))
    patient_user = User.query.get_or_404(user_id)
    profile = patient_user.patient_profile
    form = EditPatientForm(obj=profile)
    if form.validate_on_submit():
        profile.full_name = form.full_name.data
        patient_user.email = form.email.data
        profile.contact_number = form.contact_number.data
        db.session.commit()
        flash('Patient profile has been updated successfully.', 'success')
        return redirect(url_for('admin.manage_patients'))
    elif request.method == 'GET':
        form.email.data = patient_user.email
    return render_template('admin/edit_patient.html', title='Edit Patient', form=form)

@admin_bp.route('/patient/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_patient(user_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.home'))
    patient_user = User.query.get_or_404(user_id)
    if patient_user.role != 'patient':
        flash('This user is not a patient.', 'warning')
        return redirect(url_for('admin.manage_patients'))
    db.session.delete(patient_user)
    db.session.commit()
    flash(f'Patient account for {patient_user.email} has been permanently deleted.', 'success')
    return redirect(url_for('admin.manage_patients'))

@admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required
def manage_departments():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    form = DepartmentForm()
    if form.validate_on_submit():
        new_dept = Department(name=form.name.data, description=form.description.data)
        db.session.add(new_dept)
        db.session.commit()
        flash(f"Department '{form.name.data}' has been created successfully.", 'success')
        return redirect(url_for('admin.manage_departments'))
    all_departments = Department.query.order_by('name').all()
    return render_template('admin/manage_departments.html', title='Manage Departments', form=form, departments=all_departments)

@admin_bp.route('/appointments')
@login_required
def manage_appointments():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    all_appointments = Appointment.query.order_by(Appointment.appointment_datetime.desc()).all()
    return render_template('admin/manage_appointments.html', title='Manage All Appointments', appointments=all_appointments)

@admin_bp.route('/patient_history/<int:user_id>')
@login_required
def view_patient_history(user_id):
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    patient = User.query.get_or_404(user_id)
    if patient.role != 'patient':
        flash('This user is not a patient.', 'warning')
        return redirect(url_for('admin.dashboard'))

    # Admin sees ALL completed appointments for this patient
    patient_history = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_datetime.desc()).all()

    # --- NEW: Calculate Patient Age ---
    patient_age = None
    if patient.patient_profile and patient.patient_profile.date_of_birth:
        today = date.today()
        patient_age = today.year - patient.patient_profile.date_of_birth.year - \
                      ((today.month, today.day) < (patient.patient_profile.date_of_birth.month, patient.patient_profile.date_of_birth.day))

    return render_template(
        'admin/patient_history.html', # This is our one "smart" template
        title=f"History for {patient.patient_profile.full_name}",
        patient=patient,
        history=patient_history,
        patient_age=patient_age, # Pass the new age variable
        back_url=url_for('admin.dashboard')
    )
    

@admin_bp.route('/user/blacklist/<int:user_id>', methods=['POST'])
@login_required
def blacklist_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    
    user_to_blacklist = User.query.get_or_404(user_id)
    user_to_blacklist.is_active = False
    db.session.commit()
    
    flash(f'User {user_to_blacklist.email} has been blacklisted.', 'warning')
    return redirect(request.referrer or url_for('admin.dashboard'))

@admin_bp.route('/user/activate/<int:user_id>', methods=['POST'])
@login_required
def activate_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    
    user_to_activate = User.query.get_or_404(user_id)
    user_to_activate.is_active = True
    db.session.commit()
    
    flash(f'User {user_to_activate.email} has been re-activated.', 'success')
    return redirect(request.referrer or url_for('admin.dashboard'))