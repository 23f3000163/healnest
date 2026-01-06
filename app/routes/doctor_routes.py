from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time

from app import db, models
from app.forms import (
    TreatmentForm,
    BookingForm,
    DoctorUpdateProfileForm
)
from . import doctor_bp


# ---------------------------
# Doctor Dashboard
# ---------------------------
@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'doctor':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    upcoming_appointments = (
        models.Appointment.query
        .filter(
            models.Appointment.doctor_id == current_user.id,
            models.Appointment.current_status == 'BOOKED',
            models.Appointment.appointment_datetime >= datetime.now()
        )
        .order_by(models.Appointment.appointment_datetime.asc())
        .all()
    )

    assigned_patients = (
        db.session.query(models.User)
        .join(models.Appointment, models.User.id == models.Appointment.patient_id)
        .filter(models.Appointment.doctor_id == current_user.id)
        .distinct()
        .all()
    )

    return render_template(
        'doctor/dashboard.html',
        title='Doctor Dashboard',
        appointments=upcoming_appointments,
        patients=assigned_patients
    )


# ---------------------------
# Treat Patient
# ---------------------------
@doctor_bp.route('/treat/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def treat_patient(appointment_id):
    if current_user.role != 'doctor':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    appointment = models.Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != current_user.id:
        flash('You are not authorized to treat this patient.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    patient_history = (
        models.Appointment.query
        .filter(
            models.Appointment.patient_id == appointment.patient_id,
            models.Appointment.current_status == 'COMPLETED'
        )
        .order_by(models.Appointment.appointment_datetime.desc())
        .all()
    )

    form = TreatmentForm()

    if form.validate_on_submit():
        treatment = models.Treatment(
            appointment_id=appointment.id,
            visit_type=form.visit_type.data,
            tests_done=form.tests_done.data,
            diagnosis=form.diagnosis.data,
            prescription=form.prescription.data
        )
        db.session.add(treatment)

        # ---- STATUS CHANGE WITH HISTORY ----
        history = models.AppointmentStatusHistory(
            appointment_id=appointment.id,
            old_status=appointment.current_status,
            new_status='COMPLETED'
        )
        appointment.current_status = 'COMPLETED'
        db.session.add(history)

        notification = models.Notification(
            user_id=appointment.patient_id,
            type='APPOINTMENT_COMPLETED',
            message=f"Dr. {current_user.doctor_profile.full_name} has completed your appointment."
        )
        db.session.add(notification)

        db.session.commit()

        flash('Treatment recorded and appointment completed.', 'success')
        return redirect(url_for('doctor.dashboard'))

    return render_template(
        'doctor/treat_patient.html',
        title='Treat Patient',
        appointment=appointment,
        patient_history=patient_history,
        form=form
    )


# ---------------------------
# Doctor Profile
# ---------------------------
@doctor_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.role != 'doctor':
        return redirect(url_for('main.home'))

    profile = current_user.doctor_profile
    form = DoctorUpdateProfileForm(obj=profile)

    if form.validate_on_submit():
        profile.full_name = form.full_name.data
        profile.contact_number = form.contact_number.data
        profile.qualifications = form.qualifications.data
        profile.experience_years = int(form.experience_years.data or 0)
        profile.bio = form.bio.data

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('doctor.profile'))

    return render_template(
        'doctor/profile.html',
        title='My Profile',
        form=form
    )


# ---------------------------
# Cancel Appointment
# ---------------------------
@doctor_bp.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    if current_user.role != 'doctor':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    appointment = models.Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != current_user.id:
        flash('You cannot cancel this appointment.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    history = models.AppointmentStatusHistory(
        appointment_id=appointment.id,
        old_status=appointment.current_status,
        new_status='CANCELLED'
    )

    appointment.current_status = 'CANCELLED'

    notification = models.Notification(
        user_id=appointment.patient_id,
        type='APPOINTMENT_CANCELLED',
        message=(
            f"Dr. {current_user.doctor_profile.full_name} has cancelled "
            f"your appointment scheduled for "
            f"{appointment.appointment_datetime.strftime('%d %b %I:%M %p')}."
        )
    )

    db.session.add_all([history, notification])
    db.session.commit()

    flash('Appointment cancelled and patient notified.', 'info')
    return redirect(url_for('doctor.dashboard'))
