from datetime import datetime, date, timedelta, time

from flask import (
    render_template,
    flash,
    redirect,
    url_for,
    request,
    abort
)

from flask_login import login_required, current_user

from app import db, models
from app.models import Availability, DoctorProfile
from app.forms import TreatmentForm, DoctorUpdateProfileForm, ChangePasswordForm
from app.routes.decorators import doctor_required
from collections import defaultdict

from . import doctor_bp


TIME_SLOTS = {
    "morning": (time(8, 0), time(12, 0)),
    "evening": (time(16, 0), time(21, 0)),
}
SLOT_DURATION = timedelta(minutes=30)

# -------------------------------------------------
# Doctor Dashboard
# -------------------------------------------------
@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'doctor':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    now = datetime.now()
    today = date.today()

    appointments = (
        models.Appointment.query
        .filter(
            models.Appointment.doctor_id == current_user.id,
            models.Appointment.status == 'BOOKED',
            models.Appointment.appointment_datetime >= now
        )
        .order_by(models.Appointment.appointment_datetime.asc())
        .all()
    )

    # Group appointments by date
    grouped_appointments = defaultdict(list)
    for appt in appointments:
        appt_date = appt.appointment_datetime.date()
        grouped_appointments[appt_date].append(appt)

    # Separate buckets for UI clarity
    today_appointments = grouped_appointments.get(today, [])
    tomorrow_appointments = grouped_appointments.get(today.replace(day=today.day + 1), [])

    future_appointments = {
        d: appts
        for d, appts in grouped_appointments.items()
        if d > today.replace(day=today.day + 1)
    }

    return render_template(
        'doctor/dashboard.html',
        title='Doctor Dashboard',
        today_appointments=today_appointments,
        tomorrow_appointments=tomorrow_appointments,
        future_appointments=future_appointments
    )

# -------------------------------------------------
# Treat Patient
# -------------------------------------------------
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

    if appointment.status != 'BOOKED':
        flash('This appointment is not active.', 'warning')
        return redirect(url_for('doctor.dashboard'))

    patient_history = (
        models.Appointment.query
        .filter(
            models.Appointment.patient_id == appointment.patient_id,
            models.Appointment.status == 'COMPLETED'
        )
        .order_by(models.Appointment.appointment_datetime.desc())
        .all()
    )

    form = TreatmentForm()

    if form.validate_on_submit():
        db.session.add(
            models.Treatment(
                appointment_id=appointment.id,
                visit_type=form.visit_type.data,
                tests_done=form.tests_done.data,
                diagnosis=form.diagnosis.data,
                prescription=form.prescription.data
            )
        )

        old_status = appointment.status
        appointment.status = 'COMPLETED'

        db.session.add(
            models.AppointmentStatusHistory(
                appointment_id=appointment.id,
                old_status=old_status,
                new_status='COMPLETED'
            )
        )

        db.session.add(
            models.Notification(
                user_id=appointment.patient_id,
                type='APPOINTMENT_COMPLETED',
                message=f"Dr. {current_user.doctor_profile.full_name} has completed your appointment."
            )
        )

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



# -------------------------------------------------
# Doctor Profile
# -------------------------------------------------
@doctor_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.role != 'doctor':
        return redirect(url_for('main.home'))

    profile = current_user.doctor_profile or abort(404)
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


# -------------------------------------------------
# Cancel Appointment
# -------------------------------------------------
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

    if appointment.status != 'BOOKED':
        flash('This appointment cannot be cancelled.', 'warning')
        return redirect(url_for('doctor.dashboard'))

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
            user_id=appointment.patient_id,
            type='APPOINTMENT_CANCELLED',
            message=(
                f"Dr. {current_user.doctor_profile.full_name} has cancelled "
                f"your appointment scheduled for "
                f"{appointment.appointment_datetime.strftime('%d %b %Y %I:%M %p')}."
            )
        )
    )

    db.session.commit()
    flash('Appointment cancelled and patient notified.', 'info')
    return redirect(url_for('doctor.dashboard'))

# -------------------------------------------------
# Manage Availability
# -------------------------------------------------

from datetime import date, timedelta, time
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models import Availability, DoctorProfile
from app.routes.decorators import doctor_required


@doctor_required
@login_required
def manage_availability():
    doctor = DoctorProfile.query.filter_by(user_id=current_user.id).first()

    if not doctor:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("doctor.dashboard"))

    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]

    # Time slot definitions (single source of truth)
    TIME_SLOTS = {
        "morning": (time(8, 0), time(12, 0)),
        "evening": (time(16, 0), time(21, 0)),
    }

    # Fetch existing availability for the next 7 days
    existing = Availability.query.filter(
        Availability.doctor_profile_id == doctor.id,
        Availability.available_date.in_(days)
    ).all()

    # Convert DB rows → checkbox keys
    saved_slots = []
    for a in existing:
        for label, (start, _) in TIME_SLOTS.items():
            if a.start_time == start:
                saved_slots.append(f"{a.available_date.isoformat()}_{label}")

    if request.method == "POST":
        slots = request.form.getlist("slots")

        # Remove only availability for these 7 days
        Availability.query.filter(
            Availability.doctor_profile_id == doctor.id,
            Availability.available_date.in_(days)
        ).delete(synchronize_session=False)

        for slot in slots:
            try:
                date_str, session = slot.split("_")
                selected_date = date.fromisoformat(date_str)
            except ValueError:
                continue

            start, end = TIME_SLOTS.get(session, (None, None))
            if not start:
                continue

            db.session.add(
                Availability(
                    doctor_profile_id=doctor.id,
                    available_date=selected_date,
                    start_time=start,
                    end_time=end,
                )
            )

        db.session.commit()
        flash("Availability saved successfully.", "success")
        return redirect(url_for("doctor.manage_availability"))

    return render_template(
        "doctor/availability.html",
        days=days,
        saved_slots=saved_slots,
    )



@doctor_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    # 🔐 Only doctors can access
    if current_user.role != "doctor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.home"))

    form = ChangePasswordForm()

    if form.validate_on_submit():

        # Verify current password
        if not current_user.verify_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("doctor.change_password"))

        # Set new password
        current_user.set_password(form.new_password.data)
        current_user.is_temp_password = False

        db.session.commit()

        flash("Password updated successfully.", "success")
        return redirect(url_for("doctor.dashboard"))

    return render_template(
        "doctor/change_password.html",
        title="Change Password",
        form=form
    )

def get_available_slots(doctor, selected_date):
    availability_rules = Availability.query.filter_by(
        doctor_profile_id=doctor.id,
        available_date=selected_date
    ).all()

    all_slots = []
    for rule in availability_rules:
        all_slots.extend(
            generate_slots_for_range(
                rule.available_date,
                rule.start_time,
                rule.end_time
            )
        )

    booked_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_datetime.in_(all_slots),
        Appointment.status == "BOOKED"
    ).all()

    booked_slots = {appt.appointment_datetime for appt in booked_appointments}

    now = datetime.now()

    available_slots = [
        slot for slot in all_slots
        if slot not in booked_slots and slot > now
    ]

    return sorted(available_slots)


def generate_slots_for_range(date, start_time, end_time):
    slots = []
    current = datetime.combine(date, start_time)
    end_dt = datetime.combine(date, end_time)

    while current + SLOT_DURATION <= end_dt:
        slots.append(current)
        current += SLOT_DURATION

    return slots


def get_available_slots(doctor, selected_date):
    availability_rules = Availability.query.filter_by(
        doctor_profile_id=doctor.id,
        available_date=selected_date
    ).all()

    all_slots = []
    for rule in availability_rules:
        all_slots.extend(
            generate_slots_for_range(
                rule.available_date,
                rule.start_time,
                rule.end_time
            )
        )

    booked_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_datetime.in_(all_slots),
        Appointment.status == "BOOKED"
    ).all()

    booked_slots = {appt.appointment_datetime for appt in booked_appointments}

    now = datetime.now()

    available_slots = [
        slot for slot in all_slots
        if slot not in booked_slots and slot > now
    ]

    return sorted(available_slots)

