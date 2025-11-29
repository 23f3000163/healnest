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
    Accepts a URL parameter 'range' (7, 30, 90, or 'year').
    """
    if current_user.role != 'admin':
        return jsonify(error="Unauthorized"), 403

    # --- 1. Handle Date Range Logic ---
    time_range = request.args.get('range', '7') # Default to 7 days
    today = date.today()

    if time_range == '30':
        start_date = today - timedelta(days=29)
        days_count = 30
    elif time_range == '90':
        start_date = today - timedelta(days=89)
        days_count = 90
    elif time_range == 'year':
        start_date = date(today.year, 1, 1)
        days_count = (today - start_date).days + 1
    else: # Default '7'
        start_date = today - timedelta(days=6)
        days_count = 7

    # --- 2. Query Total Counts (Unchanged) ---
    doctor_count = User.query.filter_by(role='doctor').count()
    patient_count = User.query.filter_by(role='patient').count()

    # --- 3. Query Appointments by Department (Unchanged) ---
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

    # --- 4. Query New Patient Trends (Dynamic Range) ---
    # We filter by the calculated start_date
    new_patient_data = db.session.query(
        func.date(User.created_at), func.count(User.id)
    ).filter(
        User.role == 'patient',
        func.date(User.created_at) >= start_date
    ).group_by(
        func.date(User.created_at)
    ).all()
    
    # Create the list of labels (dates) for the chart
    # We generate a list of all dates in the range to ensure the chart shows 0 for days with no signups
    patient_trend_labels = []
    patient_trend_values = []
    
    # Convert DB results to a dictionary for easy lookup: {'2025-11-17': 5, ...}
    db_data_map = {day_str: count for day_str, count in new_patient_data}
    
    for i in range(days_count):
        current_day = start_date + timedelta(days=i)
        date_str_key = current_day.strftime("%Y-%m-%d")
        
        # Format label (e.g., "Nov 17")
        patient_trend_labels.append(current_day.strftime("%b %d"))
        
        # Get value from DB map, or 0 if not found
        patient_trend_values.append(db_data_map.get(date_str_key, 0))

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
            'labels': patient_trend_labels,
            'values': patient_trend_values
        }
    )

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
        profile = DoctorProfile(user_id=user.id, full_name=form.full_name.data, department_id=form.department_id.data, contact_number=form.contact_number.data, qualifications='MD')
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
        profile.contact_number = form.contact_number.data
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
    
    # 1. Safety Check: Ensure it's actually a doctor
    if doctor_user.role != 'doctor':
        flash('This user is not a doctor.', 'warning')
        return redirect(url_for('admin.manage_doctors'))

    # 2. HISTORY CHECK: Check for ANY appointments (past or future)
    appointment_count = Appointment.query.filter_by(doctor_id=doctor_user.id).count()

    if appointment_count > 0:
        # If they have history, BLOCK the delete
        flash(f'Cannot delete Dr. {doctor_user.doctor_profile.full_name} because they have {appointment_count} appointment records. Please BLACKLIST them instead to preserve medical history.', 'danger')
        return redirect(url_for('admin.manage_doctors'))

    # 3. If no history exists, it is safe to permanently delete
    db.session.delete(doctor_user)
    db.session.commit()

    flash(f'Doctor account for {doctor_user.email} has been permanently deleted.', 'success')
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
    
    # 1. Safety Check: Ensure it's actually a patient
    if patient_user.role != 'patient':
        flash('This user is not a patient.', 'warning')
        return redirect(url_for('admin.manage_patients'))

    # 2. HISTORY CHECK: Check for ANY appointments
    appointment_count = Appointment.query.filter_by(patient_id=patient_user.id).count()

    if appointment_count > 0:
        # If they have history, BLOCK the delete
        # Using patient profile name if available, else email
        name = patient_user.patient_profile.full_name if patient_user.patient_profile else patient_user.email
        
        flash(f'Cannot delete patient {name} because they have {appointment_count} appointment records. Please BLACKLIST them instead to preserve medical history.', 'danger')
        return redirect(url_for('admin.manage_patients'))

    # 3. If no history exists, it is safe to permanently delete
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

    # Determine displayed name
    if user_to_blacklist.role == 'doctor' and user_to_blacklist.doctor_profile:
        display_name = f"Dr. {user_to_blacklist.doctor_profile.full_name}"
    elif user_to_blacklist.role == 'patient' and user_to_blacklist.patient_profile:
        display_name = user_to_blacklist.patient_profile.full_name
    else:
        display_name = user_to_blacklist.email  # fallback

    flash(f'{display_name} has been blacklisted.', 'warning')
    
    return redirect(request.referrer or url_for('admin.manage_doctors'))


@admin_bp.route('/user/activate/<int:user_id>', methods=['POST'])
@login_required
def activate_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))
    
    user_to_activate = User.query.get_or_404(user_id)
    user_to_activate.is_active = True
    db.session.commit()

    # Determine proper display name
    if user_to_activate.role == 'doctor' and user_to_activate.doctor_profile:
        display_name = f"Dr. {user_to_activate.doctor_profile.full_name}"
    elif user_to_activate.role == 'patient' and user_to_activate.patient_profile:
        display_name = user_to_activate.patient_profile.full_name
    else:
        display_name = user_to_activate.email  
    
    flash(f'{display_name} has been re-activated.', 'success')

    return redirect(request.referrer or url_for('admin.dashboard'))

@admin_bp.route('/department/delete/<int:dept_id>', methods=['POST'])
@login_required
def delete_department(dept_id):
    """
    Deletes a department. 
    Note: You might want to handle cases where doctors are still assigned 
    to this department (SQLAlchemy might raise an IntegrityError).
    """
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.home'))

    department = Department.query.get_or_404(dept_id)
    
    try:
        db.session.delete(department)
        db.session.commit()
        flash(f"Department '{department.name}' has been deleted.", 'success')
    except Exception as e:
        db.session.rollback()
        flash('Cannot delete this department because doctors are currently assigned to it.', 'danger')

    return redirect(url_for('admin.manage_departments'))

@admin_bp.route('/department/edit', methods=['POST'])
@login_required
def edit_department():
    if current_user.role != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('main.home'))

    dept_id = request.form.get("dept_id")
    name = request.form.get("name")
    description = request.form.get("description")

    department = Department.query.get_or_404(dept_id)
    department.name = name
    department.description = description

    db.session.commit()

    flash("Department updated successfully!", "success")
    return redirect(url_for('admin.manage_departments'))


@admin_bp.route('/department/<int:dept_id>')
@login_required
def department_details(dept_id):
    if current_user.role != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('main.home'))

    department = Department.query.get_or_404(dept_id)

    doctors = (
        User.query
        .join(DoctorProfile)
        .filter(DoctorProfile.department_id == dept_id)
        .all()
    )

    return render_template(
        "admin/department_details.html",
        department=department,
        doctors=doctors
    )
