from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from datetime import datetime, date

from app import db, models
from app.forms import BookingForm, UpdateProfileForm
from . import patient_bp


# -------------------------------------------------
# Patient Dashboard
# -------------------------------------------------
@patient_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'patient':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    departments = models.Department.query.order_by(
        models.Department.name
    ).all()

    upcoming_appointments = (
        models.Appointment.query
        .filter(
            models.Appointment.patient_id == current_user.id,
            models.Appointment.status == 'BOOKED',
            models.Appointment.appointment_datetime >= datetime.now()
        )
        .order_by(models.Appointment.appointment_datetime.asc())
        .all()
    )

    return render_template(
        'patient/dashboard.html',
        title='My Dashboard',
        departments=departments,
        appointments=upcoming_appointments
    )


# -------------------------------------------------
# Appointment History
# -------------------------------------------------
@patient_bp.route('/my_history')
@login_required
def my_history():
    if current_user.role != 'patient':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    history = (
        models.Appointment.query
        .filter(
            models.Appointment.patient_id == current_user.id,
            models.Appointment.status == 'COMPLETED'
        )
        .order_by(models.Appointment.appointment_datetime.desc())
        .all()
    )

    patient_age = None
    profile = current_user.patient_profile
    if profile and profile.date_of_birth:
        today = date.today()
        patient_age = today.year - profile.date_of_birth.year - (
            (today.month, today.day) <
            (profile.date_of_birth.month, profile.date_of_birth.day)
        )

    return render_template(
        'admin/patient_history.html',
        title='My Appointment History',
        patient=current_user,
        history=history,
        patient_age=patient_age,
        back_url=url_for('patient.dashboard')
    )


# -------------------------------------------------
# Patient Profile
# -------------------------------------------------
@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.role != 'patient':
        return redirect(url_for('main.home'))

    profile = current_user.patient_profile
    form = UpdateProfileForm(obj=profile)

    if form.validate_on_submit():
        profile.full_name = form.full_name.data
        profile.date_of_birth = form.date_of_birth.data
        profile.gender = form.gender.data
        profile.contact_number = form.contact_number.data
        profile.blood_group = form.blood_group.data
        profile.allergies = form.allergies.data

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient.profile'))

    return render_template(
        'patient/profile.html',
        title='My Profile',
        form=form
    )


# -------------------------------------------------
# Department & Doctor Views
# -------------------------------------------------
@patient_bp.route('/department/<int:department_id>')
@login_required
def department_details(department_id):
    department = models.Department.query.get_or_404(department_id)
    return render_template(
        'patient/department_details.html',
        title=department.name,
        department=department
    )


@patient_bp.route('/doctor/<int:doctor_profile_id>')
@login_required
def doctor_details(doctor_profile_id):
    doctor_profile = models.DoctorProfile.query.get_or_404(doctor_profile_id)
    return render_template(
        'patient/doctor_details.html',
        title=f"Dr. {doctor_profile.full_name}",
        doctor=doctor_profile
    )


# -------------------------------------------------
# Book Appointment (Availability-Aware)
# -------------------------------------------------
@patient_bp.route('/book/<int:doctor_profile_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_profile_id):
    if current_user.role != 'patient':
        flash('Only patients can book appointments.', 'danger')
        return redirect(url_for('main.home'))

    doctor_profile = models.DoctorProfile.query.get_or_404(doctor_profile_id)
    form = BookingForm()

    if form.validate_on_submit():
        appointment_datetime = form.appointment_datetime.data

        # Prevent past bookings
        if appointment_datetime < datetime.now():
            flash('You cannot book an appointment in the past.', 'warning')
            return redirect(request.url)

        appointment_date = appointment_datetime.date()
        appointment_time = appointment_datetime.time()

        # Check doctor availability
        availability = models.Availability.query.filter(
            models.Availability.doctor_profile_id == doctor_profile.id,
            models.Availability.available_date == appointment_date,
            models.Availability.start_time <= appointment_time,
            models.Availability.end_time > appointment_time
        ).first()

        if not availability:
            flash('Doctor is not available at this time.', 'warning')
            return redirect(request.url)

        # Prevent double booking
        conflict = models.Appointment.query.filter(
            models.Appointment.doctor_id == doctor_profile.user_id,
            models.Appointment.appointment_datetime == appointment_datetime,
            models.Appointment.status == 'BOOKED'
        ).first()

        if conflict:
            flash('This time slot is already booked.', 'warning')
            return redirect(request.url)

        # Create appointment
        appointment = models.Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_profile.user_id,
            appointment_datetime=appointment_datetime,
            current_status='BOOKED'
        )
        db.session.add(appointment)

        # Status history
        db.session.add(
            models.AppointmentStatusHistory(
                appointment=appointment,
                old_status=None,
                new_status='BOOKED'
            )
        )

        # Notify doctor
        db.session.add(
            models.Notification(
                user_id=doctor_profile.user_id,
                type='NEW_APPOINTMENT',
                message=f"New appointment booked by "
                        f"{current_user.patient_profile.full_name}"
            )
        )

        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient.dashboard'))

    return render_template(
        'patient/book_appointment.html',
        title='Book Appointment',
        form=form,
        doctor=doctor_profile
    )


# -------------------------------------------------
# Cancel Appointment
# -------------------------------------------------
@patient_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    appointment = models.Appointment.query.get_or_404(appointment_id)

    if appointment.patient_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('patient.dashboard'))

    if appointment.status != 'BOOKED':
        flash('This appointment cannot be cancelled.', 'warning')
        return redirect(url_for('patient.dashboard'))

    old_status = appointment.status
    appointment.status = 'CANCELLED'

    db.session.add(
        models.AppointmentStatusHistory(
            appointment_id=appointment.id,
            old_status=old_status,
            new_status='CANCELLED'
        )
    )

    db.session.add(
        models.Notification(
            user_id=appointment.doctor_id,
            type='APPOINTMENT_CANCELLED',
            message='An appointment was cancelled by the patient.'
        )
    )

    db.session.commit()
    flash('Appointment cancelled successfully.', 'info')
    return redirect(url_for('patient.dashboard'))
