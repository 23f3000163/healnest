from flask import jsonify, render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta

from app import db, models
from app.models import DoctorProfile
from app.forms import BookingForm, UpdateProfileForm
from . import patient_bp
from app.routes.doctor_routes import get_available_slots


# -------------------------------------------------
# Patient Dashboard
# -------------------------------------------------
@patient_bp.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "patient":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.home"))

    now = datetime.now()

    # =========================
    # FETCH DEPARTMENTS
    # =========================
    departments = models.Department.query.order_by(
        models.Department.name.asc()
    ).all()

    # =========================
    # UPCOMING APPOINTMENTS
    # =========================
    upcoming_appointments = (
        models.Appointment.query
        .filter(
            models.Appointment.patient_id == current_user.id,
            models.Appointment.status == "BOOKED",
            models.Appointment.appointment_datetime >= now
        )
        .order_by(models.Appointment.appointment_datetime.asc())
        .all()
    )

    # =========================
    # PAST APPOINTMENTS
    # =========================
    past_appointments = (
        models.Appointment.query
        .filter(
            models.Appointment.patient_id == current_user.id,
            models.Appointment.status.in_(["COMPLETED", "CANCELLED"])
        )
        .order_by(models.Appointment.appointment_datetime.desc())
        .all()
    )

    return render_template(
        "patient/dashboard.html",
        departments=departments,  # ✅ THIS WAS MISSING
        upcoming_appointments=upcoming_appointments,
        past_appointments=past_appointments,
        today=date.today()
    )




# -------------------------------------------------
# Appointment History
# -------------------------------------------------
@patient_bp.route('/my_history')
@login_required
def my_history():

    # Ensure only patients can access
    if current_user.role != 'patient':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    # Get completed appointments only
    history = (
        models.Appointment.query
        .filter(
            models.Appointment.patient_id == current_user.id,
            models.Appointment.status == 'COMPLETED'
        )
        .order_by(models.Appointment.appointment_datetime.desc())
        .all()
    )

    # Ensure patient profile exists
    profile = current_user.patient_profile
    if not profile:
        abort(404)

    # Calculate age safely
    patient_age = None
    if profile.date_of_birth:
        today = date.today()
        patient_age = today.year - profile.date_of_birth.year - (
            (today.month, today.day) <
            (profile.date_of_birth.month, profile.date_of_birth.day)
        )

    return render_template(
        'shared/patient_history.html',
        title='My Appointment History',
        patient=current_user,      # Used in template
        history=history,           # Appointment list
        patient_age=patient_age,   # Age display
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

    profile = current_user.patient_profile or abort(404)
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
# Book Appointment (STABLE VERSION)
# -------------------------------------------------
@patient_bp.route('/book/<int:doctor_profile_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_profile_id):

    if current_user.role != 'patient':
        flash('Only patients can book appointments.', 'danger')
        return redirect(url_for('main.home'))

    doctor_profile = models.DoctorProfile.query.get_or_404(doctor_profile_id)

    if request.method == "POST":

        slot_value = request.form.get("selected_slot")

        if not slot_value:
            flash("Please select a valid time slot.", "warning")
            return redirect(request.url)

        try:
            appointment_datetime = datetime.fromisoformat(slot_value)
        except ValueError:
            flash("Invalid time slot selected.", "danger")
            return redirect(request.url)

        if appointment_datetime < datetime.now():
            flash("You cannot book a past time slot.", "warning")
            return redirect(request.url)

        conflict = models.Appointment.query.filter_by(
            doctor_id=doctor_profile.user_id,
            appointment_datetime=appointment_datetime,
            status="BOOKED"
        ).first()

        if conflict:
            flash("This slot was just booked by another patient.", "danger")
            return redirect(request.url)

        appointment = models.Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_profile.user_id,
            appointment_datetime=appointment_datetime,
            status="BOOKED"
        )

        db.session.add(appointment)
        db.session.commit()

        flash("Appointment booked successfully!", "success")
        return redirect(url_for("patient.dashboard"))

    return render_template(
        "patient/book_appointment.html",
        doctor=doctor_profile,
        min_date=date.today().isoformat(),
        max_date=(date.today() + timedelta(days=30)).isoformat()
    )



# -------------------------------------------------
# Slot API
# -------------------------------------------------
@patient_bp.route("/doctor/<int:doctor_id>/slots")
@login_required
def get_doctor_slots(doctor_id):

    date_str = request.args.get("date")
    if not date_str:
        abort(400)

    try:
        selected_date = date.fromisoformat(date_str)
    except ValueError:
        abort(400)

    doctor = DoctorProfile.query.get_or_404(doctor_id)

    slots = get_available_slots(doctor, selected_date)

    return jsonify({
        "slots": [
            {
                "value": slot["value"],
                "label": slot["label"],
                "booked": slot["booked"]
            }
            for slot in slots
        ]
    })
# -------------------------------------------------
# Cancel Appointment
# -------------------------------------------------
@patient_bp.route("/appointment/<int:appointment_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    if current_user.role != "patient":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("main.home"))

    appointment = models.Appointment.query.get_or_404(appointment_id)

    # Ownership check
    if appointment.patient_id != current_user.id:
        abort(403)

    # Time check — cannot cancel past appointments
    if appointment.appointment_datetime < datetime.now():
        flash("You cannot cancel a past appointment.", "warning")
        return redirect(url_for("patient.dashboard"))

    if appointment.status != "BOOKED":
        flash("This appointment cannot be cancelled.", "warning")
        return redirect(url_for("patient.dashboard"))

    # Status update
    appointment.status = "CANCELLED"

    # Status history
    db.session.add(
        models.AppointmentStatusHistory(
            appointment=appointment,
            old_status="BOOKED",
            new_status="CANCELLED"
        )
    )

    # Notify doctor
    db.session.add(
        models.Notification(
            user_id=appointment.doctor_id,
            type="APPOINTMENT_CANCELLED",
            message=f"Appointment cancelled by {current_user.patient_profile.full_name}"
        )
    )

    db.session.commit()

    flash("Appointment cancelled successfully.", "success")
    return redirect(url_for("patient.dashboard"))
