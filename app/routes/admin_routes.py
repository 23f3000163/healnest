from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
# Add User and Appointment models to your imports
from app.models import User, Appointment
from . import admin_bp
from app.forms import AddDoctorForm, EditDoctorForm, DepartmentForm, EditPatientForm
from app.models import Department, User, DoctorProfile, PatientProfile
from app import db, bcrypt
from datetime import datetime

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    # Fetch lists of data to display on the dashboard
    # We use .limit(5) to show a preview on the dashboard
    doctors = User.query.filter_by(role='doctor').limit(5).all()
    patients = User.query.filter_by(role='patient').limit(5).all()
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.status == 'Booked',
        Appointment.appointment_datetime >= datetime.now()
    ).order_by(Appointment.appointment_datetime.asc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html', 
        title='Admin Dashboard',
        doctors=doctors,
        patients=patients,
        appointments=upcoming_appointments
    )

# We will add more admin routes (like add_doctor) here later.
@admin_bp.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))

    form = AddDoctorForm()
    # This line dynamically populates the dropdown with departments from the database
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by('name').all()]

    if form.validate_on_submit():
        # Step 1: Create the User record for login purposes
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            email=form.email.data,
            password_hash=hashed_password,
            role='doctor'
        )
        db.session.add(user)
        db.session.commit() # We commit here to get the new user's ID

        # Step 2: Create the associated DoctorProfile record
        profile = DoctorProfile(
            user_id=user.id, # Link to the user we just created
            full_name=form.full_name.data,
            department_id=form.department_id.data,
            qualifications='MD' # A default value
        )
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

    # Query the database to get all users who are doctors
    # We order by the full_name from the associated DoctorProfile
    doctors = User.query.filter_by(role='doctor').join(DoctorProfile).order_by(DoctorProfile.full_name).all()
    
    return render_template('admin/manage_doctors.html', title='Manage Doctors', doctors=doctors)

@admin_bp.route('/patients')
@login_required
def manage_patients():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))

    # Query the database for all users with the 'patient' role
    patients = User.query.filter_by(role='patient').join(PatientProfile).order_by(PatientProfile.full_name).all()
    
    return render_template('admin/manage_patients.html', title='Manage Patients', patients=patients)

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

    # Here we delete the user. The associated DoctorProfile should be deleted automatically
    # if we set up the database relationships correctly with cascading deletes.
    db.session.delete(doctor_user)
    db.session.commit()

    flash(f'Doctor account for {doctor_user.email} has been deleted.', 'success')
    return redirect(url_for('admin.manage_doctors'))

@admin_bp.route('/doctor/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(user_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.home'))

    doctor_user = User.query.get_or_404(user_id)
    profile = doctor_user.doctor_profile
    form = EditDoctorForm(obj=profile) # Pre-populate the form with existing data

    # Dynamically populate department choices
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by('name').all()]

    if form.validate_on_submit():
        # Update the data
        profile.full_name = form.full_name.data
        doctor_user.email = form.email.data # Update email on the User model
        profile.department_id = form.department_id.data
        db.session.commit()
        flash('Doctor profile has been updated successfully.', 'success')
        return redirect(url_for('admin.manage_doctors'))
    
    # On a GET request, pre-fill the email field manually
    elif request.method == 'GET':
        form.email.data = doctor_user.email

    return render_template('admin/edit_doctor.html', title='Edit Doctor', form=form)


@admin_bp.route('/appointments')
@login_required
def manage_appointments():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))

    # Query the database for ALL appointments, ordering by the newest first
    all_appointments = Appointment.query.order_by(Appointment.appointment_datetime.desc()).all()
    
    return render_template(
        'admin/manage_appointments.html', 
        title='Manage All Appointments', 
        appointments=all_appointments
    )


@admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required
def manage_departments():
    if current_user.role != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    form = DepartmentForm()
    
    # This block runs when the admin submits the "Add Department" form
    if form.validate_on_submit():
        new_dept = Department(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(new_dept)
        db.session.commit()
        flash(f"Department '{form.name.data}' has been created successfully.", 'success')
        return redirect(url_for('admin.manage_departments')) # Redirect to refresh the page

    # This part runs on every visit (GET request)
    # It fetches all existing departments to display them
    all_departments = Department.query.order_by('name').all()
    
    return render_template(
        'admin/manage_departments.html', 
        title='Manage Departments', 
        form=form, 
        departments=all_departments
    )

@admin_bp.route('/patient/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_patient(user_id):
    """
    This route handles the deletion of a patient's account.
    It is protected to only accept POST requests for security.
    """
    # Security check to ensure only an admin can perform this action.
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.home'))

    # Find the user to be deleted in the database.
    # If a user with this ID doesn't exist, this will automatically trigger a 404 Not Found error.
    patient_user = User.query.get_or_404(user_id)
    
    # Double-check that the user being deleted is actually a patient.
    if patient_user.role != 'patient':
        flash('This user is not a patient.', 'warning')
        return redirect(url_for('admin.manage_patients'))

    # If all checks pass, delete the user from the database.
    db.session.delete(patient_user)
    db.session.commit()

    flash(f'Patient account for {patient_user.email} has been permanently deleted.', 'success')
    # Redirect the admin back to the list of patients.
    return redirect(url_for('admin.manage_patients'))


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