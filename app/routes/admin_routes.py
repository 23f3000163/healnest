from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, date, timedelta

from app import db, models
from . import admin_bp

from app.forms import AddDoctorForm


# -------------------------------------------------
# Admin Dashboard
# -------------------------------------------------
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    doctor_count = models.User.query.filter_by(role='doctor').count()
    patient_count = models.User.query.filter_by(role='patient').count()
    appointment_count = models.Appointment.query.count()

    doctors = (
        models.User.query
        .filter_by(role='doctor')
        .join(models.DoctorProfile)
        .order_by(models.DoctorProfile.full_name)
        .limit(5)
        .all()
    )

    patients = (
        models.User.query
        .filter_by(role='patient')
        .join(models.PatientProfile)
        .order_by(models.PatientProfile.full_name)
        .limit(5)
        .all()
    )

    upcoming_appointments = (
        models.Appointment.query
        .filter(
            models.Appointment.status == 'BOOKED',
            models.Appointment.appointment_datetime >= datetime.now()
        )
        .order_by(models.Appointment.appointment_datetime.asc())
        .limit(5)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        doctor_count=doctor_count,
        patient_count=patient_count,
        appointment_count=appointment_count,
        doctors=doctors,
        patients=patients,
        appointments=upcoming_appointments
    )


# -------------------------------------------------
# Dashboard Analytics API
# -------------------------------------------------
@admin_bp.route('/api/dashboard-stats')
@login_required
def dashboard_stats():
    if current_user.role != 'admin':
        return jsonify(error='Unauthorized'), 403

    time_range = request.args.get('range', '7')
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
    else:
        start_date = today - timedelta(days=6)
        days_count = 7

    doctor_count = models.User.query.filter_by(role='doctor').count()
    patient_count = models.User.query.filter_by(role='patient').count()

    new_patients = (
        db.session.query(
            func.date(models.User.created_at),
            func.count(models.User.id)
        )
        .filter(
            models.User.role == 'patient',
            func.date(models.User.created_at) >= start_date
        )
        .group_by(func.date(models.User.created_at))
        .all()
    )

    patient_map = {str(day): count for day, count in new_patients}

    labels, values = [], []
    for i in range(days_count):
        day = start_date + timedelta(days=i)
        labels.append(day.strftime('%b %d'))
        values.append(patient_map.get(str(day), 0))

    return jsonify(
        total_counts={
            'labels': ['Doctors', 'Patients'],
            'values': [doctor_count, patient_count]
        },
        new_patient_trend={
            'labels': labels,
            'values': values
        }
    )


# -------------------------------------------------
# Doctor Management
# -------------------------------------------------
@admin_bp.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    form = AddDoctorForm()
    form.department_id.choices = [
        (d.id, d.name)
        for d in models.Department.query.order_by(models.Department.name).all()
    ]

    if form.validate_on_submit():
        user = models.User(
            email=form.email.data,
            role='doctor'
        )
        user.password = form.password.data

        db.session.add(user)
        db.session.commit()

        profile = models.DoctorProfile(
            user_id=user.id,
            full_name=form.full_name.data,
            department_id=form.department_id.data,
            contact_number=form.contact_number.data
        )

        db.session.add(profile)
        db.session.commit()

        flash('Doctor added successfully.', 'success')
        return redirect(url_for('admin.manage_doctors'))

    return render_template('admin/add_doctor.html', form=form)


@admin_bp.route('/doctors')
@login_required
def manage_doctors():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    doctors = (
        models.User.query
        .filter_by(role='doctor')
        .join(models.DoctorProfile)
        .order_by(models.DoctorProfile.full_name)
        .all()
    )

    return render_template('admin/manage_doctors.html', doctors=doctors)


# -------------------------------------------------
# Patient Management
# -------------------------------------------------
@admin_bp.route('/patients')
@login_required
def manage_patients():
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    patients = (
        models.User.query
        .filter_by(role='patient')
        .join(models.PatientProfile)
        .order_by(models.PatientProfile.full_name)
        .all()
    )

    return render_template('admin/manage_patients.html', patients=patients)


# -------------------------------------------------
# 🔒 PHASE-1 STUB ACTION ROUTES (NO EXTRA FEATURES)
# -------------------------------------------------
@admin_bp.route('/delete-doctor/<int:user_id>', methods=['POST'])
@login_required
def delete_doctor(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))

    user = models.User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    flash('Doctor deleted.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/delete-patient/<int:user_id>', methods=['POST'])
@login_required
def delete_patient(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))

    user = models.User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    flash('Patient deleted.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/blacklist/<int:user_id>', methods=['POST'])
@login_required
def blacklist_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))

    user = models.User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()

    flash('User blacklisted.', 'warning')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/activate/<int:user_id>', methods=['POST'])
@login_required
def activate_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.home'))

    user = models.User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()

    flash('User activated.', 'success')
    return redirect(url_for('admin.dashboard'))
